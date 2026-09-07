"""Shopee Coins daily check-in.

The check-in control is read from the official Coins page.  It deliberately uses
the persistent browser profile and a manual VNC login when necessary; no account
credentials are collected or security challenges are automated.
"""

from __future__ import annotations

import json
import re

from src.core.claimer import BaseClaimer
from src.core.config import cfg


URL_COINS = "https://shopee.com.br/shopee-coins"

_SPACE_RE = re.compile(r"\s+")
_OFFER_RE = re.compile(
    r"(?:fa[çc]a|fazer)\s+(?:o\s+)?check[- ]?in.*?ganhe\s+(\d+)\s+moeda", re.I
)
_BALANCE_RE = re.compile(r"central\s+de\s+moedas\s*(\d+)", re.I)
_CLAIMED_RE = re.compile(
    r"check[- ]?in\s+(?:realizado|conclu[ií]do|feito)|volte\s+amanh[ãa]|j[áa]\s+fez\s+check[- ]?in",
    re.I,
)


def parse_coin_page(state: dict) -> dict:
    """Extract only the small, user-visible check-in state from a DOM snapshot."""
    text = _SPACE_RE.sub(" ", str((state or {}).get("body") or "")).strip()
    controls = " ".join(str(item) for item in ((state or {}).get("controls") or []))
    combined = f"{text} {controls}"
    offer = _OFFER_RE.search(combined)
    balance = _BALANCE_RE.search(text)
    loaded = "central de moedas" in text.lower()
    claimed = bool(_CLAIMED_RE.search(combined))
    return {
        "loaded": loaded,
        "claimed": claimed if loaded else None,
        "offeredCoins": int(offer.group(1)) if offer else None,
        "balance": int(balance.group(1)) if balance else None,
        "checkinAvailable": bool(offer) and not claimed,
    }


class ShopeeClaimer(BaseClaimer):
    store_name = "shopee"

    _PAGE_STATE_JS = r"""
        (() => {
            const text = el => (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
            const visible = el => {
                const r = el.getBoundingClientRect();
                const s = getComputedStyle(el);
                return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
            };
            return JSON.stringify({
                url: location.href,
                body: document.body ? text(document.body).slice(0, 12000) : '',
                controls: [...document.querySelectorAll('button, a, [role="button"]')]
                    .filter(visible).map(text).filter(Boolean).slice(0, 80),
            });
        })()
    """

    _CLICK_CHECKIN_JS = r"""
        (() => {
            const visible = el => {
                const r = el.getBoundingClientRect();
                const s = getComputedStyle(el);
                return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
            };
            const rx = /(?:fa[çc]a|fazer)\s+(?:o\s+)?check[- ]?in.*?ganhe\s+\d+\s+moeda/i;
            const target = [...document.querySelectorAll('button, a, [role="button"]')]
                .filter(visible).find(el => rx.test((el.innerText || el.textContent || '').replace(/\s+/g, ' ')));
            if (!target || target.disabled || target.getAttribute('aria-disabled') === 'true') return false;
            target.click();
            return true;
        })()
    """

    def __init__(self) -> None:
        super().__init__()
        self.checkin_summary: dict = {"outcome": "not_collected"}

    async def _page_state(self) -> dict:
        try:
            raw = await self.page.evaluate(self._PAGE_STATE_JS)
            return json.loads(raw) if isinstance(raw, str) else {}
        except Exception as exc:
            self.logger.debug("Could not inspect Shopee Coins page: %s", exc)
            return {}

    async def _read_coin_state(self) -> dict:
        state = parse_coin_page(await self._page_state())
        self.logger.info(
            "Shopee coin state detected by DOM: loaded=%s claimed=%s offer=%s balance=%s",
            state["loaded"], state["claimed"], state["offeredCoins"], state["balance"],
        )
        return state

    def _set_summary(self, outcome: str, state: dict, claimed_coins: int | None = None) -> None:
        self.checkin_summary = {
            "outcome": outcome,
            "claimedCoins": claimed_coins,
            "offeredCoins": state.get("offeredCoins"),
            "balance": state.get("balance"),
            "streakDays": None,
            "tomorrowCoins": None,
        }

    async def run(self) -> None:
        try:
            await self.start_browser(force_headful=True)
            await self.page.get(URL_COINS)
            await self.sleep(8)

            if await self._human_challenge_present() and not await self._wait_out_challenge("Shopee"):
                self.logger.error("Shopee security check was not completed in time.")
                return

            state = await self._read_coin_state()
            if not state["loaded"]:
                notice = self._vnc_notice(
                    "Shopee: manual login needed",
                    "Open the Shopee Coins page and finish signing in. The bot will then read the daily check-in.",
                )
                if not await self._wait_for_vnc_login(
                    lambda: self._page_loaded(), custom_msg=notice
                ):
                    self.logger.error("Shopee Coins page did not become available after the manual-login wait.")
                    return
                state = await self._read_coin_state()

            if not state["loaded"]:
                self.logger.error("Shopee Coins page did not render a recognizable check-in widget.")
                return
            self.logger.info("Shopee Coins page is signed in.")

            if state["claimed"]:
                self._set_summary("already_collected", state)
                self.logger.info("Shopee daily check-in was already collected today.")
                return
            if not state["checkinAvailable"]:
                self._set_summary("not_collected", state)
                self.logger.warning("Shopee Coins loaded but no available daily check-in button was found.")
                return
            if cfg.dryrun:
                self._set_summary("available", state)
                self.logger.info("DRYRUN - skipped Shopee daily check-in.")
                return

            before_balance = state["balance"]
            clicked = bool(await self.page.evaluate(self._CLICK_CHECKIN_JS))
            if not clicked:
                self._set_summary("not_collected", state)
                self.logger.warning("Shopee check-in control disappeared before it could be clicked.")
                return
            await self.sleep(5)
            after = await self._read_coin_state()
            confirmed = bool(after["claimed"]) or (
                before_balance is not None and after["balance"] is not None and after["balance"] > before_balance
            )
            if confirmed:
                self._set_summary("collected", after, state["offeredCoins"])
                self.logger.info("Shopee coins collected successfully.")
            else:
                self._set_summary("not_collected", after)
                self.logger.warning("Shopee check-in click could not be confirmed; no success was reported.")
        except Exception as exc:
            self.logger.exception("Shopee daily check-in failed: %s", exc)
            if cfg.notify_errors:
                await self.notify(f"Shopee failed: {exc}")
        finally:
            await self.close_browser()

    async def _page_loaded(self) -> bool:
        return bool((await self._read_coin_state())["loaded"])


async def claim_shopee() -> dict:
    """Convenience entry point for the Shopee daily coin check-in."""
    claimer = ShopeeClaimer()
    await claimer.run()
    return {
        "store": "Shopee",
        "user": claimer.user,
        "games": claimer.notify_games,
        "checkin": claimer.checkin_summary,
    }
