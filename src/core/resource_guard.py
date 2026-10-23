"""Automatic-run resource protection.

Packaged Windows runs are checked by the host launcher before Docker starts. This
module is the fallback for source/native runs and deliberately classifies the
machine as busy instead of trying to identify a game by executable name.
"""

from __future__ import annotations

import ctypes
import logging
import os
from ctypes import wintypes
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import psutil

from src.core.config import cfg

logger = logging.getLogger("fgc.resource_guard")


@dataclass(frozen=True)
class ResourceSnapshot:
    total_memory_mb: int
    available_memory_mb: int
    cpu_percent: float
    foreground_name: str | None = None
    foreground_memory_mb: int = 0
    foreground_fullscreen: bool = False


@dataclass(frozen=True)
class ResourceDecision:
    defer: bool
    critical: bool
    reason: str = ""
    snapshot: ResourceSnapshot | None = None


def _foreground_process() -> tuple[psutil.Process | None, bool]:
    """Return the foreground process and whether its window covers the screen."""
    if os.name != "nt":
        return None, False
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None, False
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        process = psutil.Process(pid.value)
        rect = wintypes.RECT()
        fullscreen = bool(
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            and rect.left <= 0
            and rect.top <= 0
            and rect.right >= user32.GetSystemMetrics(0)
            and rect.bottom >= user32.GetSystemMetrics(1)
        )
        return process, fullscreen
    except (AttributeError, OSError, psutil.Error):
        return None, False


def sample_resources(sample_seconds: float = 0.5) -> ResourceSnapshot:
    """Take a cheap snapshot suitable for a scheduler preflight."""
    memory = psutil.virtual_memory()
    foreground, fullscreen = _foreground_process()
    name = None
    process_memory = 0
    if foreground is not None:
        try:
            name = foreground.name()
            process_memory = int(foreground.memory_info().rss / 1024 / 1024)
        except psutil.Error:
            pass
    cpu = float(psutil.cpu_percent(interval=max(0.05, sample_seconds)))
    return ResourceSnapshot(
        total_memory_mb=int(memory.total / 1024 / 1024),
        available_memory_mb=int(memory.available / 1024 / 1024),
        cpu_percent=cpu,
        foreground_name=name,
        foreground_memory_mb=process_memory,
        foreground_fullscreen=fullscreen,
    )


def evaluate(snapshot: ResourceSnapshot, *, last_slot: bool = False) -> ResourceDecision:
    """Apply the safety policy to a measured snapshot.

    The final daily slot may run despite a soft pressure signal so a daily task
    is not silently lost. Critical low-memory pressure still blocks it.
    """
    min_free = max(512, int(cfg.resource_min_free_memory_mb))
    critical_free = max(256, min(int(cfg.resource_critical_free_memory_mb), min_free))
    critical = snapshot.available_memory_mb <= critical_free
    reasons: list[str] = []
    if snapshot.available_memory_mb < min_free:
        reasons.append("memória disponível baixa")
    if snapshot.cpu_percent >= max(50, min(99, int(cfg.resource_cpu_threshold))):
        reasons.append("CPU ocupada")
    if snapshot.foreground_fullscreen and snapshot.foreground_name and snapshot.foreground_memory_mb >= 1024:
        reasons.append(f"aplicação em primeiro plano ({snapshot.foreground_name})")

    if not reasons:
        return ResourceDecision(False, False, snapshot=snapshot)
    if last_slot and not critical and cfg.resource_last_slot_override:
        return ResourceDecision(False, False, "último horário: execução autorizada", snapshot)
    return ResourceDecision(True, critical, "; ".join(reasons), snapshot)


def next_fixed_slot(
    fixed_times: list[tuple[int, int]],
    *,
    now: datetime | None = None,
) -> tuple[datetime | None, bool]:
    """Return the next fixed slot and whether the current moment is past today's last slot."""
    if not fixed_times:
        return None, False
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    ordered = sorted(set(fixed_times))
    candidates = [
        current.replace(hour=hour, minute=minute, second=0, microsecond=0)
        for hour, minute in ordered
    ]
    future = [candidate for candidate in candidates if candidate > current]
    if future:
        return min(future), False
    tomorrow = current + timedelta(days=1)
    return tomorrow.replace(hour=ordered[0][0], minute=ordered[0][1], second=0, microsecond=0), True
