"""Browser CI image synchronization contract checks.

These tests guard the architectural contract that fixed the producer/consumer
race documented in run 26257538245 (PR #394). The principle:

    No external waits. No inferred identity. No timeout-as-sync.
    Producer and consumer must share a dependency edge with a passed-forward
    output. Cache identity is `inputs_fingerprint`. Runtime identity is
    `digest`. `GITHUB_SHA` is provenance, never validation.

If any of these checks regress, the fix is structural, not a snapshot update.
Read the comments before relaxing an assertion.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[1]
_INTEGRATION_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "integration.yml"
_IMAGE_BUILD_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "build-browser-ci-image.yml"


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# No workflow step may couple `docker pull` to a long polling loop.
# ---------------------------------------------------------------------------
# The historical failure was a `docker pull "$tag"` inside a `for attempt in
# $(seq 1 30); do ... sleep 20; done` budget (10 minutes) used as the
# synchronization mechanism with a separate producer workflow. That pattern
# is forbidden anywhere in the repo's workflows; image identity must arrive
# via `needs:` + a job output, not by polling GHCR for an external producer
# to land a tag.

_DOCKER_PULL_RE = re.compile(r"\bdocker\s+pull\b")
_LOOP_RE = re.compile(r"\b(for|while|until)\b")
_SEQ_RE = re.compile(r"\bseq\s+1\s+(\d+)\b")
_MAX_ATTEMPTS_RE = re.compile(r"max_attempts\s*=\s*(\d+)")
_SLEEP_RE = re.compile(r"\bsleep\s+(\d+)\b")


def _walk_workflow_steps(workflow: dict):
    for job_name, job in (workflow.get("jobs") or {}).items():
        for step in job.get("steps") or []:
            yield job_name, step


@pytest.mark.parametrize(
    "workflow_path",
    [_INTEGRATION_WORKFLOW, _IMAGE_BUILD_WORKFLOW],
    ids=["integration", "build-browser-ci-image"],
)
def test_no_docker_pull_polling_loop_with_long_budget(workflow_path: Path) -> None:
    workflow = _load(workflow_path)
    for job_name, step in _walk_workflow_steps(workflow):
        run = step.get("run") or ""
        if not run or not _DOCKER_PULL_RE.search(run):
            continue
        if not _LOOP_RE.search(run):
            continue
        # Loop + docker pull -> compute total wait budget.
        attempts = 0
        for m in _SEQ_RE.finditer(run):
            attempts = max(attempts, int(m.group(1)))
        for m in _MAX_ATTEMPTS_RE.finditer(run):
            attempts = max(attempts, int(m.group(1)))
        delays = [int(m.group(1)) for m in _SLEEP_RE.finditer(run)]
        max_delay = max(delays) if delays else 0
        budget = attempts * max_delay
        # 180s is the warm-Docker-pull ceiling shared with compose_up_total
        # in tests/conftest.py; anything beyond that is polling-as-sync.
        assert budget <= 180, (
            f"Step '{step.get('name')}' in job '{job_name}' couples docker pull "
            f"to a {budget}s polling loop ({attempts} attempts x {max_delay}s). "
            "That is the broken contract that caused run 26257538245. "
            "Image identity must flow through `needs:` + a job output, not "
            "by polling GHCR for an external producer to land a tag."
        )


# ---------------------------------------------------------------------------
# live-webclient-browser must reach resolve-browser-image via needs.
# ---------------------------------------------------------------------------
# The Browser matrix must depend on the resolver job. If someone reintroduces
# a parallel matrix that resolves identity inside its own steps, the race
# returns. This is the structural fix.


def test_live_webclient_browser_needs_resolve_browser_image() -> None:
    workflow = _load(_INTEGRATION_WORKFLOW)
    job = workflow["jobs"]["live-webclient-browser"]
    needs = job.get("needs")
    if isinstance(needs, str):
        needs = [needs]
    assert needs and "resolve-browser-image" in needs, (
        "live-webclient-browser must declare `needs: resolve-browser-image` "
        "so image identity is a passed-forward output, not a tag poll."
    )


# ---------------------------------------------------------------------------
# IJT_BROWSER_CI_IMAGE must come from a job-output expression.
# ---------------------------------------------------------------------------
# Steps that run the browser image must source the image reference from
# `${{ needs.resolve-browser-image.outputs.image_ref }}`, never from a
# step-output written by an in-job `docker pull`. The historical resolver
# wrote `image_ref` into a step output AFTER polling for a tag — that is
# precisely the inferred-identity pattern this contract forbids.

_JOB_OUTPUT_REF = re.compile(r"\$\{\{\s*needs\.resolve-browser-image\.outputs\.image_ref\s*\}\}")
_STEP_OUTPUT_REF = re.compile(r"\$\{\{\s*steps\.[A-Za-z0-9_]+\.outputs\.image_ref\s*\}\}")


def test_browser_matrix_image_ref_comes_from_job_output_not_step_output() -> None:
    workflow = _load(_INTEGRATION_WORKFLOW)
    job = workflow["jobs"]["live-webclient-browser"]
    saw_job_output_ref = False
    for step in job.get("steps") or []:
        # env block
        env_blob = "\n".join(f"{k}: {v}" for k, v in (step.get("env") or {}).items())
        run_blob = step.get("run") or ""
        for blob in (env_blob, run_blob):
            assert not _STEP_OUTPUT_REF.search(blob), (
                f"Step '{step.get('name')}' references a step-output `image_ref`. "
                "Image identity must come from needs.resolve-browser-image.outputs.image_ref, "
                "not from an in-job docker-pull side effect."
            )
            if _JOB_OUTPUT_REF.search(blob):
                saw_job_output_ref = True
    assert saw_job_output_ref, (
        "live-webclient-browser must consume "
        "needs.resolve-browser-image.outputs.image_ref in at least one step."
    )


# ---------------------------------------------------------------------------
# Cache identity is the fingerprint; runtime identity is the digest.
# ---------------------------------------------------------------------------
# The resolver's metadata-check step must compare image.inputs_fingerprint
# against the planner's CURRENT_FINGERPRINT. It must NOT require build_sha
# to equal GITHUB_SHA: a fingerprint-cache hit is by construction allowed to
# have been built from an earlier SHA with identical inputs. Enforcing SHA
# equality would defeat the cache.


def test_resolve_step_uses_fingerprint_equality_not_build_sha() -> None:
    workflow = _load(_INTEGRATION_WORKFLOW)
    resolve_job = workflow["jobs"]["resolve-browser-image"]
    pick_step = next(
        step
        for step in resolve_job["steps"]
        if step.get("name") == "Pick final image_ref and validate metadata fingerprint"
    )
    body = pick_step["run"]
    env = pick_step.get("env") or {}
    assert "CURRENT_FINGERPRINT" in env, (
        "Resolver pick step must receive the planner's fingerprint via env."
    )
    assert "inputs_fingerprint" in body
    assert "actual_fp" in body and "CURRENT_FINGERPRINT" in body, (
        "Resolver must compare image metadata inputs_fingerprint against "
        "CURRENT_FINGERPRINT — that is the single runtime trust check."
    )
    # Strip comment lines so the negative assertion can't be tripped by a
    # comment that mentions `build_sha` as provenance-only context.
    code_lines = [line for line in body.splitlines() if not line.lstrip().startswith("#")]
    code_only = "\n".join(code_lines)
    assert "build_sha" not in code_only, (
        "Resolver code must NOT reference image build_sha. A "
        "fingerprint-cache hit can legitimately carry a different build_sha; "
        "fingerprint equality is the trust check."
    )


# ---------------------------------------------------------------------------
# The producer exposes workflow_call with the planner's contract.
# ---------------------------------------------------------------------------
# The producer's PR-time entry point is workflow_call from integration.yml.
# It must accept an `expected_fingerprint` input and emit `digest`,
# `source_sha`, `inputs_fingerprint` outputs. Drift between this signature
# and the consumer's call site is what dual-tagging or tag polling tried to
# paper over before.


def test_producer_exposes_workflow_call_with_fingerprint_contract() -> None:
    workflow = _load(_IMAGE_BUILD_WORKFLOW)
    triggers = workflow.get("on", workflow.get(True, {}))
    assert "workflow_call" in triggers, (
        "build-browser-ci-image.yml must expose workflow_call so integration.yml "
        "can invoke it as part of one execution graph."
    )
    wc = triggers["workflow_call"]
    expected = wc.get("inputs", {}).get("expected_fingerprint")
    assert expected, "workflow_call must declare an expected_fingerprint input."
    assert expected.get("required") is True
    assert expected.get("type") == "string"
    outputs = wc.get("outputs") or {}
    for name in ("digest", "source_sha", "inputs_fingerprint"):
        assert name in outputs, f"workflow_call must emit a `{name}` output for consumer wiring."


# ---------------------------------------------------------------------------
# The producer publishes a fingerprint-keyed cache tag.
# ---------------------------------------------------------------------------
# Repeated Renovate-style PRs with identical Browser CI image inputs must be
# able to short-circuit at the planner via a GHCR tag lookup. That requires
# the producer to publish `${IMAGE_NAME}:fingerprint-<hex>` on every push.


def test_producer_publishes_fingerprint_cache_tag() -> None:
    workflow = _load(_IMAGE_BUILD_WORKFLOW)
    publish_job = workflow["jobs"]["publish"]
    tags_step = next(
        step for step in publish_job["steps"] if step.get("name") == "Compute publish tags"
    )
    assert "${IMAGE_NAME}:fingerprint-${INPUTS_FINGERPRINT}" in tags_step["run"], (
        "Publish must include a fingerprint-keyed cache tag so the planner "
        "can short-circuit cold builds for repeated same-input PRs."
    )


def test_planner_decision_table_emits_three_plans() -> None:
    workflow = _load(_INTEGRATION_WORKFLOW)
    planner = workflow["jobs"]["prepare-browser-image-plan"]
    decide_step = next(
        step
        for step in planner["steps"]
        if step.get("name") == "Decide image plan (pin -> cached -> build)"
    )
    body = decide_step["run"]
    for plan in ("plan=pin", "plan=cached", "plan=build"):
        assert plan in body, f"Planner must be able to emit `{plan}`."
    # Untrusted fork PRs with no cache hit must fail fast with a maintainer
    # diagnostic rather than starting a build job that lacks packages: write.
    assert "Untrusted fork PR" in body, (
        "Planner must fail fast for fork PRs with no fingerprint cache hit."
    )


# ---------------------------------------------------------------------------
# The planner must discriminate pin / cached / build deterministically.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# The reusable workflow call must not use `secrets: inherit`.
# ---------------------------------------------------------------------------
# The reusable build-browser-ci-image workflow only needs the auto-provided
# GITHUB_TOKEN for GHCR login (available without inheritance) plus the
# packages: write capability granted via job permissions. `secrets: inherit`
# would broaden the secret surface to every caller secret unnecessarily —
# zizmor flags it as `secrets-inherit`, and the least-privilege contract keeps
# the call site from inheriting unrelated caller secrets.


def test_build_browser_image_call_does_not_inherit_all_secrets() -> None:
    workflow = _load(_INTEGRATION_WORKFLOW)
    build_call = workflow["jobs"]["build-browser-image"]
    assert "secrets" not in build_call or build_call.get("secrets") != "inherit", (
        "build-browser-image must NOT use `secrets: inherit`. The reusable "
        "workflow only needs GITHUB_TOKEN (auto-provided) and packages: write "
        "(granted via job permissions). Inheriting all caller secrets violates "
        "least-privilege and is flagged by zizmor as secrets-inherit."
    )


# ---------------------------------------------------------------------------
# live-webclient-browser must override GitHub's default success() check.
# ---------------------------------------------------------------------------
# resolve-browser-image uses `if: always() && ...` so it runs even when
# build-browser-image is skipped (the common pin/cache path). GitHub's
# default `if: success()` evaluates the entire transitive `needs` graph,
# so a downstream job without its own `if:` would be implicitly skipped on
# every PR that does not require a cold image build. The Browser matrix
# must therefore declare a status-check function (`!cancelled()` or
# `always()`) AND require resolve-browser-image to have succeeded.

_STATUS_CHECK_RE = re.compile(r"!\s*cancelled\s*\(\s*\)|\balways\s*\(\s*\)")
_RESOLVE_SUCCESS_RE = re.compile(r"needs\.resolve-browser-image\.result\s*==\s*['\"]success['\"]")


def test_live_webclient_browser_job_overrides_default_success_check() -> None:
    workflow = _load(_INTEGRATION_WORKFLOW)
    job = workflow["jobs"]["live-webclient-browser"]
    if_expr = job.get("if")
    assert if_expr, (
        "live-webclient-browser MUST declare an explicit `if:` because its "
        "upstream resolve-browser-image uses `if: always()`. Without an "
        "explicit status-check function, GitHub's default success() will "
        "skip the Browser matrix whenever build-browser-image is skipped "
        "(the common pin/cache path)."
    )
    if_text = str(if_expr)
    assert _STATUS_CHECK_RE.search(if_text), (
        "live-webclient-browser.if must contain a status-check function "
        "such as !cancelled() or always() to override the default success() "
        f"evaluation of the transitive needs graph. Got: {if_text!r}"
    )
    assert _RESOLVE_SUCCESS_RE.search(if_text), (
        "live-webclient-browser.if must require "
        "needs.resolve-browser-image.result == 'success' so the Browser "
        "matrix never runs against an unresolved or failed image_ref. "
        f"Got: {if_text!r}"
    )
