#!/usr/bin/env python3
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

IS_WINDOWS = os.name == "nt"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = PROJECT_ROOT / ".state"
STATE_DIR.mkdir(parents=True, exist_ok=True)


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


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    env = _build_tmp_env()
    subprocess.check_call(cmd, cwd=str(cwd) if cwd else None, env=env)


def _run_quiet(cmd: list[str], cwd: Path | None = None) -> int:
    env = _build_tmp_env()
    completed = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=False,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return completed.returncode


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _fingerprint(requirement_files: list[Path], python_executable: Path) -> str:
    digest = hashlib.sha256()
    digest.update(str(python_executable).encode("utf-8"))
    for req in requirement_files:
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


def _ensure_venv(venv_dir: Path) -> Path:
    python_path = _python_in_venv(venv_dir)
    if python_path.exists():
        if _run_quiet([str(python_path), "-m", "pip", "--version"], cwd=PROJECT_ROOT) == 0:
            return python_path
        try:
            _run([str(python_path), "-m", "ensurepip", "--upgrade"], cwd=PROJECT_ROOT)
            return python_path
        except Exception:
            # Fallback for environments where ensurepip temp extraction is blocked.
            try:
                _run(
                    [
                        sys.executable,
                        "-m",
                        "pip",
                        "--python",
                        str(python_path),
                        "install",
                        "--upgrade",
                        "pip",
                    ],
                    cwd=PROJECT_ROOT,
                )
                return python_path
            except Exception:
                shutil.rmtree(venv_dir, ignore_errors=True)

    venv_dir.parent.mkdir(parents=True, exist_ok=True)
    # Build venv without bundled pip bootstrap first; then run ensurepip under controlled TMP dirs.
    _run([sys.executable, "-m", "venv", "--without-pip", str(venv_dir)], cwd=PROJECT_ROOT)
    python_path = _python_in_venv(venv_dir)
    if not python_path.exists():
        raise RuntimeError(f"Failed to create virtual environment at '{venv_dir}'")
    try:
        _run([str(python_path), "-m", "ensurepip", "--upgrade"], cwd=PROJECT_ROOT)
    except Exception:
        # Fallback for environments where ensurepip temp extraction is blocked.
        _run(
            [
                sys.executable,
                "-m",
                "pip",
                "--python",
                str(python_path),
                "install",
                "--upgrade",
                "pip",
            ],
            cwd=PROJECT_ROOT,
        )
    return python_path


def _clone_venv(source_dir: Path, target_dir: Path) -> Path:
    if target_dir.exists():
        shutil.rmtree(target_dir, ignore_errors=True)
    shutil.copytree(source_dir, target_dir)
    python_path = _python_in_venv(target_dir)
    if not python_path.exists():
        raise RuntimeError(f"Cloned environment is missing interpreter: '{python_path}'")
    return python_path


def _ensure_requirements(
    python_path: Path,
    requirement_files: list[Path],
    state_name: str,
    import_probe: str | None = None,
) -> None:
    existing = [p for p in requirement_files if p.exists()]
    if not existing:
        return

    state_file = STATE_DIR / f"{state_name}.json"
    expected_hash = _fingerprint(existing, python_path)
    state = _load_state(state_file)

    if state.get("fingerprint") == expected_hash and import_probe:
        if _run_quiet([str(python_path), "-c", import_probe], cwd=PROJECT_ROOT) == 0:
            return

    for req in existing:
        _run(
            [
                str(python_path),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--upgrade",
                "-r",
                str(req),
            ],
            cwd=PROJECT_ROOT,
        )

    _save_state(state_file, {"fingerprint": expected_hash})


def ensure_runtime_env(project_root: Path | None = None) -> Path:
    root = project_root.resolve() if project_root else PROJECT_ROOT
    venv_dir = root / "venv"
    python_path = _ensure_venv(venv_dir)
    _ensure_requirements(
        python_path,
        [root / "requirements.txt"],
        state_name="runtime_env",
        import_probe="import asyncua, websockets, requests, packaging, pytz, aiofiles",
    )
    return python_path


def ensure_test_env(project_root: Path | None = None) -> Path:
    root = project_root.resolve() if project_root else PROJECT_ROOT
    venv_dir = root / "venv_test"
    try:
        python_path = _ensure_venv(venv_dir)
    except Exception:
        runtime_dir = root / "venv"
        if not _python_in_venv(runtime_dir).exists():
            ensure_runtime_env(root)
        if not _python_in_venv(runtime_dir).exists():
            raise
        python_path = _clone_venv(runtime_dir, venv_dir)

    _ensure_requirements(
        python_path,
        [root / "requirements.txt", root / "requirements-dev.txt"],
        state_name="test_env",
        import_probe="import asyncua, websockets, pytest, pytest_asyncio",
    )
    return python_path


def ensure_regression_env(project_root: Path | None = None) -> Path:
    root = project_root.resolve() if project_root else PROJECT_ROOT
    venv_dir = root / "venv_test"
    try:
        python_path = _ensure_venv(venv_dir)
    except Exception:
        runtime_dir = root / "venv"
        if not _python_in_venv(runtime_dir).exists():
            ensure_runtime_env(root)
        if not _python_in_venv(runtime_dir).exists():
            raise
        python_path = _clone_venv(runtime_dir, venv_dir)

    _ensure_requirements(
        python_path,
        [root / "requirements.txt"],
        state_name="regression_env",
        import_probe="import asyncua, websockets",
    )
    return python_path


def ensure_additional_requirements(
    python_path: Path,
    requirement_files: list[Path],
    state_name: str,
    import_probe: str | None = None,
) -> None:
    _ensure_requirements(
        python_path,
        requirement_files,
        state_name=state_name,
        import_probe=import_probe,
    )


def is_current_interpreter(python_path: Path) -> bool:
    try:
        current = Path(sys.executable).resolve()
        target = python_path.resolve()
        if IS_WINDOWS:
            return str(current).lower() == str(target).lower()
        return current == target
    except Exception:
        return False
