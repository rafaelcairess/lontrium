"""Database – keeps track of which games have already been claimed.

This file manages the SQLite database (stored as /fgc/data/fgc.db inside Docker).
Every time a game is successfully claimed, a record is saved here so the bot
knows not to try claiming it again on the next run.

The database stores: game title, which store it came from, who claimed it,
any redemption codes, and timestamps.
"""

import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import DateTime, String, Text, delete, event, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.core.config import cfg
from src.core.redact import hide, mask_account, mask_code

logger = logging.getLogger("fgc.database")


# ---------------------------------------------------------------------------
# Engine & session factory
# ---------------------------------------------------------------------------

# SQL parameter logging can contain accounts, private URLs and redemption codes.
# Keep statements available through the normal logger without enabling SQLAlchemy's
# independent echo handler, which would bypass the central redaction filter.
engine = create_async_engine(cfg.database_url)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """Shared declarative base for all models."""


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ClaimedGame(Base):
    """A single row in the database representing one claimed game.
    
    Each game is uniquely identified by (store + user + game_id).
    If a game already exists in the database, we skip it on the next run.
    """

    __tablename__ = "claimed_games"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    store: Mapped[str] = mapped_column(String(32), index=True, comment="epic, gog, prime, steam")
    user: Mapped[str] = mapped_column(String(128), index=True, comment="Account display name")
    game_id: Mapped[str] = mapped_column(String(256), index=True, comment="Store-specific game identifier")
    title: Mapped[str] = mapped_column(String(512))
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(64), default="unknown", comment="claimed, existed, failed, …")
    code: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="Redemption code (GOG / external)")
    extra: Mapped[str | None] = mapped_column(Text, nullable=True, comment="JSON blob for misc data")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<ClaimedGame store={self.store!r} title={self.title!r} status={self.status!r}>"


@event.listens_for(ClaimedGame.code, "set")
def _hide_new_code(target, value, oldvalue, initiator):
    """Teach the log filter about every game code as soon as it is stored."""
    hide(value, mask_code(value))


@event.listens_for(ClaimedGame, "load")
def _hide_stored_code(target, context):
    """Teach the filter about codes loaded from an existing database too."""
    hide(target.code, mask_code(target.code))


