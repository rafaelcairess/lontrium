"""Thread-safe runtime state consumed by the local dashboard."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4


STORE_META = {
    "steam": {"name": "Steam", "badge": "S", "color": "#1b9fff"},
    "epic": {"name": "Epic Games", "badge": "E", "color": "#ffffff"},
    "fab": {"name": "Fab", "badge": "F", "color": "#6e56cf"},
    "prime": {"name": "Prime Gaming", "badge": "P", "color": "#9146ff"},
    "gog": {"name": "GOG", "badge": "G", "color": "#b65cff"},
    "ubisoft": {"name": "Ubisoft", "badge": "U", "color": "#29a3ff"},
    "unity": {"name": "Unity", "badge": "U", "color": "#ffffff"},
    "gamerpower": {"name": "GamerPower", "badge": "⚡", "color": "#ffb020"},
    "aliexpress": {"name": "AliExpress", "badge": "AE", "color": "#ff4747"},
    "shopee": {
        "name": "Shopee", "badge": "S", "color": "#ee4d2d",
        "authNoteKey": "storeAuth.shopee",
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_count(value) -> int | None:
    """Return a non-negative dashboard-safe integer, never a boolean."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _game_outcome(status: str) -> str:
    """Reduce store-specific status text to a small, secret-free vocabulary."""
    normalized = status.lower()
    if "fail" in normalized or "blocked" in normalized or "error" in normalized:
        return "failed"
    if "dry run" in normalized or "available" in normalized:
        return "available"
    if "already" in normalized or "exist" in normalized:
        return "owned"
    if "needs linking" in normalized:
        return "action_required"
    if "skip" in normalized:
        return "skipped"
    if "claimed" in normalized or "redeemed" in normalized or normalized.startswith("code:"):
        return "claimed"
    return "processed"


def summarize_store_result(store_key: str, result) -> tuple[str, dict | None]:
    """Build the dashboard summary using an explicit allowlist of safe fields."""
    if not isinstance(result, dict):
        return "Concluído sem novidades", None

    if store_key == "steam" and result.get("statusCode") == "no_active_giveaways":
        return "Nenhuma promoção Free-to-Keep ativa", None

    if store_key in {"aliexpress", "shopee"} and isinstance(result.get("checkin"), dict):
        source = result["checkin"]
        outcome = source.get("outcome")
        if outcome not in {"collected", "collected_manual", "already_collected", "not_collected", "available"}:
            outcome = "not_collected"
        details = {
            "kind": "coins",
            "outcome": outcome,
            "claimedCoins": _safe_count(source.get("claimedCoins")),
            "offeredCoins": _safe_count(source.get("offeredCoins")),
            "balance": _safe_count(source.get("balance")),
            "streakDays": _safe_count(source.get("streakDays")),
            "tomorrowCoins": _safe_count(source.get("tomorrowCoins")),
        }
        claimed = details["claimedCoins"]
        if outcome in {"collected", "collected_manual"}:
            message = f"{claimed} moedas coletadas" if claimed is not None else "Moedas coletadas"
        elif outcome == "already_collected":
            message = "Moedas já coletadas hoje"
        elif outcome == "available":
            message = "Coleta disponível (simulação)"
        else:
            message = "Moedas não coletadas"
        return message, details

    items = []
    for game in result.get("games") or []:
        if not isinstance(game, dict):
            continue
        title = game.get("title")
        status = game.get("status")
        if not isinstance(title, str) or not title.strip():
            continue
        items.append({
            "title": title.strip()[:180],
            "outcome": _game_outcome(status if isinstance(status, str) else ""),
        })

    if not items:
        return "Concluído sem novidades", None

    claimed = sum(item["outcome"] == "claimed" for item in items)
    if claimed:
        message = f"{claimed} resgatado{'s' if claimed != 1 else ''} · {len(items)} verificado{'s' if len(items) != 1 else ''}"
    else:
        message = f"{len(items)} verificado{'s' if len(items) != 1 else ''}"
    return message, {"kind": "games", "items": items}


def store_result_message_key(store_key: str, result) -> str | None:
    """Translate allow-listed store result codes into stable client keys."""
    if store_key == "steam" and isinstance(result, dict):
        if result.get("statusCode") == "no_active_giveaways":
            return "status.noActiveGiveaways"
    return None


