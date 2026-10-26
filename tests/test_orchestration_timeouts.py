"""Bounded orchestration keeps scheduled runs from retaining Docker indefinitely."""

import asyncio

import main
from src.gui.state import DashboardState


def _quiet_runtime(monkeypatch, claimers, *, store_timeout, run_timeout):
    state = DashboardState()
    persisted = []

    async def no_notify(*_args, **_kwargs):
        return None

    async def persist(record):
        if record:
            persisted.append(record)

    monkeypatch.setattr(main, "dashboard_state", state)
    monkeypatch.setattr(main, "_get_active_claimers", lambda _stores=None: claimers)
    monkeypatch.setattr(main, "notify", no_notify)
    monkeypatch.setattr(main, "notify_if_update_available", no_notify)
    monkeypatch.setattr(main, "_persist_dashboard_result", persist)
    monkeypatch.setattr(main.cfg, "store_run_timeout", store_timeout)
    monkeypatch.setattr(main.cfg, "claim_run_timeout", run_timeout)
    monkeypatch.setattr(main.cfg, "notify_summary", False)
    return state, persisted


def test_store_timeout_is_persisted_and_next_store_runs(monkeypatch):
    calls = []
    cleanup_ran = []

    async def slow():
        try:
            await asyncio.sleep(0.1)
        finally:
            cleanup_ran.append(True)

    async def fast():
        calls.append("fast")
        return {}

    state, persisted = _quiet_runtime(
        monkeypatch,
        [("Steam", slow), ("Epic Games", fast)],
        store_timeout=0.01,
        run_timeout=1,
    )

    asyncio.run(main.run_claimers())

    assert calls == ["fast"]
    assert cleanup_ran == [True]
    assert [item["messageKey"] for item in persisted] == ["status.timeout", "status.completedNoChanges"]
    assert state.snapshot(["steam", "epic"])["running"] is False


def test_global_timeout_cancels_cleanup_and_persists_remaining_stores(monkeypatch):
    cleanup_ran = []

    async def stuck():
        try:
            await asyncio.sleep(1)
        finally:
            cleanup_ran.append(True)

    async def never_reached():
        raise AssertionError("global timeout should stop the queue")

    state, persisted = _quiet_runtime(
        monkeypatch,
        [("Steam", stuck), ("Epic Games", never_reached)],
        store_timeout=1,
        run_timeout=0.02,
    )

    asyncio.run(main.run_claimers())

    assert cleanup_ran == [True]
    assert len(persisted) == 2
    assert {item["messageKey"] for item in persisted} == {"status.runTimeout"}
    assert state.snapshot(["steam", "epic"])["running"] is False


def test_windows_host_preflight_skips_duplicate_container_probe(monkeypatch):
    calls = []

    async def fake_run(stores, *, retry_incomplete=False):
        calls.append((stores, retry_incomplete))

    def unexpected_probe():
        raise AssertionError("the Windows host already completed the resource preflight")

    monkeypatch.setattr(main, "run_claimers", fake_run)
    monkeypatch.setattr(main, "sample_resources", unexpected_probe)
    monkeypatch.setattr(main.cfg, "resource_guard_enabled", True)
    monkeypatch.setattr(main, "save_last_automatic_run", lambda *_args, **_kwargs: asyncio.sleep(0))

    asyncio.run(main.run_claimers_scheduled(
        ["steam"],
        automatic=True,
        retry_incomplete=True,
        host_preflight_complete=True,
    ))

    assert calls == [(["steam"], True)]


def test_dashboard_waits_for_delayed_run_identifier(monkeypatch):
    state = DashboardState()
    monkeypatch.setattr(main, "dashboard_state", state)

    async def delayed_start():
        await asyncio.sleep(0.15)
        return state.begin_run(["steam"])

    async def scenario():
        task = asyncio.create_task(delayed_start())
        run_id = await main._wait_for_dashboard_run_start(task, None, timeout=1)
        await task
        return run_id

    run_id = asyncio.run(scenario())

    assert run_id == state.current_run_id()
