#!/usr/bin/env python3
"""Read-only release preflight for CureCompass production deploys.

Makes ZERO filesystem or process mutations (no chmod/chown, no service
restarts, no .env edits). Intended to run as the systemd service account
(e.g. curecompass) after git update and BEFORE service restart.

Checks:
  - current user identity
  - readability of application Python modules under app/
    (optionally limited to files changed since CC_PREFLIGHT_SINCE / --since)
  - offline import of app.core.config.settings, app.main, and
    app.workers.celery_app (API + worker/Beat entrypoints)
  - configured Responses model / reasoning effort (names only; no secrets)

Never prints API keys, DATABASE_URL, SECRET_KEY, .env contents, or raw
exception messages that might embed connection strings.

Does not call OpenAI, external providers, SMTP, databases, or Redis —
imports only construct in-process objects.
"""

from __future__ import annotations

import argparse
import getpass
import importlib
import os
import subprocess
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

# Prevent .pyc writes before any application import.
sys.dont_write_bytecode = True
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

IMPORT_TARGETS: tuple[tuple[str, str], ...] = (
    ("app.core.config", "settings"),
    ("app.main", "app"),
    ("app.workers.celery_app", "celery_app"),
)


def backend_root() -> Path:
    return Path(__file__).resolve().parents[1]


def safe_error_category(exc: BaseException) -> str:
    """Map exceptions to ops-safe labels without embedding secret-bearing text."""
    if isinstance(exc, PermissionError):
        return "permission"
    if isinstance(exc, ModuleNotFoundError):
        return "module_not_found"
    if isinstance(exc, ImportError):
        return "import"
    if isinstance(exc, AttributeError):
        return "attribute"
    if isinstance(exc, FileNotFoundError):
        return "file_not_found"
    if isinstance(exc, OSError):
        return "os"
    return "unexpected"


def format_safe_failure(prefix: str, exc: BaseException) -> str:
    return f"{prefix}_FAIL category={safe_error_category(exc)} type={type(exc).__name__}"


