"""Free Games Claimer Remaster – main entry point.

This is the central "brain" of the application. When the Docker container starts,
this file is the first thing that runs. Here is what it does:

  1. Prints a startup banner with the version number and author.
  2. Initialises the SQLite database (creates tables if they don't exist).
  3. Starts a scheduler that automatically runs the claiming process every X hours.
  4. On each run, it goes through each enabled store (Steam, Epic, Prime, GOG)
     and tries to claim any free games available.
  5. After all stores are done, it checks if there are any GOG codes from
     Prime Gaming that still need to be redeemed.
"""

from __future__ import annotations

import asyncio
import importlib
import logging
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.base import STATE_PAUSED
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.core.config import cfg, settings_warnings
from src.core.privacy import mask_account
from src.core.database import (
    init_db,
    load_dashboard_history,
    load_last_automatic_run,
    save_dashboard_history,
    save_last_automatic_run,
)
from src.core.selection import apply_run_selection
from src.core.updates import get_update_status, notify_if_update_available
from src.core.notifier import notify
from src.gui.settings import (
    SettingsError,
    complete_setup,
    get_settings,
    get_setup_state,
    save_settings,
)
from src.gui.state import (
    dashboard_state,
    store_result_message_key,
    store_result_succeeded,
    summarize_store_result,
)
from src.version import __version__, __author__, __repo__, __contributors__

# ---------------------------------------------------------------------------
# Logging – user-friendly by default, verbose only on errors
# ---------------------------------------------------------------------------
from rich.logging import RichHandler
from rich.markup import escape
from rich.console import Console

# This filter automatically adds the store name (e.g. "[Steam]", "[Epic]")
# in front of every log message, so you can easily tell which module is talking.
class StorePrefixFilter(logging.Filter):
    def filter(self, record):
        if record.name.startswith("fgc."):
            store = record.name.split(".")[-1]
            if store in ("epic", "steam", "gog", "prime", "aliexpress", "shopee", "ubisoft", "fab", "unity"):
                store_map = {"gog": "GOG", "epic": "Epic", "steam": "Steam", "prime": "Prime", "aliexpress": "AliExpress", "shopee": "Shopee", "ubisoft": "Ubisoft", "fab": "Fab", "unity": "Unity"}
                prefix = escape(f"[{store_map[store]}]")
                # Prepend to the message template
                record.msg = f"{prefix} {record.msg}"
        return True

handler = RichHandler(
    console=Console(width=500),
    rich_tracebacks=True,
    show_path=False,       # hide file:line references
    show_level=True,
    show_time=True,        # Re-enabled per user request
    markup=True,
)
handler.addFilter(StorePrefixFilter())

logging.basicConfig(
    level=logging.DEBUG if cfg.debug else logging.INFO,
    format="%(message)s",
    handlers=[handler],
)
logger = logging.getLogger("fgc")

# Libraries that would otherwise bury our own diagnostics: every CDP frame, every
# HTTP handshake, every SQLite call. DEBUG=true is about the bot, DEBUG_LIBS about these.
NOISY_LIBRARIES = (
    "nodriver", "uc", "websockets", "httpx", "httpcore",
    "aiosqlite", "sqlalchemy", "apscheduler", "tzlocal", "asyncio", "apprise",
)
if not cfg.debug_libs:
    for _name in NOISY_LIBRARIES:
        logging.getLogger(_name).setLevel(logging.WARNING)


# asyncio warns about Chrome PIDs we deliberately reaped ourselves in close_browser().
class ReapedChildFilter(logging.Filter):
    def filter(self, record):
        return not str(record.msg).startswith("Unknown child process pid")

logging.getLogger("asyncio").addFilter(ReapedChildFilter())

# ---------------------------------------------------------------------------
# Store registry – canonical name → (display name, coroutine function)
# ---------------------------------------------------------------------------

# Registry of all available store claimers.
# Each entry maps a short name to display name + import target. Importing store
# modules starts the heavy browser stack, so resolve the function only for a run.
ALL_CLAIMERS: dict[str, tuple[str, str]] = {
    "steam":      ("Steam",        "src.stores.steam:claim_steam"),
    "epic":       ("Epic Games",   "src.stores.epic:claim_epic"),
    "fab":        ("Fab",          "src.stores.epic_fab:claim_fab"),
    "prime":      ("Prime Gaming", "src.stores.prime:claim_prime"),
    "gog":        ("GOG",          "src.stores.gog:claim_gog"),
    "ubisoft":    ("Ubisoft",      "src.stores.ubisoft:claim_ubisoft"),
    "unity":      ("Unity",        "src.stores.unity:claim_unity"),
    "gamerpower": ("GamerPower",   "src.stores.gamerpower:claim_gamerpower"),
    "aliexpress": ("AliExpress",   "src.stores.aliexpress:claim_aliexpress"),
    "shopee":     ("Shopee",       "src.stores.shopee:claim_shopee"),
}

