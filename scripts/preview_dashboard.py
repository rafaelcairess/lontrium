"""Serve synthetic, privacy-safe dashboard data for screenshots and UI review."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from src.gui.server import start_dashboard
from src.gui.settings import SPECS
from src.gui.state import STORE_META


async def main() -> None:
    now = datetime.now(timezone.utc)

    async def status() -> dict:
        stores = []
        for key, meta in STORE_META.items():
            store = {
                **meta,
                "key": key,
                "enabled": key in {"epic", "gog", "aliexpress", "shopee"},
                "state": "idle",
                "message": "Waiting for a run",
                "messageKey": "status.waiting",
                "lastRun": None,
                "details": None,
            }
            if key == "epic":
                store.update(
                    state="success",
                    messageKey="status.resultGames",
                    lastRun=(now - timedelta(minutes=18)).isoformat(),
                    details={
                        "kind": "games",
                        "items": [
                            {"title": "Sample Adventure", "outcome": "claimed"},
                            {"title": "Orbit Tactics", "outcome": "owned"},
                        ],
                    },
                )
            elif key == "gog":
                store.update(
                    state="success",
                    messageKey="status.completedNoChanges",
                    lastRun=(now - timedelta(minutes=16)).isoformat(),
                )
            elif key == "aliexpress":
                store.update(
                    state="success",
                    messageKey="status.resultCoins",
                    lastRun=(now - timedelta(minutes=12)).isoformat(),
                    details={
                        "kind": "coins",
                        "outcome": "collected",
                        "claimedCoins": 15,
                        "offeredCoins": 15,
                        "balance": 480,
                        "streakDays": 7,
                        "tomorrowCoins": 18,
                    },
                )
            elif key == "shopee":
                store.update(
                    state="success",
                    messageKey="status.resultCoins",
                    lastRun=(now - timedelta(minutes=10)).isoformat(),
                    details={
                        "kind": "coins",
                        "outcome": "collected",
                        "claimedCoins": 3,
                        "offeredCoins": 3,
                        "balance": 6,
                        "streakDays": None,
                        "tomorrowCoins": None,
                    },
                )
            stores.append(store)
        return {
            "running": False,
            "startedAt": (now - timedelta(minutes=20)).isoformat(),
            "finishedAt": (now - timedelta(minutes=12)).isoformat(),
            "stores": stores,
            "schedule": {"nextRun": (now + timedelta(hours=11, minutes=48)).isoformat()},
        }

    async def config() -> dict:
        values = {
            "STORES": ["epic", "gog", "aliexpress", "shopee"],
            "SCHEDULER_HOURS": 12,
            "SCHEDULER_FIXED_TIMES": "",
            "SCHEDULER_TIMEZONE": "America/Sao_Paulo",
            "RUN_ON_STARTUP": True,
            "SHOW": True,
            "VNC_LOGIN_TIMEOUT": 180,
            "NOTIFY_SUMMARY": True,
            "NOTIFY_ERRORS": True,
            "NOTIFY_CLAIM_FAILS": False,
            "NOTIFY_LOGIN_REQUEST": True,
            "EG_MOBILE": True,
            "PG_REDEEM": False,
            "GOG_NEWSLETTER": False,
            "UNITY_ACCEPT_TOS": False,
            "AE_MIN_COINS": 2,
            "AE_FLAG_RETRIES": 3,
            "AE_FLAG_WAIT": 480,
            "FAB_ACCEPT_EULA": True,
            "FANATICAL_ENABLE": False,
            "ALIENWARE_ENABLE": False,
            "ITCHIO_ENABLE": False,
            "INDIEGALA_ENABLE": False,
        }
        return {
            "schema": [spec.public() for spec in SPECS],
            "values": values,
            "configured": {spec.key: False for spec in SPECS if spec.secret},
            "setup": {"required": True, "complete": False},
        }

    async def save(_values: dict) -> dict:
        return {"changed": [], "restartRequired": []}

    async def setup(_values: dict) -> dict:
        return {"changed": [], "restartRequired": [], "setup": {"required": True, "complete": True}}

    async def update() -> dict:
        return {"currentVersion": "1.0.0", "available": False, "latestVersion": "1.0.0"}

    async def run(_stores: list[str] | None) -> bool:
        return True

    server = start_dashboard(
        loop=asyncio.get_running_loop(),
        port=8765,
        status_callback=status,
        config_callback=config,
        save_callback=save,
        setup_callback=setup,
        update_callback=update,
        run_callback=run,
    )
    try:
        await asyncio.Event().wait()
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    asyncio.run(main())
