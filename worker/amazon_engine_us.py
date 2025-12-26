import re
from typing import Dict, List

from playwright.async_api import async_playwright

# US hiring site
SEARCH_URL = "https://hiring.amazon.com/app#/jobSearch"


async def _get_all_text(page) -> str:
    """Return combined innerText from all frames."""
    chunks = []
    for frame in page.frames:
        try:
            text = await frame.evaluate(
                "() => document.body ? document.body.innerText : ''"
            )
            if text:
                chunks.append(text)
        except Exception:
            continue
    return "\n".join(chunks)


def _parse_jobs_from_text(text: str) -> List[Dict]:
    """
    Parse page text into a list of job dicts:
    {title, type, duration, pay, location, url}
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    jobs: List[Dict] = []

    joined = "\n".join(lines)

    for i, line in enumerate(lines):
        if "Type:" not in line:
            continue

        title = lines[i - 1] if i > 0 else "Unknown role"

        job_type = ""
        duration = ""
        pay = ""
        location = ""

        parts = line.split("Type:", 1)
        if len(parts) > 1:
            job_type = parts[1].strip()

        for k in range(i + 1, min(i + 8, len(lines))):
            l = lines[k]

            if "Duration:" in l:
                duration = l.split("Duration:", 1)[1].strip()
                continue
            if "Pay rate:" in l:
                pay = l.split("Pay rate:", 1)[1].strip()
                continue

            if not location and ("," in l or "United States" in l or "USA" in l):
                location = l.strip()

        jobs.append(
            {
                "title": title,
                "type": job_type,
                "duration": duration,
                "pay": pay,
                "location": location,
                "url": None,
            }
        )

    unique: Dict[tuple, Dict] = {}
    for j in jobs:
        key = (j["title"], j["location"])
        if key not in unique:
            unique[key] = j

    return list(unique.values())


async def _find_job_url(page, title: str) -> str | None:
    """Try to find a clickable link for the job title in the DOM."""
    try:
        locator = page.locator(f"text={title}")
        count = await locator.count()
        if count == 0:
            return None

        first = locator.nth(0)
        handle = await first.element_handle()
        if not handle:
            return None

        href = await handle.evaluate(
            "node => (node.closest('a') && node.closest('a').href) || ''"
        )
        href = (href or "").strip()
        if href:
            return href
    except Exception:
        pass

    return None


async def fetch_jobs(headless: bool = False) -> List[Dict]:
    """
    High-level engine function for the US site:
    - Opens the Amazon hiring page with Playwright
    - Handles cookies / sticky alerts / modals
    - Extracts visible text
    - Parses jobs into structured dicts
    - Returns: list of jobs
    """
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(
                permissions=[],
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
                ),
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )
            page = await context.new_page()

            print("[engine_us] Loading page...")
            response = await page.goto(SEARCH_URL, wait_until="domcontentloaded")
            try:
                status = response.status if response else "no-response"
            except Exception:
                status = "unknown"
            print(f"[engine_us] Page status: {status}")

            try:
                await page.wait_for_timeout(3000)
                for frame in page.frames:
                    buttons = await frame.query_selector_all("button")
                    for btn in buttons:
                        try:
                            text = (await btn.inner_text()).strip().lower()
                            if any(
                                k in text
                                for k in [
                                    "continue",
                                    "reject",
                                    "accept",
                                    "save preferences",
                                    "accept all",
                                ]
                            ):
                                await btn.click()
                                print(f"[engine_us] Clicked cookie banner button: {text}")
                                break
                        except Exception:
                            continue
            except Exception as e:
                print(f"[engine_us] Cookie banner handling error: {e}")

            # Wait a bit longer for dynamic content to render
            try:
                await page.wait_for_timeout(5000)
                await page.wait_for_selector("text=job", timeout=5000)
            except Exception:
                pass

            try:
                await page.wait_for_timeout(1000)
                sticky_btns = await page.query_selector_all("button")
                for btn in sticky_btns:
                    try:
                        text = (await btn.inner_text()).strip().lower()
                        if "close sticky alerts" in text:
                            await btn.click(force=True)
                            print("[engine_us] Closed sticky alerts popup.")
                            break
                    except Exception:
                        continue
            except Exception as e:
                print(f"[engine_us] Sticky alert handling error: {e}")

            try:
                await page.wait_for_timeout(2000)
                await page.evaluate(
                    """
                    const modals = document.querySelectorAll(
                        'div[style*="position: fixed"], div[class*="modal"], div[role="dialog"]'
                    );
                    modals.forEach(m => m.remove());
                    """
                )
                print("[engine_us] Removed job alert / step modal via JavaScript.")
            except Exception as e:
                print(f"[engine_us] Failed to remove job alert modal: {e}")

            try:
                await page.wait_for_timeout(4000)
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1500)
            except Exception as e:
                print(f"[engine_us] Error during scroll/render: {e}")

            try:
                full_text = await _get_all_text(page)
            except Exception as e:
                print(f"[engine_us] Error getting page text: {e}")
                full_text = ""

            try:
                title = await page.title()
            except Exception:
                title = "unknown"
            print(f"[engine_us] Page title: {title}")
            print(f"[engine_us] Page text length: {len(full_text)}")
            print("[engine_us] Page text sample (first 800 chars):")
            print(full_text[:800])

            jobs = _parse_jobs_from_text(full_text)
            print(f"[engine_us] Parsed {len(jobs)} job(s) from text.")

            for job in jobs:
                try:
                    url = await _find_job_url(page, job["title"])
                except Exception as e:
                    print(f"[engine_us] Error finding URL for {job['title']}: {e}")
                    url = None
                job["url"] = url or SEARCH_URL

            await browser.close()
            return jobs

    except Exception as e:
        print(f"[engine_us] Fatal error in fetch_jobs (returning 0 jobs): {e}")
        return []
