import asyncio
import json
import re
import os
from PIL import Image
import pytesseract
from playwright.async_api import async_playwright



async def open_page_and_capture(link: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            device_scale_factor=1,
        )
        page = await context.new_page()
        print(f"Navigating to {link}")
        await page.goto(link, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000)

        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(2000)

        try:
            await page.wait_for_selector("body", state="visible", timeout=10000)
        except Exception:
            print("⚠️ Body not visible, continuing anyway...")

        await handle_cookie_prompt(page)

        screenshot_path = "viewport_screenshot.png"
        await page.screenshot(path=screenshot_path)
        print(f"✅ Screenshot saved to: {screenshot_path}")

        await scrape(page=page, link=link)

        if not await try_click_apply_button(page):
            print("❌ No Apply button could be interacted with via standard logic")
            if not await is_embedded_form_present(page):
                await lazy_scroll_and_find_apply_button(page)

        await browser.close()


async def handle_cookie_prompt(page):
    print("🔍 Checking for cookie prompt...")
    try:
        buttons = page.locator("button, a",
                               has_text=re.compile(r"(accept all|reject all|Decline the cookies|cookie settings)", re.IGNORECASE))
        count = await buttons.count()

        for i in range(count):
            button = buttons.nth(i)
            text = await button.inner_text()
            if text.lower() in ["accept all", "reject all", "Decline the cookies"]:
                print(f"✅ Found cookie button: {text}. Clicking it...")
                await button.click()
                await page.wait_for_timeout(2000)
                print("✅ Cookie prompt handled successfully.")
                return
    except Exception as e:
        print(f"⚠️ Cookie prompt detection failed: {e}")
    print("❌ No cookie prompt detected or handled.")


async def scrape(page, link):
    print("inside scrape")
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await page.wait_for_timeout(2000)

    screenshot_path = "fullpage.png"
    await page.screenshot(path=screenshot_path, full_page=True)
    print("📸 Full page screenshot taken.")

    img = Image.open(screenshot_path)
    text = pytesseract.image_to_string(img)

    if len(text) < 2000:
        print("Scroll and capture function invoked")
        await scroll_and_capture_all(link)

    print("🧠 OCR Result:\n", text[:5000])


async def scroll_and_capture_all(link: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1,
        )
        page = await context.new_page()
        await page.goto(link, wait_until="networkidle", timeout=60000)

        total_height = await page.evaluate("() => document.body.scrollHeight")
        view_height = 1080
        screenshots = []

        for i, offset in enumerate(range(0, total_height, view_height)):
            await page.evaluate(f"window.scrollTo(0, {offset})")
            await page.wait_for_timeout(1000)
            path = f"screenshot_{i}.png"
            await page.screenshot(path=path)
            screenshots.append(path)

        await browser.close()

        stitched = Image.new("RGB", (1920, view_height * len(screenshots)))
        for i, file in enumerate(screenshots):
            img = Image.open(file)
            stitched.paste(img, (0, i * view_height))
        stitched.save("stitched_full_page.png")
        print("✅ Stitched screenshot saved as: stitched_full_page.png")

        for file in screenshots:
            os.remove(file)


async def try_click_apply_button(page):
    print("🔍 Looking for an Apply button using robust candidate scoring (standard logic)...")
    pattern = re.compile(r"(apply|submit resume|start application)", re.IGNORECASE)
    candidate, score = await get_best_apply_candidate(page, pattern)

    if not candidate or score<1:
        print("❌ No candidate found for Apply button (standard logic).")
        return False

    try:
        text = await candidate.inner_text()  # ✅ Awaiting text retrieval
        print(f"🔍 Best candidate found with score {score} and text: '{text.strip()}'")
    except Exception:
        pass

    try:
        await candidate.scroll_into_view_if_needed(timeout=3000)  # ✅ Awaiting the scroll action
        await asyncio.sleep(1)

        if await candidate.is_visible():  # ✅ Awaiting visibility check
            await candidate.click()  # ✅ Awaiting click action
            print("✅ Clicked the Apply button (visible)")

        elif await candidate.is_enabled():  # ✅ Awaiting enabled check
            handle = await candidate.element_handle()  # ✅ Awaiting handle retrieval
            if handle:
                await page.evaluate("(el) => el.click()", handle)
                print("✅ Clicked the Apply button (JS click on enabled element)")
            else:
                print("❌ Could not obtain element handle for candidate")
                return False
        else:
            print("❌ Candidate found but not interactable")
            return False

        await asyncio.sleep(5)
        await page.screenshot(path="after_apply.png")
        return True

    except Exception as e:
        print(f"❌ Could not click the Apply button (standard logic): {e}")
        return False


