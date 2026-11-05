"""Public CI/CD observability portal generator for GitHub Pages.

Builds a self-contained static HTML/Markdown/JSON observability portal from
already-generated IJT workflow summaries (`ci_run_summary.py` and
`system_tests_run_summary.py`), Test Client specification reports (`report.html`
and `report.xlsx`), Schema-v1 timing bundles (`timing-latest.json`), JUnit XML
artifacts, and per-job GitHub Actions console logs.

Security & Governance Invariants:
- Strictly allowlists `ci` and `integration` workflows and hard-blocks
  `internal-private-envelope.yml` so private submodule telemetry never leaks.
- Uses `reporting._http.https_only_opener()` exclusively for all network I/O.
- Sanitizes all console logs against token, credential, and secret patterns
  before writing any file to disk.
- Enforces bounded retention (default: 50 `main` runs + protected release tags,
  capped at 600 MB) to pair with a single-commit orphan branch (`public-reports-state`).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import re
import shutil
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from reporting._http import https_only_opener

ALLOWED_WORKFLOW_SLUGS: frozenset[str] = frozenset({"ci", "integration"})

FORBIDDEN_WORKFLOW_IDENTIFIERS: frozenset[str] = frozenset(
    {
        "internal-private-envelope",
        "internal-private-envelope.yml",
        "private-envelope",
        "internal — private envelope validation",
    }
)

WORKFLOW_LABELS: dict[str, str] = {
    "ci": "CI — Unit, Static, and Smoke Gates",
    "integration": "System Tests — Live OPC UA, Browser, Docker, Specification Testing",
}

DEFAULT_MAX_RUNS = 50
DEFAULT_MAX_TOTAL_MB = 600

# ── Log sanitization patterns ─────────────────────────────────────────────────
_GITHUB_TOKEN_RE = re.compile(
    r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,255}|github_pat_[A-Za-z0-9_]{20,255})\b"
)
_EXTRAHEADER_RE = re.compile(
    r"(?i)(extraheader\s*=\s*AUTHORIZATION:\s*(?:basic|bearer)\s+)[A-Za-z0-9+/=_-]+"
)
_AUTH_HEADER_RE = re.compile(r"(?i)(authorization\s*[:=]\s*(?:bearer|token|basic)\s+)[^\s\"'\r\n]+")
_JWT_TOKEN_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")
_URL_QUERY_SECRET_RE = re.compile(r"(?i)([?&](?:sig|token|access_token|client_secret)=)[^&\s\"']+")
_URL_CREDENTIALS_RE = re.compile(r"https?://[^/\s:@]+:[^/\s@]+@")
_AWS_ACCESS_KEY_RE = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
_PRIVATE_KEY_BLOCK_RE = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z0-9 ]*PRIVATE KEY-----"
)
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
_LOG_TIMESTAMP_PREFIX_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z)\s?(?P<rest>.*)$"
)
_SAFE_SLUG_RE = re.compile(r"[^a-z0-9]+")
_SAFE_RUN_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_FAILURE_CONCLUSIONS: frozenset[str] = frozenset(
    {"failure", "timed_out", "action_required", "startup_failure"}
)


@dataclass
class StepLogSlice:
    """A single step's console log slice and metadata within a job."""

    number: int
    name: str
    conclusion: str
    duration_seconds: float
    lines: list[str] = field(default_factory=list)


@dataclass
class JobLogBundle:
    """Harvested metadata and sanitized console logs for a single workflow job."""

    job_id: int
    name: str
    status: str
    conclusion: str
    duration_seconds: float
    html_url: str
    raw_log_relpath: str
    steps: list[StepLogSlice] = field(default_factory=list)
    line_count: int = 0


@dataclass
class RunPortalMetadata:
    """Metadata for a single published workflow run in `runs-index.json`."""

    run_id: str
    run_number: int
    workflow_slug: str
    workflow_name: str
    conclusion: str
    commit_sha: str
    branch: str
    event_name: str
    created_at: str
    html_url: str
    is_release: bool = False
    has_spec_html: bool = False
    has_spec_xlsx: bool = False
    has_timing_json: bool = False
    has_junit_zip: bool = False
    job_count: int = 0
    failed_job_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "run_number": self.run_number,
            "workflow_slug": self.workflow_slug,
            "workflow_name": self.workflow_name,
            "conclusion": self.conclusion,
            "commit_sha": self.commit_sha,
            "branch": self.branch,
            "event_name": self.event_name,
            "created_at": self.created_at,
            "html_url": self.html_url,
            "is_release": self.is_release,
            "has_spec_html": self.has_spec_html,
            "has_spec_xlsx": self.has_spec_xlsx,
            "has_timing_json": self.has_timing_json,
            "has_junit_zip": self.has_junit_zip,
            "job_count": self.job_count,
            "failed_job_count": self.failed_job_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunPortalMetadata:
        return cls(
            run_id=str(data.get("run_id", "")),
            run_number=int(data.get("run_number", 0) or 0),
            workflow_slug=str(data.get("workflow_slug", "ci")),
            workflow_name=str(data.get("workflow_name", "")),
            conclusion=str(data.get("conclusion", "unknown")),
            commit_sha=str(data.get("commit_sha", "")),
            branch=str(data.get("branch", "main")),
            event_name=str(data.get("event_name", "push")),
            created_at=str(data.get("created_at", "")),
            html_url=str(data.get("html_url", "")),
            is_release=bool(data.get("is_release", False)),
            has_spec_html=bool(data.get("has_spec_html", False)),
            has_spec_xlsx=bool(data.get("has_spec_xlsx", False)),
            has_timing_json=bool(data.get("has_timing_json", False)),
            has_junit_zip=bool(data.get("has_junit_zip", False)),
            job_count=int(data.get("job_count", 0) or 0),
            failed_job_count=int(data.get("failed_job_count", 0) or 0),
        )


def validate_public_workflow(workflow_slug: str, workflow_name: str = "") -> str:
    """Validate that a workflow is allowed to publish to the public portal.

    Raises ValueError if the workflow is `internal-private-envelope` or is not
    in the explicit allowlist (`ci`, `integration`).
    """
    slug_norm = workflow_slug.strip().lower()
    name_norm = workflow_name.strip().lower()
    for forbidden in FORBIDDEN_WORKFLOW_IDENTIFIERS:
        if forbidden in slug_norm or (name_norm and forbidden in name_norm):
            raise ValueError(
                f"Refusing to publish forbidden private workflow: "
                f"slug={workflow_slug!r}, name={workflow_name!r}"
            )
    if slug_norm not in ALLOWED_WORKFLOW_SLUGS:
        raise ValueError(
            f"Workflow slug {workflow_slug!r} is not in ALLOWED_WORKFLOW_SLUGS "
            f"({sorted(ALLOWED_WORKFLOW_SLUGS)})"
        )
    return slug_norm


