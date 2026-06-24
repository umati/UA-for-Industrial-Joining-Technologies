"""Renovate noise-control policy checks."""

from __future__ import annotations

import json
from pathlib import Path

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
