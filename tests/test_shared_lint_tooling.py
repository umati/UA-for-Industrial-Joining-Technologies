"""Shared hadolint / yamllint tooling contract (Web Client + Server + CI + pre-commit)."""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_CLIENT_DIR = REPO_ROOT / "OPC_UA_Clients" / "Release2" / "IJT_Web_Client"
WORKFLOWS = REPO_ROOT / ".github" / "workflows"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
import ensure_hadolint as eh  # noqa: E402
import tool_bootstrap as bootstrap  # noqa: E402

# --- ensure_hadolint -------------------------------------------------------------------------


def test_pinned_assets_cover_supported_platforms_with_valid_checksums():
    assert eh.HADOLINT_VERSION == "2.12.0"
    assert set(eh.ASSETS) == {
        "Linux-x86_64",
        "Linux-arm64",
        "Darwin-x86_64",
        "Darwin-arm64",
        "Windows-x86_64",
        "Windows-arm64",
    }
    for asset, sha in eh.ASSETS.values():
        assert re.fullmatch(r"[0-9a-f]{64}", sha), asset
        assert asset.startswith("hadolint-")
    assert eh.ASSETS["Linux-x86_64"] == (
        "hadolint-Linux-x86_64",
        "56de6d5e5ec427e17b74fa48d51271c7fc0d61244bf5c90e828aab8362d55010",
    )
    assert eh.ASSETS["Windows-x86_64"][0] == "hadolint-Windows-x86_64.exe"


@pytest.mark.parametrize(
    ("system", "machine", "key"),
    [
        ("Linux", "x86_64", "Linux-x86_64"),
        ("Linux", "aarch64", "Linux-arm64"),
        ("Darwin", "arm64", "Darwin-arm64"),
        ("Darwin", "x86_64", "Darwin-x86_64"),
        ("Windows", "AMD64", "Windows-x86_64"),
    ],
)
def test_platform_key_normalizes_os_and_arch(system, machine, key):
    assert eh.platform_key(system, machine) == key
    assert key in eh.ASSETS


def test_unsupported_platform_is_rejected():
    with pytest.raises(RuntimeError, match="architecture"):
        eh.platform_key("Linux", "riscv64")
    with pytest.raises(RuntimeError, match="No pinned hadolint"):
        eh.asset_for("FreeBSD-x86_64")


def _fake_download(payload: bytes, calls: list[str]):
    def download(url: str, destination: Path) -> None:
        calls.append(url)
        destination.write_bytes(payload)

    return download


def test_ensure_hadolint_downloads_verifies_and_caches(tmp_path, monkeypatch):
    payload = b"fake hadolint binary"
    sha = hashlib.sha256(payload).hexdigest()
    monkeypatch.setitem(eh.ASSETS, "Linux-x86_64", ("hadolint-Linux-x86_64", sha))
    calls: list[str] = []
    monkeypatch.setattr(eh, "_download", _fake_download(payload, calls))

    first = eh.ensure_hadolint(tmp_path, key="Linux-x86_64")
    second = eh.ensure_hadolint(tmp_path, key="Linux-x86_64")

    assert (
        first
        == second
        == tmp_path.resolve() / ".state" / "tools" / "hadolint-2.12.0-Linux-x86_64" / "hadolint"
    )
    assert first.read_bytes() == payload
    assert calls == [
        "https://github.com/hadolint/hadolint/releases/download/v2.12.0/hadolint-Linux-x86_64"
    ]


def test_ensure_hadolint_rejects_checksum_mismatch_and_leaves_no_binary(tmp_path, monkeypatch):
    monkeypatch.setattr(eh, "_download", _fake_download(b"tampered", []))
    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        eh.ensure_hadolint(tmp_path, key="Linux-x86_64")
    target = eh.cache_path(tmp_path, "Linux-x86_64")
    assert not target.exists()
    assert not list(target.parent.glob(".download-*"))


def test_ensure_hadolint_redownloads_corrupted_cache(tmp_path, monkeypatch):
    payload = b"good"
    sha = hashlib.sha256(payload).hexdigest()
    monkeypatch.setitem(eh.ASSETS, "Windows-x86_64", ("hadolint-Windows-x86_64.exe", sha))
    target = eh.cache_path(tmp_path, "Windows-x86_64")
    assert target.name == "hadolint.exe"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"corrupt")
    calls: list[str] = []
    monkeypatch.setattr(eh, "_download", _fake_download(payload, calls))

    assert eh.ensure_hadolint(tmp_path, key="Windows-x86_64") == target
    assert target.read_bytes() == payload and len(calls) == 1


def test_main_prints_path_links_and_passes_through_with_shared_config(
    tmp_path, monkeypatch, capsys
):
    binary = tmp_path / "hadolint"
    binary.write_text("x", encoding="utf-8")
    monkeypatch.setattr(eh, "ensure_hadolint", lambda project=None, **kw: binary)

    assert eh.main(["--project", str(tmp_path)]) == 0
    assert capsys.readouterr().out.strip() == str(binary)

    link = tmp_path / "bin" / "hadolint-link"
    assert eh.main(["--link", str(link)]) == 0
    assert link.exists()

    ran: list[list[str]] = []

    class Result:
        returncode = 7

    monkeypatch.setattr(eh.subprocess, "run", lambda cmd, **kw: ran.append(cmd) or Result())
    assert eh.main(["--", "a/Dockerfile", "b/Dockerfile"]) == 7
    assert ran == [
        [str(binary), "--config", str(REPO_ROOT / ".hadolint.yaml"), "a/Dockerfile", "b/Dockerfile"]
    ]
    assert eh.main(["--"]) == 0  # pre-commit with no matching files


