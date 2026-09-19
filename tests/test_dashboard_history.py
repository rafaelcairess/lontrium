"""Persistent, privacy-safe dashboard history tests."""

import asyncio
import json
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.database import (
    Base,
    load_last_automatic_run,
    load_dashboard_history,
    sanitise_dashboard_details,
    save_last_automatic_run,
    save_dashboard_history,
)
from src.gui.state import DashboardState


def test_dashboard_history_restores_last_store_state():
    state = DashboardState()
    state.begin_run(["aliexpress"])
    state.begin_store("aliexpress")
    record = state.finish_store(
        "aliexpress",
        "15 moedas coletadas",
        details={"kind": "coins", "outcome": "collected", "claimedCoins": 15},
    )

    restored = DashboardState()
    restored.restore([record])
    payload = restored.snapshot(["aliexpress"])
    store = next(item for item in payload["stores"] if item["key"] == "aliexpress")

    assert payload["finishedAt"] == record["finishedAt"]
    assert "history" not in payload
    assert restored.history() == [record]
    assert store["lastRun"] == record["finishedAt"]
    assert store["details"]["claimedCoins"] == 15


def test_history_details_use_a_strict_display_allowlist():
    details = sanitise_dashboard_details({
        "kind": "games",
        "account": "private@example.invalid",
        "cookie": "secret-cookie",
        "items": [{
            "title": "Example Game",
            "outcome": "claimed",
            "url": "https://secret.invalid/redeem/ABC-123",
            "code": "ABC-123",
        }],
    })

    assert details == {"kind": "games", "items": [{"title": "Example Game", "outcome": "claimed"}]}
    serialized = json.dumps(details)
    assert "private@example.invalid" not in serialized
    assert "secret.invalid" not in serialized
    assert "ABC-123" not in serialized
    assert "secret-cookie" not in serialized


def test_dashboard_history_survives_a_new_database_session(tmp_path):
    async def scenario():
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'history.db'}")
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        now = datetime.now(timezone.utc).isoformat()
        record = {
            "runId": "run-1",
            "store": "epic",
            "state": "success",
            "messageKey": "status.resultGames",
            "message": "1 game checked",
            "startedAt": now,
            "finishedAt": now,
            "details": {
                "kind": "games",
                "items": [{"title": "Example Game", "outcome": "claimed", "code": "DO-NOT-SAVE"}],
            },
        }
        await save_dashboard_history(record, factory)
        rows = await load_dashboard_history(session_factory=factory)
        await engine.dispose()
        return rows

    rows = asyncio.run(scenario())
    assert len(rows) == 1
    assert rows[0]["store"] == "epic"
    assert rows[0]["details"] == {
        "kind": "games",
        "items": [{"title": "Example Game", "outcome": "claimed"}],
    }
    assert "DO-NOT-SAVE" not in json.dumps(rows)


def test_automatic_run_cooldown_survives_a_new_database_session(tmp_path):
    async def scenario():
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'runtime.db'}")
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        expected = datetime(2026, 9, 6, 12, 30, tzinfo=timezone.utc)
        await save_last_automatic_run(expected, factory)
        actual = await load_last_automatic_run(factory)
        await engine.dispose()
        return expected, actual

    expected, actual = asyncio.run(scenario())
    assert actual == expected
