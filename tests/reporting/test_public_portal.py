"""Unit and contract tests for `reporting.public_portal` and `build_public_portal.py`."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from reporting.public_portal import (
    JobLogBundle,
    RunPortalMetadata,
    prune_portal_runs,
    publish_run_to_portal,
    render_markdown_to_html,
    sanitize_log_text,
    slice_job_log_into_steps,
    validate_public_workflow,
)
from scripts.reporting import build_public_portal


def test_validate_public_workflow_accepts_only_ci_and_integration() -> None:
    assert validate_public_workflow("ci") == "ci"
    assert validate_public_workflow("  INTEGRATION  ") == "integration"

    for forbidden in (
        "internal-private-envelope",
        "internal-private-envelope.yml",
        "private-envelope",
    ):
        with pytest.raises(ValueError, match="forbidden private workflow"):
            validate_public_workflow(forbidden)

    with pytest.raises(ValueError, match="forbidden private workflow"):
        validate_public_workflow("ci", "Internal — Private Envelope Validation")

    with pytest.raises(ValueError, match="not in ALLOWED_WORKFLOW_SLUGS"):
        validate_public_workflow("codeql")


def test_sanitize_log_text_redacts_tokens_headers_urls_and_keys() -> None:
    fake_ghp = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6"
    fake_pat = "github_pat_" + "Z9y8X7w6V5u4T3s2R1q0P9o8N7m6"
    raw = (
        f"\x1b[32mCloning https://x-access-token:{fake_ghp}@github.com/umati/repo.git\x1b[0m\r\n"
        f"Authorization: Bearer {fake_pat}\n"
        "AWS key AKIA0123456789ABCDEF leaked\n"
        "-----BEGIN RSA PRIVATE KEY-----\nMIIBOgIBAAJBAKj34GkxFhD\n-----END RSA PRIVATE KEY-----\n"
    )
    sanitized = sanitize_log_text(raw)

    assert fake_ghp not in sanitized
    assert fake_pat not in sanitized
    assert "AKIA0123456789ABCDEF" not in sanitized
    assert "MIIBOgIBAAJBAKj34GkxFhD" not in sanitized
    assert "\x1b[" not in sanitized
    assert "https://[REDACTED_CREDENTIALS]@github.com/umati/repo.git" in sanitized
    assert "[REDACTED_AUTH]" in sanitized
    assert "[REDACTED_AWS_KEY]" in sanitized
    assert "[REDACTED_PRIVATE_KEY]" in sanitized


def test_slice_job_log_into_steps_assigns_lines_by_step_timestamps() -> None:
    steps_meta = [
        {
            "number": 1,
            "name": "Set up job",
            "conclusion": "success",
            "started_at": "2026-11-04T18:00:00Z",
            "completed_at": "2026-11-04T18:00:05Z",
        },
        {
            "number": 2,
            "name": "Run pytest",
            "conclusion": "failure",
            "started_at": "2026-11-04T18:00:06Z",
            "completed_at": "2026-11-04T18:00:20Z",
        },
    ]
    log_text = (
        "2026-11-04T18:00:01.1234567Z Preparing runner environment\n"
        "2026-11-04T18:00:04.0000000Z Runner ready\n"
        "2026-11-04T18:00:08.5000000Z collecting ... collected 42 items\n"
        "2026-11-04T18:00:19.0000000Z FAILED tests/test_demo.py::test_one\n"
    )
    slices = slice_job_log_into_steps(log_text, steps_meta)

    assert len(slices) == 2
    assert slices[0].name == "Set up job"
    assert slices[0].duration_seconds == 5.0
    assert slices[0].lines == ["Preparing runner environment", "Runner ready"]
    assert slices[1].name == "Run pytest"
    assert slices[1].conclusion == "failure"
    assert slices[1].duration_seconds == 14.0
    assert "FAILED tests/test_demo.py::test_one" in slices[1].lines


def test_render_markdown_to_html_handles_tables_details_alerts_and_escapes_xss() -> None:
    md = (
        '<a id="system-test-results"></a>\n'
        "## System Test Results\n\n"
        "> [!NOTE]\n"
        "> Server readiness verified.\n\n"
        "| Suite | Status |\n"
        "| --- | --- |\n"
        "| `web-client` | **Passed** [link](https://example.com) [bad](javascript:alert(1)) |\n\n"
        "<details>\n"
        "<summary>Expand <script>alert(1)</script></summary>\n\n"
        "- item one\n"
        "</details>\n"
    )
    rendered = render_markdown_to_html(md)

    assert '<a id="system-test-results"></a>' in rendered
    assert '<h2 id="system-test-results">System Test Results</h2>' in rendered
    assert "alert-note" in rendered
    assert "<table>" in rendered
    assert "<code>web-client</code>" in rendered
    assert "<strong>Passed</strong>" in rendered
    assert '<a href="https://example.com">link</a>' in rendered
    assert "javascript:alert" not in rendered
    assert "<script>" not in rendered
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered


def test_publish_run_to_portal_creates_run_and_latest_views(tmp_path: Path) -> None:
    site_dir = tmp_path / "site"
    artifacts_dir = tmp_path / "all-results"
    (artifacts_dir / "timing-system-tests").mkdir(parents=True)
    (artifacts_dir / "results-testclient").mkdir(parents=True)

    (artifacts_dir / "timing-system-tests" / "summary.md").write_text(
        "# 📋 System Tests Report\n\n| Job | Result |\n|---|---|\n| Test Client | ✅ Passed |\n",
        encoding="utf-8",
    )
    (artifacts_dir / "timing-system-tests" / "timing-latest.json").write_text(
        json.dumps({"schema_version": 1, "jobs": []}),
        encoding="utf-8",
    )
    (artifacts_dir / "results-testclient" / "report.html").write_text(
        "<html><body>Spec Report</body></html>",
        encoding="utf-8",
    )
    (artifacts_dir / "results-testclient" / "report.xlsx").write_bytes(b"PK\x03\x04dummy-xlsx")
    (artifacts_dir / "results-testclient" / "pytest.xml").write_text(
        '<testsuite tests="1" failures="0"><testcase name="t1"/></testsuite>',
        encoding="utf-8",
    )

    meta = publish_run_to_portal(
        site_dir=site_dir,
        workflow_slug="integration",
        workflow_name="System Tests — Live OPC UA, Browser, Docker, Specification Testing",
        run_id="12345",
        run_number=99,
        conclusion="success",
        commit_sha="e4830ba504bb8436a7fa0cb6486715bd23e6125d",
        branch="main",
        event_name="push",
        html_url="https://github.com/umati/UA-for-Industrial-Joining-Technologies/actions/runs/12345",
        artifacts_dir=artifacts_dir,
    )

    assert meta.has_spec_html is True
    assert meta.has_spec_xlsx is True
    assert meta.has_timing_json is True
    assert meta.has_junit_zip is True
    assert (site_dir / ".nojekyll").is_file()
    assert (site_dir / "index.html").is_file()
    assert (site_dir / "runs" / "12345" / "index.html").is_file()
    assert (site_dir / "runs" / "12345" / "report.html").is_file()
    assert (site_dir / "runs" / "12345" / "report.xlsx").is_file()
    assert (site_dir / "latest" / "integration" / "index.html").is_file()
    assert (site_dir / "latest" / "integration" / "report.html").is_file()
    assert (site_dir / "latest" / "integration" / "report.xlsx").is_file()
    page = (site_dir / "runs" / "12345" / "index.html").read_text(encoding="utf-8")
    assert "Test Client" in page
    assert ">Excel</a>" in page
    assert 'src="report.html"' not in page


def test_prune_portal_runs_preserves_releases_and_caps_non_release_runs(tmp_path: Path) -> None:
    site_dir = tmp_path / "site"
    runs_dir = site_dir / "runs"
    runs: list[RunPortalMetadata] = []
    for idx in range(1, 6):
        rid = str(100 + idx)
        (runs_dir / rid).mkdir(parents=True)
        (runs_dir / rid / "index.html").write_text("ok", encoding="utf-8")
        runs.append(
            RunPortalMetadata(
                run_id=rid,
                run_number=idx,
                workflow_slug="ci",
                workflow_name="CI",
                conclusion="success",
                commit_sha="abcdef12",
                branch="v1.0.0" if idx == 1 else "main",
                event_name="push",
                created_at=f"2026-11-04 10:0{idx}:00 UTC",
                html_url="",
                is_release=(idx == 1),
            )
        )

    kept = prune_portal_runs(site_dir, runs, max_runs=2, max_total_mb=600)
    kept_ids = [r.run_id for r in kept]

    # Release run (101) + 2 newest non-release runs (105, 104) are retained; 102 and 103 are pruned.
    assert "101" in kept_ids
    assert "105" in kept_ids
    assert "104" in kept_ids
    assert "102" not in kept_ids
    assert "103" not in kept_ids
    assert not (runs_dir / "102").exists()
    assert (runs_dir / "101").exists()


def test_build_public_portal_cli_entrypoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    site_dir = tmp_path / "cli-site"
    timing_dir = tmp_path / "timing-results"
    timing_dir.mkdir(parents=True)
    (timing_dir / "summary.md").write_text("# CI Summary\n", encoding="utf-8")
    (timing_dir / "timing-latest.json").write_text("{}", encoding="utf-8")

    monkeypatch.setenv("GH_RUN_ID", "777")
    monkeypatch.setenv("GH_RUN_NUMBER", "12")
    monkeypatch.setenv("GH_SHA", "1234567890abcdef")
    monkeypatch.setenv("GH_BRANCH", "main")
    monkeypatch.setenv("GH_TOKEN", "")

    rc = build_public_portal.main(
        [
            "--site-dir",
            str(site_dir),
            "--workflow-slug",
            "ci",
            "--timing-dir",
            str(timing_dir),
            "--artifacts-dir",
            str(tmp_path / "empty-artifacts"),
        ]
    )
    assert rc == 0
    assert (site_dir / "runs" / "777" / "index.html").is_file()
    assert (site_dir / "latest" / "ci" / "index.html").is_file()


# ── Regression tests for critical-review findings ─────────────────────────────

_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "expected"


def _publish_minimal(
    site_dir: Path, run_id: str, run_number: int, **overrides: Any
) -> RunPortalMetadata:
    kwargs: dict[str, Any] = {
        "site_dir": site_dir,
        "workflow_slug": "ci",
        "workflow_name": "",
        "run_id": run_id,
        "run_number": run_number,
        "conclusion": "success",
        "commit_sha": "abcdef1234567890",
        "branch": "main",
        "event_name": "push",
        "html_url": "",
    }
    kwargs.update(overrides)
    return publish_run_to_portal(**kwargs)


def test_redirect_handler_strips_authorization_cross_host_and_rejects_http() -> None:
    import io
    import urllib.error
    import urllib.request
    from email.message import Message

    from reporting.public_portal import _HttpsOnlyRedirectHandler

    handler = _HttpsOnlyRedirectHandler()
    req = urllib.request.Request(
        "https://api.github.com/repos/o/r/actions/jobs/1/logs",
        headers={"Authorization": "Bearer secret-token", "User-Agent": "ua"},
    )
    req.add_unredirected_header("Authorization", "Bearer secret-token")
    hdrs = Message()

    cross = handler.redirect_request(
        req, io.BytesIO(), 302, "Found", hdrs, "https://pipelines.blob.core.windows.net/log?sig=x"
    )
    assert cross is not None
    all_keys = {k.lower() for k in (*cross.headers, *cross.unredirected_hdrs)}
    assert "authorization" not in all_keys

    same = handler.redirect_request(
        req, io.BytesIO(), 302, "Found", hdrs, "https://api.github.com/other"
    )
    assert same is not None
    assert any(k.lower() == "authorization" for k in same.headers)

    with pytest.raises(urllib.error.URLError, match="non-HTTPS"):
        handler.redirect_request(req, io.BytesIO(), 302, "Found", hdrs, "http://evil.example/x")


def test_publish_rejects_path_traversal_run_id(tmp_path: Path) -> None:
    site_dir = tmp_path / "site"
    for bad in ("../escape", "..", "a/b", "x" * 65, ""):
        with pytest.raises(ValueError, match="Invalid run_id"):
            _publish_minimal(site_dir, bad, 1)
    assert not (tmp_path / "escape").exists()


def test_prune_never_deletes_outside_runs_dir(tmp_path: Path) -> None:
    site_dir = tmp_path / "site"
    (site_dir / "runs").mkdir(parents=True)
    victim = tmp_path / "victim"
    victim.mkdir()
    bad = RunPortalMetadata(
        run_id="../../victim",
        run_number=1,
        workflow_slug="ci",
        workflow_name="CI",
        conclusion="success",
        commit_sha="",
        branch="main",
        event_name="push",
        created_at="2020-01-01 00:00:00 UTC",
        html_url="",
    )
    newer = RunPortalMetadata.from_dict({**bad.to_dict(), "run_id": "200", "created_at": "2030"})
    prune_portal_runs(site_dir, [newer, bad], max_runs=1)
    assert victim.is_dir()


def test_inline_markdown_code_spans_entities_and_protocol_relative_links() -> None:
    rendered = render_markdown_to_html(
        "Run `[x](https://evil)` and [bad](//evil.com) and [ok](/docs) "
        "&nbsp;&bull; a &lt; b &amp; <b>bold</b> _italic note_ snake_case_name\n"
    )
    assert "<code>[x](https://evil)</code>" in rendered
    assert 'href="//evil.com"' not in rendered
    assert '<a href="/docs">ok</a>' in rendered
    assert "&amp;nbsp;" not in rendered
    assert "&amp;bull;" not in rendered
    assert "&nbsp;&bull;" in rendered
    assert "a &lt; b &amp;" in rendered
    assert "&amp;lt;" not in rendered
    assert "<strong>bold</strong>" in rendered
    assert "<em>italic note</em>" in rendered
    assert "snake_case_name" in rendered


def test_table_cells_split_on_unescaped_pipes_only() -> None:
    rendered = render_markdown_to_html("| A | B |\n|---|---|\n| x \\| y | z |\n")
    assert "<td>x | y</td>" in rendered
    assert "<td>z</td>" in rendered


@pytest.mark.parametrize("fixture_name", ["ci_summary.md", "integration_summary.md"])
def test_real_summary_fixtures_render_without_corruption(fixture_name: str) -> None:
    md = (_FIXTURES_DIR / fixture_name).read_text(encoding="utf-8")
    rendered = render_markdown_to_html(md)
    for corrupted in ("&amp;nbsp;", "&amp;bull;", "&amp;lt;", "&amp;gt;", "&lt;b&gt;"):
        assert corrupted not in rendered, f"{fixture_name}: found {corrupted}"
    expected_summaries = md.count("<details><summary>") + md.count("<details open><summary>")
    assert expected_summaries > 0
    assert rendered.count("<summary>") == expected_summaries
    assert rendered.count("<details") == rendered.count("</details>")


def test_details_open_attribute_preserved() -> None:
    rendered = render_markdown_to_html(
        "<details open><summary>❌ <b>Failed suite</b> — 1 Failed</summary>\n\nbody\n\n</details>\n"
    )
    assert (
        "<details open><summary>❌ <strong>Failed suite</strong> — 1 Failed</summary>" in rendered
    )


def test_sanitize_log_text_redacts_jwt_extraheader_sas_and_dec_private_modes() -> None:
    jwt = "eyJhbGciOiJIUzI1NiJ9" + "." + "eyJzdWIiOiIxMjM0NTY3ODkwIn0" + "." + "abcdefghijklmnop"
    raw = (
        "\x1b[?25lprogress\x1b[?25h\n"
        f"token={jwt}\n"
        "git -c http.https://github.com/.extraheader=AUTHORIZATION: basic "
        "eC1hY2Nlc3M6c2VjcmV0 fetch\n"
        "GET https://x.blob.core.windows.net/log?sv=1&sig=SECRETSIG123&se=2\n"
    )
    cleaned = sanitize_log_text(raw)
    assert "\x1b[" not in cleaned
    assert jwt not in cleaned
    assert "eC1hY2Nlc3M6c2VjcmV0" not in cleaned
    assert "SECRETSIG123" not in cleaned
    assert "&sig=[REDACTED_SECRET]" in cleaned


def test_fetch_jobs_excludes_publish_public_jobs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from reporting import public_portal

    jobs_payload = {
        "jobs": [
            {"id": 1, "name": "Unit Tests", "status": "completed", "conclusion": "success"},
            {
                "id": 2,
                "name": "🌐 Publish Public CI Report / 🌐 Publish Public Observability Portal",
                "status": "completed",
                "conclusion": "success",
            },
            {"id": 3, "name": "Startup", "status": "completed", "conclusion": "startup_failure"},
        ]
    }

    def fake_get(url: str, headers: dict[str, str], timeout: int = 30) -> bytes:
        del headers, timeout
        if url.endswith("/jobs?per_page=100"):
            return json.dumps(jobs_payload).encode()
        return b"log line\n"

    monkeypatch.setattr(public_portal, "_https_get_bytes", fake_get)
    fake_token = "-".join(("unit", "test", "token"))
    bundles = public_portal.fetch_run_jobs_and_logs(
        api_url="https://api.github.com",
        repository="o/r",
        run_id="5",
        token=fake_token,
        run_out_dir=tmp_path / "run",
    )
    names = [b.name for b in bundles]
    assert "Unit Tests" in names
    assert not any("Publish Public" in n for n in names)
    assert names[0] == "Startup"  # failures sorted first


def test_auto_conclusion_without_jobs_uses_timing_then_summary(tmp_path: Path) -> None:
    timing_dir = tmp_path / "timing"
    timing_dir.mkdir()
    (timing_dir / "timing-latest.json").write_text(
        json.dumps({"jobs": [{"name": "x", "conclusion": "action_required"}]}), encoding="utf-8"
    )
    meta = _publish_minimal(tmp_path / "s1", "1", 1, conclusion="auto", timing_dir=timing_dir)
    assert meta.conclusion == "failure"

    summary = tmp_path / "summary.md"
    summary.write_text("## CI\n\n> ❌ **2 / 13 Jobs Failed**\n", encoding="utf-8")
    meta2 = _publish_minimal(tmp_path / "s2", "2", 2, conclusion="", summary_file=summary)
    assert meta2.conclusion == "failure"

    meta3 = _publish_minimal(tmp_path / "s3", "3", 3, conclusion="")
    assert meta3.conclusion == "success"
    fallback = (tmp_path / "s3" / "runs" / "3" / "summary.md").read_text(encoding="utf-8")
    assert "status `success`" in fallback


def test_harvest_prefers_workflow_timing_bundle_over_subproject(tmp_path: Path) -> None:
    from reporting.public_portal import harvest_run_artifacts

    artifacts = tmp_path / "all-results"
    (artifacts / "results-web-py").mkdir(parents=True)
    (artifacts / "timing-ci").mkdir(parents=True)
    (artifacts / "results-web-py" / "timing-latest.json").write_text('{"who":"sub"}', "utf-8")
    (artifacts / "timing-ci" / "timing-latest.json").write_text('{"who":"workflow"}', "utf-8")
    out = tmp_path / "out"
    caps = harvest_run_artifacts(
        artifacts_dir=artifacts, summary_file=None, timing_dir=None, run_out_dir=out
    )
    assert caps["has_timing_json"] is True
    assert json.loads((out / "timing.json").read_text("utf-8"))["who"] == "workflow"


def test_older_backfill_does_not_overwrite_latest_pointer(tmp_path: Path) -> None:
    site_dir = tmp_path / "site"
    _publish_minimal(site_dir, "500", 50, commit_sha="newsha00")
    _publish_minimal(site_dir, "400", 40, commit_sha="oldsha00", event_name="workflow_dispatch")
    latest_html = (site_dir / "latest" / "ci" / "index.html").read_text(encoding="utf-8")
    assert "newsha00" in latest_html
    assert "oldsha00" not in latest_html
    index = json.loads((site_dir / "runs-index.json").read_text(encoding="utf-8"))
    assert {r["run_id"] for r in index} == {"500", "400"}


def test_cancelled_run_does_not_replace_latest(tmp_path: Path) -> None:
    site_dir = tmp_path / "site"
    _publish_minimal(site_dir, "10", 10, commit_sha="goodsha1")
    _publish_minimal(site_dir, "11", 11, commit_sha="cancsha1", conclusion="cancelled")
    latest_html = (site_dir / "latest" / "ci" / "index.html").read_text(encoding="utf-8")
    dashboard = (site_dir / "index.html").read_text(encoding="utf-8")
    assert "goodsha1" in latest_html
    assert "cancsha1" not in latest_html
    assert "Latest Run:</strong> #10" in dashboard
    index = json.loads((site_dir / "runs-index.json").read_text(encoding="utf-8"))
    assert {row["run_id"] for row in index} == {"10", "11"}


def test_cancelled_rollup_is_not_a_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from reporting import public_portal

    def fake_jobs(**_kwargs: object) -> list[JobLogBundle]:
        return [
            JobLogBundle(
                1, "Web Client - JavaScript", "completed", "success", 1.0, "", "logs/a.txt"
            ),
            JobLogBundle(2, "Console Client", "completed", "cancelled", 1.0, "", "logs/b.txt"),
            JobLogBundle(3, "All checks passed", "completed", "failure", 1.0, "", "logs/c.txt"),
        ]

    monkeypatch.setattr(public_portal, "fetch_run_jobs_and_logs", fake_jobs)
    meta = _publish_minimal(tmp_path / "site", "12", 12, conclusion="auto")
    assert meta.conclusion == "cancelled"


def test_real_failure_still_becomes_latest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from reporting import public_portal

    site_dir = tmp_path / "site"
    _publish_minimal(site_dir, "20", 20, commit_sha="goodsha2")

    def fake_jobs(**_kwargs: object) -> list[JobLogBundle]:
        return [
            JobLogBundle(
                1, "Web Client - JavaScript", "completed", "failure", 1.0, "", "logs/a.txt"
            ),
            JobLogBundle(2, "Console Client", "completed", "cancelled", 1.0, "", "logs/b.txt"),
        ]

    monkeypatch.setattr(public_portal, "fetch_run_jobs_and_logs", fake_jobs)
    meta = _publish_minimal(site_dir, "21", 21, commit_sha="badsha22", conclusion="auto")
    assert meta.conclusion == "failure"
    latest_html = (site_dir / "latest" / "ci" / "index.html").read_text(encoding="utf-8")
    assert "badsha22" in latest_html


def test_run_page_shows_summary_and_drops_unsafe_run_url(tmp_path: Path) -> None:
    artifacts = tmp_path / "all-results" / "results-testclient"
    artifacts.mkdir(parents=True)
    (artifacts / "report.html").write_text("<html></html>", encoding="utf-8")
    _publish_minimal(
        tmp_path / "site",
        "9",
        9,
        workflow_slug="integration",
        artifacts_dir=tmp_path / "all-results",
        html_url="javascript:alert(1)",
    )
    page = (tmp_path / "site" / "runs" / "9" / "index.html").read_text(encoding="utf-8")
    assert 'src="report.html"' not in page
    assert "javascript:alert" not in page
