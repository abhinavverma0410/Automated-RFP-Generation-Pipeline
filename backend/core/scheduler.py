import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
# AsyncIOScheduler — APScheduler's async-compatible scheduler
# It runs inside Python's asyncio event loop — the same loop
# that FastAPI and Playwright use, so everything works together
# without conflicts or thread-safety issues

from apscheduler.triggers.interval import IntervalTrigger
# IntervalTrigger — fires a job every X minutes/hours/seconds
# Other trigger types exist:
# CronTrigger   — fires at specific times like "every day at 2am"
# DateTrigger   — fires once at a specific datetime

from core.scraper import run_scraper
# run_scraper is the main entry point of our scraping pipeline
# The scheduler calls this every 30 minutes

# Create logger for this file
# __name__ = "core.scheduler"
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# SCRAPER JOB
# ─────────────────────────────────────────────────────────────────────────────

async def scraper_job():
    """
    The actual job function that APScheduler calls every 30 minutes.

    Why wrap run_scraper() in another function?
    -------------------------------------------
    APScheduler needs a plain callable to schedule.
    Wrapping run_scraper() here lets us:
    - Add logging before and after the scrape
    - Catch and handle errors without crashing the scheduler
    - Add future pre/post job logic without touching scraper.py

    What happens if this function raises an exception?
    --------------------------------------------------
    Without the try/except, an unhandled exception would cause
    APScheduler to mark the job as failed and potentially stop
    scheduling future runs. The try/except ensures the scheduler
    always survives, even if one scrape fails.
    """
    logger.info("Scheduler triggered — starting scraper job...")

    try:
        # run_scraper() is async so we await it
        # await means: pause here until scraper is done, then continue
        await run_scraper()
        logger.info("Scraper job completed successfully")

    except Exception as e:
        # If the scraper crashes for any reason, log the error
        # but DO NOT re-raise it — this keeps the scheduler alive
        # The scheduler will simply try again at the next 30-minute interval
        logger.error(f"Scraper job failed: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# SCHEDULER FACTORY
# ─────────────────────────────────────────────────────────────────────────────

def create_scheduler() -> AsyncIOScheduler:
    """
    Creates and configures the APScheduler instance.

    What is APScheduler?
    --------------------
    APScheduler (Advanced Python Scheduler) runs functions at specified
    intervals — similar to a cron job but running inside your Python
    process instead of the operating system.

    Why AsyncIOScheduler specifically?
    -----------------------------------
    Our scraper uses async/await (Playwright, httpx).
    AsyncIOScheduler runs inside Python's asyncio event loop —
    the same loop FastAPI uses. This means:
    - No thread conflicts
    - No need to bridge sync and async code
    - Scheduler and FastAPI share the same event loop cleanly

    Why does this function return the scheduler instead of starting it?
    -------------------------------------------------------------------
    Separation of concerns. Creating and starting are two different steps.
    main.py calls create_scheduler() to get the instance, then calls
    scheduler.start() at the right moment during app startup.
    This gives main.py full control over the lifecycle.

    Returns
    -------
    AsyncIOScheduler
        Configured but NOT yet started scheduler instance.
    """

    # Create the async scheduler instance
    scheduler = AsyncIOScheduler()

    # Add the scraper job to the scheduler
    scheduler.add_job(
        scraper_job,
        # The async function to call — APScheduler handles awaiting it

        trigger=IntervalTrigger(minutes=30),
        # Fire every 30 minutes
        # Other examples:
        # IntervalTrigger(hours=1)    — every hour
        # IntervalTrigger(seconds=60) — every 60 seconds (useful for testing)

        id="scraper_job",
        # Unique string ID for this job
        # Used to reference, pause, or remove the job later
        # e.g., scheduler.pause_job("scraper_job")

        name="CanadaBuys Tender Scraper",
        # Human-readable name — appears in logs and APScheduler's job list

        max_instances=1,
        # Only ONE instance of this job can run at a time
        # If a scrape takes longer than 30 minutes, the next scheduled
        # run is skipped until the current one finishes
        # Without this, you could end up with multiple overlapping scrapes

        replace_existing=True,
        # If a job with the same ID already exists, replace it
        # Prevents duplicate jobs if create_scheduler() is called twice
    )

    logger.info("Scheduler configured — scraper job added (every 30 minutes)")

    # Return the configured scheduler — not started yet
    # main.py calls scheduler.start() during app lifespan startup
    return scheduler


# ─────────────────────────────────────────────────────────────────────────────
# MANUAL TRIGGER
# ─────────────────────────────────────────────────────────────────────────────

async def run_scraper_now():
    """
    Utility function to manually trigger the scraper immediately.

    Why is this useful?
    -------------------
    When the app first starts, we don't want to wait 30 minutes
    for the first scheduled scrape. This function is called in
    main.py on startup so the database is populated right away.

    It is also exposed via the POST /scrape endpoint so you can
    manually trigger a scrape from the frontend or API docs at
    any time — useful for testing and on-demand refreshes.

    Why call scraper_job() instead of run_scraper() directly?
    ---------------------------------------------------------
    scraper_job() already has error handling built in.
    Reusing it here means we don't duplicate the try/except logic.
    """
    logger.info("Manual scraper trigger called")
    await scraper_job()