def sanitize_log_text(raw_text: str) -> str:
    """Strip ANSI escape codes and redact credentials/tokens from console logs."""
    cleaned = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = _ANSI_ESCAPE_RE.sub("", cleaned)
    cleaned = _PRIVATE_KEY_BLOCK_RE.sub("[REDACTED_PRIVATE_KEY]", cleaned)
    cleaned = _GITHUB_TOKEN_RE.sub("[REDACTED_GITHUB_TOKEN]", cleaned)
    cleaned = _EXTRAHEADER_RE.sub(r"\1[REDACTED_AUTH]", cleaned)
    cleaned = _AUTH_HEADER_RE.sub(r"\1[REDACTED_AUTH]", cleaned)
    cleaned = _JWT_TOKEN_RE.sub("[REDACTED_JWT]", cleaned)
    cleaned = _URL_QUERY_SECRET_RE.sub(r"\1[REDACTED_SECRET]", cleaned)
    cleaned = _URL_CREDENTIALS_RE.sub("https://[REDACTED_CREDENTIALS]@", cleaned)
    cleaned = _AWS_ACCESS_KEY_RE.sub("[REDACTED_AWS_KEY]", cleaned)
    return cleaned


def _parse_iso_utc(value: str | None) -> dt.datetime | None:
    if not value or not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    match = re.match(
        r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\.(\d{6})\d*([+-]\d{2}:\d{2})$",
        text,
    )
    if match:
        text = f"{match.group(1)}.{match.group(2)}{match.group(3)}"
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=dt.UTC)
    return parsed.astimezone(dt.UTC)


def _duration_seconds(started_at: str | None, completed_at: str | None) -> float:
    start_dt = _parse_iso_utc(started_at)
    end_dt = _parse_iso_utc(completed_at)
    if start_dt is None or end_dt is None:
        return 0.0
    return max(0.0, round((end_dt - start_dt).total_seconds(), 1))


def _slugify(value: str) -> str:
    slug = _SAFE_SLUG_RE.sub("-", value.lower()).strip("-")
    return slug[:60] or "job"


def slice_job_log_into_steps(
    sanitized_log: str,
    steps_meta: list[dict[str, Any]],
) -> list[StepLogSlice]:
    """Slice a sanitized GitHub Actions job log into per-step sections."""
    raw_lines = sanitized_log.splitlines()
    if not steps_meta:
        return [
            StepLogSlice(
                number=1,
                name="Console Output",
                conclusion="neutral",
                duration_seconds=0.0,
                lines=raw_lines,
            )
        ]

    slices: list[StepLogSlice] = []
    step_windows: list[tuple[dt.datetime | None, dt.datetime | None, StepLogSlice]] = []
    for idx, step in enumerate(steps_meta, start=1):
        number = int(step.get("number", idx) or idx)
        name = str(step.get("name") or f"Step {number}")
        conclusion = str(step.get("conclusion") or step.get("status") or "neutral")
        dur = _duration_seconds(step.get("started_at"), step.get("completed_at"))
        step_slice = StepLogSlice(
            number=number,
            name=name,
            conclusion=conclusion,
            duration_seconds=dur,
            lines=[],
        )
        slices.append(step_slice)
        step_windows.append(
            (
                _parse_iso_utc(step.get("started_at")),
                _parse_iso_utc(step.get("completed_at")),
                step_slice,
            )
        )

    current_idx = 0
    unassigned: list[str] = []
    for line in raw_lines:
        ts_match = _LOG_TIMESTAMP_PREFIX_RE.match(line)
        line_ts = _parse_iso_utc(ts_match.group("ts")) if ts_match else None
        display_line = ts_match.group("rest") if ts_match else line

        if line_ts is not None:
            while current_idx + 1 < len(step_windows):
                _, cur_end, _ = step_windows[current_idx]
                next_start, _, _ = step_windows[current_idx + 1]
                past_end = cur_end is not None and line_ts > cur_end
                past_next = next_start is not None and line_ts >= next_start and cur_end is None
                if past_end or past_next:
                    current_idx += 1
                else:
                    break
            step_windows[current_idx][2].lines.append(display_line)
        else:
            if slices:
                slices[current_idx].lines.append(display_line)
            else:
                unassigned.append(display_line)

    if unassigned and slices:
        slices[0].lines = unassigned + slices[0].lines
    return slices


class _HttpsOnlyRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Follow redirects over HTTPS only; strip Authorization when the host changes."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        parsed = urllib.parse.urlparse(newurl)
        if parsed.scheme != "https" or not parsed.netloc:
            raise urllib.error.URLError(f"Refusing redirect to non-HTTPS URL: {newurl!r}")
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is None:
            return None
        orig_host = urllib.parse.urlparse(req.full_url).netloc.lower()
        if parsed.netloc.lower() != orig_host:
            for hdr_dict in (redirected.headers, redirected.unredirected_hdrs):
                for key in list(hdr_dict.keys()):
                    if key.lower() == "authorization":
                        del hdr_dict[key]
        return redirected


