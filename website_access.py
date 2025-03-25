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


        clicked = try_click_apply_button(page)
        if not clicked:
            print("❌ No Apply button could be interacted with")


        browser.close()


# Try to find and click the Apply button robustly
def try_click_apply_button(page):
    print("🔍 Looking for an Apply button...")

    # 1. Try common button, link, or role="button" containers
    apply_button = page.locator("button, a, div[role='button']", has_text="Apply").first

    try:
        # 2. Scroll into view and wait
        apply_button.scroll_into_view_if_needed(timeout=3000)
        page.wait_for_timeout(1000)

        # 3. Check visibility or fallback to enabled
        if apply_button.is_visible():
            apply_button.click()
            print("✅ Clicked the Apply button (visible)")
        elif apply_button.is_enabled():
            page.evaluate("(el) => el.click()", apply_button)
            print("✅ Clicked the Apply button (JS click on enabled element)")
        else:
            print("❌ Apply button found but not interactable")
            return False

        # 4. Wait after click
        page.wait_for_timeout(5000)
        page.screenshot(path="after_apply.png")
        return True

    except Exception as e:
        print(f"❌ Could not click the Apply button: {e}")

    # 5. Fallback: Look in iframes (Issue 4)
    print("🔍 Checking iframes for Apply button...")
    for frame in page.frames:
        try:
            frame_button = frame.locator("button, a, div[role='button']", has_text="Apply").first
            if frame_button.is_visible():
                frame_button.click()
                print("✅ Clicked Apply inside an iframe")
                frame.page.wait_for_timeout(5000)
                frame.page.screenshot(path="after_apply_iframe.png")
                return True
        except Exception as fe:
            continue

    print("❌ Apply button not found or clickable in main page or iframes.")
    return False



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
open_page_and_capture("https://neuralink.com/careers/apply/?gh_jid=5315757003&gh_src=c356a2533us")