# What runs when neither the CLI nor STORES names anything. GamerPower goes last so the
# stores with their own module claim first and its database dedup can do its job.
DEFAULT_STORES: list[str] = ["steam", "epic", "fab", "prime", "gog", "ubisoft",
                             "aliexpress", "gamerpower"]

# Display name (e.g. "Prime Gaming") → canonical store key (e.g. "prime").
_DISPLAY_TO_KEY: dict[str, str] = {disp: key for key, (disp, _) in ALL_CLAIMERS.items()}


def _store_key(name: str) -> str:
    """Map a display name or key to the canonical store key."""
    return _DISPLAY_TO_KEY.get(name, (name or "").lower())


# Accepted aliases → canonical name
_ALIASES: dict[str, str] = {
    "steam":         "steam",
    "steam-games":   "steam",
    "epic":          "epic",
    "epic-games":    "epic",
    "epicgames":     "epic",
    "fab":           "fab",
    "epic-fab":      "fab",
    "prime":         "prime",
    "prime-gaming":  "prime",
    "primegaming":   "prime",
    "amazon":        "prime",
    "gog":           "gog",
    "ubisoft":       "ubisoft",
    "ubi":           "ubisoft",
    "unity":         "unity",
    "unity-assets":  "unity",
    "gamerpower":    "gamerpower",
    "gp":            "gamerpower",
    "aliexpress":    "aliexpress",
    "ae":            "aliexpress",
    "shopee":        "shopee",
    "sh":            "shopee",
}

_FIXED_TIME_RE = re.compile(r"^\d{2}:\d{2}$")
_CLAIM_JOB_OPTIONS = {
    "max_instances": 1,
    "coalesce": True,
    "misfire_grace_time": 1800,
}
_claim_run_lock = asyncio.Lock()
_dashboard_run_task: asyncio.Task | None = None
_dashboard_individual_tasks: set[asyncio.Task] = set()
_dashboard_individual_stores: set[str] = set()


def _parse_fixed_times(raw: str) -> list[tuple[int, int]]:
    """Parse SCHEDULER_FIXED_TIMES as comma-separated HH:MM values."""
    if not raw.strip():
        return []

    fixed_times: list[tuple[int, int]] = []
    invalid: list[str] = []
    seen: set[tuple[int, int]] = set()

    for value in (part.strip() for part in raw.split(",")):
        if not value:
            continue

        if not _FIXED_TIME_RE.fullmatch(value):
            invalid.append(value)
            continue

        hour, minute = (int(part) for part in value.split(":", 1))
        if hour > 23 or minute > 59:
            invalid.append(value)
            continue

        key = (hour, minute)
        if key in seen:
            continue

        seen.add(key)
        fixed_times.append(key)

    if invalid:
        logger.warning(
            "Ignoring invalid SCHEDULER_FIXED_TIMES value(s): %s. "
            "Use comma-separated HH:MM times, for example 07:30,17:05,21:30.",
            ", ".join(invalid),
        )

    return fixed_times


def _scheduler_timezone() -> ZoneInfo:
    """Return the configured scheduler timezone or fail with a clear message."""
    try:
        return ZoneInfo(cfg.scheduler_timezone)
    except ZoneInfoNotFoundError as exc:
        logger.error(
            "Invalid SCHEDULER_TIMEZONE '%s'. Use an IANA timezone name "
            "such as UTC, Europe/Berlin, America/New_York, or Asia/Tokyo.",
            cfg.scheduler_timezone,
        )
        raise SystemExit(2) from exc


def _resolve_stores(raw: list[str]) -> list[str]:
    """Resolve a list of user-provided store names to canonical keys."""
    resolved = []
    for name in raw:
        key = _ALIASES.get(name.lower().strip())
        if key is None:
            logger.warning("Unknown store '%s' – ignoring. Valid: %s",
                           name, ", ".join(ALL_CLAIMERS.keys()))
            continue
        if key not in resolved:
            resolved.append(key)
    return resolved


