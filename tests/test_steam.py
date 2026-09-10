"""Focused tests for Steam discovery and login control flow."""

import asyncio
import sys
from types import ModuleType

# These unit tests exercise pure parsing and mocked control flow, not Chrome.
# Keeping nodriver out also makes them independent of generated CDP bindings.
sys.modules.setdefault("nodriver", ModuleType("nodriver"))

from src.gui.state import store_result_message_key, summarize_store_result
from src.stores.steam import SteamClaimer, classify_login_state, parse_steam_store_search


def test_official_search_keeps_only_time_limited_free_to_keep_games():
    html = """
    <div class="search_results_count">2 results match your search.</div>
    <a href="https://store.steampowered.com/app/123/Keep_Me/" class="search_result_row ds_collapse_flag">
      <span class="title">Keep &amp; Play</span>
      <div class="discount_pct">-100%</div>
      <div class="discount_original_price">$9.99</div>
      <div class="discount_final_price">Free</div>
    </a>
    <a href="https://store.steampowered.com/app/456/Always_Free/" class="search_result_row">
      <span class="title">Always Free</span>
      <div class="discount_final_price">Free To Play</div>
    </a>
    """

    assert parse_steam_store_search(html) == [{
        "title": "Keep & Play",
        "url": "https://store.steampowered.com/app/123/Keep_Me/",
        "app_id": "123",
        "source": "steam_store",
    }]


def test_login_detection_requires_positive_account_evidence():
    assert classify_login_state({"hasLoginLink": True, "hasLoginForm": True}) == (False, "")
    assert classify_login_state({}) == (False, "")
    assert classify_login_state({"accountId": 42}) == (True, "")
    assert classify_login_state({"accountName": "player"}) == (True, "player")


def test_empty_official_search_has_an_explicit_dashboard_result():
    result = {"games": [], "statusCode": "no_active_giveaways"}
    assert summarize_store_result("steam", result) == (
        "Nenhuma promoção Free-to-Keep ativa",
        None,
    )
    assert store_result_message_key("steam", result) == "status.noActiveGiveaways"


def test_run_logs_in_before_official_discovery_and_accepts_valid_empty_result():
    claimer = SteamClaimer()
    calls: list[str] = []

    class Page:
        async def get(self, _url):
            calls.append("open-store")

    async def start_browser(**_kwargs):
        calls.append("start")
        claimer.page = Page()

    async def no_sleep(_seconds):
        pass

    async def dismiss():
        calls.append("cookies")

    async def ensure(_return_url):
        calls.append("login")
        return True

    async def official():
        calls.append("official-search")
        return []

    async def steamdb():
        raise AssertionError("valid empty official results must not open SteamDB")

    async def close():
        calls.append("close")

    claimer.start_browser = start_browser
    claimer.sleep = no_sleep
    claimer._dismiss_cookie_banner = dismiss
    claimer._ensure_logged_in = ensure
    claimer._fetch_steam_store_promotions = official
    claimer._fetch_steamdb_via_browser = steamdb
    claimer.close_browser = close

    asyncio.run(claimer.run())

    assert calls == [
        "start", "open-store", "cookies", "login", "official-search",
        "open-store", "close",
    ]


def test_run_does_not_start_discovery_when_manual_login_times_out():
    claimer = SteamClaimer()
    discovered = False

    class Page:
        async def get(self, _url):
            pass

    async def start_browser(**_kwargs):
        claimer.page = Page()

    async def no_op(*_args, **_kwargs):
        pass

    async def login_failed(_return_url):
        return False

    async def official():
        nonlocal discovered
        discovered = True
        return []

    claimer.start_browser = start_browser
    claimer.sleep = no_op
    claimer._dismiss_cookie_banner = no_op
    claimer._ensure_logged_in = login_failed
    claimer._fetch_steam_store_promotions = official
    claimer.close_browser = no_op

    asyncio.run(claimer.run())

    assert discovered is False
