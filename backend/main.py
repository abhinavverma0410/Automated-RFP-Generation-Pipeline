import asyncio
import sys
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import uvicorn

from datetime import datetime, timezone, timedelta
from apscheduler.triggers.interval import IntervalTrigger

from core.database import engine, Base, get_database, SessionLocal
from core.gemini import generate_proposal_draft
from core.models import Tender, Proposal
from core.scheduler import create_scheduler, run_scraper_now

# Windows requires ProactorEventLoop for subprocess support
# Playwright launches Chromium as a subprocess — needs this on Windows
# This must be set before any async code runs
if sys.platform == "win32":
    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# LIFESPAN — Startup and Shutdown Logic
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    What is lifespan?
    -----------------
    In FastAPI, lifespan replaces the old @app.on_event("startup") pattern.
    Code BEFORE yield runs on startup.
    Code AFTER yield runs on shutdown.

    What is @asynccontextmanager?
    -----------------------------
    A decorator that turns an async generator function into a context manager.
    The yield splits it into two phases — before (startup) and after (shutdown).
    FastAPI calls this automatically when the server starts and stops.
    """

    # ── STARTUP ──────────────────────────────────────────────────────────────
    logger.info("Application starting up...")

    # Create all database tables defined in models.py
    # checkfirst=True means: only create table if it doesn't already exist
    # This is safe to run on every startup — won't wipe existing data
    Base.metadata.create_all(bind=engine, checkfirst=True)
    logger.info("Database tables created or verified")

    # Create the APScheduler instance
    scheduler = create_scheduler()

    # Add auto-delete job — runs every 24 hours
    scheduler.add_job(
        auto_delete_rejected_proposals,
        trigger=IntervalTrigger(hours=24),
        hours=24,
        id="auto_delete_job",
        name="Auto Delete Rejected Proposals",
        replace_existing=True
    )
    
    # Start the scheduler — begins listening for jobs
    # It runs in the background inside the same asyncio event loop as FastAPI
    scheduler.start()
    logger.info("Scheduler started — scraper will run every 30 minutes")
    logger.info("Application startup complete")
    logger.info("API running at:  http://localhost:8000")
    logger.info("API health:      http://localhost:8000/health")
    logger.info("API docs at:     http://localhost:8000/docs")
    logger.info("Tenders at:      http://localhost:8000/tenders")

    # Run the scraper immediately on startup
    # So the database is populated right away instead of waiting 30 minutes
    # asyncio.create_task() runs it in the background without blocking startup
    asyncio.create_task(run_scraper_now())
    logger.info("Initial scraper run triggered in background")

    # yield hands control back to FastAPI
    # Everything after yield runs on shutdown
    yield

    # ── SHUTDOWN ─────────────────────────────────────────────────────────────
    logger.info("Application shutting down...")

    # Gracefully stop the scheduler
    # wait=False means don't wait for running jobs to finish
    scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped")


# ─────────────────────────────────────────────────────────────────────────────
# FASTAPI APP INSTANCE
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Automated RFP Generation Pipeline",
    description="Monitors Canadian government tenders and generates AI proposals",
    version="1.0.0",
    lifespan=lifespan  # Register the lifespan handler
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React dev server URL
    allow_credentials=True,
    allow_methods=["*"],     # Allow GET, POST, PUT, DELETE etc.
    allow_headers=["*"],     # Allow all headers
)

# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    """
    Health check endpoint — used by Docker to verify the backend is running.
    Returns immediately with no DB calls — purely checks if FastAPI is alive.
    """
    return {"status": "healthy"}


@app.get("/")
def root():
    """Root endpoint — confirms the API is reachable."""
    return {"message": "RFP Generation Pipeline is running"}


@app.get("/tenders")
def get_tenders(db: Session = Depends(get_database)):
    """
    Returns all tenders currently stored in the database.

    What is Depends(get_db)?
    ------------------------
    FastAPI's dependency injection system.
    Instead of manually opening a DB session in every endpoint,
    we declare it as a dependency. FastAPI automatically:
    1. Calls get_db() to open a session
    2. Passes it to this function as 'db'
    3. Closes it when the request is done

    This ensures sessions are always properly closed — even on errors.
    """
    # db.query(Tender) = SELECT * FROM tenders
    # .all() = fetch all rows as a list of Tender objects
    tenders = db.query(Tender).all()

    # Return as a list of dictionaries
    # FastAPI automatically converts this to JSON
    return [
        {
            "reference_number": t.reference_number,
            "title": t.title,
            "organization": t.organization,
            "closing_date": t.closing_date,
            "source_link": t.source_link,
            "is_amended": t.is_amended,
            "proposal_drafted": t.proposal_drafted,
            "created_at": t.created_at,
        }
        for t in tenders
        # This is a list comprehension — builds a list by looping over tenders
        # For each Tender object t, it creates a dictionary
    ]


@app.post("/scrape")
async def trigger_scrape():
    """
    Manually triggers a scraper run immediately.

    Why POST and not GET?
    ---------------------
    GET requests should be read-only — they return data without side effects.
    POST requests perform actions that change state.
    Triggering a scrape changes the database — so POST is correct here.

    asyncio.create_task() runs the scraper in the background
    so this endpoint returns immediately without waiting for scrape to finish.
    """
    await run_scraper_now()
    return {"message": "Scraper triggered — running in background"}


@app.get("/tenders/{reference_number}")
def get_tender(reference_number: str, db: Session = Depends(get_database)):
    """
    Returns a single tender by its reference number.

    What is {reference_number} in the path?
    ----------------------------------------
    A path parameter — FastAPI extracts it from the URL automatically.
    e.g., GET /tenders/nsnspw2026-053
    FastAPI passes "nsnspw2026-053" as the reference_number argument.
    """
    tender = db.query(Tender).filter(
        Tender.reference_number == reference_number
    ).first()
    # .filter() = WHERE reference_number = 'nsnspw2026-053'
    # .first()  = return first match or None

    if not tender:
        # Import HTTPException to return proper HTTP error responses
        from fastapi import HTTPException
        raise HTTPException(
            status_code=404,
            detail=f"Tender {reference_number} not found"
        )
        # 404 = Not Found — standard HTTP status code for missing resources

    return {
        "reference_number": tender.reference_number,
        "title": tender.title,
        "organization": tender.organization,
        "closing_date": tender.closing_date,
        "description": tender.description,
        "source_link": tender.source_link,
        "is_amended": tender.is_amended,
        "proposal_drafted": tender.proposal_drafted,
        "created_at": tender.created_at,
    }

@app.post("/tenders/{reference_number}/generate")
async def generate_proposal(reference_number: str, db: Session = Depends(get_database)):
    """
    Generates an AI proposal draft for a specific tender.

    What happens here step by step:
    --------------------------------
    1. Fetch the tender from the database by reference number
    2. Check if a proposal already exists — don't regenerate unnecessarily
    3. Build a tender dictionary and send it to Gemini
    4. Save the returned draft to the Proposal table
    5. Mark the tender as proposal_drafted = True
    6. Return the draft to the frontend

    Why POST?
    ---------
    This endpoint creates a new Proposal record in the database.
    Any endpoint that creates or modifies data should be POST, not GET.
    """

    # Step 1 — Fetch the tender
    tender = db.query(Tender).filter(
        Tender.reference_number == reference_number
    ).first()

    if not tender:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=404,
            detail=f"Tender {reference_number} not found"
        )

    # Step 2 — Check if proposal already exists
    existing_proposal = db.query(Proposal).filter(
        Proposal.reference_number == reference_number
    ).first()

    if existing_proposal:
        # Return the existing draft instead of generating a new one
        # This prevents wasting Gemini API credits on duplicate generation
        logger.info(f"Returning existing proposal for {reference_number}")
        return {
            "reference_number": reference_number,
            "draft_content": existing_proposal.draft_content,
            "already_existed": True,
            # already_existed flag tells the frontend this wasn't freshly generated
        }

    # Step 3 — Build tender dict and send to Gemini
    # We convert the SQLAlchemy model to a plain dictionary
    # because build_proposal_prompt() expects a dict
    tender_dict = {
        "reference_number": tender.reference_number,
        "title": tender.title,
        "organization": tender.organization,
        "closing_date": tender.closing_date,
        "description": tender.description,
        "source_link": tender.source_link,
    }

    try:
        logger.info(f"Generating proposal for tender: {reference_number}")
        draft_content = await generate_proposal_draft(tender_dict)
        # generate_proposal_draft() is async so we await it
        # It can take several seconds — FastAPI handles other requests meanwhile

    except Exception as e:
        from fastapi import HTTPException
        logger.error(f"Proposal generation failed for {reference_number}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Proposal generation failed: {str(e)}"
            # 500 = Internal Server Error — something went wrong on our side
        )

    # Step 4 — Save the draft to the Proposal table
    new_proposal = Proposal(
        reference_number=reference_number,
        draft_content=draft_content,
        # created_at is set automatically by func.now() in models.py
    )
    db.add(new_proposal)
    # db.add() stages the new record — not saved yet

    # Step 5 — Mark tender as drafted
    tender.proposal_drafted = True
    # SQLAlchemy tracks changes to existing objects automatically
    # No need to call db.add() for updates — just modify the attribute

    # Save both changes in one transaction
    db.commit()
    # If anything fails before this line, neither change is saved
    # This guarantees the Proposal and the Tender flag are always in sync

    logger.info(f"Proposal saved for tender: {reference_number}")

    # Step 6 — Return the draft
    return {
        "reference_number": reference_number,
        "draft_content": draft_content,
        "already_existed": False,
    }


@app.get("/proposals")
def get_proposals(db: Session = Depends(get_database)):
    """
    Returns all generated proposals from the database.

    Used by the frontend to display the list of drafted proposals.
    Each proposal links back to its tender via reference_number.
    """
    proposals = db.query(Proposal).all()

    return [
        {
            "reference_number": p.reference_number,
            "draft_content": p.draft_content,
            "created_at": p.created_at,
        }
        for p in proposals
    ]


@app.get("/proposals/{reference_number}")
def get_proposal(reference_number: str, db: Session = Depends(get_database)):
    """
    Returns a single proposal by reference number.

    Used by the frontend when user clicks to view a specific draft.
    """
    proposal = db.query(Proposal).filter(
        Proposal.reference_number == reference_number
    ).first()

    if not proposal:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=404,
            detail=f"Proposal for tender {reference_number} not found"
        )

    return {
        "reference_number": proposal.reference_number,
        "draft_content": proposal.draft_content,
        "created_at": proposal.created_at,
    }


# ── Update/save edited proposal ───────────────────────────────────────────────
@app.put("/proposals/{reference_number}")
async def update_proposal(
    reference_number: str,
    request: dict,
    db: Session = Depends(get_database)
):
    """
    Saves the user's edited version of the proposal.
    Called every time user saves in the editor.
    """
    proposal = db.query(Proposal).filter(
        Proposal.reference_number == reference_number
    ).first()

    if not proposal:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Proposal not found")

    # Save edited content
    proposal.edited_content = request.get("edited_content")
    proposal.status = "edited"
    db.commit()

    return {"message": "Proposal saved successfully"}


# ── Submit proposal to admin ──────────────────────────────────────────────────
@app.post("/proposals/{reference_number}/submit")
async def submit_proposal(
    reference_number: str,
    request: dict,
    db: Session = Depends(get_database)
):
    """
    Marks proposal as submitted — sends it to admin review queue.
    """
    proposal = db.query(Proposal).filter(
        Proposal.reference_number == reference_number
    ).first()

    if not proposal:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Proposal not found")

    proposal.status = "submitted"
    proposal.submitted_by = request.get("user_id")
    proposal.submitted_at = datetime.now(timezone.utc)
    db.commit()

    return {"message": "Proposal submitted for review"}


# ── Admin — get all submitted proposals ──────────────────────────────────────
@app.get("/admin/proposals")
def get_submitted_proposals(db: Session = Depends(get_database)):
    """
    Returns all proposals with status submitted, approved or rejected.
    Admin only endpoint.
    """
    proposals = db.query(Proposal).filter(
        Proposal.status.in_(["submitted", "approved", "rejected"])
    ).all()

    return [
        {
            "reference_number": p.reference_number,
            "draft_content": p.draft_content,
            "edited_content": p.edited_content,
            "status": p.status,
            "submitted_by": p.submitted_by,
            "submitted_at": p.submitted_at,
            "created_at": p.created_at,
        }
        for p in proposals
    ]


# ── Admin — approve or reject proposal ───────────────────────────────────────
@app.put("/admin/proposals/{reference_number}/status")
async def update_proposal_status(
    reference_number: str,
    request: dict,
    db: Session = Depends(get_database)
):
    proposal = db.query(Proposal).filter(
        Proposal.reference_number == reference_number
    ).first()

    if not proposal:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Proposal not found")

    new_status = request.get("status")
    proposal.status = new_status

    # Record rejection timestamp for 30-day auto-delete countdown
    if new_status == "rejected":
        proposal.rejected_at = datetime.now(timezone.utc)
    else:
        # Clear rejected_at if restored back to submitted
        proposal.rejected_at = None

    db.commit()
    return {"message": f"Proposal {proposal.status}"}

# ── Recycle bin — fetch all rejected proposals ────────────────────────────────
@app.get("/admin/recycle-bin")
def get_recycle_bin(db: Session = Depends(get_database)):
    """
    Returns all rejected proposals with days remaining before auto-delete.
    """
    proposals = db.query(Proposal).filter(
        Proposal.status == "rejected"
    ).all()

    result = []
    for p in proposals:
        # Calculate days remaining before auto-deletion
        if p.rejected_at:
            rejected_at = p.rejected_at.replace(tzinfo=timezone.utc)
            days_elapsed = (datetime.now(timezone.utc) - rejected_at).days
            days_remaining = max(0, 30 - days_elapsed)
        else:
            days_remaining = 30

        result.append({
            "reference_number": p.reference_number,
            "draft_content": p.draft_content,
            "edited_content": p.edited_content,
            "status": p.status,
            "submitted_by": p.submitted_by,
            "submitted_at": p.submitted_at,
            "rejected_at": p.rejected_at,
            "days_remaining": days_remaining,
            # days_remaining shown in UI as countdown
        })

    return result


# ── Permanent delete ──────────────────────────────────────────────────────────
@app.delete("/admin/proposals/{reference_number}")
def delete_proposal(
    reference_number: str,
    db: Session = Depends(get_database)
):
    """
    Permanently deletes a proposal from the recycle bin.
    Also resets proposal_drafted flag on the tender.
    """
    proposal = db.query(Proposal).filter(
        Proposal.reference_number == reference_number
    ).first()

    if not proposal:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Proposal not found")

    # Reset tender's proposal_drafted flag so it can be regenerated
    tender = db.query(Tender).filter(
        Tender.reference_number == reference_number
    ).first()
    if tender:
        tender.proposal_drafted = False

    db.delete(proposal)
    db.commit()
    return {"message": "Proposal permanently deleted"}


# ── Restore proposal back to submitted ───────────────────────────────────────
@app.put("/admin/proposals/{reference_number}/restore")
def restore_proposal(
    reference_number: str,
    db: Session = Depends(get_database)
):
    """
    Restores a rejected proposal back to submitted status.
    Removes it from recycle bin.
    """
    proposal = db.query(Proposal).filter(
        Proposal.reference_number == reference_number
    ).first()

    if not proposal:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Proposal not found")

    proposal.status = "submitted"
    proposal.rejected_at = None
    db.commit()
    return {"message": "Proposal restored"}

@app.delete("/proposals/{reference_number}")
def delete_user_proposal(reference_number: str, db: Session = Depends(get_database)):
    # Use db.query().filter().first() to match the rest of your codebase's style
    proposal = db.query(Proposal).filter(
        Proposal.reference_number == reference_number
    ).first()
    
    if not proposal:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    # Optional: Reset the tender's proposal_drafted flag so you can generate it again later
    tender = db.query(Tender).filter(
        Tender.reference_number == reference_number
    ).first()
    if tender:
        tender.proposal_drafted = False

    db.delete(proposal)
    db.commit()
    return {"message": "Proposal deleted successfully"}

# ── Auto-delete job — runs daily ──────────────────────────────────────────────
async def auto_delete_rejected_proposals():
    """
    Runs every 24 hours.
    Permanently deletes proposals rejected more than 30 days ago.
    """
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        # Find all proposals rejected more than 30 days ago
        old_rejected = db.query(Proposal).filter(
            Proposal.status == "rejected",
            Proposal.rejected_at < cutoff
        ).all()

        for proposal in old_rejected:
            # Reset tender flag
            tender = db.query(Tender).filter(
                Tender.reference_number == proposal.reference_number
            ).first()
            if tender:
                tender.proposal_drafted = False

            db.delete(proposal)
            logger.info(f"Auto-deleted rejected proposal: {proposal.reference_number}")

        db.commit()
        logger.info(f"Auto-delete job complete — removed {len(old_rejected)} proposals")

    finally:
        db.close()

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)