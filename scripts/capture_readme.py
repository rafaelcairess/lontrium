"""Capture the sanitized dashboard preview for README documentation."""

from __future__ import annotations

import os
from pathlib import Path

import nodriver as uc


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "docs" / "images"
URL = os.environ.get("LONTRIUM_PREVIEW_URL", "http://127.0.0.1:8765")
LOCALE = os.environ.get("LONTRIUM_CAPTURE_LOCALE", "en")
EDGE = os.environ.get(
    "LONTRIUM_BROWSER_PATH",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
)


async def shot(page, name: str) -> None:
    await page.sleep(0.35)
    await page.save_screenshot(str(OUTPUT / name))


async def click(page, selector: str) -> None:
    await page.evaluate(f"document.querySelector({selector!r}).click()")
    await page.sleep(0.2)


async def screenshot(page, name: str, *, scroll_top: bool = True) -> None:
    if scroll_top:
        await page.evaluate(
            "document.querySelector('.settings-content')?.scrollTo(0, 0);"
            "window.scrollTo(0, 0);"
        )
    await shot(page, name)


async def settings_section(page, section: str, name: str) -> None:
    print(f"capturing settings/{section}", flush=True)
    selector = f'[data-section="section.{section}"]'
    await page.evaluate(f"document.querySelector({selector!r})?.click()")
    await page.sleep(0.35)
    await screenshot(page, name)
    print(f"saved {name}", flush=True)


async def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    browser = await uc.start(
        headless=True,
        browser_executable_path=EDGE,
        browser_args=["--window-size=1440,1050", "--force-device-scale-factor=1"],
    )
    try:
        page = await browser.get(URL)
        await page.sleep(1)
        await page.evaluate(
            f"localStorage.setItem('claimer-control-language', {LOCALE!r}); location.reload()"
        )
        await page.sleep(1)
        await click(page, "#setupNext")
        await click(page, "#setupNext")
        await click(page, 'input[name="setup-login-mode"][value="credentials"]')
        await click(page, "#setupNext")
        await click(page, ".help-button")
        await shot(page, "08-credentials.png")

        await click(page, "#setupNext")
        await click(page, "#setupNext")
        await click(page, "#setupNext")
        await page.sleep(1)
        await screenshot(page, "01-dashboard.png")

        await click(page, "#settingsButton")
        await settings_section(page, "help", "02-help.png")
        await settings_section(page, "stores", "03-stores.png")
        await settings_section(page, "schedule", "04-schedule.png")
        await settings_section(page, "browser", "05-browser.png")
        await settings_section(page, "notifications", "06-notifications.png")

        await click(page, "#closeSettings")
        await page.sleep(0.35)
        await page.evaluate("""
          [...document.querySelectorAll('.store-row')].forEach(row => {
            row.style.display = row.querySelector('.store-name')?.textContent === 'AliExpress' ? 'grid' : 'none';
          });
          document.querySelector('.add-store-row').style.display = 'none';
          document.querySelector('.stores-section').scrollIntoView({block: 'center'});
        """)
        await shot(page, "07-aliexpress.png")
    finally:
        browser.stop()


if __name__ == "__main__":
    uc.loop().run_until_complete(main())
