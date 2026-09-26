"""Optional live-browser check for the two procedural spatial subtypes."""

from pathlib import Path
import struct
import tempfile

from playwright.sync_api import sync_playwright


def png_size(download):
    with open(download.path(), "rb") as image:
        header = image.read(24)
    assert header[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", header[16:24])


def check():
    with sync_playwright() as playwright:
        cached = Path.home() / "AppData/Local/ms-playwright/chromium-1223/chrome-win64/chrome.exe"
        browser = playwright.chromium.launch(headless=True,
                                             **({"executable_path": str(cached)} if cached.is_file() else {}))
        page = browser.new_page(viewport={"width": 1200, "height": 900}, accept_downloads=True)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        for name, theme in (("Dice Folding", "Characters"),
                            ("Dice Unfolding", "Abstract Structures"),
                            ("Dice Folding", "Shapes/Polygons")):
            page.goto("http://127.0.0.1:5000")
            page.get_by_role("button", name="Spatial Reasoning:").click()
            page.get_by_role("button", name=f"{name}:").click()
            page.locator("#item-count").fill("5")
            page.locator("#choice-count").fill("6")
            page.locator("#timer-enabled").check()
            page.locator("#seconds-per-item").fill("45")
            page.get_by_label("Challenge").check()
            page.locator("#cube-theme").select_option(theme)
            page.get_by_role("button", name="Start practice").click()
            page.get_by_role("heading", name="Question 1 of 5").wait_for()
            assert page.locator(".placeholder-label").count() == 0
            assert page.locator(".choice-figures svg").count() == 6
            assert page.locator(".question-figures svg").count() == (2 if name == "Dice Unfolding" else 1)
            assert page.locator(".question-prompt").inner_text().startswith("Which")
            page.screenshot(path=str(Path(tempfile.gettempdir()) / f"reasoniqs-{name.lower().replace(' ', '-')}-{theme.lower().replace('/', '-').replace(' ', '-')}.png"), full_page=True)
            page.locator(".question-figures .figure-card").first.hover()
            page.locator(".question-figures .figure-inspect").first.click()
            assert page.get_by_role("dialog").is_visible()
            page.get_by_role("button", name="Zoom in").click()
            assert page.locator(".figure-zoom-value").inner_text() == "125%"
            page.keyboard.press("Escape")
            with page.expect_download() as event:
                page.locator(".question-figures .figure-export").first.click()
            width, height = png_size(event.value)
            assert width > 200 and height > 200
            if name == "Dice Unfolding":
                assert width > height, (width, height)
            for viewport in (320, 375, 768, 1200):
                page.set_viewport_size({"width": viewport, "height": 900})
                assert not page.evaluate("document.documentElement.scrollWidth > innerWidth"), viewport
            page.set_viewport_size({"width": 1200, "height": 900})
            page.get_by_role("button", name="Submit answer").click()
            assert "Select an answer" in page.locator("#answer-feedback").inner_text()
            first_correct = int((page.evaluate("async () => { const {state} = await import('/static/js/state.js'); return state.questions[0].correct_answer_id; }")).split("-")[-1]) - 1
            wrong = (first_correct + 1) % 6
            page.locator(".choice-figures .figure-surface").nth(wrong).click()
            assert page.locator(".choice input").nth(wrong).is_checked()
            page.get_by_role("button", name="Submit answer").click()
            assert page.locator("#answer-feedback strong").inner_text() == "Incorrect"
            assert page.locator("#timer").count() == 0
            page.screenshot(path=str(Path(tempfile.gettempdir()) / "reasoniqs-answer-feedback.png"), full_page=True)
            assert page.locator(".choice-result-incorrect").count() == 1
            assert page.locator(".choice-result-correct").count() == 1
            assert page.locator(".choice input:disabled").count() == 6
            for viewport in (320, 375):
                page.set_viewport_size({"width": viewport, "height": 900})
                assert not page.evaluate("document.documentElement.scrollWidth > innerWidth"), viewport
            page.set_viewport_size({"width": 1200, "height": 900})
            page.get_by_role("button", name="Next").click()
            page.get_by_role("heading", name="Question 2 of 5").wait_for()
            assert page.locator("#timer").is_visible()
            second_correct = int((page.evaluate("async () => { const {state} = await import('/static/js/state.js'); return state.questions[1].correct_answer_id; }")).split("-")[-1]) - 1
            page.locator(".choice-figures .figure-surface").nth(second_correct).click()
            page.get_by_role("button", name="Submit answer").click()
            assert page.locator("#answer-feedback strong").inner_text() == "Correct"
            page.get_by_role("button", name="Previous").click()
            assert page.locator("#answer-feedback strong").inner_text() == "Incorrect"
            page.get_by_role("button", name="Next").click()
            assert page.locator("#answer-feedback strong").inner_text() == "Correct"
            page.once("dialog", lambda dialog: dialog.accept())
            page.get_by_role("button", name="Finish", exact=True).click()
            page.get_by_role("heading", name="Session complete.").wait_for()
            assert "correct answers" in page.locator(".result-score").inner_text().lower()
            assert "1/5" in page.locator(".result-score").inner_text()
        assert not errors, errors
        browser.close()
    print("Spatial browser workflow passed.")


if __name__ == "__main__":
    check()
