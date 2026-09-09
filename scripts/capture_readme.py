"""Capture the sanitized dashboard preview for README documentation."""

from __future__ import annotations

import asyncio
from pathlib import Path

import nodriver as uc


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "docs" / "images"
URL = "http://host.docker.internal:8765"


async def shot(page, name: str) -> None:
    await page.sleep(0.35)
    await page.save_screenshot(str(OUTPUT / name))


async def click(page, selector: str) -> None:
    await page.evaluate(f"document.querySelector({selector!r}).click()")
    await page.sleep(0.2)


async def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    browser = await uc.start(
        headless=True,
        browser_args=["--window-size=1440,1050", "--force-device-scale-factor=1"],
    )
    try:
        page = await browser.get(URL)
        await page.sleep(1)
        await page.evaluate("localStorage.setItem('claimer-control-language', 'pt-BR'); location.reload()")
        await page.sleep(1)
        await click(page, "#setupNext")
        await click(page, "#setupNext")
        await click(page, 'input[name="setup-login-mode"][value="credentials"]')
        await click(page, "#setupNext")
        await click(page, ".help-button")
        await shot(page, "04-credentials.png")

        await click(page, "#setupNext")
        await click(page, "#setupNext")
        await click(page, "#setupNext")
        await page.sleep(1)
        await shot(page, "05-dashboard.png")

        await page.evaluate("""
          [...document.querySelectorAll('.store-row')].forEach(row => {
            row.style.display = row.querySelector('.store-key')?.textContent === 'aliexpress' ? 'grid' : 'none';
          });
          document.querySelector('.add-store-row').style.display = 'none';
          document.querySelector('.stores-section').scrollIntoView({block: 'center'});
        """)
        await shot(page, "06-aliexpress.png")
    finally:
        browser.stop()


if __name__ == "__main__":
    uc.loop().run_until_complete(main())