def _warn_about_settings() -> None:
    """Name the settings that do nothing, instead of ignoring them in silence (issue #40)."""
    for line in settings_warnings():
        name = line.split(" ", 1)[0].split("=", 1)[0]
        hint = ""
        if name.endswith("_ENABLE") and _ALIASES.get(name[:-7].lower()) in ALL_CLAIMERS:
            hint = " Stores are chosen with STORES=..., there is no switch of its own for this one."
        logger.warning("%s%s", line, hint)

    unknown = sorted(cfg.notify_skip_stores - set(ALL_CLAIMERS))
    if unknown:
        logger.warning("NOTIFY_SKIP_STORES names %s, which is not a store, so nothing is silenced there. "
                       "Valid: %s", ", ".join(unknown), ", ".join(ALL_CLAIMERS))


def _get_active_store_keys(
    requested_stores: list[str] | None = None,
    *,
    publish_selection: bool = True,
) -> list[str]:
    """Determine which store keys are active without importing store modules.

    Priority:
      1. CLI positional args  (e.g.  ``python main.py steam prime``)
      2. ``STORES`` env var   (e.g.  ``STORES=steam,prime``)
      3. ``DEFAULT_STORES``   (default)
    """
    # An explicit dashboard selection has priority over CLI and environment.
    cli_stores = [a for a in sys.argv[1:] if not a.startswith("-")]
    if requested_stores is not None:
        selected = _resolve_stores(requested_stores)
    elif cli_stores:
        selected = _resolve_stores(cli_stores)
    elif cfg.stores:
        selected = _resolve_stores([s for s in cfg.stores.split(",") if s.strip()])
    else:
        selected = list(DEFAULT_STORES)

    # Only a real run publishes this selection. Dashboard polling is read-only
    # and must not rewrite global run state or flood the logs every few seconds.
    if publish_selection:
        apply_run_selection(selected)
        logger.debug("Store selection: cli=%s STORES=%r -> %s", cli_stores, cfg.stores, selected)
    return [key for key in selected if key in ALL_CLAIMERS]


def _get_active_claimers(requested_stores: list[str] | None = None) -> list[tuple[str, object]]:
    """Resolve only the selected store callables immediately before a run."""
    claimers = []
    for key in _get_active_store_keys(requested_stores):
        display_name, target = ALL_CLAIMERS[key]
        module_name, function_name = target.split(":", 1)
        function = getattr(importlib.import_module(module_name), function_name)
        claimers.append((display_name, function))
    return claimers


def _print_banner() -> None:
    """Print startup banner with version and author info."""
    commit = os.getenv("COMMIT", "")[:8]
    branch = os.getenv("BRANCH", "")
    build_info = f"  ({branch}@{commit})" if commit else ""

    W = 60  # inner width between ║ chars
    lines = [
        f"  Free Games Claimer Remaster  v{__version__}{build_info}",
        f"  by {__author__}",
        f"  {__repo__}",
    ]
    if __contributors__:
        contrib_str = ", ".join(__contributors__)
        lines.extend([
            "",
            f"  Special thanks to project contributors: {contrib_str}",
        ])
    print(f"\n╔{'═' * W}╗")
    for line in lines:
        print(f"║{line.ljust(W)}║")
    print(f"╚{'═' * W}╝\n")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

async def _persist_dashboard_result(record: dict | None) -> None:
    """Save dashboard history without allowing UI storage to break a claim run."""
    if record is None:
        return
    try:
        await save_dashboard_history(record)
    except Exception:
        logger.exception("Could not save dashboard history for %s", record.get("store"))