class DashboardState:
    def __init__(self) -> None:
        self._lock = Lock()
        self._running = False
        self._run_id: str | None = None
        self._started_at: str | None = None
        self._finished_at: str | None = None
        self._store_runs: dict[str, tuple[str, str]] = {}
        self._history: list[dict] = []
        self._manual_actions: dict[str, dict] = {}
        self._stores = {
            key: {
                **meta,
                "key": key,
                "state": "idle",
                "message": "Aguardando execução",
                "messageKey": "status.waiting",
                "lastRun": None,
                "details": None,
            }
            for key, meta in STORE_META.items()
        }

    def request_manual_action(self, kind: str, store: str) -> str | None:
        """Publish a deduplicated, secret-free action for the local Windows helper."""
        if kind != "captcha" or store not in STORE_META:
            return None
        with self._lock:
            for event_id, event in self._manual_actions.items():
                if event["kind"] == kind and event["store"] == store:
                    return event_id
            event_id = uuid4().hex
            self._manual_actions[event_id] = {
                "id": event_id,
                "kind": kind,
                "store": store,
                "createdAt": _now(),
            }
            return event_id

    def resolve_manual_action(self, event_id: str | None) -> None:
        if not event_id:
            return
        with self._lock:
            self._manual_actions.pop(event_id, None)

    def manual_actions(self, enabled: bool) -> dict:
        """Return only allow-listed local notification data; never page or account data."""
        with self._lock:
            events = deepcopy(list(self._manual_actions.values())) if enabled else []
        return {"enabled": bool(enabled), "events": events}

    def begin_run(self, store_keys: list[str]) -> None:
        with self._lock:
            self._running = True
            self._run_id = uuid4().hex
            self._started_at = _now()
            for key in store_keys:
                if key in self._stores:
                    self._store_runs[key] = (self._run_id, self._started_at)
                    self._stores[key].update(
                        state="queued", message="Na fila", messageKey="status.queued", details=None
                    )

    def begin_store(self, key: str) -> None:
        with self._lock:
            if key in self._stores:
                self._stores[key].update(
                    state="running", message="Executando agora", messageKey="status.runningNow", details=None
                )

    def finish_store(
        self,
        key: str,
        message: str,
        *,
        failed: bool = False,
        details: dict | None = None,
        message_key: str | None = None,
    ) -> dict | None:
        with self._lock:
            if key in self._stores:
                finished_at = _now()
                run_id, started_at = self._store_runs.pop(
                    key, (self._run_id or uuid4().hex, self._started_at or finished_at)
                )
                resolved_key = message_key or (
                    "status.failed" if failed else (
                        "status.resultCoins" if details and details.get("kind") == "coins" else
                        "status.resultGames" if details and details.get("kind") == "games" else
                        "status.completedNoChanges"
                    )
                )
                self._stores[key].update(
                    state="error" if failed else "success",
                    message=message,
                    messageKey=resolved_key,
                    lastRun=finished_at,
                    details=deepcopy(details),
                )
                record = {
                    "runId": run_id,
                    "store": key,
                    "state": "error" if failed else "success",
                    "message": message,
                    "messageKey": resolved_key,
                    "startedAt": started_at,
                    "finishedAt": finished_at,
                    "details": deepcopy(details),
                }
                self._history.insert(0, deepcopy(record))
                del self._history[250:]
                return record
            return None

    def finish_run(self) -> None:
        with self._lock:
            # Independent store actions may overlap a scheduled run. Keep the
            # global indicator active while any row is still queued or running.
            self._running = any(
                store["state"] in {"queued", "running"}
                for store in self._stores.values()
            )
            if not self._running:
                self._finished_at = _now()

    def restore(self, records: list[dict]) -> None:
        """Restore recent safe results loaded from the persistent database."""
        with self._lock:
            safe_records = []
            restored_stores = set()
            for record in records[:250]:
                if not isinstance(record, dict) or record.get("store") not in self._stores:
                    continue
                if record.get("state") not in {"success", "error"}:
                    continue
                safe_records.append(deepcopy(record))
                key = record["store"]
                if key not in restored_stores:
                    self._stores[key].update(
                        state=record["state"],
                        message=record.get("message") or "",
                        messageKey=record.get("messageKey") or "status.completedNoChanges",
                        lastRun=record.get("finishedAt"),
                        details=deepcopy(record.get("details")),
                    )
                    restored_stores.add(key)
            self._history = safe_records
            self._finished_at = safe_records[0].get("finishedAt") if safe_records else None

    def snapshot(self, enabled: list[str], schedule: dict | None = None) -> dict:
        with self._lock:
            stores = deepcopy(list(self._stores.values()))
            payload = {
                "running": self._running,
                "startedAt": self._started_at,
                "finishedAt": self._finished_at,
                "stores": stores,
                "history": deepcopy(self._history),
            }
        enabled_set = set(enabled)
        for store in payload["stores"]:
            store["enabled"] = store["key"] in enabled_set
        payload["schedule"] = schedule or {}
        return payload


dashboard_state = DashboardState()