class DashboardHistory(Base):
    """A privacy-safe store result shown in the persistent dashboard history."""

    __tablename__ = "dashboard_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(36), index=True)
    store: Mapped[str] = mapped_column(String(32), index=True)
    state: Mapped[str] = mapped_column(String(16))
    message_key: Mapped[str] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(String(256))
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class RuntimeState(Base):
    """Small persistent values used to resume automation safely after restarts."""

    __tablename__ = "runtime_state"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def init_db() -> None:
    """Create all tables if they don't exist yet."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.debug("Database ready.")


async def get_or_create(
    session: AsyncSession,
    *,
    store: str,
    user: str,
    game_id: str,
    title: str,
    url: str | None = None,
    status: str = "unknown",
    code: str | None = None,
) -> tuple[ClaimedGame, bool]:
    """Return existing row or insert a new one.  Returns ``(obj, created)``."""
    from sqlalchemy import select

    stmt = select(ClaimedGame).where(
        ClaimedGame.store == store,
        ClaimedGame.user == user,
        ClaimedGame.game_id == game_id,
    )
    result = await session.execute(stmt)
    obj = result.scalar_one_or_none()
    if obj is not None:
        logger.debug("DB hit: %s/%s/%s already stored as '%s' (%s)",
                     store, mask_account(user), game_id, obj.title, obj.status)
        return obj, False

    obj = ClaimedGame(
        store=store,
        user=user,
        game_id=game_id,
        title=title,
        url=url,
        status=status,
        code=code,
    )
    session.add(obj)
    await session.flush()
    logger.debug("DB new row: %s/%s/%s '%s' (%s)", store, mask_account(user), game_id, title, status)
    return obj, True


_GAME_OUTCOMES = {"claimed", "owned", "available", "failed", "skipped", "action_required", "processed"}
_COIN_OUTCOMES = {"collected", "collected_manual", "already_collected", "not_collected", "available"}
_COIN_FIELDS = ("claimedCoins", "offeredCoins", "balance", "streakDays", "tomorrowCoins")
_HISTORY_RETENTION_DAYS = 90


def sanitise_dashboard_details(details) -> dict | None:
    """Keep only fields already intended for display in the local dashboard."""
    if not isinstance(details, dict):
        return None
    if details.get("kind") == "games":
        items = []
        for item in details.get("items") or []:
            if not isinstance(item, dict):
                continue
            title = item.get("title")
            outcome = item.get("outcome")
            if not isinstance(title, str) or not title.strip() or outcome not in _GAME_OUTCOMES:
                continue
            items.append({"title": title.strip()[:180], "outcome": outcome})
        return {"kind": "games", "items": items[:100]}
    if details.get("kind") == "coins":
        outcome = details.get("outcome")
        safe = {
            "kind": "coins",
            "outcome": outcome if outcome in _COIN_OUTCOMES else "not_collected",
        }
        for field in _COIN_FIELDS:
            value = details.get(field)
            safe[field] = value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None
        return safe
    return None


def _as_utc(value) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            parsed = datetime.now(timezone.utc)
    else:
        parsed = datetime.now(timezone.utc)
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def _history_row(row: DashboardHistory) -> dict:
    try:
        details = sanitise_dashboard_details(json.loads(row.details_json)) if row.details_json else None
    except (TypeError, json.JSONDecodeError):
        details = None
    return {
        "runId": row.run_id,
        "store": row.store,
        "state": row.state,
        "messageKey": row.message_key,
        "message": row.message,
        "startedAt": _as_utc(row.started_at).isoformat(),
        "finishedAt": _as_utc(row.finished_at).isoformat(),
        "details": details,
    }


async def save_dashboard_history(record: dict, session_factory=None) -> None:
    """Persist one sanitised store result and prune entries older than 90 days."""
    factory = session_factory or async_session
    details = sanitise_dashboard_details(record.get("details"))
    row = DashboardHistory(
        run_id=str(record.get("runId") or "")[:36],
        store=str(record.get("store") or "")[:32],
        state="error" if record.get("state") == "error" else "success",
        message_key=str(record.get("messageKey") or "status.completedNoChanges")[:64],
        message=str(record.get("message") or "")[:256],
        details_json=json.dumps(details, ensure_ascii=False, separators=(",", ":")) if details else None,
        started_at=_as_utc(record.get("startedAt")),
        finished_at=_as_utc(record.get("finishedAt")),
    )
    cutoff = datetime.now(timezone.utc) - timedelta(days=_HISTORY_RETENTION_DAYS)
    async with factory() as session:
        session.add(row)
        await session.execute(delete(DashboardHistory).where(DashboardHistory.finished_at < cutoff))
        await session.commit()


async def load_dashboard_history(limit: int = 250, session_factory=None) -> list[dict]:
    """Load recent dashboard results, newest first, from the persistent volume."""
    factory = session_factory or async_session
    safe_limit = min(max(int(limit), 1), 1000)
    async with factory() as session:
        result = await session.execute(
            select(DashboardHistory)
            .order_by(DashboardHistory.finished_at.desc(), DashboardHistory.id.desc())
            .limit(safe_limit)
        )
        return [_history_row(row) for row in result.scalars().all()]


def _redemption_target(row: ClaimedGame) -> tuple[str, str] | None:
    """Return the public destination key/name for an external Prime code."""
    try:
        extra = json.loads(row.extra or "{}")
    except (TypeError, json.JSONDecodeError):
        extra = {}
    tag = str(extra.get("external_store") or "").strip().lower()
    if "gog" in tag:
        return "gog", "GOG"
    if tag in {"microsoft store", "microsoft", "xbox"}:
        return "microsoft", "Microsoft / Xbox"
    if tag == "legacy games":
        return "legacygames", "Legacy Games"
    return None


async def load_redemption_status(limit: int = 100, session_factory=None) -> list[dict]:
    """Return a secret-free view of Prime redemption codes for the dashboard."""
    factory = session_factory or async_session
    safe_limit = min(max(int(limit), 1), 250)
    async with factory() as session:
        rows = (await session.execute(
            select(ClaimedGame)
            .where(ClaimedGame.store == "prime")
            .order_by(ClaimedGame.updated_at.desc(), ClaimedGame.id.desc())
            .limit(safe_limit * 3)
        )).scalars().all()

    public = []
    for row in rows:
        target = _redemption_target(row)
        if target is None or not row.code:
            continue
        status = str(row.status or "").lower()
        if "already redeemed" in status or "claimed and redeemed" in status:
            state = "redeemed"
        elif ("redeem failed" in status or "rejected" in status or "expired" in status
              or "code used" in status):
            state = "failed"
        elif "unconfirmed" in status:
            state = "retry"
        else:
            state = "pending"
        key, name = target
        public.append({
            "title": str(row.title or "Game")[:180],
            "target": key,
            "targetName": name,
            "state": state,
            "action": "configure" if state in {"pending", "retry"} else None,
        })
        if len(public) >= safe_limit:
            break
    return public


_LAST_AUTOMATIC_RUN_KEY = "last_automatic_run"


async def save_last_automatic_run(value: datetime, session_factory=None) -> None:
    """Persist the end of an automatic cycle so restarts respect its cooldown."""
    factory = session_factory or async_session
    encoded = _as_utc(value).isoformat()
    async with factory() as session:
        row = await session.get(RuntimeState, _LAST_AUTOMATIC_RUN_KEY)
        if row is None:
            session.add(RuntimeState(key=_LAST_AUTOMATIC_RUN_KEY, value=encoded))
        else:
            row.value = encoded
        await session.commit()


async def load_last_automatic_run(session_factory=None) -> datetime | None:
    """Return the most recently completed automatic cycle, if one was recorded."""
    factory = session_factory or async_session
    async with factory() as session:
        row = await session.get(RuntimeState, _LAST_AUTOMATIC_RUN_KEY)
        if row is None:
            return None
        try:
            parsed = datetime.fromisoformat(row.value.replace("Z", "+00:00"))
            return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
        except (AttributeError, TypeError, ValueError):
            logger.warning("Ignoring invalid persisted automatic-run timestamp.")
            return None