def _https_get_bytes(url: str, headers: dict[str, str], timeout: int = 30) -> bytes:
    """Perform an HTTPS-only GET request (following HTTPS redirects) and return bytes."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"Refusing non-HTTPS URL: {url!r}")

    opener = https_only_opener()
    opener.add_handler(_HttpsOnlyRedirectHandler())
    req = urllib.request.Request(url, headers=headers, method="GET")
    with opener.open(req, timeout=timeout) as resp:
        data: bytes = resp.read()
        return data


def fetch_run_jobs_and_logs(
    *,
    api_url: str,
    repository: str,
    run_id: str,
    token: str,
    run_out_dir: Path,
    exclude_job_names: frozenset[str] = frozenset(
        {"🌐 Publish Public Report", "publish-public-report"}
    ),
) -> list[JobLogBundle]:
    """Fetch all completed jobs and their raw console logs for a workflow run."""
    logs_dir = run_out_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    if not api_url.startswith("https://") or not repository or not run_id or not token:
        return []

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ijt-public-portal/1.0",
    }
    jobs_url = f"{api_url.rstrip('/')}/repos/{repository}/actions/runs/{run_id}/jobs?per_page=100"
    try:
        payload_bytes = _https_get_bytes(jobs_url, headers=headers, timeout=30)
        jobs_payload = json.loads(payload_bytes.decode("utf-8", errors="replace"))
    except (OSError, ValueError, urllib.error.URLError):
        return []

    raw_jobs = jobs_payload.get("jobs", [])
    if not isinstance(raw_jobs, list):
        return []

    bundles: list[JobLogBundle] = []
    for job in raw_jobs:
        if not isinstance(job, dict):
            continue
        job_name = str(job.get("name") or "")
        job_name_lower = job_name.lower()
        if (
            job_name in exclude_job_names
            or "publish public" in job_name_lower
            or "publish-public-report" in job_name_lower
        ):
            continue
        status = str(job.get("status") or "")
        if status != "completed":
            continue

        job_id = int(job.get("id", 0) or 0)
        if job_id <= 0:
            continue

        conclusion = str(job.get("conclusion") or "neutral")
        duration = _duration_seconds(job.get("started_at"), job.get("completed_at"))
        html_url = str(job.get("html_url") or "")
        log_filename = f"job-{job_id}-{_slugify(job_name)}.log.txt"
        log_relpath = f"logs/{log_filename}"
        log_path = run_out_dir / log_relpath

        log_url = f"{api_url.rstrip('/')}/repos/{repository}/actions/jobs/{job_id}/logs"
        sanitized_log = ""
        try:
            raw_log_bytes = _https_get_bytes(log_url, headers=headers, timeout=45)
            sanitized_log = sanitize_log_text(raw_log_bytes.decode("utf-8", errors="replace"))
        except (OSError, ValueError, urllib.error.URLError) as exc:
            sanitized_log = (
                f"[Console log unavailable for job {job_name!r} (id={job_id}): "
                f"{sanitize_log_text(str(exc))}]\n"
            )

        log_path.write_text(sanitized_log, encoding="utf-8", newline="\n")
        raw_steps = job.get("steps")
        steps_meta: list[dict[str, Any]] = (
            [s for s in raw_steps if isinstance(s, dict)] if isinstance(raw_steps, list) else []
        )
        step_slices = slice_job_log_into_steps(sanitized_log, steps_meta)
        bundles.append(
            JobLogBundle(
                job_id=job_id,
                name=job_name,
                status=status,
                conclusion=conclusion,
                duration_seconds=duration,
                html_url=html_url,
                raw_log_relpath=log_relpath,
                steps=step_slices,
                line_count=len(sanitized_log.splitlines()),
            )
        )

    def _sort_key(item: JobLogBundle) -> tuple[int, str]:
        priority = 0 if item.conclusion in (_FAILURE_CONCLUSIONS | {"cancelled"}) else 1
        return (priority, item.name.lower())

    bundles.sort(key=_sort_key)
    return bundles


def harvest_run_artifacts(
    *,
    artifacts_dir: Path | None,
    summary_file: Path | None,
    timing_dir: Path | None,
    run_out_dir: Path,
) -> dict[str, bool]:
    """Copy summary.md, timing.json, report.html, report.xlsx, and JUnit XMLs into run_out_dir."""
    run_out_dir.mkdir(parents=True, exist_ok=True)
    capabilities = {
        "has_summary_md": False,
        "has_timing_json": False,
        "has_spec_html": False,
        "has_spec_xlsx": False,
        "has_junit_zip": False,
    }

    base_resolved = artifacts_dir.resolve() if (artifacts_dir and artifacts_dir.is_dir()) else None

    def _safe_artifact_file(p: Path) -> bool:
        if base_resolved is None:
            return False
        return p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(base_resolved)

    def _nonempty(p: Path) -> bool:
        try:
            return p.is_file() and not p.is_symlink() and p.stat().st_size > 0
        except OSError:
            return False

    summary_candidates: list[Path] = []
    if summary_file is not None and _nonempty(summary_file):
        summary_candidates.append(summary_file)
    if timing_dir is not None and _nonempty(timing_dir / "summary.md"):
        summary_candidates.append(timing_dir / "summary.md")
    if artifacts_dir is not None and artifacts_dir.is_dir():
        for timing_sub in sorted(artifacts_dir.glob("timing-*/summary.md")):
            if _safe_artifact_file(timing_sub) and _nonempty(timing_sub):
                summary_candidates.append(timing_sub)
        for direct_sub in sorted(artifacts_dir.glob("summary.md")):
            if _safe_artifact_file(direct_sub) and _nonempty(direct_sub):
                summary_candidates.append(direct_sub)

    if summary_candidates:
        shutil.copyfile(summary_candidates[0], run_out_dir / "summary.md")
        capabilities["has_summary_md"] = True

    timing_candidates: list[Path] = []
    if timing_dir is not None:
        td_timing = timing_dir / "timing-latest.json"
        if td_timing.is_file() and not td_timing.is_symlink():
            timing_candidates.append(td_timing)
    if artifacts_dir is not None and artifacts_dir.is_dir():
        for wf_timing in sorted(artifacts_dir.glob("timing-*/timing-latest.json")):
            if _safe_artifact_file(wf_timing):
                timing_candidates.append(wf_timing)
        for direct_timing in sorted(artifacts_dir.glob("timing-latest.json")):
            if _safe_artifact_file(direct_timing):
                timing_candidates.append(direct_timing)
        for fallback_timing in sorted(artifacts_dir.rglob("timing-latest.json")):
            if _safe_artifact_file(fallback_timing) and fallback_timing not in timing_candidates:
                timing_candidates.append(fallback_timing)

    if timing_candidates:
        shutil.copyfile(timing_candidates[0], run_out_dir / "timing.json")
        capabilities["has_timing_json"] = True

    if artifacts_dir is not None and artifacts_dir.is_dir():
        html_candidates: list[Path] = []
        for pattern in ("results-testclient/report.html", "report.html"):
            for p in sorted(artifacts_dir.glob(pattern)):
                if _safe_artifact_file(p) and p not in html_candidates:
                    html_candidates.append(p)
        for p in sorted(artifacts_dir.rglob("report.html")):
            if _safe_artifact_file(p) and p not in html_candidates:
                html_candidates.append(p)
        if html_candidates:
            shutil.copyfile(html_candidates[0], run_out_dir / "report.html")
            capabilities["has_spec_html"] = True

        xlsx_candidates: list[Path] = []
        for pattern in ("results-testclient/report.xlsx", "report.xlsx"):
            for p in sorted(artifacts_dir.glob(pattern)):
                if _safe_artifact_file(p) and p not in xlsx_candidates:
                    xlsx_candidates.append(p)
        for p in sorted(artifacts_dir.rglob("report.xlsx")):
            if _safe_artifact_file(p) and p not in xlsx_candidates:
                xlsx_candidates.append(p)
        if xlsx_candidates:
            shutil.copyfile(xlsx_candidates[0], run_out_dir / "report.xlsx")
            capabilities["has_spec_xlsx"] = True

        xml_files = [p for p in sorted(artifacts_dir.rglob("*.xml")) if _safe_artifact_file(p)]
        if xml_files:
            zip_path = run_out_dir / "junit-and-coverage.zip"
            with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for xml_file in xml_files:
                    arcname = xml_file.relative_to(artifacts_dir).as_posix()
                    zf.write(xml_file, arcname=arcname)
            capabilities["has_junit_zip"] = True

    return capabilities


# ── Pure-Python GFM Markdown-to-HTML Renderer ─────────────────────────────────
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
_ITALIC_RE = re.compile(r"(?<![A-Za-z0-9\\])_([^_\n]+?)_(?![A-Za-z0-9])")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_ANCHOR_TAG_RE = re.compile(r'^<a\s+id="([A-Za-z0-9_.-]+)"\s*></a>$')
_DETAILS_SUMMARY_RE = re.compile(
    r"^<details(?P<open>\s+open)?\s*>\s*<summary>(?P<inner>.*)</summary>$",
    re.IGNORECASE,
)
_DETAILS_OPEN_RE = re.compile(r"^<details(?P<open>\s+open)?\s*>$", re.IGNORECASE)
_REPO_BLOB_BASE = "https://github.com/umati/UA-for-Industrial-Joining-Technologies/blob/main/"


def _render_inline_markdown(text: str) -> str:
    """Render inline Markdown (code spans, bold, italics, links, and safe HTML entities/breaks)."""
    code_placeholders: list[str] = []

    def _stash_code(match: re.Match[str]) -> str:
        idx = len(code_placeholders)
        raw_code = html.unescape(match.group(1))
        code_placeholders.append(f"<code>{html.escape(raw_code, quote=True)}</code>")
        return f"\x00CODE_{idx}\x00"

    work = _INLINE_CODE_RE.sub(_stash_code, text)
    work = re.sub(r"<br\s*/?>", "\x00BR\x00", work, flags=re.IGNORECASE)
    work = re.sub(
        r"<b>(.*?)</b>",
        "\x00B_OPEN\x00\\1\x00B_CLOSE\x00",
        work,
        flags=re.IGNORECASE,
    )
    work = work.replace("&nbsp;", "\x00NBSP\x00").replace("&bull;", "\x00BULL\x00")
    work = work.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    escaped = html.escape(work, quote=True)

    link_opens: list[str] = []

    def _replace_link(match: re.Match[str]) -> str:
        label = match.group(1)
        href = html.unescape(match.group(2)).strip()
        if href.startswith("//"):
            return label
        allowed = href.startswith(("https://", "http://", "#", "./", "../", "/"))
        if not allowed and re.fullmatch(r"[A-Za-z0-9_./-]+", href):
            if href.startswith(("OPC_UA_", "docs/", "README.md", ".github/")):
                href = f"{_REPO_BLOB_BASE}{href}"
            allowed = True
        if allowed:
            idx = len(link_opens)
            safe_href = html.escape(href, quote=True)
            link_opens.append(f'<a href="{safe_href}">')
            return f"\x00LINK_OPEN_{idx}\x00{label}\x00LINK_CLOSE\x00"
        return label

    escaped = _LINK_RE.sub(_replace_link, escaped)
    escaped = _BOLD_RE.sub(r"<strong>\1</strong>", escaped)
    escaped = _ITALIC_RE.sub(r"<em>\1</em>", escaped)
    escaped = (
        escaped.replace("\x00B_OPEN\x00", "<strong>")
        .replace("\x00B_CLOSE\x00", "</strong>")
        .replace("\x00NBSP\x00", "&nbsp;")
        .replace("\x00BULL\x00", "&bull;")
        .replace("\x00BR\x00", "<br/>")
        .replace("\x00LINK_CLOSE\x00", "</a>")
    )
    for idx, link_open in enumerate(link_opens):
        escaped = escaped.replace(f"\x00LINK_OPEN_{idx}\x00", link_open)
    for idx, code_html in enumerate(code_placeholders):
        escaped = escaped.replace(f"\x00CODE_{idx}\x00", code_html)
    return escaped


def render_markdown_to_html(md_text: str) -> str:
    """Render IJT GitHub-Flavored Markdown summaries into clean, XSS-safe HTML."""
    lines = md_text.replace("\r\n", "\n").splitlines()
    out: list[str] = []
    in_code_block = False
    in_table = False
    in_list = False

    def _close_blocks() -> None:
        nonlocal in_table, in_list
        if in_table:
            out.append("</tbody></table></div>")
            in_table = False
        if in_list:
            out.append("</ul>")
            in_list = False

    i = 0
    while i < len(lines):
        raw_line = lines[i]
        stripped = raw_line.strip()

        if stripped.startswith("```"):
            _close_blocks()
            if not in_code_block:
                in_code_block = True
                out.append('<pre class="code-block"><code>')
            else:
                in_code_block = False
                out.append("</code></pre>")
            i += 1
            continue

        if in_code_block:
            out.append(html.escape(raw_line))
            i += 1
            continue

        if not stripped:
            _close_blocks()
            i += 1
            continue

        anchor_match = _ANCHOR_TAG_RE.match(stripped)
        if anchor_match:
            _close_blocks()
            out.append(f'<a id="{html.escape(anchor_match.group(1), quote=True)}"></a>')
            i += 1
            continue

        details_sum_match = _DETAILS_SUMMARY_RE.match(stripped)
        if details_sum_match:
            _close_blocks()
            open_attr = " open" if details_sum_match.group("open") else ""
            inner = details_sum_match.group("inner")
            out.append(f"<details{open_attr}><summary>{_render_inline_markdown(inner)}</summary>")
            i += 1
            continue

        details_open_match = _DETAILS_OPEN_RE.match(stripped)
        if details_open_match:
            _close_blocks()
            open_attr = " open" if details_open_match.group("open") else ""
            out.append(f"<details{open_attr}>")
            i += 1
            continue

        if stripped.lower() == "</details>":
            _close_blocks()
            out.append("</details>")
            i += 1
            continue

        if stripped.startswith("<summary>") and stripped.endswith("</summary>"):
            _close_blocks()
            inner = stripped[len("<summary>") : -len("</summary>")]
            out.append(f"<summary>{_render_inline_markdown(inner)}</summary>")
            i += 1
            continue

        if stripped in {"---", "***", "___"}:
            _close_blocks()
            out.append("<hr/>")
            i += 1
            continue

        if stripped.startswith("#"):
            _close_blocks()
            hashes = len(stripped) - len(stripped.lstrip("#"))
            level = min(6, max(1, hashes))
            heading_text = stripped[hashes:].strip()
            slug = _slugify(heading_text)
            out.append(
                f'<h{level} id="{html.escape(slug, quote=True)}">'
                f"{_render_inline_markdown(heading_text)}</h{level}>"
            )
            i += 1
            continue

        if stripped.startswith(">"):
            _close_blocks()
            quote_lines: list[str] = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                q_text = lines[i].strip()[1:].strip()
                quote_lines.append(q_text)
                i += 1
            first = quote_lines[0] if quote_lines else ""
            alert_match = re.match(r"^\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*(.*)$", first)
            if alert_match:
                kind = alert_match.group(1).lower()
                rest_first = alert_match.group(2)
                body_parts = ([rest_first] if rest_first else []) + quote_lines[1:]
                rendered_body = "<br/>".join(_render_inline_markdown(p) for p in body_parts if p)
                out.append(
                    f'<div class="alert alert-{kind}">'
                    f"<strong>{alert_match.group(1)}:</strong> {rendered_body}</div>"
                )
            else:
                rendered_body = "<br/>".join(_render_inline_markdown(p) for p in quote_lines)
                out.append(f"<blockquote>{rendered_body}</blockquote>")
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [
                c.replace(r"\|", "|").strip() for c in re.split(r"(?<!\\)\|", stripped.strip("|"))
            ]
            if not in_table:
                _close_blocks()
                in_table = True
                out.append('<div class="table-wrap"><table><thead><tr>')
                for cell in cells:
                    out.append(f"<th>{_render_inline_markdown(cell)}</th>")
                out.append("</tr></thead><tbody>")
                if i + 1 < len(lines):
                    next_s = lines[i + 1].strip()
                    if next_s.startswith("|") and re.fullmatch(r"[\s|:-]+", next_s):
                        i += 2
                        continue
            else:
                out.append("<tr>")
                for cell in cells:
                    out.append(f"<td>{_render_inline_markdown(cell)}</td>")
                out.append("</tr>")
            i += 1
            continue

        if stripped.startswith(("- ", "* ")):
            if in_table:
                out.append("</tbody></table></div>")
                in_table = False
            if not in_list:
                in_list = True
                out.append("<ul>")
            out.append(f"<li>{_render_inline_markdown(stripped[2:].strip())}</li>")
            i += 1
            continue

        _close_blocks()
        out.append(f"<p>{_render_inline_markdown(stripped)}</p>")
        i += 1

    if in_code_block:
        out.append("</code></pre>")
    _close_blocks()
    return "\n".join(out)


_ROLLUP_JOB_NAMES = frozenset({"all checks passed"})


def _is_cancelled_conclusion(conclusion: str) -> bool:
    return conclusion.strip().lower() == "cancelled"


def _latest_run(runs: list[RunPortalMetadata]) -> RunPortalMetadata | None:
    """Newest settled run. A cancelled run is latest only when nothing else exists."""
    if not runs:
        return None
    settled = [run for run in runs if not _is_cancelled_conclusion(run.conclusion)]
    pool = settled or runs
    return max(pool, key=lambda run: (run.run_number, run.created_at, run.run_id))


def _status_badge(conclusion: str) -> tuple[str, str, str]:
    norm = conclusion.strip().lower()
    if norm == "success":
        return ("✅", "Passed", "badge-pass")
    if norm in _FAILURE_CONCLUSIONS:
        return ("❌", "Failed", "badge-fail")
    if norm == "cancelled":
        return ("⚠️", "Cancelled", "badge-warn")
    if norm == "skipped":
        return ("⏭️", "Skipped", "badge-neutral")
    return ("ℹ️", conclusion or "Completed", "badge-neutral")


_PORTAL_CSS = """
:root {
  --bg: #0d1117;
  --panel: #161b22;
  --panel-alt: #21262d;
  --border: #30363d;
  --text: #e6edf3;
  --muted: #8b949e;
  --accent: #58a6ff;
  --pass: #238636;
  --fail: #da3633;
  --warn: #9e6a03;
}
@media (prefers-color-scheme: light) {
  :root {
    --bg: #f6f8fa;
    --panel: #ffffff;
    --panel-alt: #f3f4f6;
    --border: #d0d7de;
    --text: #1f2328;
    --muted: #57606a;
    --accent: #0969da;
    --pass: #1a7f37;
    --fail: #cf222e;
    --warn: #9a6700;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.5;
}
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
.container { max-width: 1380px; margin: 0 auto; padding: 20px 24px 48px; }
.topbar {
  background: var(--panel);
  border-bottom: 1px solid var(--border);
  padding: 14px 24px;
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}
.topbar-title { font-weight: 600; font-size: 1.05rem; }
.btn-row { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--panel-alt);
  color: var(--text);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
}
.btn:hover { border-color: var(--accent); text-decoration: none; }
.btn-primary { background: var(--pass); color: #fff; border-color: transparent; }
.badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 600;
}
.badge-pass {
  background: rgba(35, 134, 54, 0.2);
  color: #3fb950;
  border: 1px solid var(--pass);
}
.badge-fail {
  background: rgba(218, 54, 51, 0.2);
  color: #f85149;
  border: 1px solid var(--fail);
}
.badge-warn {
  background: rgba(158, 106, 3, 0.2);
  color: #d29922;
  border: 1px solid var(--warn);
}
.badge-neutral {
  background: var(--panel-alt);
  color: var(--muted);
  border: 1px solid var(--border);
}
.card {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 18px 20px;
  margin-bottom: 16px;
}
.grid-2 {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
  gap: 16px;
}
.tabs {
  display: flex;
  gap: 8px;
  border-bottom: 1px solid var(--border);
  margin: 16px 0;
  flex-wrap: wrap;
}
.tab-btn {
  padding: 9px 16px;
  border: 1px solid transparent;
  border-bottom: none;
  border-radius: 6px 6px 0 0;
  background: transparent;
  color: var(--muted);
  font-weight: 600;
  cursor: pointer;
  font-size: 0.92rem;
}
.tab-btn.active {
  background: var(--panel);
  color: var(--text);
  border-color: var(--border);
}
.tab-pane { display: none; }
.tab-pane.active { display: block; }
.table-wrap { overflow-x: auto; margin: 12px 0; }
table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
th, td { border: 1px solid var(--border); padding: 8px 12px; text-align: left; }
th { background: var(--panel-alt); font-weight: 600; }
code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  background: var(--panel-alt);
  padding: 2px 5px;
  border-radius: 4px;
  font-size: 0.85em;
}
pre.code-block, pre.log-pre {
  background: #010409;
  color: #e6edf3;
  padding: 12px 14px;
  border-radius: 6px;
  border: 1px solid var(--border);
  overflow-x: auto;
  font-size: 0.82rem;
  line-height: 1.45;
  margin: 8px 0;
}
.logs-layout {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 16px;
}
@media (max-width: 900px) {
  .logs-layout { grid-template-columns: 1fr; }
}
.job-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  text-align: left;
  padding: 10px 12px;
  margin-bottom: 6px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--panel-alt);
  color: var(--text);
  cursor: pointer;
  font-size: 0.88rem;
}
.job-item.active { border-color: var(--accent); font-weight: 600; }
.step-details {
  border: 1px solid var(--border);
  border-radius: 6px;
  margin-bottom: 8px;
  background: var(--panel);
}
.step-details summary {
  padding: 8px 12px;
  cursor: pointer;
  font-weight: 500;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.alert {
  padding: 10px 14px;
  border-left: 4px solid var(--accent);
  background: var(--panel-alt);
  border-radius: 4px;
  margin: 10px 0;
}
.meta-row {
  color: var(--muted);
  font-size: 0.88rem;
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 6px;
}
"""


def _compute_sha256_and_size(path: Path) -> tuple[str, str]:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    size_bytes = path.stat().st_size
    if size_bytes >= 1024 * 1024:
        size_str = f"{size_bytes / (1024 * 1024):.2f} MB"
    elif size_bytes >= 1024:
        size_str = f"{size_bytes / 1024:.1f} KB"
    else:
        size_str = f"{size_bytes} B"
    return digest, size_str


def render_run_portal_page(
    *,
    meta: RunPortalMetadata,
    summary_markdown: str,
    jobs: list[JobLogBundle],
    run_out_dir: Path,
    root_rel: str = "../..",
) -> str:
    """Render the self-contained `index.html` for a single workflow run."""
    icon, status_text, badge_cls = _status_badge(meta.conclusion)
    short_sha = meta.commit_sha[:8] if meta.commit_sha else "unknown"
    summary_html = render_markdown_to_html(summary_markdown)
    safe_root = html.escape(root_rel, quote=True)

    short_label = "CI" if meta.workflow_slug == "ci" else "System Tests"
    action_buttons: list[str] = [
        f'<a class="btn" href="{safe_root}/index.html">Runs</a>',
        f'<a class="btn" href="{safe_root}/latest/ci/index.html">CI</a>',
        f'<a class="btn" href="{safe_root}/latest/integration/index.html">System Tests</a>',
    ]
    if meta.has_spec_xlsx:
        action_buttons.append('<a class="btn btn-primary" href="report.xlsx" download>Excel</a>')
    if meta.html_url and meta.html_url.startswith(("https://", "http://")):
        safe_run_url = html.escape(meta.html_url, quote=True)
        action_buttons.append(
            f'<a class="btn" href="{safe_run_url}" target="_blank" rel="noopener">'
            "🔗 View on GitHub Actions</a>"
        )

    job_sidebar_items: list[str] = []
    job_log_panes: list[str] = []
    for idx, job in enumerate(jobs):
        j_icon, _, _ = _status_badge(job.conclusion)
        active_cls = " active" if idx == 0 else ""
        job_sidebar_items.append(
            f'<button type="button" class="job-item{active_cls}" '
            f'onclick="selectJob({idx})" id="job-btn-{idx}">'
            f"<span>{j_icon} {html.escape(job.name)}</span>"
            f'<span style="color:var(--muted);font-size:0.8rem;">'
            f"{job.duration_seconds:.0f}s</span>"
            f"</button>"
        )

        step_blocks: list[str] = []
        for step in job.steps:
            s_icon, _, _ = _status_badge(step.conclusion)
            is_failed = step.conclusion in (_FAILURE_CONCLUSIONS | {"cancelled"})
            open_attr = " open" if is_failed or len(job.steps) == 1 else ""
            escaped_log = html.escape("\n".join(step.lines))
            step_blocks.append(
                f'<details class="step-details"{open_attr}>'
                f"<summary>"
                f"<span>{s_icon} Step {step.number}: {html.escape(step.name)}</span>"
                f'<span style="color:var(--muted);font-size:0.8rem;">'
                f"{step.duration_seconds:.0f}s</span>"
                f"</summary>"
                f'<pre class="log-pre">{escaped_log}</pre>'
                f"</details>"
            )

        pane_display = "block" if idx == 0 else "none"
        raw_link = html.escape(job.raw_log_relpath, quote=True)
        header_style = (
            "display:flex;justify-content:space-between;align-items:center;"
            "margin-bottom:10px;flex-wrap:wrap;gap:8px;"
        )
        job_log_panes.append(
            f'<div class="job-pane" id="job-pane-{idx}" style="display:{pane_display};">'
            f'<div style="{header_style}">'
            f"<strong>{j_icon} {html.escape(job.name)} ({job.line_count} lines)</strong>"
            f'<a class="btn" href="{raw_link}" download>📥 Download Raw Job Log (.log.txt)</a>'
            f"</div>"
            f"{''.join(step_blocks)}"
            f"</div>"
        )

    if not jobs:
        logs_section_html = (
            '<div class="card">'
            "<p>No completed job console logs were harvested for this run.</p>"
            "</div>"
        )
    else:
        logs_section_html = (
            f'<div class="logs-layout">'
            f"<div>{''.join(job_sidebar_items)}</div>"
            f"<div>{''.join(job_log_panes)}</div>"
            f"</div>"
        )

    artifact_rows: list[str] = []
    for fname, desc in (
        ("report.xlsx", "OPC UA IJT 123-CU Specification Conformance Excel Workbook"),
        ("report.html", "Interactive Self-Contained HTML Specification Test Report"),
        ("summary.md", "Raw GitHub-Flavored Markdown Run Summary"),
        ("timing.json", "Schema-v1 Workflow & Job Timing Artifact"),
        ("junit-and-coverage.zip", "Combined JUnit XML & Cobertura Coverage Archive"),
    ):
        fpath = run_out_dir / fname
        if fpath.is_file():
            sha_short, size_label = _compute_sha256_and_size(fpath)
            safe_fn = html.escape(fname, quote=True)
            artifact_rows.append(
                f"<tr>"
                f'<td><a href="{safe_fn}" download><code>{html.escape(fname)}</code></a></td>'
                f"<td>{html.escape(desc)}</td>"
                f"<td>{html.escape(size_label)}</td>"
                f"<td><code>{sha_short}</code></td>"
                f"</tr>"
            )
    for job in jobs:
        lpath = run_out_dir / job.raw_log_relpath
        if lpath.is_file():
            sha_short, size_label = _compute_sha256_and_size(lpath)
            safe_rel = html.escape(job.raw_log_relpath, quote=True)
            artifact_rows.append(
                f"<tr>"
                f'<td><a href="{safe_rel}" download>'
                f"<code>{html.escape(job.raw_log_relpath)}</code></a></td>"
                f"<td>Sanitized Raw Console Log — {html.escape(job.name)}</td>"
                f"<td>{html.escape(size_label)}</td>"
                f"<td><code>{sha_short}</code></td>"
                f"</tr>"
            )

    card_top_style = (
        "display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{html.escape(short_label)} #{meta.run_number} | IJT</title>
  <style>{_PORTAL_CSS}</style>
</head>
<body>
  <header class="topbar">
    <div class="topbar-title">
      🔬 OPC UA IJT Public CI/CD Observability Portal
    </div>
    <div class="btn-row">
      {"".join(action_buttons)}
    </div>
  </header>
  <main class="container">
    <div class="card">
      <div style="{card_top_style}">
        <h1 style="margin:0;font-size:1.35rem;">
          {html.escape(short_label)} #{meta.run_number}
        </h1>
        <span class="badge {badge_cls}">{icon} {html.escape(status_text)}</span>
      </div>
      <div class="meta-row">
        <span><strong>Run ID:</strong> <code>{html.escape(meta.run_id)}</code></span>
        <span><strong>Branch:</strong> <code>{html.escape(meta.branch)}</code></span>
        <span><strong>Commit:</strong> <code>{html.escape(short_sha)}</code></span>
        <span><strong>Trigger:</strong> <code>{html.escape(meta.event_name)}</code></span>
        <span><strong>Published (UTC):</strong> <code>{html.escape(meta.created_at)}</code></span>
        <span>
          <strong>Jobs Harvested:</strong> {meta.job_count} ({meta.failed_job_count} failed)
        </span>
      </div>
    </div>

    <nav class="tabs">
      <button type="button" class="tab-btn active"
              onclick="selectTab('summary')" id="tab-btn-summary">
        Summary
      </button>
      <button type="button" class="tab-btn"
              onclick="selectTab('logs')" id="tab-btn-logs">
        Logs ({len(jobs)})
      </button>
      <button type="button" class="tab-btn"
              onclick="selectTab('artifacts')" id="tab-btn-artifacts">
        Files
      </button>
    </nav>

    <section class="tab-pane active" id="tab-pane-summary">
      <div class="card">
        {summary_html}
      </div>
    </section>

    <section class="tab-pane" id="tab-pane-logs">
      {logs_section_html}
    </section>

    <section class="tab-pane" id="tab-pane-artifacts">
      <div class="card">
        <h2 style="margin-top:0;">Files</h2>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>File</th>
                <th>Description</th>
                <th>Size</th>
                <th>SHA-256 (12c)</th>
              </tr>
            </thead>
            <tbody>
              {"".join(artifact_rows)}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  </main>
  <script>
    function selectTab(name) {{
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      const btn = document.getElementById('tab-btn-' + name);
      const pane = document.getElementById('tab-pane-' + name);
      if (btn && pane) {{
        btn.classList.add('active');
        pane.classList.add('active');
      }}
    }}
    function selectJob(idx) {{
      document.querySelectorAll('.job-item').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.job-pane').forEach(p => p.style.display = 'none');
      const btn = document.getElementById('job-btn-' + idx);
      const pane = document.getElementById('job-pane-' + idx);
      if (btn && pane) {{
        btn.classList.add('active');
        pane.style.display = 'block';
      }}
    }}
    if (window.location.hash === '#logs') selectTab('logs');
    if (window.location.hash === '#artifacts') selectTab('artifacts');
  </script>
</body>
</html>
"""


def render_dashboard_index(runs: list[RunPortalMetadata]) -> str:
    """Render the root `index.html` dashboard showing latest `main` cards and run history."""
    latest_by_slug: dict[str, RunPortalMetadata] = {}
    for slug in {run.workflow_slug for run in runs}:
        chosen = _latest_run([run for run in runs if run.workflow_slug == slug])
        if chosen is not None:
            latest_by_slug[slug] = chosen

    cards_html: list[str] = []
    card_hdr_style = (
        "display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;"
    )
    short_labels = {"ci": "CI", "integration": "System Tests"}
    for slug in ("ci", "integration"):
        label = short_labels[slug]
        latest = latest_by_slug.get(slug)
        if latest is None:
            cards_html.append(
                f'<div class="card">'
                f'<h2 style="margin-top:0;font-size:1.1rem;">{html.escape(label)}</h2>'
                f'<p style="color:var(--muted);">No published runs yet on <code>main</code>.</p>'
                f"</div>"
            )
            continue

        icon, status_text, badge_cls = _status_badge(latest.conclusion)
        short_sha = latest.commit_sha[:8] if latest.commit_sha else "unknown"

        cards_html.append(
            f'<div class="card">'
            f'<div style="{card_hdr_style}">'
            f'<h2 style="margin:0;font-size:1.1rem;">{html.escape(label)}</h2>'
            f'<span class="badge {badge_cls}">{icon} {html.escape(status_text)}</span>'
            f"</div>"
            f'<div class="meta-row" style="margin:10px 0 14px;">'
            f"<span><strong>Latest Run:</strong> #{latest.run_number}</span>"
            f"<span><strong>Commit:</strong> <code>{html.escape(short_sha)}</code></span>"
            f"<span><strong>UTC:</strong> <code>{html.escape(latest.created_at)}</code></span>"
            f"</div>"
            f'<div class="btn-row">'
            f'<a class="btn" href="latest/{slug}/index.html">Open</a>'
            f"</div>"
            f"</div>"
        )

    rows_html: list[str] = []
    for run in runs:
        icon, status_text, badge_cls = _status_badge(run.conclusion)
        short_sha = run.commit_sha[:8] if run.commit_sha else "unknown"
        safe_rid = html.escape(run.run_id, quote=True)
        open_link = f'<a href="runs/{safe_rid}/index.html">Open</a>'
        rows_html.append(
            f'<tr data-workflow="{html.escape(run.workflow_slug, quote=True)}">'
            f'<td><span class="badge {badge_cls}">{icon} {html.escape(status_text)}</span></td>'
            f'<td><a href="runs/{safe_rid}/index.html"><strong>#{run.run_number}</strong></a></td>'
            f"<td>{html.escape(run.workflow_name)}</td>"
            f"<td><code>{html.escape(run.branch)}</code></td>"
            f"<td><code>{html.escape(short_sha)}</code></td>"
            f"<td><code>{html.escape(run.created_at)}</code></td>"
            f"<td>{open_link}</td>"
            f"</tr>"
        )

    repo_url = "https://github.com/umati/UA-for-Industrial-Joining-Technologies"
    tbl_hdr_style = (
        "display:flex;justify-content:space-between;align-items:center;"
        "flex-wrap:wrap;gap:12px;margin-bottom:12px;"
    )
    empty_row = '<tr><td colspan="7">No runs published yet.</td></tr>'
    tbody_content = "".join(rows_html) if rows_html else empty_row

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>OPC UA IJT — Public CI &amp; System Tests Observability Portal</title>
  <style>{_PORTAL_CSS}</style>
</head>
<body>
  <header class="topbar">
    <div class="topbar-title">
      🔬 umati / UA-for-Industrial-Joining-Technologies — Public CI &amp; System Tests Portal
    </div>
    <div class="btn-row">
      <a class="btn" href="{repo_url}" target="_blank" rel="noopener">
        📦 GitHub Repository
      </a>
      <a class="btn" href="{repo_url}/actions" target="_blank" rel="noopener">
        ⚙️ GitHub Actions
      </a>
    </div>
  </header>
  <main class="container">
    <div class="grid-2">
      {"".join(cards_html)}
    </div>

    <div class="card">
      <div style="{tbl_hdr_style}">
        <h2 style="margin:0;font-size:1.15rem;">
          🗂️ Recent <code>main</code> Branch Runs (Zero Sign-In Required)
        </h2>
        <div class="btn-row">
          <button type="button" class="btn" onclick="filterRuns('all')">
            All ({len(runs)})
          </button>
          <button type="button" class="btn" onclick="filterRuns('ci')">
            CI Only
          </button>
          <button type="button" class="btn" onclick="filterRuns('integration')">
            System Tests Only
          </button>
        </div>
      </div>
      <div class="table-wrap">
        <table id="runs-table">
          <thead>
            <tr>
              <th>Status</th>
              <th>Run</th>
              <th>Workflow</th>
              <th>Branch</th>
              <th>Commit</th>
              <th>Published (UTC)</th>
              <th>Direct Public Links</th>
            </tr>
          </thead>
          <tbody>
            {tbody_content}
          </tbody>
        </table>
      </div>
    </div>
  </main>
  <script>
    function filterRuns(slug) {{
      document.querySelectorAll('#runs-table tbody tr[data-workflow]').forEach(row => {{
        const matches = (slug === 'all' || row.getAttribute('data-workflow') === slug);
        row.style.display = matches ? '' : 'none';
      }});
    }}
  </script>
</body>
</html>
"""


def _dir_size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def _safe_rmtree_run(runs_dir: Path, run_id: str) -> None:
    if not _SAFE_RUN_ID_RE.fullmatch(run_id):
        return
    runs_resolved = runs_dir.resolve()
    target = (runs_dir / run_id).resolve()
    if target.is_relative_to(runs_resolved) and target != runs_resolved:
        shutil.rmtree(target, ignore_errors=True)


def prune_portal_runs(
    site_dir: Path,
    runs: list[RunPortalMetadata],
    *,
    max_runs: int = DEFAULT_MAX_RUNS,
    max_total_mb: int = DEFAULT_MAX_TOTAL_MB,
) -> list[RunPortalMetadata]:
    """Prune oldest non-release runs to stay within `max_runs` and `max_total_mb`."""
    sorted_runs = sorted(
        runs,
        key=lambda r: (r.created_at, r.run_number, r.run_id),
        reverse=True,
    )

    kept: list[RunPortalMetadata] = []
    non_release_count = 0
    runs_dir = site_dir / "runs"

    for run in sorted_runs:
        if run.is_release:
            kept.append(run)
            continue
        if non_release_count < max_runs:
            kept.append(run)
            non_release_count += 1
        else:
            _safe_rmtree_run(runs_dir, run.run_id)

    max_bytes = max_total_mb * 1024 * 1024
    while len(kept) > 1 and _dir_size_bytes(runs_dir) > max_bytes:
        evict_idx = next(
            (i for i in range(len(kept) - 1, -1, -1) if not kept[i].is_release),
            None,
        )
        if evict_idx is None:
            break
        evicted = kept.pop(evict_idx)
        _safe_rmtree_run(runs_dir, evicted.run_id)

    return kept


def publish_run_to_portal(
    *,
    site_dir: Path,
    workflow_slug: str,
    workflow_name: str,
    run_id: str,
    run_number: int,
    conclusion: str,
    commit_sha: str,
    branch: str,
    event_name: str,
    html_url: str,
    is_release: bool = False,
    artifacts_dir: Path | None = None,
    summary_file: Path | None = None,
    timing_dir: Path | None = None,
    api_url: str = "",
    repository: str = "",
    token: str = "",
    max_runs: int = DEFAULT_MAX_RUNS,
    max_total_mb: int = DEFAULT_MAX_TOTAL_MB,
) -> RunPortalMetadata:
    """Build or update the static public observability portal in `site_dir`."""
    slug = validate_public_workflow(workflow_slug, workflow_name)
    canonical_name = workflow_name.strip() or WORKFLOW_LABELS[slug]

    run_id_str = str(run_id).strip()
    if not _SAFE_RUN_ID_RE.fullmatch(run_id_str):
        raise ValueError(f"Invalid run_id {run_id!r}: must match {_SAFE_RUN_ID_RE.pattern}")

    site_dir.mkdir(parents=True, exist_ok=True)
    (site_dir / ".nojekyll").write_text("", encoding="utf-8")

    runs_root = site_dir / "runs"
    runs_root.mkdir(parents=True, exist_ok=True)
    run_out_dir = runs_root / run_id_str
    if not run_out_dir.resolve().is_relative_to(runs_root.resolve()):
        raise ValueError(f"Refusing path traversal in run_id: {run_id!r}")
    if run_out_dir.exists():
        shutil.rmtree(run_out_dir)
    run_out_dir.mkdir(parents=True, exist_ok=True)

    capabilities = harvest_run_artifacts(
        artifacts_dir=artifacts_dir,
        summary_file=summary_file,
        timing_dir=timing_dir,
        run_out_dir=run_out_dir,
    )

    effective_run_number = int(run_number)
    effective_sha = commit_sha.strip()
    effective_branch = branch.strip() or "main"
    effective_url = html_url.strip()
    created_at_utc = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    timing_jobs: list[dict[str, Any]] = []

    timing_path = run_out_dir / "timing.json"
    if timing_path.is_file():
        try:
            timing_data = json.loads(timing_path.read_text(encoding="utf-8", errors="replace"))
            if isinstance(timing_data, dict):
                raw_tjobs = timing_data.get("jobs")
                if isinstance(raw_tjobs, list):
                    timing_jobs = [tj for tj in raw_tjobs if isinstance(tj, dict)]
                run_block = timing_data.get("run")
                if isinstance(run_block, dict):
                    t_num = str(run_block.get("run_number") or "").strip()
                    if (
                        effective_run_number <= 0 or event_name == "workflow_dispatch"
                    ) and t_num.isdigit():
                        effective_run_number = int(t_num)
                    if event_name == "workflow_dispatch" or not effective_sha:
                        effective_sha = str(run_block.get("sha") or effective_sha).strip()
                    if event_name == "workflow_dispatch" and run_block.get("branch"):
                        effective_branch = str(run_block.get("branch") or effective_branch).strip()
                    if not effective_url and run_block.get("url"):
                        effective_url = str(run_block.get("url") or "").strip()
                gen_utc = _parse_iso_utc(str(timing_data.get("generated_utc") or ""))
                if gen_utc is not None and event_name == "workflow_dispatch":
                    created_at_utc = gen_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
        except (OSError, ValueError):
            timing_jobs = []

    jobs = fetch_run_jobs_and_logs(
        api_url=api_url,
        repository=repository,
        run_id=run_id_str,
        token=token,
        run_out_dir=run_out_dir,
    )

    summary_path = run_out_dir / "summary.md"
    existing_summary_md = (
        summary_path.read_text(encoding="utf-8", errors="replace") if summary_path.is_file() else ""
    )

    effective_conclusion = conclusion.strip().lower()
    if effective_conclusion in {"", "unknown", "auto"}:
        real_failures = [
            job
            for job in jobs
            if job.conclusion in _FAILURE_CONCLUSIONS
            and job.name.strip().lower() not in _ROLLUP_JOB_NAMES
        ]
        cancelled_jobs = [job for job in jobs if _is_cancelled_conclusion(job.conclusion)]
        if cancelled_jobs and not real_failures:
            # The rollup job exits non-zero when a needed job was cancelled.
            # That is not a product failure; the workflow itself was cancelled.
            effective_conclusion = "cancelled"
        elif real_failures or any(job.conclusion in _FAILURE_CONCLUSIONS for job in jobs):
            effective_conclusion = "failure"
        elif jobs:
            effective_conclusion = "success"
        elif any(
            str(tj.get("conclusion", "")).lower() in _FAILURE_CONCLUSIONS for tj in timing_jobs
        ):
            effective_conclusion = "failure"
        elif any(_is_cancelled_conclusion(str(tj.get("conclusion", ""))) for tj in timing_jobs):
            effective_conclusion = "cancelled"
        elif timing_jobs:
            effective_conclusion = "success"
        elif "> ❌" in existing_summary_md or "Jobs Failed" in existing_summary_md:
            effective_conclusion = "failure"
        elif "> ⚠️" in existing_summary_md:
            effective_conclusion = "cancelled"
        else:
            effective_conclusion = "success"

    if existing_summary_md:
        summary_md = existing_summary_md
    else:
        summary_md = (
            f"# {canonical_name}\n\n"
            f"Run `#{effective_run_number}` (`{run_id_str}`) completed with status "
            f"`{effective_conclusion}`.\n"
        )
        summary_path.write_text(summary_md, encoding="utf-8", newline="\n")

    failed_jobs = sum(1 for j in jobs if j.conclusion in (_FAILURE_CONCLUSIONS | {"cancelled"}))

    meta = RunPortalMetadata(
        run_id=run_id_str,
        run_number=effective_run_number,
        workflow_slug=slug,
        workflow_name=canonical_name,
        conclusion=effective_conclusion,
        commit_sha=effective_sha,
        branch=effective_branch,
        event_name=event_name,
        created_at=created_at_utc,
        html_url=effective_url,
        is_release=is_release,
        has_spec_html=capabilities["has_spec_html"],
        has_spec_xlsx=capabilities["has_spec_xlsx"],
        has_timing_json=capabilities["has_timing_json"],
        has_junit_zip=capabilities["has_junit_zip"],
        job_count=len(jobs),
        failed_job_count=failed_jobs,
    )

    run_html = render_run_portal_page(
        meta=meta,
        summary_markdown=summary_md,
        jobs=jobs,
        run_out_dir=run_out_dir,
        root_rel="../..",
    )
    (run_out_dir / "index.html").write_text(run_html, encoding="utf-8", newline="\n")

    index_json_path = site_dir / "runs-index.json"
    existing_runs: list[RunPortalMetadata] = []
    if index_json_path.is_file():
        try:
            raw_list = json.loads(index_json_path.read_text(encoding="utf-8"))
            if isinstance(raw_list, list):
                for item in raw_list:
                    if isinstance(item, dict) and str(item.get("run_id", "")) != run_id_str:
                        existing_runs.append(RunPortalMetadata.from_dict(item))
        except (OSError, ValueError):
            existing_runs = []

    all_runs = [meta, *existing_runs]
    kept_runs = prune_portal_runs(
        site_dir,
        all_runs,
        max_runs=max_runs,
        max_total_mb=max_total_mb,
    )

    slug_runs = [r for r in kept_runs if r.workflow_slug == slug]
    chosen_latest = _latest_run(slug_runs)
    latest_slug_dir = site_dir / "latest" / slug
    if chosen_latest is not None and (
        chosen_latest.run_id == meta.run_id or not latest_slug_dir.exists()
    ):
        source_dir = (
            run_out_dir if chosen_latest.run_id == meta.run_id else runs_root / chosen_latest.run_id
        )
        if source_dir.is_dir():
            if latest_slug_dir.exists():
                shutil.rmtree(latest_slug_dir)
            shutil.copytree(source_dir, latest_slug_dir)

    index_json_path.write_text(
        json.dumps([r.to_dict() for r in kept_runs], indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    dashboard_html = render_dashboard_index(kept_runs)
    (site_dir / "index.html").write_text(dashboard_html, encoding="utf-8", newline="\n")
    return meta
