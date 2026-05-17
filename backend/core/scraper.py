import asyncio
# asyncio is Python's built-in library for asynchronous programming
# It manages the "event loop" — the engine that runs async/await code

import random
# Used to add random delays between retries
# Why random? Because fixed delays are easier for bot-detection systems to identify

import re
# Regular expressions — a powerful pattern matching tool
# We use it to extract dates from raw text like "2026/05/07" or "April 1, 2026"

from typing import Optional
# Type hints — tell Python (and you) what type a variable should be
# Optional[str] means "either a string or None"d

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
# async_playwright — the async version of Playwright we use with await
# TimeoutError — raised when a page takes too long to load
# We rename it PlaywrightTimeoutError to avoid confusion with Python's built-in TimeoutError

from playwright_stealth import Stealth
# playwright_stealth is a third-party library that hides the fact that
# we are using an automated browser. Websites use JavaScript fingerprinting
# to detect bots — stealth patches those detection points.
# Without this, CanadaBuys may return a CAPTCHA or block us entirely.

from core.models import Tender
# Import our SQLAlchemy Tender model
# We instantiate it directly in the scraper instead of using plain dictionaries
# This means the scraper returns ready-to-save DB objects

from core.database import SessionLocal
# SessionLocal is our DB session factory
# We use it in run_scraper() to open a database connection

import logging
# Python's built-in logging — same as we set up in the previous version

# Create a logger for this file
# __name__ = "core.scraper" — appears in every log line from this file
logger = logging.getLogger(__name__)

# The URL we are scraping
# status[0]=1920 = Active tenders
# status[1]=87   = Amended tenders
TARGET_URL = (
    "https://canadabuys.canada.ca/en/tender-opportunities"
    "?status%5B0%5D=1920&status%5B1%5D=87"
)

# headless=True  = browser runs invisibly in the background
# headless=False = browser window opens visibly (useful for debugging)
HEADLESS = True

# Column index constants — confirmed from CanadaBuys HTML structure
# Using named constants instead of magic numbers like cells[4]
# makes the code self-documenting and easy to update if columns change
COL_TITLE        = 0   # Tender title + hyperlink
COL_CATEGORY     = 1   # Procurement category (skipped)
COL_OPEN_AMENDED = 2   # Publication date + amendment signal
COL_CLOSING      = 3   # Closing/deadline date
COL_ORGANIZATION = 4   # Issuing government department


# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# _ prefix on function names — Python convention meaning
# "this is a private helper, not meant to be called from outside this file"
# ─────────────────────────────────────────────────────────────────────────────

def _extract_date_from_text(text: str) -> Optional[str]:
    """
    Extracts a date string from raw text using regex pattern matching.

    Why do we need this?
    --------------------
    CanadaBuys sometimes returns dates embedded in messy text like:
    "Published: 2026/05/07" or "Apr 1, 2026 (Amended)"
    We can't just store the whole string — we need the date part only.

    What is regex?
    --------------
    Regular expressions (regex) are patterns that match text.
    re.search(pattern, text) scans the text and returns the first match.
    If no match is found, it returns None.

    Return type Optional[str] means this function returns
    either a string or None — always handle both cases in the caller.
    """
    if not text:
        # Return None immediately if text is empty
        return None

    patterns = [
        r"\d{4}[/\-]\d{2}[/\-]\d{2}",         # Matches: 2026/04/01 or 2026-04-01
        r"\d{2}[/\-]\d{2}[/\-]\d{4}",          # Matches: 01/04/2026
        r"[A-Za-z]{3,9}\s+\d{1,2},?\s*\d{4}",  # Matches: April 1, 2026 or Apr 1 2026
    ]
    # \d     = any digit (0-9)
    # {4}    = exactly 4 of the previous character
    # [/\-]  = either / or -
    # \s+    = one or more whitespace characters
    # ,?     = optional comma

    for pattern in patterns:
        matched = re.search(pattern, text)
        if matched:
            # matched.group(0) returns the full matched string
            return matched.group(0).strip()

    # No date pattern matched — return None
    return None


