"""Optional browser smoke check: pip install playwright, then python tests/browser_check.py."""

from pathlib import Path
import os
from playwright.sync_api import sync_playwright


BASE = "http://127.0.0.1:5000"
SCREENSHOT = Path(os.environ.get("TEMP", ".")) / "reasoniqs-desktop.png"
MOBILE_SCREENSHOT = Path(os.environ.get("TEMP", ".")) / "reasoniqs-mobile.png"
SUBTYPE_SCREENSHOT = Path(os.environ.get("TEMP", ".")) / "reasoniqs-subtypes.png"
SETUP_SCREENSHOT = Path(os.environ.get("TEMP", ".")) / "reasoniqs-setup.png"
TEST_SCREENSHOT = Path(os.environ.get("TEMP", ".")) / "reasoniqs-test.png"
RESULT_SCREENSHOT = Path(os.environ.get("TEMP", ".")) / "reasoniqs-result.png"
MOBILE_SETUP_SCREENSHOT = Path(os.environ.get("TEMP", ".")) / "reasoniqs-mobile-setup.png"
MOBILE_TEST_SCREENSHOT = Path(os.environ.get("TEMP", ".")) / "reasoniqs-mobile-test.png"


def check():
    with sync_playwright() as playwright:
        cached_browser = Path.home() / "AppData/Local/ms-playwright/chromium-1223/chrome-win64/chrome.exe"
        launch_options = {"executable_path": str(cached_browser)} if cached_browser.is_file() else {}
        browser = playwright.chromium.launch(headless=True, **launch_options)
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(BASE)
        page.get_by_role("button", name="Mechanical Reasoning:").wait_for()
        assert page.locator(".domain").count() == 3
        page.screenshot(path=str(SCREENSHOT), full_page=True)
        for domain in ("Mechanical", "Spatial", "Verbal"):
            page.get_by_role("button", name=f"{domain} Reasoning:").click()
            assert page.locator(".subtype").count() == 6
            page.get_by_role("link", name="ReasonIQs home").click()
        page.get_by_role("button", name="Mechanical Reasoning:").click()
        page.screenshot(path=str(SUBTYPE_SCREENSHOT), full_page=True)
        page.get_by_role("button", name="Gears & Rotation:").click()
        page.locator("#item-count").fill("5")
        page.locator("#choice-count").fill("6")
        page.locator("#timer-enabled").check()
        assert page.locator("#duration-row").is_visible()
        page.locator("#seconds-per-item").fill("10")
        page.get_by_label("Challenge").check()
        assert "5 items · 6 choices · Challenge · 10 sec/item" in page.locator("#summary-line").inner_text()
        page.reload()
        assert page.locator("#item-count").input_value() == "5"
        assert page.locator("#timer-enabled").is_checked()
        page.screenshot(path=str(SETUP_SCREENSHOT), full_page=True)
        page.get_by_role("button", name="Start practice").click()
        page.get_by_role("heading", name="Question 1 of 5").wait_for()
        page.screenshot(path=str(TEST_SCREENSHOT), full_page=True)
        assert page.locator(".choice").count() == 6
        assert page.locator("#timer").is_visible()
        first_time = page.locator("#timer-value").inner_text()
        page.wait_for_timeout(1200)
        assert page.locator("#timer-value").inner_text() != first_time
        page.get_by_role("heading", name="Question 2 of 5").wait_for(timeout=12000)
        assert "1 timed out" in page.locator(".test-header p").inner_text()
        page.locator(".choice").nth(1).click()
        page.get_by_role("button", name="Next").click()
        page.get_by_role("button", name="Previous").click()
        assert page.locator(".choice input").nth(1).is_checked()
        page.once("dialog", lambda dialog: dialog.accept())
        page.get_by_role("button", name="Finish", exact=True).click()
        page.get_by_role("heading", name="Session complete.").wait_for()
        page.screenshot(path=str(RESULT_SCREENSHOT), full_page=True)
        assert "placeholder score" in page.locator(".result-score").inner_text().lower()
        page.get_by_role("button", name="Practice again").click()
        page.get_by_role("heading", name="Question 1 of 5").wait_for()
        page.once("dialog", lambda dialog: dialog.accept())
        page.get_by_role("button", name="Leave practice").click()
        page.get_by_role("heading", name="Set your practice pace.").wait_for()
        page.locator("#timer-enabled").uncheck()
        assert not page.locator("#duration-row").is_visible()
        page.get_by_role("button", name="Start practice").click()
        page.get_by_role("heading", name="Question 1 of 5").wait_for()
        assert page.locator("#timer").count() == 0
        for width in (320, 375, 768, 1024, 1366):
            page.set_viewport_size({"width": width, "height": 900})
            assert not page.evaluate("document.documentElement.scrollWidth > window.innerWidth"), f"Test overflow at {width}px"
            if width == 320:
                page.screenshot(path=str(MOBILE_TEST_SCREENSHOT), full_page=True)
        page.reload()
        page.get_by_role("heading", name="Set your practice pace.").wait_for()
        for width in (320, 375, 768, 1024, 1366, 1920):
            page.set_viewport_size({"width": width, "height": 900})
            page.wait_for_timeout(100)
            overflow = page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
            assert not overflow, f"Horizontal overflow at {width}px"
            if width == 320:
                page.screenshot(path=str(MOBILE_SETUP_SCREENSHOT), full_page=True)
        page.emulate_media(reduced_motion="reduce")
        assert page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches")
        page.get_by_role("link", name="ReasonIQs home").click()
        page.set_viewport_size({"width": 375, "height": 812})
        page.get_by_role("button", name="Spatial Reasoning:").click()
        assert not page.evaluate("document.documentElement.scrollWidth > window.innerWidth"), "Subtype overflow at 375px"
        page.get_by_role("button", name="All reasoning domains").click()
        page.screenshot(path=str(MOBILE_SCREENSHOT), full_page=True)
        page.keyboard.press("Tab")
        assert page.evaluate("document.activeElement.classList.contains('domain')")
        assert not errors, errors
        browser.close()
    print(f"Browser workflow passed. Screenshots: {SCREENSHOT}, {MOBILE_SCREENSHOT}")


if __name__ == "__main__":
    check()