async def run_claimers(
    requested_stores: list[str] | None = None,
    *,
    retry_incomplete: bool = False,
) -> None:
    """Run selected claimers sequentially (they each open their own browser)."""
    claimers = _get_active_claimers(requested_stores)

    if not claimers:
        logger.warning("No valid stores selected. Nothing to do.")
        return

    store_names = [name for name, _ in claimers]
    store_keys = [_store_key(name) for name in store_names]
    dashboard_state.begin_run(store_keys)
    logger.info("🎮 Starting claiming run… %s", ", ".join(store_names))

    # Long-running containers never restart, so this is the only place they'd hear about a release.
    await notify_if_update_available()

    aggregated_results = []

    async def _run_sequence() -> None:
        for name, func in claimers:
            store_key = _store_key(name)
            dashboard_state.begin_store(store_key)
            try:
                logger.debug("▶ Running %s claimer…", name)
                res = await asyncio.wait_for(func(), timeout=max(0.001, cfg.store_run_timeout))
                if isinstance(res, dict):
                    logger.debug("%s returned %d game entr(ies): %s", name, len(res.get("games") or []), res.get("games"))
                if isinstance(res, dict) and res.get("games"):
                    aggregated_results.append(res)
                message, details = summarize_store_result(store_key, res)
                result_message_key = store_result_message_key(store_key, res)
                succeeded = (
                    result_message_key != "status.actionRequired"
                    and (not retry_incomplete or store_result_succeeded(store_key, res))
                )
                record = dashboard_state.finish_store(
                    store_key,
                    message,
                    failed=not succeeded,
                    details=details,
                    message_key=(
                        result_message_key
                        or (None if succeeded else "status.failed")
                    ),
                )
                await _persist_dashboard_result(record)
            except TimeoutError:
                logger.error("✗ %s exceeded the %ds store timeout", name, cfg.store_run_timeout)
                record = dashboard_state.finish_store(
                    store_key,
                    "Tempo limite excedido",
                    failed=True,
                    message_key="status.timeout",
                )
                await _persist_dashboard_result(record)
                if cfg.store_notify_enabled(store_key):
                    await notify(f"{name} timed out after {cfg.store_run_timeout // 60} minutes. It will retry later.")
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("✗ %s crashed", name)
                record = dashboard_state.finish_store(store_key, "Falha na última execução", failed=True)
                await _persist_dashboard_result(record)
                if cfg.store_notify_enabled(store_key):
                    await notify(f"{name} claimer crashed with an unhandled exception. Check logs.")

        # Redeem pending GOG codes only when GOG participated in this run.
        if "GOG" not in store_names:
            logger.debug("Skipping pending GOG codes redemption as 'gog' is not in STORES.")
        else:
            try:
                from src.core.database import async_session, ClaimedGame
                from sqlalchemy import select

                async with async_session() as session:
                    has_pending = cfg.gog_force_redeem
                    if not has_pending:
                        stmt = select(ClaimedGame).where(
                            ClaimedGame.status == "claimed",
                            ClaimedGame.code.isnot(None),
                            ClaimedGame.code != "",
                        ).limit(1)
                        result = await session.execute(stmt)
                        has_pending = result.scalars().first() is not None

                if has_pending:
                    from src.stores.gog import GOGClaimer
                    gog = GOGClaimer()
                    await gog.redeem_pending_codes()
                    if gog.notify_games:
                        gog_entry = next((e for e in aggregated_results if e["store"] == "GOG"), None)
                        if gog_entry:
                            gog_entry["games"].extend(gog.notify_games)
                        else:
                            aggregated_results.append({"store": "GOG", "user": gog.user, "games": gog.notify_games})
                else:
                    logger.debug("No pending GOG codes to redeem.")
            except Exception:
                logger.exception("Failed to run post-claim GOG code redemption")

        if cfg.notify_summary and aggregated_results:
            from src.core.notifier import format_game_list
            msg_parts = []
            for result in aggregated_results:
                if not cfg.store_notify_enabled(_store_key(result.get("store", ""))):
                    continue
                keep_owned = cfg.notify_already_claimed
                relevant_games = [
                    g for g in result["games"]
                    if "status" in g
                    and (keep_owned or "exist" not in g["status"].lower())
                    and (keep_owned or "already" not in g["status"].lower())
                    and (keep_owned or "skip" not in g["status"].lower() or "dry run" in g["status"].lower())
                    and (cfg.notify_claim_fails or "fail" not in g["status"].lower())
                ]
                if not relevant_games:
                    continue
                account = mask_account(result.get('user'))
                header = f"**{result['store']}** ({account}):" if account else f"**{result['store']}**:"
                msg_parts.append(f"{header}\n{format_game_list(relevant_games)}")
            if msg_parts:
                final_msg = "\n\n".join(msg_parts)
                if cfg.dryrun:
                    final_msg = "🛑 **DRY RUN SUMMARY: games remaining to be claimed**\n\n" + final_msg
                await notify(final_msg)

    try:
        await asyncio.wait_for(_run_sequence(), timeout=max(0.001, cfg.claim_run_timeout))
    except TimeoutError:
        logger.error("✗ Claiming run exceeded the %ds global timeout", cfg.claim_run_timeout)
        records = dashboard_state.cancel_run("Tempo limite da execução excedido", "status.runTimeout")
        dashboard_state.request_manual_action("run_timeout", "system")
        for record in records:
            await _persist_dashboard_result(record)
        await notify(
            f"The claiming run timed out after {cfg.claim_run_timeout // 60} minutes. "
            "Unfinished stores will retry later."
        )
    finally:
        dashboard_state.finish_run()
    logger.info("✔ Claiming run complete.")