async def _get_cell_text(row, col_index: int) -> str:
    """
    Safely returns the text of the nth <td> cell in a row.

    Why a helper function?
    ----------------------
    We call this many times for different columns.
    Wrapping it in a function means if it fails on one cell,
    it returns an empty string instead of crashing the whole scraper.

    What is .locator()?
    -------------------
    Playwright's locator() is a smarter version of query_selector.
    It finds elements lazily — only fetches them when you actually
    call a method like inner_text() or get_attribute().
    .nth(col_index) picks the element at that position (0-based index).
    """
    try:
        return (await row.locator("td").nth(col_index).inner_text()).strip()
    except Exception:
        # If the cell doesn't exist or throws any error
        # return empty string — caller handles missing data
        return ""


async def _dump_row_structure(row) -> None:
    """
    Debug helper — prints every column's index, CSS class and text.
    Only called on the first row to verify column mapping in logs.

    Why is this useful?
    -------------------
    When scraping real websites, the HTML structure can change without
    warning. This function lets you instantly see what each column
    contains by reading the uvicorn logs — no need to open a browser.

    What is row.evaluate()?
    -----------------------
    evaluate() runs JavaScript directly inside the browser page.
    This is faster than making multiple Playwright calls for each cell.
    It returns the result back to Python as a dictionary.
    """
    try:
        debug: list = await row.evaluate("""row => {
            return Array.from(row.querySelectorAll('td')).map((td, i) => ({
                index: i,
                className: td.className,
                text: td.innerText.trim().slice(0, 80)
            }));
        }""")
        # slice(0, 80) limits text to 80 characters so logs stay readable

        print("Row column dump (first row):")
        for col in debug:
            print(f"   [{col['index']}] class='{col['className']}' | '{col['text']}'")

    except Exception as e:
        print(f"Could not dump row structure: {e}")