# --- shared policy / pins --------------------------------------------------------------------


def test_shared_hadolint_config_ignores_exactly_the_agreed_rules():
    config = yaml.safe_load((REPO_ROOT / ".hadolint.yaml").read_text(encoding="utf-8"))
    assert config == {"ignored": ["DL3008", "DL3009"]}


def test_no_workflow_or_runner_inlines_hadolint_download_or_ignores():
    for workflow in WORKFLOWS.glob("*.yml"):
        text = workflow.read_text(encoding="utf-8")
        assert "hadolint/releases/download" not in text, workflow.name
        assert "--ignore DL30" not in text, workflow.name
    for runner in (
        WEB_CLIENT_DIR / "run_all_tests.py",
        REPO_ROOT / "OPC_UA_Servers" / "Release2" / "run_all_tests.py",
    ):
        text = runner.read_text(encoding="utf-8")
        assert "DL3008" not in text and "DL3009" not in text, runner
        assert ".hadolint.yaml" in text, runner
        assert "ensure_hadolint" in text, runner


def test_workflows_install_hadolint_through_ensure_script():
    for name in ("ci.yml", "integration.yml"):
        assert "scripts/ensure_hadolint.py" in (WORKFLOWS / name).read_text(encoding="utf-8"), name


def test_yamllint_pin_is_in_lockstep_everywhere():
    version = bootstrap.YAMLLINT_VERSION
    precommit = yaml.safe_load((REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    repo = next(
        r for r in precommit["repos"] if r["repo"] == "https://github.com/adrienverge/yamllint"
    )
    assert repo["rev"] == f"v{version}"
    hook = next(h for h in repo["hooks"] if h["id"] == "yamllint")
    assert hook["args"] == ["-c", "OPC_UA_Clients/Release2/IJT_Web_Client/.yamllint.yml"]
    assert (REPO_ROOT / hook["args"][1]).is_file()

    pyproject = (WEB_CLIENT_DIR / "pyproject.toml").read_text(encoding="utf-8")
    assert f'"yamllint=={version}"' in pyproject
    lock = (WEB_CLIENT_DIR / "uv.lock").read_text(encoding="utf-8")
    assert f'name = "yamllint"\nversion = "{version}"' in lock.replace("\r\n", "\n")


def test_yamllint_config_line_length_and_covered_files_fit():
    """Dependency-free guard; the real yamllint run is the pre-commit hook + both runners."""
    config = yaml.safe_load((WEB_CLIENT_DIR / ".yamllint.yml").read_text(encoding="utf-8"))
    max_len = config["rules"]["line-length"]["max"]
    assert max_len == 120
    for path in (
        WEB_CLIENT_DIR / "docker-compose.yml",
        WEB_CLIENT_DIR / "docker-compose.smoke.yml",
        REPO_ROOT / "OPC_UA_Servers" / "Release2" / "docker-compose.yml",
        REPO_ROOT / ".hadolint.yaml",
    ):
        too_long = [
            n
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
            if len(line) > max_len
        ]
        assert not too_long, f"{path} lines exceed {max_len} columns: {too_long}"


def test_precommit_wires_yamllint_hadolint_and_context_contract():
    precommit = yaml.safe_load((REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    local = next(r for r in precommit["repos"] if r["repo"] == "local")["hooks"]
    by_id = {h["id"]: h for h in local}
    assert by_id["hadolint"]["entry"] == "python scripts/ensure_hadolint.py --"
    assert re.search(
        by_id["hadolint"]["files"], "OPC_UA_Clients/Release2/IJT_Web_Client/Dockerfile"
    )
    assert re.search(by_id["hadolint"]["files"], "OPC_UA_Servers/Release2/Dockerfile")
    contract_args = by_id["docker-context-contract"]["args"]
    assert "tests/test_docker_context_contract.py" in contract_args
    assert re.search(by_id["docker-context-contract"]["files"], ".dockerignore")
    assert re.search(by_id["docker-context-contract"]["files"], "scripts/simulator_extract.py")


def test_runners_use_explicit_yamllint_config():
    web = (WEB_CLIENT_DIR / "run_all_tests.py").read_text(encoding="utf-8")
    server = (REPO_ROOT / "OPC_UA_Servers" / "Release2" / "run_all_tests.py").read_text(
        encoding="utf-8"
    )
    assert '"-c", str(yamllint_config)' in web
    assert '"-c", str(_SHARED_YAMLLINT_CONFIG)' in server
    assert "IJT_Web_Client" in server and ".yamllint.yml" in server


def test_web_infra_lint_fails_instead_of_skipping_on_hosted_ci_host():
    """Hosted phase1 must fail-closed; in-image ijt_tests must soft-skip host-only tools."""
    web = (WEB_CLIENT_DIR / "run_all_tests.py").read_text(encoding="utf-8")
    assert "strict = IS_GITHUB_ACTIONS and not running_in_docker()" in web
    assert "(required in CI)" in web
    server = (REPO_ROOT / "OPC_UA_Servers" / "Release2" / "run_all_tests.py").read_text(
        encoding="utf-8"
    )
    assert "def _strict_lint_environment()" in server
    assert 'os.getenv("GITHUB_ACTIONS") == "true"' in server
    assert 'os.getenv("IS_DOCKER"' in server