async def is_embedded_form_present(page) -> bool:
    print("🔍 Checking for embedded application form using scoring system...")

    # Layer 1: Traditional <form> tag with enough inputs
    form_input_count = await page.locator("form input, form textarea, form select").count()
    if form_input_count >= 3:
        print(f"✅ Found <form> tag with {form_input_count} fields. Passing immediately.")
        return True

    # Layer 2: Scoring non-semantic inputs
    inputs = page.locator("input, textarea, select")
    total_fields = await inputs.count()
    score = 0

    for i in range(total_fields):
        el = inputs.nth(i)

        try:
            # Get useful metadata
            placeholder = (await el.get_attribute("placeholder") or "").lower()
            aria_label = (await el.get_attribute("aria-label") or "").lower()
            name_attr = (await el.get_attribute("name") or "").lower()
            field_type = (await el.get_attribute("type") or "").lower()
            associated_text = f"{placeholder} {aria_label} {name_attr}"

            # Scoring rules
            if "email" in associated_text:
                score += 3
            if "phone" in associated_text:
                score += 3
            if "resume" in associated_text or "cv" in associated_text:
                score += 10
            if "upload" in associated_text or "file" in associated_text:
                score += 5
            if "linkedin" in associated_text or "github" in associated_text:
                score += 3
            if "cover" in associated_text:
                score += 5
            if field_type == "file":
                score += 10

        except Exception:
            continue

    # Bonus for sufficient number of fields
    if total_fields >= 4:
        score += 5

    print(f"🧮 Application form field score: {score}")

    if score >= 15:
        print("✅ High enough score to confirm an embedded application form.")
        return True

    # Layer 3: Iframe check for known ATS platforms
    for frame in page.frames:
        frame_url = frame.url.lower()
        if any(host in frame_url for host in ["greenhouse.io", "lever.co", "workday.com"]):
            frame_inputs = await frame.locator("input, textarea, select").count()
            if frame_inputs > 2:
                print(f"✅ Detected embedded application form in iframe ({frame_url}) with {frame_inputs} fields.")
                return True

    print("❌ No application form detected.")
    return False


async def lazy_scroll_and_find_apply_button(page):
    print("🔍 Trying lazy-loading approach for Apply button using robust candidate scoring...")
    pattern = re.compile(r"(apply|submit resume|start application)", re.IGNORECASE)
    previous_height = 0
    max_scroll_attempts = 10
    candidate = None

    for attempt in range(max_scroll_attempts):
        candidate, score = await get_best_apply_candidate(page, pattern)

        if candidate:
            try:
                text = await candidate.inner_text()  # ✅ Awaiting text retrieval
            except Exception:
                text = ""

            print(f"🔍 (Lazy) Candidate found on scroll attempt {attempt + 1} with score {score} and text: '{text}'")
            if score > 0:
                break

        # Scroll down to load more content
        await page.evaluate("window.scrollBy(0, window.innerHeight)")
        await page.wait_for_timeout(2000)
        new_height = await page.evaluate("document.body.scrollHeight")

        if new_height == previous_height:
            print("Reached the bottom of the page.")
            break

        previous_height = new_height

    if not candidate:
        print("❌ No Apply button found via lazy-loading approach.")
        return False

    try:
        try:
            await candidate.scroll_into_view_if_needed(timeout=3000)
        except Exception as se:
            print(f"⚠️ scroll_into_view_if_needed failed (lazy-loading): {se}")

        await page.wait_for_timeout(1000)

        if await candidate.is_visible():
            await candidate.click()
            print("✅ Clicked the Apply button (lazy-loading approach)")
        elif await candidate.is_enabled():
            handle = await candidate.element_handle()  # ✅ Awaiting the handle retrieval
            if handle:
                await page.evaluate("(el) => el.click()", handle)
                print("✅ Clicked the Apply button (JS click in lazy-loading approach)")
            else:
                print("❌ Could not obtain element handle for candidate in lazy-loading approach")
                return False
        else:
            print("❌ Candidate found in lazy-loading approach but not interactable")
            return False

        await page.wait_for_timeout(5000)
        await page.screenshot(path="after_apply_lazy.png")
        return True

    except Exception as e:
        print(f"❌ Could not click the Apply button (lazy-loading approach): {e}")
        return False


async def compute_candidate_score(candidate, page) -> int:
    score = 0
    try:
        text = await candidate.inner_text()
        text = text.strip().lower()
    except Exception:
        text = ""

    print(f"🧐 Scoring candidate: '{text}'")

    if "apply" in text:
        score += 10
    if text in ["apply", "apply now"]:
        score += 5
    if "submit resume" in text or "start application" in text:
        score += 8

    # Negative keywords
    if "learn more" in text or "how to" in text or "details" in text:
        score -= 30
    if "save" in text or "bookmark" in text:
        score -= 20
    if "saving" in text:
        score -=20

    # Tag bonuses
    try:
        tag = await candidate.evaluate("el => el.tagName")
        if tag:
            tag = tag.lower()
            if tag == "button":
                score += 5
            elif tag == "a":
                score += 3
            elif tag == "div":
                score += 1
    except Exception:
        pass

    # Bounding box size check
    try:
        box = await candidate.bounding_box()
        if box:
            if box["width"] < 50 or box["height"] < 20:
                print(f"⚠️ Small button detected: {box}")
                score -= 10
            else:
                score += 2
    except Exception:
        pass

    print(f"🔢 Final score: {score}")
    return score


async def get_best_apply_candidate(page, pattern) -> (object, int):
    """
    Returns the candidate element with the highest score and its score.
    """
    candidates = page.locator("button, a, div[role='button']", has_text=pattern)
    count = await candidates.count()
    best_candidate = None
    best_score = -9999

    for i in range(count):
        candidate = candidates.nth(i)

        try:
            text = await candidate.inner_text()  # ✅ You need to await this call
        except Exception:
            text = ""

        score = await compute_candidate_score(candidate,page)  # ✅ Awaiting the compute function as well

        print(f"Candidate {i}: text='{text}', score={score}")

        if score > best_score:
            best_score = score
            best_candidate = candidate

    return best_candidate, best_score


if __name__ == "__main__":
    link = "https://jobs.gem.com/the-boring-company/0571f593-dfe2-4eca-aa92-70ba5c12abb7"
    asyncio.run(open_page_and_capture(link))
