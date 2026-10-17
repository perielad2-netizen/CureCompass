#!/usr/bin/env python3
"""Read-only release preflight for CureCompass production deploys.

Makes ZERO filesystem or process changes. Intended to run as the systemd
service account (e.g. curecompass) after git update and BEFORE service restart.

Checks:
  - current user identity
  - readability of critical Python modules
  - offline import of app.core.config and app.main
  - configured Responses model / reasoning effort (names only; no secrets)

Never prints API keys, DATABASE_URL, SECRET_KEY, or .env contents.
"""

from __future__ import annotations

import getpass
import importlib
import os
import sys
from pathlib import Path

# Critical paths relative to backend/ that must be readable by the service account.
CRITICAL_RELPATHS = (
    "app/core/config.py",
    "app/main.py",
    "app/services/openai_responses.py",
)


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _check_readable(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, f"missing: {path}"
    if not os.access(path, os.R_OK):
        try:
            mode = oct(path.stat().st_mode & 0o777)
        except OSError:
            mode = "unknown"
        return False, f"unreadable mode={mode} path={path}"
    try:
        mode = oct(path.stat().st_mode & 0o777)
    except OSError:
        mode = "unknown"
    return True, f"ok mode={mode} path={path}"


def main() -> int:
    backend = _backend_root()
    os.chdir(backend)
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))

    print(f"preflight_user={getpass.getuser()}")
    print(f"preflight_uid={os.getuid() if hasattr(os, 'getuid') else 'n/a'}")
    print(f"preflight_cwd={backend}")
    print(f"preflight_umask_note=deploy_shell_should_use_umask_022_for_git_checkout")

    failed = False
    for rel in CRITICAL_RELPATHS:
        ok, msg = _check_readable(backend / rel)
        print(f"readable_{'ok' if ok else 'FAIL'}: {msg}")
        if not ok:
            failed = True

    if failed:
        print(
            "preflight_result=FAIL "
            "(service account cannot read critical source; "
            "fix mode/ownership on listed files only — no recursive chmod/chown)"
        )
        return 1

    try:
        config_mod = importlib.import_module("app.core.config")
        get_settings = getattr(config_mod, "get_settings")
        settings = get_settings()
        model = getattr(settings, "openai_responses_model", "<unset>")
        effort = getattr(settings, "openai_reasoning_effort", "<unset>")
        # Names only — never dump settings / env.
        print(f"config_import_ok model={model} reasoning_effort={effort}")
    except PermissionError as exc:
        print(f"config_import_FAIL PermissionError: {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001 — surface type only for ops
        print(f"config_import_FAIL {type(exc).__name__}: {exc}")
        return 1

    try:
        main_mod = importlib.import_module("app.main")
        app = getattr(main_mod, "app", None)
        title = getattr(app, "title", type(app).__name__)
        print(f"app_import_ok title={title}")
    except PermissionError as exc:
        print(f"app_import_FAIL PermissionError: {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"app_import_FAIL {type(exc).__name__}: {exc}")
        return 1

    print("preflight_result=PASS (offline import/config only; not a live model or health probe)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
