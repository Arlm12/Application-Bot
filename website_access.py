from playwright.sync_api import sync_playwright
import json
from PIL import Image
import pytesseract


def open_page_and_capture(link: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # set to True in headless mode
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            device_scale_factor=1,
        )
        page = context.new_page()

        # Go to the page and wait until DOM is loaded
        print(f"Navigating to {link}")
        page.goto(link, wait_until="domcontentloaded", timeout=60000)

        # Extra delay to allow full visual rendering
        page.wait_for_timeout(5000)  # wait 5 seconds after DOM is loaded

        # Scroll down a little if needed
        page.mouse.wheel(0, 10)

        # Wait until body is visible and attached to DOM
        try:
            page.wait_for_selector("body", state="visible", timeout=10000)
        except Exception as e:
            print("⚠️ Body not visible, continuing anyway...")

        # Take a screenshot (viewport only)
        screenshot_path = "viewport_screenshot.png"
        page.screenshot(path=screenshot_path)
        print(f"✅ Screenshot saved to: {screenshot_path}")

        scrape(page=page,link=link)

        apply_button = page.locator("button, a", has_text="Apply").first
        if apply_button.is_visible():
            apply_button.click()
            print("✅ Clicked the Apply button")
            page.wait_for_timeout(5000)
            page.screenshot(path="after_apply.png")

        else:
            print("❌ Apply button not found or not visible")



        browser.close()


def scrape(page, link):
    print("inside")
    # Scroll fully to ensure content is rendered
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(2000)

    # Full page screenshot
    screenshot_path = "fullpage.png"
    page.screenshot(path=screenshot_path, full_page=True)
    print("📸 Screenshot taken.")

    # OCR it
    img = Image.open(screenshot_path)
    text = pytesseract.image_to_string(img)
    print("🧠 OCR Result:\n", text[:1000])  # print first 1000 chars
    return text



# Test it
open_page_and_capture("https://www.google.com/about/careers/applications/jobs/results/133883848537580230-workspace-sales-specialist-iii-greenfield-google-cloud?has_remote=true")
