"""Focused tests for the Shopee Coins page parser and dashboard-safe result."""

from src.gui.state import summarize_store_result
from src.stores.shopee import parse_coin_page


def test_parse_available_shopee_daily_checkin():
    result = parse_coin_page({
        "body": "Central de Moedas 0 Hoje Dia 2 Dia 3",
        "controls": ["Faça o check-in e ganhe 1 moeda(s)"],
    })
    assert result == {
        "loaded": True,
        "claimed": False,
        "offeredCoins": 1,
        "balance": 0,
        "checkinAvailable": True,
    }


def test_parse_claimed_shopee_daily_checkin():
    result = parse_coin_page({
        "body": "Central de Moedas 12 Check-in realizado. Volte amanhã.",
        "controls": [],
    })
    assert result["loaded"] is True
    assert result["claimed"] is True
    assert result["checkinAvailable"] is False
    assert result["balance"] == 12


def test_shopee_result_uses_existing_safe_coin_details():
    message, details = summarize_store_result("shopee", {
        "checkin": {"outcome": "collected", "claimedCoins": 1, "offeredCoins": 1, "balance": 7}
    })
    assert message == "1 moedas coletadas"
    assert details == {
        "kind": "coins", "outcome": "collected", "claimedCoins": 1,
        "offeredCoins": 1, "balance": 7, "streakDays": None, "tomorrowCoins": None,
    }
