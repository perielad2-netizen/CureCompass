"""Tests for read-only release preflight (real app settings API; no paid calls)."""

from __future__ import annotations

import importlib
import re
import subprocess
import sys
from pathlib import Path

import pytest

from app.core.config import settings as real_settings

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import release_preflight as preflight  # noqa: E402


BACKEND = Path(__file__).resolve().parents[1]
SECRETISH = "postgresql+psycopg://user:SUPER_SECRET_PASSWORD@db:5432/curecompass"


def test_config_module_exposes_settings_not_get_settings():
    mod = importlib.import_module("app.core.config")
    assert hasattr(mod, "settings")
    assert not hasattr(mod, "get_settings")
    assert mod.settings.openai_responses_model == real_settings.openai_responses_model


def test_preflight_source_has_no_get_settings_dependency():
    source = (SCRIPTS_DIR / "release_preflight.py").read_text(encoding="utf-8")
    assert "get_settings" not in source
    assert 'import_module_attr("app.core.config", "settings")' in source
    assert "app.workers.celery_app" in source
    assert "dont_write_bytecode" in source


def test_safe_error_category_does_not_embed_message():
    class Boom(Exception):
        pass

    exc = Boom(SECRETISH)
    line = preflight.format_safe_failure("config_import", exc)
    assert SECRETISH not in line
    assert "SUPER_SECRET" not in line
    assert "category=unexpected" in line
    assert "type=Boom" in line


def test_permission_error_category():
    line = preflight.format_safe_failure("app_import", PermissionError(SECRETISH))
    assert SECRETISH not in line
    assert "category=permission" in line


def test_check_readable_missing_file(tmp_path: Path):
    ok, msg = preflight.check_readable(tmp_path / "missing.py")
    assert ok is False
    assert "missing" in msg


def test_run_preflight_fails_on_unreadable_or_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    missing = tmp_path / "gone.py"
    code = preflight.run_preflight(backend=BACKEND, files=[missing], skip_imports=True)
    assert code == 1


def test_run_preflight_succeeds_with_real_application_settings(capsys: pytest.CaptureFixture[str]):
    """Exercise real app.core.config.settings + API/worker imports (no paid/network I/O)."""
    code = preflight.run_preflight(backend=BACKEND)
    captured = capsys.readouterr().out
    assert code == 0, captured
    assert "config_import_ok" in captured
    assert f"model={real_settings.openai_responses_model}" in captured
    assert f"reasoning_effort={real_settings.openai_reasoning_effort}" in captured
    assert "app_import_ok" in captured
    assert "celery_import_ok" in captured
    assert "preflight_result=PASS" in captured
    assert "get_settings" not in captured
    assert SECRETISH not in captured
    assert "OPENAI_API_KEY" not in captured
    assert not re.search(r"sk-[A-Za-z0-9]", captured)


def test_run_preflight_import_failure_is_nonzero_without_secrets(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    def boom(module_name: str, attr_name: str) -> object:
        raise ImportError(f"cannot import {module_name}: {SECRETISH}")

    monkeypatch.setattr(preflight, "import_module_attr", boom)
    code = preflight.run_preflight(
        backend=BACKEND,
        files=[BACKEND / "app" / "core" / "config.py"],
    )
    out = capsys.readouterr().out
    assert code == 1
    assert "config_import_FAIL" in out
    assert "category=import" in out
    assert SECRETISH not in out
    assert "SUPER_SECRET" not in out


def test_script_subprocess_exit_zero():
    """Run the script with -B against the real tree (offline imports only)."""
    import os

    py = sys.executable
    script = SCRIPTS_DIR / "release_preflight.py"
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(
        [py, "-B", str(script)],
        cwd=str(BACKEND),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "config_import_ok" in proc.stdout
    assert "celery_import_ok" in proc.stdout
    assert "get_settings" not in proc.stdout
