"""Optional figure workflow check against a running local Flask server."""

import struct
from pathlib import Path
from playwright.sync_api import sync_playwright


def png_size(download):
    with open(download.path(), "rb") as image:
        header = image.read(24)
    assert header[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", header[16:24])


def check():
    with sync_playwright() as playwright:
        cached_browser = Path.home() / "AppData/Local/ms-playwright/chromium-1223/chrome-win64/chrome.exe"
        launch_options = {"executable_path": str(cached_browser)} if cached_browser.is_file() else {}
        browser = playwright.chromium.launch(headless=True, **launch_options)
        page = browser.new_page(viewport={"width": 1200, "height": 900}, accept_downloads=True)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto("http://127.0.0.1:5000")
        page.get_by_role("button", name="Mechanical Reasoning:").click()
        page.get_by_role("button", name="Gears & Rotation:").click()
        page.get_by_role("button", name="Start practice").click()
        page.get_by_role("heading", name="Question 1 of 10").wait_for()
        assert page.locator(".question-figures .figure-card").count() == 2
        assert page.locator(".choices-visual .choice").count() == 4

        original_width = page.locator(".question-figures svg").first.bounding_box()["width"]
        page.locator(".question-figures .figure-surface").first.click()
        assert page.get_by_role("dialog").count() == 0
        page.locator(".question-figures .figure-card").first.hover()
        page.locator(".question-figures .figure-inspect").first.click()
        dialog = page.get_by_role("dialog", name="First prototype diagram")
        assert dialog.is_visible()
        assert dialog.locator("svg").bounding_box()["width"] > original_width
        page.get_by_role("button", name="Zoom in").click()
        assert dialog.locator(".figure-zoom-value").inner_text() == "125%"
        page.keyboard.press("ArrowRight")
        page.keyboard.press("0")
        assert dialog.locator(".figure-zoom-value").inner_text() == "100%"
        page.keyboard.press("Escape")
        assert page.get_by_role("dialog").count() == 0
        assert page.locator(".choice input:checked").count() == 0
        page.locator(".choice-figures .figure-surface").first.click()
        assert page.get_by_role("dialog").count() == 0
        assert page.locator(".choice input:checked").count() == 0
        inspect = page.locator(".choice-figures .figure-inspect").first
        inspect.focus()
        page.wait_for_function("getComputedStyle(document.querySelector('.choice-figures .figure-actions')).opacity === '1'")
        assert inspect.evaluate("element => getComputedStyle(element.parentElement).opacity") == "1"
        page.keyboard.press("Enter")
        assert page.get_by_role("dialog").is_visible()
        page.keyboard.press("Escape")

        with page.expect_download() as merged_event:
            page.locator(".question-figures .figure-export").first.click()
        merged = merged_event.value
        assert merged.suggested_filename == "reasoniqs_question_01.png"
        merged_width, merged_height = png_size(merged)
        assert merged_width > merged_height > 200

        page.locator(".choice-figures .figure-card").first.hover()
        with page.expect_download() as single_event:
            page.locator(".choice-figures .figure-export").first.click()
        single = single_event.value
        assert single.suggested_filename == "reasoniqs_question_01_choice_a.png"
        assert png_size(single)[0] > 200

        page.locator(".choice-select").nth(1).click()
        assert page.locator(".choice input").nth(1).is_checked()
        page.get_by_role("button", name="Next").click()
        assert page.locator(".question-prompt").count() == 0
        assert page.locator(".question-figures .figure-card").count() == 1
        page.get_by_role("button", name="Previous").click()
        assert page.locator(".choice input").nth(1).is_checked()

        page.evaluate("""async () => {
          const { state } = await import('/static/js/state.js');
          const { renderTest } = await import('/static/js/render.js');
          const { registerCanvasRenderer, registerDomRenderer } = await import('/static/js/figures.js');
          registerCanvasRenderer('test-canvas', (ctx) => {
            ctx.fillStyle = '#408080'; ctx.fillRect(0, 0, 400, 200);
          });
          registerDomRenderer('test-dom', () => {
            const node = document.createElement('div');
            node.style.cssText = 'width: 220px; height: 110px; background: #ffd080';
            node.textContent = 'A + B';
            return node;
          });
          const raster = document.createElement('canvas');
          raster.width = 240; raster.height = 140;
          raster.getContext('2d').fillRect(0, 0, 240, 140);
          const encoded = raster.toDataURL('image/png');
          state.questions[0].figures = [
            { kind: 'canvas', renderer: 'test-canvas', width: 400, height: 200, alt: 'Canvas diagram' },
            { kind: 'dom', renderer: 'test-dom', alt: 'DOM diagram' },
            { kind: 'image', src: encoded, alt: 'Raster diagram' },
            { kind: 'image', base64: encoded.split(',')[1], mime: 'image/png', alt: 'Base64 diagram' },
            { kind: 'image', src: '/static/assets/icons/mark.svg', alt: 'Local image diagram' }
          ];
          state.questions[0].choices[0].figures = [
            state.questions[0].figures[0], state.questions[0].figures[2]
          ];
          renderTest();
        }""")
        assert page.locator(".question-figures .figure-card").count() == 5
        page.locator(".question-figures .figure-card").last.hover()
        with page.expect_download() as adapters_event:
            page.locator(".question-figures .figure-export").last.click()
        assert adapters_event.value.suggested_filename == "reasoniqs_question_01.png"
        assert png_size(adapters_event.value)[0] > 500
        assert page.locator(".choice-figures").first.locator(".figure-card").count() == 2
        page.locator(".choice-figures").first.locator(".figure-card").first.hover()
        with page.expect_download() as choice_pair_event:
            page.locator(".choice-figures").first.locator(".figure-export").first.click()
        assert choice_pair_event.value.suggested_filename == "reasoniqs_question_01_choice_a.png"

        for width in (320, 375, 768, 1200):
            page.set_viewport_size({"width": width, "height": 900})
            assert not page.evaluate("document.documentElement.scrollWidth > innerWidth"), width
        assert not errors, errors
        touch = browser.new_context(viewport={"width": 375, "height": 812}, is_mobile=True, has_touch=True, accept_downloads=True)
        touch_page = touch.new_page()
        touch_page.goto("http://127.0.0.1:5000")
        touch_page.get_by_role("button", name="Mechanical Reasoning:").tap()
        touch_page.get_by_role("button", name="Gears & Rotation:").tap()
        touch_page.get_by_role("button", name="Start practice").tap()
        export = touch_page.locator(".question-figures .figure-export").first
        assert export.evaluate("element => getComputedStyle(element).opacity") == "1"
        touch_page.locator(".question-figures .figure-surface").first.tap()
        assert touch_page.get_by_role("dialog").count() == 0
        touch_page.locator(".question-figures .figure-inspect").first.tap()
        assert touch_page.get_by_role("dialog").is_visible()
        touch_page.get_by_role("button", name="Zoom in").tap()
        assert touch_page.locator(".figure-zoom-value").inner_text() == "125%"
        touch_page.get_by_role("button", name="Close figure inspection").tap()
        touch.close()
        browser.close()
    print("Figure workflow passed.")


if __name__ == "__main__":
    check()