def iter_tracked_app_python(backend: Path) -> list[Path]:
    """List tracked backend/app/**/*.py via git when available; else walk app/."""
    app_dir = backend / "app"
    try:
        proc = subprocess.run(
            ["git", "-C", str(backend.parent), "ls-files", "backend/app"],
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            paths: list[Path] = []
            for line in proc.stdout.splitlines():
                rel = line.strip()
                if not rel.endswith(".py"):
                    continue
                # git ls-files paths are repo-root relative (backend/app/...).
                if rel.startswith("backend/"):
                    paths.append(backend.parent / rel)
                else:
                    paths.append(backend / rel)
            return sorted({p.resolve() for p in paths})
    except OSError:
        pass

    return sorted(p.resolve() for p in app_dir.rglob("*.py") if p.is_file())


def iter_changed_app_python(backend: Path, since_ref: str) -> list[Path]:
    """Python files under backend/app changed between since_ref and HEAD."""
    repo = backend.parent
    proc = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "diff",
            "--name-only",
            f"{since_ref}..HEAD",
            "--",
            "backend/app/**/*.py",
            "backend/app/",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError("git_diff_failed")
    paths: list[Path] = []
    for line in proc.stdout.splitlines():
        rel = line.strip()
        if not rel.endswith(".py"):
            continue
        if not (rel.startswith("backend/app/") or rel.startswith("app/")):
            continue
        path = (repo / rel) if rel.startswith("backend/") else (backend / rel)
        paths.append(path.resolve())
    # Always include config + entrypoints even if unchanged — import gate needs them readable.
    for required in (
        backend / "app" / "core" / "config.py",
        backend / "app" / "main.py",
        backend / "app" / "workers" / "celery_app.py",
    ):
        paths.append(required.resolve())
    return sorted(set(paths))


def python_files_to_check(backend: Path, since_ref: str | None) -> list[Path]:
    if since_ref:
        return iter_changed_app_python(backend, since_ref)
    return iter_tracked_app_python(backend)


def check_readable(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, f"missing path={path.as_posix()}"
    if not os.access(path, os.R_OK):
        try:
            mode = oct(path.stat().st_mode & 0o777)
        except OSError:
            mode = "unknown"
        return False, f"unreadable mode={mode} path={path.as_posix()}"
    try:
        mode = oct(path.stat().st_mode & 0o777)
    except OSError:
        mode = "unknown"
    return True, f"ok mode={mode} path={path.as_posix()}"


def import_module_attr(module_name: str, attr_name: str) -> object:
    mod = importlib.import_module(module_name)
    return getattr(mod, attr_name)


def run_preflight(
    *,
    backend: Path | None = None,
    since_ref: str | None = None,
    files: Sequence[Path] | None = None,
    skip_imports: bool = False,
) -> int:
    """Execute preflight. Returns process exit code (0 = PASS)."""
    root = (backend or backend_root()).resolve()
    os.chdir(root)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    print(f"preflight_user={getpass.getuser()}")
    print(f"preflight_uid={os.getuid() if hasattr(os, 'getuid') else 'n/a'}")
    print(f"preflight_cwd={root.as_posix()}")
    print("preflight_umask_note=deploy_shell_should_use_umask_022_for_git_checkout")
    print("preflight_bytecode=disabled")
    if since_ref:
        print(f"preflight_since={since_ref}")

    try:
        targets: Iterable[Path] = files if files is not None else python_files_to_check(root, since_ref)
        target_list = list(targets)
    except RuntimeError:
        print("readable_FAIL category=git_diff type=RuntimeError")
        print("preflight_result=FAIL")
        return 1

    if not target_list:
        print("readable_FAIL category=empty_file_list type=RuntimeError")
        print("preflight_result=FAIL")
        return 1

    print(f"readable_check_count={len(target_list)}")
    failed = False
    for path in target_list:
        ok, msg = check_readable(path)
        print(f"readable_{'ok' if ok else 'FAIL'}: {msg}")
        if not ok:
            failed = True

    if failed:
        print(
            "preflight_result=FAIL "
            "(service account cannot read application Python source; "
            "fix mode/ownership on listed files only — no recursive chmod/chown)"
        )
        return 1

    if skip_imports:
        print("preflight_result=PASS readable_only")
        return 0

    # Config via real application API: module-level `settings` singleton.
    try:
        settings_obj = import_module_attr("app.core.config", "settings")
        model = getattr(settings_obj, "openai_responses_model", "<unset>")
        effort = getattr(settings_obj, "openai_reasoning_effort", "<unset>")
        print(f"config_import_ok model={model} reasoning_effort={effort}")
    except Exception as exc:  # noqa: BLE001 — sanitized
        print(format_safe_failure("config_import", exc))
        print("preflight_result=FAIL")
        return 1

    try:
        app_obj = import_module_attr("app.main", "app")
        title = getattr(app_obj, "title", type(app_obj).__name__)
        print(f"app_import_ok title={title}")
    except Exception as exc:  # noqa: BLE001
        print(format_safe_failure("app_import", exc))
        print("preflight_result=FAIL")
        return 1

    try:
        celery_obj = import_module_attr("app.workers.celery_app", "celery_app")
        print(f"celery_import_ok name={getattr(celery_obj, 'main', type(celery_obj).__name__)}")
    except Exception as exc:  # noqa: BLE001
        print(format_safe_failure("celery_import", exc))
        print("preflight_result=FAIL")
        return 1

    print(
        "preflight_result=PASS "
        "(offline import/config only; not a live model, DB, Redis, or HTTP health probe)"
    )
    return 0


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only CureCompass release preflight")
    parser.add_argument(
        "--since",
        default=os.environ.get("CC_PREFLIGHT_SINCE") or None,
        help="If set, check readability of app/*.py changed since this git ref (plus entrypoints)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    return run_preflight(since_ref=args.since)


if __name__ == "__main__":
    raise SystemExit(main())
