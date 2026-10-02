#!/usr/bin/env python3
# NOTE: Web Client venv management library (fingerprint-based, cached).
# Imported by run_regression.py and run_cross_client_regression.py.
# For running tests, use run_all_tests.py at the Web Client root instead.
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

for _parent in Path(__file__).resolve().parents:
    if (_parent / "scripts" / "tool_bootstrap.py").is_file():
        sys.path.insert(0, str(_parent / "scripts"))
        break
from tool_bootstrap import ensure_uv

IS_WINDOWS = os.name == "nt"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = PROJECT_ROOT / ".state"
STATE_DIR.mkdir(parents=True, exist_ok=True)


def _detect_repo_root(start_dir: Path) -> Path:
    for candidate in [start_dir] + list(start_dir.parents):
        if (candidate / "OPC_UA_Clients").exists() and (candidate / "OPC_UA_Servers").exists():
            return candidate
    return start_dir


REPO_ROOT = _detect_repo_root(PROJECT_ROOT)
PYTHON_LOCK = PROJECT_ROOT / "uv.lock"


def _python_in_venv(venv_dir: Path) -> Path:
    return venv_dir / ("Scripts/python.exe" if IS_WINDOWS else "bin/python")


def _build_tmp_env() -> dict[str, str]:
    tmp_dir = STATE_DIR / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["TMPDIR"] = str(tmp_dir)
    env["TEMP"] = str(tmp_dir)
    env["TMP"] = str(tmp_dir)
    return env


def _run(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    run_env = _build_tmp_env()
    if env:
        run_env.update(env)
    subprocess.check_call(cmd, cwd=str(cwd) if cwd else None, env=run_env)


def _run_quiet(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> int:
    run_env = _build_tmp_env()
    if env:
        run_env.update(env)
    completed = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=False,
        env=run_env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return completed.returncode


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _fingerprint(files: list[Path], python_executable: Path) -> str:
    digest = hashlib.sha256()
    digest.update(str(python_executable).encode("utf-8"))
    for req in files:
        if req.exists():
            digest.update(req.name.encode("utf-8"))
            digest.update(_read_text(req).encode("utf-8"))
    return digest.hexdigest()


def _load_state(state_file: Path) -> dict:
    if not state_file.exists():
        return {}
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state_file: Path, state: dict) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _sync_uv_environment(
    venv_dir: Path,
    project_root: Path,
    dev: bool = False,
    state_name: str = "runtime_env",
    import_probe: str | None = None,
) -> Path:
    python_path = _python_in_venv(venv_dir)
    lock_file = project_root / "uv.lock"
    pyproject_file = project_root / "pyproject.toml"
    state_file = STATE_DIR / f"{state_name}.json"

    expected_hash = _fingerprint([lock_file, pyproject_file], python_path)
    state = _load_state(state_file)

    if (
        python_path.exists()
        and state.get("fingerprint") == expected_hash
        and (not import_probe or _run_quiet([str(python_path), "-c", import_probe], cwd=project_root) == 0)
    ):
        return python_path

    uv = ensure_uv(PROJECT_ROOT)
    env = {
        "UV_PROJECT_ENVIRONMENT": str(venv_dir.resolve()),
    }
    cmd = [uv, "sync", "--locked"]
    if dev:
        cmd.extend(["--group", "dev"])
    else:
        cmd.append("--no-dev")

    _run(cmd, cwd=project_root, env=env)

    if not python_path.exists():
        raise RuntimeError(f"Failed to synchronize environment at '{venv_dir}' with uv")

    _save_state(state_file, {"fingerprint": expected_hash})
    return python_path


def ensure_runtime_env(project_root: Path | None = None) -> Path:
    root = project_root.resolve() if project_root else PROJECT_ROOT
    venv_dir = root / ".venv"
    return _sync_uv_environment(
        venv_dir,
        root,
        dev=False,
        state_name="runtime_env",
        import_probe="import asyncua, websockets, packaging, pytz, aiofiles",
    )


def ensure_test_env(project_root: Path | None = None) -> Path:
    root = project_root.resolve() if project_root else PROJECT_ROOT
    venv_dir = root / ".venv_test"
    return _sync_uv_environment(
        venv_dir,
        root,
        dev=True,
        state_name="test_env",
        import_probe="import asyncua, websockets, pytest, pytest_asyncio",
    )


def ensure_regression_env(project_root: Path | None = None) -> Path:
    root = project_root.resolve() if project_root else PROJECT_ROOT
    venv_dir = root / ".venv_test"
    return _sync_uv_environment(
        venv_dir,
        root,
        dev=True,
        state_name="regression_env",
        import_probe="import asyncua, websockets",
    )


def ensure_additional_requirements(
    python_path: Path,
    requirement_files: list[Path],
    state_name: str,
    import_probe: str | None = None,
) -> None:
    state_file = STATE_DIR / f"{state_name}.json"
    existing = [p for p in requirement_files if p.exists()]
    expected_hash = _fingerprint(existing, python_path)
    state = _load_state(state_file)

    if state.get("fingerprint") == expected_hash and import_probe:
        if _run_quiet([str(python_path), "-c", import_probe], cwd=PROJECT_ROOT) == 0:
            return

    for req in existing:
        if req.suffix in {".txt", ".in"}:
            _run(
                [
                    str(python_path),
                    "-m",
                    "pip",
                    "install",
                    # uv.lock
                    "--disable-pip-version-check",
                    "-r",
                    str(req),
                ],
                cwd=PROJECT_ROOT,
            )
        elif req.name == "uv.lock" or req.suffix == ".lock":
            uv = ensure_uv(PROJECT_ROOT)
            client_dir = req.parent
            export_proc = subprocess.run(
                [uv, "export", "--frozen", "--no-dev", "--no-emit-project"],
                cwd=str(client_dir),
                capture_output=True,
                text=True,
                check=False,
            )
            if export_proc.returncode != 0:
                raise RuntimeError(f"Failed to export locked dependencies from {req}: {export_proc.stderr}")
            tmp_req = STATE_DIR / f"{client_dir.name}_locked_deps.txt"
            tmp_req.write_text(export_proc.stdout, encoding="utf-8")
            _run(
                [
                    uv,
                    "pip",
                    "install",
                    # uv.lock
                    "--python",
                    str(python_path),
                    "-r",
                    str(tmp_req),
                ],
                cwd=client_dir,
            )

    if import_probe and _run_quiet([str(python_path), "-c", import_probe], cwd=PROJECT_ROOT) != 0:
        raise RuntimeError(f"Import probe failed for {state_name} ({import_probe}) after installing requirement files.")

    _save_state(state_file, {"fingerprint": expected_hash})


def is_current_interpreter(python_path: Path) -> bool:
    try:
        current = Path(sys.executable).resolve()
        target = python_path.resolve()
        if IS_WINDOWS:
            return str(current).lower() == str(target).lower()
        return current == target
    except Exception:
        return False
