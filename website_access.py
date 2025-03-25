from playwright.sync_api import sync_playwright
import json
from PIL import Image
import pytesseract
import re

def open_page_and_capture(link: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            device_scale_factor=1,
        )
        page = context.new_page()
        print(f"Navigating to {link}")
        page.goto(link, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)  # extra delay for full rendering

        # Additional scroll to help lazy loading
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(2000)

        try:
            page.wait_for_selector("body", state="visible", timeout=10000)
        except Exception as e:
            print("⚠️ Body not visible, continuing anyway...")

        screenshot_path = "viewport_screenshot.png"
        page.screenshot(path=screenshot_path)
        print(f"✅ Screenshot saved to: {screenshot_path}")

        scrape(page=page, link=link)

        # Use our robust apply button click logic
        if not try_click_apply_button(page):
            print("❌ No Apply button could be interacted with via standard logic")
            if not is_embedded_form_present(page):
                # If no embedded form either, try lazy scrolling
                lazy_scroll_and_find_apply_button(page)

        browser.close()


def compute_candidate_score(candidate) -> int:
    """
    Returns a score for a candidate element based on its inner text, tag name,
    and bounding box dimensions. Adjust weights as needed.
    """
    try:
        text = candidate.inner_text().strip().lower()
    except Exception:
        text = ""
    score = 0
    # Positive keywords
    if "apply" in text:
        score += 10
    if text in ["apply", "apply now"]:
        score += 5
    if "submit resume" in text:
        score += 8
    if "start application" in text:
        score += 8

    # Negative keywords (false positives)
    if "learn more" in text:
        score -= 50
    if "how to" in text:
        score -= 30
    if "details" in text:
        score -= 10
    if "job alert" in text:
        score -= 10

    # Tag name bonus
    try:
        tag_name = candidate.evaluate("el => el.tagName")
        if tag_name:
            tag_name = tag_name.lower()
            if tag_name == "button":
                score += 5
            elif tag_name == "a":
                score += 3
            elif tag_name == "div":
                score += 2
    except Exception:
        pass

    # Optionally consider size (if element is very small, it might not be the real button)
    try:
        box = candidate.bounding_box()
        if box:
            if box["width"] < 50 or box["height"] < 20:
                score -= 5
            else:
                score += 2
    except Exception:
        pass

    return score


def get_best_apply_candidate(page, pattern) -> (object, int):
    """
    Returns the candidate element with the highest score and its score.
    """
    candidates = page.locator("button, a, div[role='button']", has_text=pattern)
    count = candidates.count()
    best_candidate = None
    best_score = -9999

    for i in range(count):
        candidate = candidates.nth(i)
        try:
            text = candidate.inner_text().strip()
        except Exception:
            text = ""
        score = compute_candidate_score(candidate)
        print(f"Candidate {i}: text='{text}', score={score}")
        if score > best_score:
            best_score = score
            best_candidate = candidate

    return best_candidate, best_score


def try_click_apply_button(page):
    print("🔍 Looking for an Apply button using robust candidate scoring (standard logic)...")
    # Use a regex that broadly matches our interest keywords
    pattern = re.compile(r"(apply|submit resume|start application)", re.IGNORECASE)
    candidate, score = get_best_apply_candidate(page, pattern)
    if not candidate:
        print("❌ No candidate found for Apply button (standard logic).")
        return False

    try:
        print(f"🔍 Best candidate found with score {score} and text: '{candidate.inner_text().strip()}'")
    except Exception:
        pass

    try:
        try:
            candidate.scroll_into_view_if_needed(timeout=3000)
        except Exception as se:
            print(f"⚠️ scroll_into_view_if_needed failed: {se}")
        page.wait_for_timeout(1000)

        if candidate.is_visible():
            candidate.click()
            print("✅ Clicked the Apply button (visible)")
        elif candidate.is_enabled():
            handle = candidate.element_handle()
            if handle:
                page.evaluate("(el) => el.click()", handle)
                print("✅ Clicked the Apply button (JS click on enabled element)")
            else:
                print("❌ Could not obtain element handle for candidate")
                return False
        else:
            print("❌ Candidate found but not interactable")
            return False

        page.wait_for_timeout(5000)
        page.screenshot(path="after_apply.png")
        return True

    except Exception as e:
        print(f"❌ Could not click the Apply button (standard logic): {e}")
        return False


def is_embedded_form_present(page) -> bool:
    print("🔍 Checking for embedded application form...")
    try:
        for frame in page.frames:
            frame_url = frame.url.lower()
            if any(host in frame_url for host in ["greenhouse.io", "lever.co", "workday.com"]):
                if frame.locator("input, textarea, select").count() > 0:
                    print(f"✅ Detected embedded application form in iframe: {frame_url}")
                    return True
    except Exception as e:
        print("⚠️ Error while checking for embedded form:", e)
    print("❌ No embedded form detected.")
    return False


def lazy_scroll_and_find_apply_button(page):
    print("🔍 Trying lazy-loading approach for Apply button using robust candidate scoring...")
    pattern = re.compile(r"(apply|submit resume|start application)", re.IGNORECASE)
    previous_height = 0
    max_scroll_attempts = 10
    candidate = None

    for attempt in range(max_scroll_attempts):
        candidate, score = get_best_apply_candidate(page, pattern)
        if candidate:
            try:
                text = candidate.inner_text().strip()
            except Exception:
                text = ""
            print(f"🔍 (Lazy) Candidate found on scroll attempt {attempt+1} with score {score} and text: '{text}'")
            if score > 0:
                break
        # Scroll down to load more content
        page.evaluate("window.scrollBy(0, window.innerHeight)")
        page.wait_for_timeout(2000)
        new_height = page.evaluate("document.body.scrollHeight")
        if new_height == previous_height:
            print("Reached the bottom of the page.")
            break
        previous_height = new_height

    if not candidate:
        print("❌ No Apply button found via lazy-loading approach.")
        return False

    try:
        try:
            candidate.scroll_into_view_if_needed(timeout=3000)
        except Exception as se:
            print(f"⚠️ scroll_into_view_if_needed failed (lazy-loading): {se}")
        page.wait_for_timeout(1000)
        if candidate.is_visible():
            candidate.click()
            print("✅ Clicked the Apply button (lazy-loading approach)")
        elif candidate.is_enabled():
            handle = candidate.element_handle()
            if handle:
                page.evaluate("(el) => el.click()", handle)
                print("✅ Clicked the Apply button (JS click in lazy-loading approach)")
            else:
                print("❌ Could not obtain element handle for candidate in lazy-loading approach")
                return False
        else:
            print("❌ Candidate found in lazy-loading approach but not interactable")
            return False

        page.wait_for_timeout(5000)
        page.screenshot(path="after_apply_lazy.png")
        return True

    except Exception as e:
        print(f"❌ Could not click the Apply button (lazy-loading approach): {e}")
        return False


def scrape(page, link):
    print("inside scrape")
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(2000)
    screenshot_path = "fullpage.png"
    page.screenshot(path=screenshot_path, full_page=True)
    print("📸 Full page screenshot taken.")
    img = Image.open(screenshot_path)
    text = pytesseract.image_to_string(img)
    print("🧠 OCR Result:\n", text[:1000])
    return text


# Test the functions
open_page_and_capture("https://neuralink.com/careers/apply/?gh_jid=5315757003&gh_src=c356a2533us")
