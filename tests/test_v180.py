"""Regression coverage for Lontrium 1.8.0's privacy and release UX."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core import redact as redaction
from src.core.database import Base, ClaimedGame, load_redemption_status
from src.core.redact import RedactFilter, hide, hide_settings, redact
from src.gui.releases import acknowledge_release, get_release_history
from src.stores.epic import checkout_total_is_zero
from src.stores.gamerpower import fanatical_total_is_zero

ROOT = Path(__file__).resolve().parent.parent


class TestReleaseHistory:
    def test_catalog_contains_only_lontrium_semver_releases(self):
        payload = json.loads((ROOT / "src/gui/static/release-history.json").read_text(encoding="utf-8"))
        versions = [item["version"] for item in payload["releases"]]
        assert versions[0] == "1.8.0" and versions[-1] == "1.0.0"
        assert "1.8" not in versions and "1.8d" not in versions
        assert all(version.count(".") == 2 for version in versions)

    def test_update_notice_is_seen_once(self, tmp_path):
        state = tmp_path / "ui-state.json"
        first = get_release_history(setup_complete=True, state_path=state)
        assert first["showNotice"] is True
        acknowledge_release(first["currentVersion"], state)
        assert get_release_history(setup_complete=True, state_path=state)["showNotice"] is False

    def test_fresh_setup_never_gets_a_false_update_notice(self, tmp_path):
        state = tmp_path / "ui-state.json"
        assert get_release_history(setup_complete=False, state_path=state)["showNotice"] is False

    def test_another_version_cannot_be_acknowledged(self, tmp_path):
        with pytest.raises(ValueError):
            acknowledge_release("999.0.0", tmp_path / "ui-state.json")


class TestLogRedaction:
    @pytest.fixture(autouse=True)
    def reset_mask(self, monkeypatch):
        monkeypatch.setattr(redaction, "_hidden", {})
        monkeypatch.setattr(redaction, "_pattern", None)

    def test_secrets_accounts_webhooks_and_codes_are_masked(self):
        cfg = SimpleNamespace(
            ms_email="person@example.com",
            ms_password="Secret-password",
            ms_otp_key="JBSWY3DPEHPK3PXP",
            discord_webhook="https://discord.com/api/webhooks/123456789012345678/token-value-123",
            notify_url="",
        )
        hide_settings(cfg)
        hide("ABCDE-FGHIJ-KLMNO", "ABCDE…")
        line = redact("person@example.com Secret-password JBSWY3DPEHPK3PXP 123456789012345678 token-value-123 ABCDE-FGHIJ-KLMNO")
        assert line == "p***@example.com *** *** *** *** ABCDE…"

    def test_exception_trace_is_redacted(self):
        hide("private-token")
        try:
            raise ValueError("private-token for user@example.com")
        except ValueError:
            import sys
            record = logging.LogRecord("x", logging.ERROR, __file__, 1, "request failed", (), sys.exc_info())
        RedactFilter().filter(record)
        text = record.getMessage()
        assert "private-token" not in text and "user@example.com" not in text


class TestSafeRedemptionApi:
    def test_codes_never_leave_the_database_status_api(self, tmp_path):
        async def scenario():
            engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'status.db'}")
            factory = async_sessionmaker(engine, expire_on_commit=False)
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            async with factory() as session:
                session.add(ClaimedGame(
                    store="prime", user="private@example.com", game_id="g1", title="Example Game",
                    url="https://private.example/code", status="claimed", code="ABCDE-FGHIJ-KLMNO",
                    extra=json.dumps({"external_store": "microsoft store", "token": "secret"}),
                ))
                await session.commit()
            result = await load_redemption_status(session_factory=factory)
            await engine.dispose()
            return result

        payload = asyncio.run(scenario())
        assert payload == [{
            "title": "Example Game", "target": "microsoft", "targetName": "Microsoft / Xbox",
            "state": "pending", "action": "configure",
        }]
        encoded = json.dumps(payload)
        assert "ABCDE" not in encoded and "private@example.com" not in encoded and "secret" not in encoded


class TestPriceGuards:
    @pytest.mark.parametrize("text,expected", [
        ("Order summary Total $0.00", True),
        ("Total 0,00 €", True),
        ("Total $1.99", False),
        ("Free asset with no total", None),
    ])
    def test_epic_and_fab_zero_total(self, text, expected):
        assert checkout_total_is_zero(text) is expected

    @pytest.mark.parametrize("text,expected", [
        ("Subtotal $10.00 Discount $10.00 Total $0.00", True),
        ("Total €2,49", False),
        ("Claim game for free", None),
    ])
    def test_fanatical_zero_total(self, text, expected):
        assert fanatical_total_is_zero(text) is expected


class TestBrowserAndFrontend:
    def test_chrome_cache_is_capped_and_close_is_clean_first(self):
        source = (ROOT / "src/core/claimer.py").read_text(encoding="utf-8")
        assert "--disk-cache-size=262144000" in source
        close = source.split("async def close_browser", 1)[1].split("def _clear_profile_locks", 1)[0]
        assert close.index("uc.cdp.browser.close") < close.index("self._kill_process_tree")

    def test_aliexpress_has_every_locale_and_calendar_confirmation(self):
        source = (ROOT / "src/stores/aliexpress.py").read_text(encoding="utf-8")
        assert "CHECKIN_LABELS" in source and "TODAY_LABELS" in source
        assert "aecoin-today-checked-" in source and "CHECKIN_BUTTON_CSS" in source

    def test_update_modal_and_history_are_wired(self):
        html = (ROOT / "src/gui/static/index.html").read_text(encoding="utf-8")
        js = (ROOT / "src/gui/static/app.js").read_text(encoding="utf-8")
        assert 'id="releaseNotice"' in html and 'id="redemptionsSection"' in html
        assert "/api/releases/acknowledge" in js and "createReleaseHistory" in js
