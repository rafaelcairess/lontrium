"""Run a sanitized browser smoke test against the local documentation preview."""

from __future__ import annotations

import json
import os

import nodriver as uc


URL = os.environ.get("CLAIMER_PREVIEW_URL", "http://host.docker.internal:8765")
LOCALES = ("en", "pt-BR", "es")


async def click(page, selector: str) -> None:
    await page.evaluate(f"document.querySelector({selector!r}).click()")
    await page.sleep(0.1)


async def check_locale(page, locale: str) -> None:
    await page.evaluate(
        f"localStorage.setItem('claimer-control-language', {locale!r}); location.reload()"
    )
    await page.sleep(0.5)
    result = json.loads(await page.evaluate("""
      JSON.stringify({
        lang: document.documentElement.lang,
        title: document.querySelector('.setup-page-header h2')?.textContent.trim(),
        fits: document.documentElement.scrollWidth <= window.innerWidth
      })
    """))
    assert result["lang"] == locale
    assert result["title"]
    assert result["fits"]

    await click(page, "#setupNext")
    await click(page, "#setupNext")
    await click(page, 'input[name="setup-login-mode"][value="credentials"]')
    await click(page, "#setupNext")
    await click(page, ".help-button")
    tooltip = json.loads(await page.evaluate("""
      JSON.stringify((() => {
        const button = document.querySelector('.help-button');
        const tip = document.getElementById(button.getAttribute('aria-describedby'));
        button.focus();
        return {
          expanded: button.getAttribute('aria-expanded'),
          role: tip?.getAttribute('role'),
          text: tip?.textContent.trim(),
          visible: getComputedStyle(tip).visibility === 'visible',
          fits: document.querySelector('#onboardingContent').scrollWidth <=
            document.querySelector('#onboardingContent').clientWidth
        };
      })())
    """))
    assert tooltip["expanded"] == "true"
    assert tooltip["role"] == "tooltip"
    assert tooltip["text"]
    assert tooltip["visible"]
    assert tooltip["fits"]


async def check_settings_navigation(page) -> None:
    await page.evaluate("location.reload()")
    await page.sleep(0.5)
    for _ in range(6):
        await click(page, "#setupNext")
    await click(page, "#settingsButton")
    result = json.loads(await page.evaluate("""
      JSON.stringify({
        items: document.querySelectorAll('.settings-nav-item').length,
        icons: document.querySelectorAll('.settings-nav-item .store-icon, .settings-nav-item .settings-nav-symbol').length,
        storeLogos: document.querySelectorAll('.settings-nav-item .store-logo').length,
        fits: document.querySelector('#settingsDrawer').scrollWidth <= window.innerWidth
      })
    """))
    assert result["items"] == result["icons"]
    assert result["storeLogos"] > 0
    assert result["fits"]
    await click(page, '.settings-nav-item[data-section="section.introduction"]')
    await click(page, ".settings-introduction .button")
    preview = json.loads(await page.evaluate("""
      JSON.stringify({
        visible: !document.querySelector('#onboarding').hidden,
        exitVisible: !document.querySelector('#setupExit').hidden
      })
    """))
    assert preview == {"visible": True, "exitVisible": True}
    await click(page, "#setupExit")
    assert await page.evaluate("document.querySelector('#onboarding').hidden") is True


async def main() -> None:
    for viewport in ("1440,900", "390,844"):
        browser = await uc.start(
            headless=True,
            browser_args=[f"--window-size={viewport}", "--force-device-scale-factor=1"],
        )
        try:
            page = await browser.get(URL)
            await page.sleep(0.5)
            for locale in LOCALES:
                await check_locale(page, locale)
            await check_settings_navigation(page)
        finally:
            browser.stop()
    print("Visual smoke test passed for en, pt-BR and es at desktop and mobile widths.")


if __name__ == "__main__":
    uc.loop().run_until_complete(main())