async def run_claimers_scheduled(
    requested_stores: list[str] | None = None,
    *,
    automatic: bool = False,
    retry_incomplete: bool = False,
) -> None:
    """Run claimers from scheduler jobs without overlapping executions."""
    if _claim_run_lock.locked():
        logger.warning("A claiming run is already in progress; skipping this scheduled trigger.")
        return

    async with _claim_run_lock:
        try:
            await run_claimers(requested_stores, retry_incomplete=retry_incomplete)
        finally:
            # Keep the dashboard usable even if an unexpected orchestration
            # error escapes after an individual store has finished.
            dashboard_state.finish_run()
            if automatic:
                try:
                    await save_last_automatic_run(datetime.now(timezone.utc))
                except Exception:
                    logger.exception("Could not persist the automatic-run cooldown.")


def _next_interval_run(
    last_automatic_run: datetime | None,
    interval_hours: int,
    *,
    now: datetime | None = None,
) -> datetime | None:
    """Anchor the interval to persisted state without replaying missed cycles."""
    if interval_hours <= 0:
        return None
    current = now or datetime.now(timezone.utc)
    current = current.replace(tzinfo=timezone.utc) if current.tzinfo is None else current.astimezone(timezone.utc)
    if last_automatic_run is None:
        return current + timedelta(hours=interval_hours)
    last = last_automatic_run.replace(tzinfo=timezone.utc) if last_automatic_run.tzinfo is None else last_automatic_run.astimezone(timezone.utc)
    due = last + timedelta(hours=interval_hours)
    return due if due > current else current + timedelta(hours=interval_hours)


def _startup_run_due(
    last_automatic_run: datetime | None,
    interval_hours: int,
    *,
    fixed_times: list[tuple[int, int]] | None = None,
    fixed_timezone: ZoneInfo | None = None,
    now: datetime | None = None,
) -> bool:
    """Run at boot only when no recent automatic cycle is still in cooldown."""
    if last_automatic_run is None:
        return True
    last = last_automatic_run.replace(tzinfo=timezone.utc) if last_automatic_run.tzinfo is None else last_automatic_run.astimezone(timezone.utc)
    current = now or datetime.now(timezone.utc)
    current = current.replace(tzinfo=timezone.utc) if current.tzinfo is None else current.astimezone(timezone.utc)
    interval_due = interval_hours > 0 and current >= last + timedelta(hours=interval_hours)
    fixed_due = False
    if fixed_times:
        local_now = current.astimezone(fixed_timezone or timezone.utc)
        candidates = []
        for hour, minute in fixed_times:
            candidate = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if candidate > local_now:
                candidate -= timedelta(days=1)
            candidates.append(candidate.astimezone(timezone.utc))
        fixed_due = bool(candidates) and last < max(candidates)
    if interval_hours <= 0 and not fixed_times:
        return True
    return interval_due or fixed_due


def _configure_scheduled_jobs(
    scheduler: AsyncIOScheduler,
    last_automatic_run: datetime | None = None,
) -> list[tuple[int, int]]:
    """Replace recurring jobs with the dashboard/current config values."""
    for job in scheduler.get_jobs():
        if job.id in {"claim_all", "claim_all_startup"} or job.id.startswith("claim_fixed_"):
            scheduler.remove_job(job.id)

    if cfg.windows_host_scheduler:
        logger.info("In-container scheduler disabled; Windows Task Scheduler owns automatic runs.")
        return []

    if cfg.scheduler_hours > 0:
        next_run = _next_interval_run(last_automatic_run, cfg.scheduler_hours)
        scheduler.add_job(
            run_claimers_scheduled,
            trigger=IntervalTrigger(hours=cfg.scheduler_hours, start_date=next_run),
            id="claim_all",
            name="Claim free games",
            replace_existing=True,
            kwargs={"automatic": True},
        )

    fixed_times = _parse_fixed_times(cfg.scheduler_fixed_times)
    fixed_timezone = _scheduler_timezone() if fixed_times else None
    for hour, minute in fixed_times:
        scheduler.add_job(
            run_claimers_scheduled,
            trigger=CronTrigger(hour=hour, minute=minute, timezone=fixed_timezone),
            id=f"claim_fixed_{hour:02d}_{minute:02d}",
            name=f"Claim free games at {hour:02d}:{minute:02d}",
            replace_existing=True,
            kwargs={"automatic": True},
        )
    return fixed_times


