"""Resource-gate policy tests independent of Windows or Docker."""

from datetime import datetime
from zoneinfo import ZoneInfo

from src.core import resource_guard


def snapshot(**overrides):
    values = {
        "total_memory_mb": 16_000,
        "available_memory_mb": 8_000,
        "cpu_percent": 20,
        "foreground_name": "explorer",
        "foreground_memory_mb": 500,
        "foreground_fullscreen": False,
    }
    values.update(overrides)
    return resource_guard.ResourceSnapshot(**values)


def test_low_memory_defers_a_normal_slot(monkeypatch):
    monkeypatch.setattr(resource_guard.cfg, "resource_min_free_memory_mb", 3_072)
    monkeypatch.setattr(resource_guard.cfg, "resource_critical_free_memory_mb", 1_024)

    decision = resource_guard.evaluate(snapshot(available_memory_mb=2_000))

    assert decision.defer is True
    assert decision.critical is False
    assert "memória" in decision.reason


def test_last_slot_runs_through_soft_pressure(monkeypatch):
    monkeypatch.setattr(resource_guard.cfg, "resource_min_free_memory_mb", 3_072)
    monkeypatch.setattr(resource_guard.cfg, "resource_critical_free_memory_mb", 1_024)
    monkeypatch.setattr(resource_guard.cfg, "resource_last_slot_override", True)

    decision = resource_guard.evaluate(snapshot(available_memory_mb=2_000), last_slot=True)

    assert decision.defer is False
    assert "último" in decision.reason


def test_last_slot_still_defers_critical_memory(monkeypatch):
    monkeypatch.setattr(resource_guard.cfg, "resource_min_free_memory_mb", 3_072)
    monkeypatch.setattr(resource_guard.cfg, "resource_critical_free_memory_mb", 1_024)

    decision = resource_guard.evaluate(snapshot(available_memory_mb=900), last_slot=True)

    assert decision.defer is True
    assert decision.critical is True


def test_fullscreen_heavy_application_defers(monkeypatch):
    monkeypatch.setattr(resource_guard.cfg, "resource_min_free_memory_mb", 3_072)

    decision = resource_guard.evaluate(snapshot(
        foreground_name="game",
        foreground_memory_mb=4_000,
        foreground_fullscreen=True,
    ))

    assert decision.defer is True
    assert "primeiro plano" in decision.reason


def test_next_fixed_slot_and_last_slot():
    current = datetime(2026, 10, 23, 18, 30, tzinfo=ZoneInfo("America/Sao_Paulo"))

    next_slot, last_slot = resource_guard.next_fixed_slot([(12, 0), (16, 0), (19, 0)], now=current)
    assert next_slot.hour == 19 and next_slot.day == 23
    assert last_slot is False

    next_slot, last_slot = resource_guard.next_fixed_slot([(12, 0), (16, 0), (19, 0)], now=current.replace(hour=20))
    assert next_slot.hour == 12 and next_slot.day == 24
    assert last_slot is True
