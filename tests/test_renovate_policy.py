"""Renovate noise-control policy checks."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[1]
_RENOVATE_CONFIG = _REPO_ROOT / "renovate.json"
_DEPENDABOT_CONFIG = _REPO_ROOT / ".github" / "dependabot.yml"


def _renovate() -> dict:
    return json.loads(_RENOVATE_CONFIG.read_text(encoding="utf-8"))


def _dependabot() -> dict:
    return yaml.safe_load(_DEPENDABOT_CONFIG.read_text(encoding="utf-8"))


def _rules() -> list[dict]:
    rules = _renovate().get("packageRules")
    assert isinstance(rules, list) and rules, "renovate.json must define packageRules"
    return rules


def test_dependabot_owns_weekly_grouped_github_actions_updates() -> None:
    """Exactly one bot should own action digest PRs, and it should batch them."""
    actions_updates = [
        update
        for update in _dependabot().get("updates", [])
        if update.get("package-ecosystem") == "github-actions"
    ]
    assert len(actions_updates) == 1
    update = actions_updates[0]
    assert update["schedule"]["interval"] == "weekly"
    assert update["schedule"]["timezone"] == "Europe/Stockholm"
    assert update.get("groups", {}).get("actions", {}).get("patterns") == ["*"]


def test_renovate_does_not_duplicate_github_actions_digest_prs() -> None:
    """Renovate must not race Dependabot for SHA-pinned GitHub Actions updates."""
    action_owner_rules = [
        rule for rule in _rules() if "github-actions" in rule.get("matchManagers", [])
    ]
    assert action_owner_rules, "renovate.json must explicitly document actions ownership"
    assert all(rule.get("enabled") is False for rule in action_owner_rules)


def test_renovate_batches_docker_digest_updates_weekly() -> None:
    """Docker digest churn is normal; Renovate should batch it into reviewed PRs."""
    docker_digest_rules = [
        rule
        for rule in _rules()
        if "docker" in rule.get("matchDatasources", [])
        and "digest" in rule.get("matchUpdateTypes", [])
    ]
    assert docker_digest_rules, "renovate.json must group Docker digest updates"
    rule = docker_digest_rules[0]
    assert rule["groupSlug"] == "docker-digests"
    assert rule["schedule"] == ["before 7am on monday"]
    assert rule["minimumReleaseAge"] == "3 days"
    assert rule["automerge"] is False
    assert "needs-manual-review" in rule["addLabels"]


def test_renovate_batches_playwright_updates_weekly() -> None:
    """Playwright bumps drive Browser CI image inputs and should not arrive daily."""
    playwright_rules = [
        rule
        for rule in _rules()
        if {"@playwright/test", "playwright"}.issubset(set(rule.get("matchPackageNames", [])))
    ]
    assert playwright_rules, "renovate.json must define a Playwright batching rule"
    rule = playwright_rules[0]
    assert rule["groupSlug"] == "playwright-monorepo"
    assert rule["schedule"] == ["before 7am on monday"]
    assert rule["minimumReleaseAge"] == "3 days"
    assert rule["automerge"] is False


def test_renovate_keeps_python_package_updates_enabled() -> None:
    """Python lock updates, including security updates, must remain available to Renovate."""
    python_disabled = [
        rule
        for rule in _rules()
        if rule.get("enabled") is False and "python" in rule.get("matchCategories", [])
    ]
    assert not python_disabled, (
        "Do not disable Python updates globally; this also blocks security fixes."
    )
    release2 = _REPO_ROOT / "OPC_UA_Clients" / "Release2"
    for client_name in (
        "IJT_Console_Client",
        "IJT_Performance_Client",
        "IJT_Test_Client",
        "IJT_Web_Client",
    ):
        assert (release2 / client_name / "uv.lock").is_file(), (
            f"{client_name} must have its own uv.lock"
        )


@pytest.mark.parametrize(
    ("package", "allowed", "blocked"),
    [
        (
            "python",
            ["3.14", "3.14.6", "3.14-slim-bookworm", "3.14.6-slim-bookworm"],
            ["3.13", "3.15", "3.15-slim-bookworm", "3.140", "4.0"],
        ),
        (
            "nikolaik/python-nodejs",
            ["python3.14-nodejs24", "python3.14.6-nodejs24", "python3.14-nodejs26"],
            ["python3.13-nodejs24", "python3.15-nodejs24", "python3.140-nodejs24"],
        ),
    ],
)
def test_renovate_holds_python_runtime_without_freezing_updates(
    package: str, allowed: list[str], blocked: list[str]
) -> None:
    """Runtime holds allow maintained tags without disabling dependency/digest updates."""
    rules = [
        rule
        for rule in _rules()
        if package in rule.get("matchPackageNames", []) and "allowedVersions" in rule
    ]
    assert len(rules) == 1
    rule = rules[0]
    assert rule["matchDatasources"] == ["docker"]
    assert rule.get("enabled", True) is True
    assert "matchUpdateTypes" not in rule
    assert rule["automerge"] is False
    expression = rule["allowedVersions"]
    assert expression.startswith("/") and expression.endswith("/")
    pattern = re.compile(expression[1:-1])
    assert all(pattern.search(version) for version in allowed)
    assert not any(pattern.search(version) for version in blocked)


def test_python_runtime_pins_match_maintained_line() -> None:
    """Runtime files and both Python images must remain aligned with the hold."""
    assert (_REPO_ROOT / ".python-version").read_text(encoding="utf-8").strip() == "3.14"
    browser = (_REPO_ROOT / ".github" / "docker" / "ijt-browser-ci" / "Dockerfile").read_text(
        encoding="utf-8"
    )
    web = (_REPO_ROOT / "OPC_UA_Clients" / "Release2" / "IJT_Web_Client" / "Dockerfile").read_text(
        encoding="utf-8"
    )
    assert re.search(r"^FROM python:3\.14(?:[.-])", browser, re.MULTILINE)
    assert re.search(r"^FROM nikolaik/python-nodejs:python3\.14-nodejs", web, re.MULTILINE)


def test_renovate_batches_python_dev_tools_weekly() -> None:
    """Python dev tools should be batched weekly into one reviewed PR."""
    dev_rules = [rule for rule in _rules() if rule.get("groupSlug") == "python-dev-tools"]
    assert dev_rules, "renovate.json must define a Python dev tools batching rule"
    for rule in dev_rules:
        assert rule["schedule"] == ["before 7am on monday"]
        assert rule["minimumReleaseAge"] == "3 days"
        assert rule["automerge"] is False
    package_names = set().union(*(r.get("matchPackageNames", []) for r in dev_rules))
    package_patterns = set().union(*(r.get("matchPackagePatterns", []) for r in dev_rules))
    assert package_names >= {"mypy", "ruff", "bandit", "pip-audit"}
    assert "^pytest" in package_patterns


def test_renovate_groups_zizmor_pypi_and_precommit() -> None:
    """Root PyPI zizmor, pre-commit hook, and ci.yml version must bump together."""
    renovate = _renovate()
    assert ":enablePreCommit" in renovate.get("extends", []), (
        "zizmor-lockstep needs Renovate pre-commit manager (:enablePreCommit); "
        "it is disabled by default"
    )
    precommit_limits = [
        rule
        for rule in _rules()
        if "pre-commit" in rule.get("matchManagers", []) and rule.get("enabled") is False
    ]
    assert precommit_limits, "must limit Renovate pre-commit updates (avoid SHA/frozen hook noise)"
    assert any(
        "!zizmorcore/zizmor-pre-commit" in rule.get("matchPackageNames", [])
        for rule in precommit_limits
    ), "zizmor-pre-commit must remain enabled under the pre-commit manager (negation match)"
    assert all("excludePackageNames" not in rule for rule in precommit_limits), (
        "use matchPackageNames negation, not deprecated excludePackageNames"
    )

    zizmor_ci_managers = [
        mgr
        for mgr in renovate.get("customManagers", [])
        if mgr.get("depNameTemplate") == "zizmor"
        and any("ci\\.yml" in pat for pat in mgr.get("managerFilePatterns", []))
    ]
    assert zizmor_ci_managers, (
        "renovate.json must regex-manage ci.yml zizmor-action version: (depName zizmor)"
    )
    assert zizmor_ci_managers[0].get("datasourceTemplate") == "pypi"

    rules = [rule for rule in _rules() if rule.get("groupSlug") == "zizmor-lockstep"]
    assert rules, "renovate.json must define a zizmor-lockstep grouping rule"
    rule = rules[0]
    assert rule["schedule"] == ["before 7am on monday"]
    assert rule["minimumReleaseAge"] == "3 days"
    assert rule["automerge"] is False
    matched = set(rule.get("matchPackageNames", []))
    assert {"zizmor", "zizmorcore/zizmor-pre-commit"}.issubset(matched)
    # Keep GHA zizmor-action *package* out of this group (Dependabot owns action SHAs).
    # The version *input* joins via regex customManager depName=zizmor.
    assert "zizmorcore/zizmor-action" not in matched
    assert "zizmor-action" not in matched
    other_zizmor_groups = [
        r
        for r in _rules()
        if r.get("groupSlug") not in (None, "zizmor-lockstep")
        and "zizmor" in r.get("matchPackageNames", [])
    ]
    assert not other_zizmor_groups, (
        f"zizmor must not join other Renovate groups: {other_zizmor_groups}"
    )


def test_no_legacy_requirements_in_release2_python_clients() -> None:
    """Release 2 Python clients must use pyproject.toml + uv.lock without legacy requirements."""
    release2 = _REPO_ROOT / "OPC_UA_Clients" / "Release2"
    legacy_files = []
    for client in release2.iterdir():
        if client.is_dir():
            for pattern in ("requirements.txt", "requirements-dev.txt", "requirements.lock"):
                if (client / pattern).is_file():
                    legacy_files.append(str((client / pattern).relative_to(_REPO_ROOT)))
    assert not legacy_files, f"Legacy requirements files found: {legacy_files}"


def test_renovate_groups_uv_toolchain_and_covers_workflows() -> None:
    """uv updates must be grouped as an atomic toolchain across CLI, workflows, and Docker."""
    renovate_config = _renovate()
    custom_managers = renovate_config.get("customManagers", [])
    workflow_mgr = [
        mgr
        for mgr in custom_managers
        if any(".github/workflows" in pat for pat in mgr.get("managerFilePatterns", []))
    ]
    assert workflow_mgr, "renovate.json must define a custom manager covering .github/workflows"
    assert workflow_mgr[0].get("depNameTemplate") == "uv"

    toolchain_rules = [rule for rule in _rules() if rule.get("groupSlug") == "uv-toolchain"]
    assert toolchain_rules, "renovate.json must define a 'uv-toolchain' grouping rule"
    rule = toolchain_rules[0]
    matched = set(rule.get("matchPackageNames", []))
    assert {"uv", "ghcr.io/astral-sh/uv"}.issubset(matched)


def test_renovate_holds_opc_foundation_major_updates() -> None:
    """OPC Foundation SDK 2.0 requires Roslyn source generation migration; hold major updates."""
    opc_rules = [
        rule
        for rule in _rules()
        if {"OPCFoundation.NetStandard.Opc.Ua", "OPCFoundation.NetStandard.Opc.Ua.Core"}.issubset(
            set(rule.get("matchPackageNames", []))
        )
    ]
    assert opc_rules, "renovate.json must define a rule holding OPCFoundation.NetStandard packages"
    rule = opc_rules[0]
    assert rule.get("enabled") is False, "Major update for OPC Foundation must be disabled"
    assert rule.get("matchUpdateTypes") == ["major"], (
        "Only major updates must be held (1.x patches allowed)"
    )