async def scrape_tender_description(source_link: str) -> str:
    """
    Visits the individual tender detail page to extract full description.

    Why is this separate from scrape_tenders()?
    --------------------------------------------
    Loading every detail page takes significant time.
    We only call this for NEW tenders not already in the database,
    avoiding unnecessary page loads on every 30-minute scraper run.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS)
        page = await browser.new_page()

        try:
            await page.goto(source_link, wait_until="networkidle", timeout=60000)

            # Try multiple CSS selectors to find the description
            # Comma-separated means "try first, if not found try next"
            description_element = await page.query_selector(
                ".tender-description, .field--name-body, main p"
            )

            description = await description_element.inner_text() if description_element else ""
            return description.strip()

        except Exception as e:
            print(f"Failed to scrape description from {source_link}: {e}")
            return ""

        finally:
            # Always close browser even if an error occurred
            await browser.close()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN SCRAPING FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

async def scrape_tenders() -> list[Tender]:
    """
    Main scraping function. Launches a stealth browser, navigates to
    CanadaBuys, extracts all tender rows and returns them as Tender objects.

    What is List[Tender]?
    ---------------------
    The return type annotation. This function promises to return
    a list of Tender SQLAlchemy model instances — not plain dictionaries.
    This makes them ready to save directly to the database.

    What is the retry loop?
    -----------------------
    Government websites are unpredictable — they can be slow, return
    empty pages, or temporarily block scrapers. Instead of failing
    immediately, we retry with increasing delays (exponential backoff).
    """
    attempt = 0
    # base_delay is the starting wait time in seconds between retries
    # Each retry multiplies this: 2s, 4s, 8s, 16s, 32s (capped at 2^5=32)
    base_delay = 2

    # async with async_playwright() starts Playwright and automatically
    # shuts it down when the block exits — even if an error occurs
    async with async_playwright() as p:

        # Launch Chromium browser ONCE outside the retry loop
        # We reuse the same browser across retries — faster than
        # launching a new browser on every attempt
        browser = await p.chromium.launch(
            headless=HEADLESS,
            args=[
                # Tell Chrome not to announce it is being automated
                # Without this, websites detect the browser as a bot
                "--disable-blink-features=AutomationControlled",

                # Required in Docker/Linux environments
                # Docker containers don't have a real display or sandbox
                "--no-sandbox",
                "--disable-dev-shm-usage",

                # Disable cross-origin restrictions and site isolation
                # Some government portals load resources across subdomains
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-site-isolation-trials",

                # Set a realistic browser window size
                # Headless browsers often default to tiny sizes
                # which some sites use to detect automation
                "--window-size=1280,800",
            ],
        )

        # while True creates an infinite loop
        # We break out of it by returning tenders on success
        # or by raising an exception after too many failures
        while True:
            attempt += 1
            context = None

            try:
                print(f"Playwright attempt {attempt}")

                # A browser context is like a fresh incognito window
                # Each retry gets a completely new context —
                # fresh cookies, fresh session, fresh fingerprint
                # This prevents the site from tracking previous failed attempts
                context = await browser.new_context(
                    # Pretend to be a real Windows Chrome browser
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    ),

                    # Realistic viewport size — matches --window-size above
                    viewport={"width": 1280, "height": 800},

                    # Canadian locale and timezone
                    # Some sites serve different content based on location
                    locale="en-CA",
                    timezone_id="America/Toronto",

                    # Desktop device settings
                    device_scale_factor=1,
                    has_touch=False,
                    is_mobile=False,

                    # HTTP headers that real Chrome sends automatically
                    # Missing headers are a common bot detection signal
                    extra_http_headers={
                        "Accept-Language": "en-CA,en;q=0.9",
                        "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124"',
                        "Sec-Ch-Ua-Mobile": "?0",
                        "Sec-Ch-Ua-Platform": '"Windows"',
                    },
                )

                # Open a new tab inside this context
                page = await context.new_page()

                # Apply stealth patches to the page
                # Stealth modifies JavaScript properties that websites
                # check to detect Playwright/Puppeteer automation
                # e.g., navigator.webdriver is normally True in automated
                # browsers — stealth sets it to False
                stealth = Stealth()
                await stealth.apply_stealth_async(page)

                # Navigate to the target URL
                # wait_until="domcontentloaded" is faster than "networkidle"
                # It fires as soon as the HTML is parsed — before all
                # images and scripts finish loading
                # We then separately wait for networkidle below
                response = await page.goto(
                    TARGET_URL, wait_until="domcontentloaded", timeout=60000
                )
                print(f"   Response status: {response.status}")
                # 200 = success, 403 = blocked, 503 = server error

                # Now wait for all network activity to finish
                # This ensures JavaScript has rendered the tender table
                await page.wait_for_load_state("networkidle", timeout=30000)

                # Some government sites show a cookie consent banner
                # that blocks the page until dismissed
                # We try to click Accept — if it's not there, we ignore the error
                try:
                    await page.click("button:has-text('Accept')", timeout=3000)
                except Exception:
                    # timeout=3000 means give up after 3 seconds
                    # Exception is silently ignored — banner may not exist
                    pass

                # Wait for at least one tender row to appear in the table
                # If this times out, the page didn't load correctly
                await page.wait_for_selector(
                    "table.tender-opportunities-table tbody tr, table tbody tr",
                    timeout=30000,
                )

                # Add a small random human-like delay before reading the page
                # Fixed delays are easier for bot detection to identify
                # random.randint(800, 1500) = wait between 0.8 and 1.5 seconds
                await page.wait_for_timeout(random.randint(800, 1500))

                # Get all tender rows from the table
                # .all() returns a list of all matching Locator elements
                rows = await page.locator("table tbody tr").all()
                print(f"Found {len(rows)} rows")

                if not rows:
                    # No rows found — close context and retry
                    await context.close()
                    print("No rows found. Retrying...")

                    # Exponential backoff — each retry waits longer
                    # min(attempt-1, 5) caps the exponent at 5
                    # so max wait is 2 * 2^5 = 64 seconds
                    await asyncio.sleep(base_delay * (2 ** min(attempt - 1, 5)))
                    continue
                    # continue jumps back to the top of the while True loop

                # Debug — print first row structure to logs
                # Helps verify column mapping is still correct
                await _dump_row_structure(rows[0])

                # Initialize empty list to collect Tender objects
                tenders: list[Tender] = []

                # Loop through every row in the table
                for row in rows:
                    try:
                        # ── Title and Link ────────────────────────────────────
                        # The title is inside an <a> tag in the first cell
                        # .locator("td").nth(COL_TITLE) = first <td>
                        # .locator("a").first = first <a> inside that <td>
                        title_node = row.locator("td").nth(COL_TITLE).locator("a").first

                        # get_attribute("href") returns the URL the link points to
                        # e.g., "/en/tender-opportunities/tender-notice/nsnspw2026-053"
                        href = await title_node.get_attribute("href")

                        if not href:
                            # No link means this row is not a real tender
                            # (could be a header row or empty separator row)
                            continue

                        # inner_text() gets the visible text of the element
                        title = (await title_node.inner_text()).strip()

                        # Build absolute URL from relative href
                        # href starts with "/" so we prepend the domain
                        link = (
                            f"https://canadabuys.canada.ca{href}"
                            if href.startswith("/")
                            else href
                            # If href already starts with "http", use it as-is
                        )

                        # ── Reference Number ──────────────────────────────────
                        # Primary method: extract from URL slug
                        # e.g., ".../tender-notice/nsnspw2026-053"
                        # rstrip("/") removes trailing slash if present
                        # split("/")[-1] takes the last segment
                        reference_number = href.rstrip("/").split("/")[-1]

                        # Fallback method: look for a cell with reference class
                        # Some tender types display the reference in its own cell
                        ref_by_class = row.locator(
                            "td[class*='reference'], td[class*='solicitation']"
                        ).first
                        # [class*='reference'] means "class attribute contains 'reference'"
                        # This is a CSS attribute selector with wildcard matching

                        if await ref_by_class.count() > 0:
                            # count() returns how many elements matched
                            # Only use this if the element actually exists
                            ref_text = (await ref_by_class.inner_text()).strip()
                            if ref_text:
                                # Override URL-based reference with cell-based one
                                reference_number = ref_text

                        # ── Open/Amendment Date ───────────────────────────────
                        # This cell serves dual purpose:
                        # 1. Shows the publication/amendment date
                        # 2. Contains "Amended" text if tender was amended
                        open_amended_text = await _get_cell_text(row, COL_OPEN_AMENDED)

                        # Extract just the date part from the raw text
                        # e.g., "Amended 2026/05/07" → "2026/05/07"
                        publication_date = _extract_date_from_text(open_amended_text)

                        # ── Amendment Detection ───────────────────────────────
                        # We use THREE independent signals to detect amendments
                        # Using multiple signals reduces false negatives —
                        # if the site changes one signal, others still catch it

                        # Signal 1: CSS class on the <tr> row element
                        # Some sites add "amended" class to the entire row
                        row_class: str = await row.get_attribute("class") or ""
                        # "or ''" ensures we get empty string if class is None
                        amended_by_class = "amended" in row_class.lower()
                        # .lower() makes comparison case-insensitive

                        # Signal 2: The word "Amended" in the open/amended cell text
                        # re.search() with \b matches whole word only
                        # \b is a word boundary — prevents matching "unamended"
                        amended_by_text = bool(
                            re.search(r"\bamended\b", open_amended_text, re.IGNORECASE)
                        )
                        # bool() converts the match object to True/False
                        # re.IGNORECASE makes it match "Amended", "AMENDED", etc.

                        # Signal 3: Any element with amended-related CSS class
                        # inside the row — like an amendment icon or badge
                        amended_by_icon = (
                            await row.locator(
                                ".amended-icon, [class*='amended']"
                            ).count() > 0
                        )

                        # Final result — True if ANY signal detected amendment
                        is_amended = amended_by_class or amended_by_text or amended_by_icon

                        # ── Closing Date ──────────────────────────────────────
                        closing_raw = await _get_cell_text(row, COL_CLOSING)

                        closing_date: Optional[str] = None

                        if (closing_raw
                                and re.search(r"\d", closing_raw)
                                and "CAD" not in closing_raw):
                            # re.search(r"\d") checks if text contains any digit
                            # "CAD" check filters out price values mistakenly
                            # appearing in the closing date column
                            closing_date = closing_raw
                        else:
                            # Fall back to regex date extraction
                            closing_date = _extract_date_from_text(closing_raw)

                        # ── Organization ──────────────────────────────────────
                        org_raw = await _get_cell_text(row, COL_ORGANIZATION)

                        # Safety fallback — if column 4 is empty,
                        # try reading the very last <td> in the row
                        # This handles cases where the table has extra columns
                        if not org_raw:
                            all_cells = await row.locator("td").all()
                            if len(all_cells) > 0:
                                org_raw = (await all_cells[-1].inner_text()).strip()
                                # all_cells[-1] = last element in the list
                                # Python negative indexing — -1 is always the last item

                        # Define values we consider as "no organization"
                        # Using a set for fast lookup — O(1)
                        _noise = {"", "-", "—", "n/a", "not specified"}

                        organization = (
                            org_raw
                            if org_raw
                            and org_raw.lower() not in _noise
                            and "CAD" not in org_raw
                            # Reject if empty, noise value, or contains currency
                            else "Not specified"
                        )

                        # ── Debug Log ─────────────────────────────────────────
                        # Print key fields for every row so you can verify
                        # extraction is working correctly in uvicorn logs
                        print(
                            f"   ref={reference_number} | "
                            f"org='{organization}' | "
                            f"amended={is_amended} | "
                            f"closes='{closing_date}'"
                        )

                        # ── Build Tender Object ───────────────────────────────
                        # Instantiate the SQLAlchemy Tender model directly
                        # This is different from using a plain dictionary —
                        # these objects can be passed directly to db.add()
                        tenders.append(
                            Tender(
                                reference_number=reference_number,
                                title=title,
                                source_link=link,
                                organization=organization,
                                closing_date=closing_date,
                                is_amended=is_amended,
                                proposal_drafted=False,
                                description=""  # Filled later by detail scraper
                            )
                        )

                    except Exception as row_err:
                        # If one row fails, log it and move to the next
                        # We never let one bad row crash the entire scrape
                        print(f"   Skipping row — {row_err}")
                        continue

                # Close the browser context after processing all rows
                await context.close()

                if tenders:
                    # Success — we got tenders, exit the retry loop
                    print(f"Scraper collected {len(tenders)} tender(s)")
                    return tenders
                else:
                    # Rows existed but none parsed successfully
                    # Retry — something may have changed in the HTML
                    print("No tenders extracted. Retrying...")
            
            except PlaywrightTimeoutError as e:
                # PlaywrightTimeoutError is raised when:
                # - page.goto() takes longer than timeout=60000ms
                # - wait_for_selector() can't find the table in time
                # - wait_for_load_state() never reaches networkidle
                # We catch it separately from generic exceptions because
                # timeouts are common and expected on slow government sites
                print(f"   Timeout on attempt {attempt}: {e}")

            except Exception as e:
                # Catches any other unexpected error —
                # network failures, HTML parsing errors, etc.
                print(f"   Unexpected error on attempt {attempt}: {e}")

            finally:
                # finally block ALWAYS runs — even if an exception occurred
                # This guarantees the browser context is always closed
                # A leaked context wastes memory and can cause future failures
                if context:
                    try:
                        await context.close()
                    except Exception:
                        # context.close() itself might fail if browser crashed
                        # Silently ignore — nothing we can do at this point
                        pass

            # ── Exponential Backoff ───────────────────────────────────────────
            # We only reach here if the attempt failed (no return above)
            # Calculate how long to wait before the next attempt
            # 2^0=1, 2^1=2, 2^2=4, 2^3=8, 2^4=16, 2^5=32 (capped)
            # random.uniform(0, 1) adds a random fraction to avoid
            # multiple scrapers retrying at exactly the same time
            delay = base_delay * (2 ** min(attempt - 1, 5)) + random.uniform(0, 1)
            print(f"   Retrying in {delay:.1f} seconds...")
            # {delay:.1f} formats the float to 1 decimal place e.g. "4.7 seconds"
            await asyncio.sleep(delay)
            # asyncio.sleep() pauses without blocking other async tasks
            # Unlike time.sleep() which freezes the entire program

def sync_tenders_with_db(scraped_tenders: list[Tender], db) -> None:
    """
    Syncs scraped tenders with the database.

    What does this function do?
    ---------------------------
    Compares what we scraped with what's in the database and:
    1. Removes tenders no longer on the website (unless proposal drafted)
    2. Adds brand new tenders to the database
    3. Updates amended status if it changed on existing tenders

    Why sync instead of just inserting?
    ------------------------------------
    Because we run every 30 minutes. We don't want duplicates,
    and we want the database to always reflect the current website state.
    """

    # Build a set of reference numbers from the current scrape
    # Sets are used here because "x in set" is O(1) — instant lookup
    # regardless of how many items are in the set
    scraped_refs = {t.reference_number for t in scraped_tenders}
    # This is a set comprehension — same idea as list comprehension
    # but produces a set (no duplicates, unordered, fast lookup)

    # Fetch all tenders currently in the database
    existing_tenders:list[Tender] = db.query(Tender).all()

    # Build a set of reference numbers already in the database
    existing_refs = {t.reference_number for t in existing_tenders}

    # ── Step 1: Remove stale tenders ─────────────────────────────────────────
    # A tender is stale if it's in our DB but no longer on the website
    for tender in existing_tenders:
        if tender.reference_number not in scraped_refs:
            if not tender.proposal_drafted:
                # Safe to delete — no proposal drafted for this tender
                print(f"Removing stale tender: {tender.reference_number}")
                db.delete(tender)
            else:
                # Keep it — a proposal exists, user may still need it
                print(f"Keeping tender {tender.reference_number} — proposal exists")

    # ── Step 2: Add new tenders ───────────────────────────────────────────────
    for tender in scraped_tenders:
        if tender.reference_number not in existing_refs:
            # Brand new tender — add to database
            # tender is already a Tender model instance from the scraper
            # so we pass it directly to db.add()
            db.add(tender)
            print(f"Added new tender: {tender.reference_number} — {tender.title}")

        else:
            # ── Step 3: Update amended status if changed ──────────────────────
            existing = db.query(Tender).filter(
                Tender.reference_number == tender.reference_number
            ).first()
            # .filter() is SQLAlchemy's WHERE clause
            # .first() returns the first matching row or None

            if existing and existing.is_amended != tender.is_amended:
                existing.is_amended = tender.is_amended
                print(f"Updated amended status for: {tender.reference_number}")

    # Commit all changes to the database in one transaction
    # A transaction means: all changes succeed together or none do
    # If anything fails before commit(), SQLAlchemy rolls back automatically
    db.commit()
    print("Database sync complete")


async def run_scraper() -> None:
    """
    Main entry point called by the scheduler every 30 minutes.

    Orchestrates the full pipeline:
    Step 1 — Scrape tender listings from the website
    Step 2 — Fetch descriptions for new tenders only
    Step 3 — Sync everything with the database

    Why is this separate from scrape_tenders()?
    --------------------------------------------
    scrape_tenders() only handles browser automation.
    run_scraper() handles the full pipeline — DB session management,
    description fetching, and syncing. Keeping them separate makes
    each function focused on one responsibility.
    This is called the Single Responsibility Principle in software design.
    """
    print("=== Scraper run started ===")

    # Step 1 — Scrape the tender listing page
    tenders = await scrape_tenders()

    if not tenders:
        # scrape_tenders() returned empty list — nothing to sync
        print("No tenders scraped — skipping DB sync")
        return
        # return exits the function early — nothing more to do

    # Step 2 — Open a DB session
    # SessionLocal() creates a new session from our session factory
    db = SessionLocal()

    try:
        # Get reference numbers already in the database
        # We only fetch descriptions for NEW tenders to save time
        existing_refs = {t.reference_number for t in db.query(Tender).all()}

        for tender in tenders:
            if tender.reference_number not in existing_refs:
                print(f"Fetching description for: {tender.reference_number}")
                # Import here to avoid circular imports at module level
                tender.description = await scrape_tender_description(tender.source_link)

        # Step 3 — Sync scraped data with the database
        sync_tenders_with_db(tenders, db)

    finally:
        # Always close the DB session when done
        # finally ensures this runs even if an exception occurred above
        db.close()

    print("=== Scraper run complete ===")