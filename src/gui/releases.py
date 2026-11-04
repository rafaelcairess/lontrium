"""Offline Lontrium release history and one-time update notice state."""

from __future__ import annotations

import json
from pathlib import Path

from src.core.config import cfg
from src.version import __version__

CATALOG_PATH = Path(__file__).resolve().parent / "static" / "release-history.json"
STATE_FILE = "ui-state.json"


def _state_path(path: Path | None = None) -> Path:
    return path or (cfg._data_dir / STATE_FILE)


def _read_state(path: Path | None = None) -> dict:
    try:
        payload = json.loads(_state_path(path).read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _catalog() -> list[dict]:
    try:
        payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        releases = payload.get("releases", [])
        return releases if isinstance(releases, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def get_release_history(*, setup_complete: bool = True, state_path: Path | None = None) -> dict:
    """Return bundled public history and whether this installation should announce the release."""
    last_seen = str(_read_state(state_path).get("lastSeenVersion") or "")
    return {
        "currentVersion": __version__,
        "lastSeenVersion": last_seen or None,
        "showNotice": bool(setup_complete and last_seen != __version__),
        "releases": _catalog(),
    }


def acknowledge_release(version: str, path: Path | None = None) -> dict:
    """Persist acknowledgement only for the exact installed version."""
    if str(version or "") != __version__:
        raise ValueError("Only the installed version can be acknowledged")
    target = _state_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp")
    temporary.write_text(
        json.dumps({"lastSeenVersion": __version__}, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary.replace(target)
    try:
        target.chmod(0o600)
    except OSError:
        pass
    return {"acknowledged": True, "version": __version__}