def _next_scheduled_run(scheduler: AsyncIOScheduler) -> str | None:
    runs = [
        job.next_run_time
        for job in scheduler.get_jobs()
        if job.id != "claim_all_startup" and job.next_run_time is not None
    ]
    return min(runs).isoformat() if runs else None


async def main() -> None:
    """Initialise DB and either run once or start the scheduler."""
    _print_banner()
    # Effective settings (no credentials), the first thing worth knowing in a bug report.
    logger.debug(
        "Settings: dryrun=%s debug_libs=%s show=%s %dx%d timeout=%ss stores=%r scheduler_hours=%s fixed=%r tz=%s "
        "notify(summary=%s errors=%s fails=%s login=%s skip=%s) eg_mobile=%s(%s) data=%s",
        cfg.dryrun, cfg.debug_libs, cfg.show, cfg.width, cfg.height, cfg.timeout // 1000, cfg.stores or "all",
        cfg.scheduler_hours, cfg.scheduler_fixed_times, cfg.scheduler_timezone,
        cfg.notify_summary, cfg.notify_errors, cfg.notify_claim_fails, cfg.notify_login_request,
        sorted(cfg.notify_skip_stores) or "none", cfg.eg_mobile, ",".join(cfg.eg_mobile_platform_list) or "none",
        cfg._data_dir,
    )
    _warn_about_settings()
    await init_db()
    logger.info("Database ready.")
    try:
        dashboard_state.restore(await load_dashboard_history())
    except Exception:
        logger.exception("Could not restore dashboard history; starting with an empty dashboard.")

    if cfg.reset_db_games:
        try:
            from src.core.database import async_session, ClaimedGame
            from sqlalchemy import delete
            
            seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
            
            async with async_session() as session:
                stmt = delete(ClaimedGame).where(ClaimedGame.created_at >= seven_days_ago)
                res = await session.execute(stmt)
                if res.rowcount > 0:
                    logger.info("Reset %d entry(s) from the last 7 days from history.", res.rowcount)
                else:
                    logger.debug("DB reset requested, but no entries found from the last 7 days.")
                await session.commit()
        except Exception as e:
            logger.error("Failed to reset DB games: %s", e)

    # Send a test notification if NOTIFY_TEST=true (for verifying notification setup)
    if cfg.notify_test:
        logger.info("🔔 NOTIFY_TEST=true, sending test notification...")
        services = ", ".join(filter(None, [
            "Discord" if cfg.discord_webhook else None,
            "Apprise" if cfg.notify_url else None,
        ])) or "⚠️ None configured"
        test_msg = (
            "🔔 **Free Games Claimer: Test Notification**\n\n"
            "✅ If you see this message, your notification setup is working correctly!\n\n"
            f"**Version:** v{__version__}\n"
            f"**Services:** {services}"
        )
        await notify(test_msg)
        logger.info("✅ Test notification dispatched! Check your configured services. "
                     "Set NOTIFY_TEST=0 in your .env to disable this on future restarts.")

    # If --once flag is set, run a single pass and exit
    if "--once" in sys.argv:
        await run_claimers()
        return

    # Otherwise start the scheduler
    scheduler = AsyncIOScheduler(job_defaults=_CLAIM_JOB_OPTIONS)
    try:
        last_automatic_run = await load_last_automatic_run()
    except Exception:
        logger.exception("Could not load the automatic-run cooldown.")
        last_automatic_run = None
    fixed_times = _configure_scheduled_jobs(scheduler, last_automatic_run)
    if cfg.scheduler_hours <= 0:
        logger.info("Interval scheduler disabled because SCHEDULER_HOURS=%s.", cfg.scheduler_hours)

    setup_pending = cfg.gui_setup_required and not get_setup_state()["complete"]

    # The packaged Windows experience opens the local setup wizard before any
    # account automation. Existing source/Docker users are unaffected unless
    # they explicitly enable GUI_SETUP_REQUIRED.
    fixed_timezone = _scheduler_timezone() if fixed_times else None
    if not cfg.windows_host_scheduler and cfg.run_on_startup and not setup_pending and _startup_run_due(
        last_automatic_run,
        cfg.scheduler_hours,
        fixed_times=fixed_times,
        fixed_timezone=fixed_timezone,
    ):
        scheduler.add_job(
            run_claimers_scheduled,
            id="claim_all_startup",
            name="Initial claiming run",
            replace_existing=True,
            kwargs={"automatic": True},
        )
    elif cfg.windows_host_scheduler:
        logger.info("Initial claiming run delegated to Windows Task Scheduler.")
    elif cfg.run_on_startup and not setup_pending:
        logger.info("Initial claiming run skipped because the previous automatic cycle is still in cooldown.")
    elif not cfg.run_on_startup:
        logger.info("Initial claiming run disabled by RUN_ON_STARTUP=false.")
    else:
        logger.info("Initial claiming run paused until local setup is complete.")

    scheduler.start(paused=setup_pending)
    dashboard_server = None
    if cfg.gui_enabled:
        from src.gui.server import start_dashboard

        async def dashboard_status() -> dict:
            enabled = _get_active_store_keys(publish_selection=False)
            last_automatic_run = await load_last_automatic_run()
            schedule = {
                "nextRun": _next_scheduled_run(scheduler),
                "timezone": cfg.scheduler_timezone,
                "fixedTimes": cfg.scheduler_fixed_times,
                "intervalHours": cfg.scheduler_hours,
                "hostManaged": cfg.windows_host_scheduler,
                "economyEnabled": cfg.windows_economy_schedule,
                "runOnStartup": cfg.run_on_startup,
                "wakeOnAc": cfg.windows_wake_on_ac,
                "lastAutomaticRun": last_automatic_run.isoformat() if last_automatic_run else None,
            }
            return dashboard_state.snapshot(enabled, schedule)

        async def dashboard_history(limit: int, run_id: str | None) -> dict:
            return {"history": dashboard_state.history(limit=limit, run_id=run_id)}

        async def dashboard_config() -> dict:
            return get_settings(DEFAULT_STORES)

        async def dashboard_save(values: dict) -> dict:
            try:
                result = save_settings(values)
            except SettingsError:
                raise
            _configure_scheduled_jobs(scheduler, await load_last_automatic_run())
            dashboard_state.mark_activity()
            return result

        async def dashboard_setup(values: dict) -> dict:
            result = complete_setup(values)
            _configure_scheduled_jobs(scheduler, await load_last_automatic_run())
            if scheduler.state == STATE_PAUSED:
                scheduler.resume()
            dashboard_state.mark_activity()
            return result

        async def dashboard_update() -> dict:
            return await get_update_status()

        async def dashboard_manual_actions() -> dict:
            return dashboard_state.manual_actions(cfg.windows_notifications)

        async def dashboard_run(
            stores: list[str] | None,
            mode: str | None = None,
            local_date: str | None = None,
            utc_offset_minutes: int | None = None,
        ) -> bool | dict:
            global _dashboard_run_task
            if cfg.gui_setup_required and not get_setup_state()["complete"]:
                raise SettingsError("Complete local setup before running", "error.setupRequired")
            if mode == "scheduled-retry":
                if stores is not None:
                    raise ValueError("Scheduled runs select stores automatically")
                if not isinstance(local_date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", local_date):
                    raise ValueError("Invalid local date")
                if isinstance(utc_offset_minutes, bool) or not isinstance(utc_offset_minutes, int):
                    raise ValueError("Invalid UTC offset")
                if not -840 <= utc_offset_minutes <= 840:
                    raise ValueError("Invalid UTC offset")
                try:
                    host_day = datetime.strptime(local_date, "%Y-%m-%d").date()
                except ValueError as exc:
                    raise ValueError("Invalid local date") from exc
                host_today = (datetime.now(timezone.utc) + timedelta(minutes=utc_offset_minutes)).date()
                if host_day != host_today:
                    raise ValueError("Local date is outside the current day")
                stores = dashboard_state.pending_stores_for_day(
                    _get_active_store_keys(),
                    host_day,
                    utc_offset_minutes,
                )
                if not stores:
                    return {"accepted": False, "reason": "already-complete", "stores": []}
            if stores is not None:
                if any(not isinstance(store, str) for store in stores):
                    raise ValueError("Seleção de lojas inválida")
                resolved = _resolve_stores(stores)
                if not resolved or len(resolved) != len(set(stores)):
                    raise ValueError("Seleção de lojas inválida")
                stores = resolved

            if mode is None:
                dashboard_state.mark_activity()

            busy = _claim_run_lock.locked() or (_dashboard_run_task and not _dashboard_run_task.done())
            # Shopee has its own persistent browser profile and may need the owner
            # waiting in VNC for a first login. An explicit Shopee action can run
            # without waiting for an unrelated scheduled multi-store run.
            if mode is None and busy and stores == ["shopee"]:
                if "shopee" in _dashboard_individual_stores:
                    return False
                _dashboard_individual_stores.add("shopee")
                task = asyncio.create_task(run_claimers(stores))
                _dashboard_individual_tasks.add(task)

                def _release_individual(done: asyncio.Task) -> None:
                    _dashboard_individual_tasks.discard(done)
                    _dashboard_individual_stores.discard("shopee")

                task.add_done_callback(_release_individual)
                return True
            if busy:
                return {"accepted": False, "reason": "busy", "stores": stores or []} if mode else False
            previous_run_id = dashboard_state.current_run_id()
            _dashboard_run_task = asyncio.create_task(
                run_claimers_scheduled(
                    stores,
                    automatic=mode == "scheduled-retry",
                    retry_incomplete=mode == "scheduled-retry",
                )
            )
            for _ in range(10):
                await asyncio.sleep(0)
                if dashboard_state.current_run_id() != previous_run_id:
                    break
            if mode:
                run_id = dashboard_state.current_run_id()
                if not run_id or run_id == previous_run_id:
                    return {"accepted": False, "reason": "busy", "stores": stores or []}
                return {
                    "accepted": True,
                    "runId": run_id,
                    "stores": stores or [],
                }
            return True

        async def dashboard_stop():
            tasks = [
                task for task in [_dashboard_run_task, *_dashboard_individual_tasks]
                if task is not None and not task.done()
            ]
            for task in tasks:
                task.cancel()
            records = dashboard_state.cancel_run()
            for record in records:
                await _persist_dashboard_result(record)
            event_id = dashboard_state.request_manual_action("stop_all", "system")

            async def _fallback_exit():
                await asyncio.sleep(10)
                os._exit(0)

            asyncio.create_task(_fallback_exit())
            return {
                "accepted": True,
                "cancelledTasks": len(tasks),
                "hostShutdownRequested": bool(event_id),
            }

        async def dashboard_activity() -> dict:
            dashboard_state.mark_activity()
            return {"accepted": True}

        dashboard_server = start_dashboard(
            loop=asyncio.get_running_loop(),
            port=cfg.gui_port,
            status_callback=dashboard_status,
            history_callback=dashboard_history,
            config_callback=dashboard_config,
            save_callback=dashboard_save,
            setup_callback=dashboard_setup,
            update_callback=dashboard_update,
            manual_actions_callback=dashboard_manual_actions,
            run_callback=dashboard_run,
            stop_callback=dashboard_stop,
            activity_callback=dashboard_activity,
        )
        asyncio.create_task(notify_if_update_available(at_startup=True))

        async def _idle_shutdown_monitor() -> None:
            if not cfg.windows_host_scheduler or cfg.gui_idle_timeout <= 0:
                return
            while True:
                await asyncio.sleep(min(30, max(1, cfg.gui_idle_timeout)))
                if get_setup_state()["complete"] and not dashboard_state.snapshot([], {})["running"]:
                    if dashboard_state.idle_seconds() >= cfg.gui_idle_timeout:
                        logger.info("Dashboard idle for %ds; requesting economy shutdown.", cfg.gui_idle_timeout)
                        dashboard_state.request_manual_action("stop_all", "system")
                        return

        asyncio.create_task(_idle_shutdown_monitor())
    else:
        # Headless users still receive update notifications; the GUI path above
        # deliberately starts this only after the dashboard is listening.
        asyncio.create_task(notify_if_update_available(at_startup=True))
    interval_text = (
        f"runs every {cfg.scheduler_hours} hours"
        if cfg.scheduler_hours > 0
        else "interval disabled"
    )
    fixed_text = (
        "fixed daily times: "
        + ", ".join(f"{hour:02d}:{minute:02d}" for hour, minute in fixed_times)
        + f" ({cfg.scheduler_timezone})"
        if fixed_times
        else "no fixed daily times configured"
    )
    logger.info("Scheduler active - %s; %s.", interval_text, fixed_text)

    try:
        # Keep the event loop alive
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down…")
        scheduler.shutdown(wait=False)
        if dashboard_server is not None:
            dashboard_server.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
