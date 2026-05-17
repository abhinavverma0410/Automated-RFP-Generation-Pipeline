# Automated RFP Generation Pipeline

A full-stack AI-powered pipeline that monitors Canadian government procurement portals, extracts live tender data, generates structured proposal responses using Google Gemini AI, and provides a complete proposal management workflow with admin review capabilities.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [API Endpoints](#api-endpoints)
- [How the Pipeline Works](#how-the-pipeline-works)
- [Frontend Pages](#frontend-pages)
- [Admin Panel](#admin-panel)
- [Authentication](#authentication)
- [Daily Workflow](#daily-workflow)
- [Docker Reference](#docker-reference)

---

## Overview

This system automatically:

1. Scrapes active and amended tenders from [CanadaBuys](https://canadabuys.canada.ca) every 30 minutes
2. Stores tender data in PostgreSQL (deduplicating by reference number)
3. Removes tenders no longer listed on the website (unless a proposal has been drafted)
4. Lets users generate AI proposal drafts for any tender via Gemini 2.5 Flash
5. Provides a rich text editor for users to edit and submit proposals for admin review
6. Admin panel with approve/reject workflow and 30-day recycle bin for rejected proposals

---

## Features

### Core Pipeline
- Live scraping from CanadaBuys with stealth mode and retry logic
- Auto-deduplication by reference number
- 30-minute scheduled scraping via APScheduler
- Manual scrape trigger via API or frontend button

### AI Generation
- Gemini 2.5 Flash proposal generation
- Structured prompt with 6 sections: Executive Summary, Requirements, Methodology, Experience, Compliance, Pricing
- Duplicate prevention — returns existing draft if already generated

### Proposal Editor
- Rich text editor powered by Tiptap
- Markdown auto-formatting: `#` → H1, `**text**` → Bold, `*text*` → Italic
- Toolbar: Bold, Italic, H1, H2, H3, Lists, Blockquote, Undo, Redo
- Auto-save with draft persistence
- Submit for admin review workflow

### Admin Panel
- Submitted proposals review queue
- Approve / Reject with one click
- Recycle bin for rejected proposals
- Visual 30-day countdown per rejected proposal
- Color-coded urgency: purple (safe) → amber (≤10 days) → red (≤5 days)
- Restore proposals from recycle bin
- Permanent delete
- Auto-deletion of proposals after 30 days rejection

### Authentication
- Clerk authentication with Google, Microsoft, Apple, Email/Password
- Protected routes — all pages require sign in
- Admin panel gated by Clerk User ID
- Theme toggle on sign in/sign up pages

### UI/UX
- Day/Night theme toggle with persistence
- Night Mode: Shadow Monarch Purple (`#9d4edd`)
- Day Mode: Arctic Blue (`#0ea5e9`)
- Toast notifications (no browser alerts)
- Responsive grid layout
- Live indicator in navbar
- Search by title or organization

### Preview
[!Automated RFP Generation Pipeline](frontend/assets/SS1.png)
---

## Tech Stack

### Backend
| Tool | Purpose |
|---|---|
| FastAPI | REST API framework |
| SQLAlchemy 2.x | ORM for PostgreSQL |
| PostgreSQL 18 | Database |
| Playwright | Browser automation for scraping |
| playwright-stealth | Anti-bot detection bypass |
| APScheduler | 30-minute scraper + 24-hour auto-delete jobs |
| Google Gemini 2.5 Flash | AI proposal generation |
| google-genai | Official Gemini SDK |
| Poetry | Python dependency management |
| Docker + docker-compose | Containerization |

### Frontend
| Tool | Purpose |
|---|---|
| React + TypeScript | UI framework |
| Tailwind CSS v4 | Styling |
| Tiptap | Rich text editor |
| Axios | HTTP requests to backend |
| React Router v6 | Client-side routing |
| Clerk v5 | Authentication (Google, Microsoft, Apple, Email) |
| marked + DOMPurify | Markdown rendering in modal |
| Vite | Build tool and dev server |

---

## Project Structure

```
Automated RFP Generation Pipeline/
├── backend/
│   ├── core/
│   │   ├── database.py       # SQLAlchemy engine, session, Base
│   │   ├── models.py         # Tender and Proposal table definitions
│   │   ├── scraper.py        # Playwright scraper + DB sync logic
│   │   ├── scheduler.py      # APScheduler 30-minute scraper job
│   │   └── gemini.py         # Gemini AI prompt builder + generation
│   ├── main.py               # FastAPI app, lifespan, all endpoints
│   ├── .env                  # Environment variables (never commit)
│   ├── .env.example          # Template for environment variables
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── pyproject.toml
│   └── poetry.lock
│
└── frontend/
    ├── src/
    │   ├── api/
    │   │   └── client.ts          # Axios instance pointing to backend
    │   ├── assets/
    │   │   └── screenshots (.png) # UI Screenshots
    │   ├── components/
    │   │   ├── Navbar.tsx         # Top navigation bar with theme toggle
    │   │   ├── TenderCard.tsx     # Single tender card component
    │   │   └── ProposalModal.tsx  # Modal to display AI draft
    │   ├── hooks/
    │   │   └── useTheme.ts        # Custom hook for day/night theme
    │   ├── pages/
    │   │   ├── Dashboard.tsx      # All tenders + search + stats
    │   │   ├── TenderDetail.tsx   # Single tender + generate button
    │   │   ├── Proposals.tsx      # All generated proposals
    │   │   ├── ProposalEditor.tsx # Rich text editor + submit
    │   │   ├── AdminPanel.tsx     # Admin review + recycle bin
    │   │   ├── SignInPage.tsx     # Clerk sign in
    │   │   └── SignUpPage.tsx     # Clerk sign up
    │   ├── types/
    │   │   └── index.ts           # TypeScript interfaces
    │   ├── App.tsx                # Router setup + auth guards
    │   ├── index.css              # Tailwind + CSS variables + scrollbar
    │   └── main.tsx               # React entry point + ClerkProvider
    ├── .env                       # Frontend environment variables
    ├── .env.example
    ├── package.json
    └── vite.config.ts
```

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- [Node.js v18+](https://nodejs.org/) and npm
- [Python 3.12+](https://www.python.org/)
- [Poetry](https://python-poetry.org/) for Python dependency management
- A [Google Gemini API key](https://aistudio.google.com/app/apikey)
- A [Clerk account](https://clerk.com) with an application set up

---

## Getting Started

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd "Automated RFP Generation Pipeline"
```

### 2. Set up backend environment variables

```bash
cd backend
cp .env.example .env
```

Edit `backend/.env`:

```env
DATABASE_URL=postgresql://postgres:yourpassword@db:5432/rfp_database
POSTGRES_PASSWORD=yourpassword
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Set up frontend environment variables

```bash
cd frontend
cp .env.example .env
```

Edit `frontend/.env`:

```env
VITE_CLERK_PUBLISHABLE_KEY=pk_test_your_clerk_publishable_key_here
```

### 4. Set your Admin User ID

In both files replace `your_clerk_user_id_here` with your actual Clerk User ID (found in Clerk Dashboard → Users):

- `frontend/src/pages/AdminPanel.tsx` — `const ADMIN_USER_ID`
- `frontend/src/components/Navbar.tsx` — `const ADMIN_USER_ID`

### 5. Start the backend with Docker

```bash
cd backend
docker-compose up --build
```

Verify backend at:
```
http://localhost:8000
http://localhost:8000/health
http://localhost:8000/docs
```

### 6. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open the app at:
```
http://localhost:5173
```

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description | Example |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string — use `db` host inside Docker | `postgresql://postgres:pass@db:5432/rfp_database` |
| `POSTGRES_PASSWORD` | PostgreSQL password | `yourpassword` |
| `GEMINI_API_KEY` | Google Gemini API key | `AIza...` |

### Frontend (`frontend/.env`)

| Variable | Description | Example |
|---|---|---|
| `VITE_CLERK_PUBLISHABLE_KEY` | Clerk publishable key | `pk_test_...` |

---

## API Endpoints

### Tenders
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Root check |
| `GET` | `/health` | Docker health check |
| `GET` | `/tenders` | List all tenders |
| `GET` | `/tenders/{reference_number}` | Get single tender with description |
| `POST` | `/scrape` | Manually trigger scraper |
| `POST` | `/tenders/{reference_number}/generate` | Generate AI proposal draft |

### Proposals
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/proposals` | List all proposals |
| `GET` | `/proposals/{reference_number}` | Get single proposal |
| `PUT` | `/proposals/{reference_number}` | Save edited proposal content |
| `POST` | `/proposals/{reference_number}/submit` | Submit proposal for admin review |

### Admin
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/admin/proposals` | List submitted/approved/rejected proposals |
| `GET` | `/admin/recycle-bin` | List rejected proposals with days remaining |
| `PUT` | `/admin/proposals/{reference_number}/status` | Approve or reject proposal |
| `PUT` | `/admin/proposals/{reference_number}/restore` | Restore from recycle bin |
| `DELETE` | `/admin/proposals/{reference_number}` | Permanently delete proposal |

Full interactive API docs: `http://localhost:8000/docs`

---

## How the Pipeline Works

```
Every 30 minutes (or manual trigger via POST /scrape)
            ↓
    Playwright scrapes CanadaBuys
    (stealth mode, exponential backoff retry, anti-bot headers)
            ↓
    Extract: title, reference number, organization,
             closing date, amendment status, source link
            ↓
    For NEW tenders only — scrape full description
    from individual tender detail page
            ↓
    Sync with PostgreSQL:
    - Add new tenders
    - Remove stale tenders (unless proposal drafted)
    - Update amended status if changed
            ↓
    User clicks "Generate Proposal Draft"
            ↓
    Tender data sent to Gemini 2.5 Flash with structured prompt
            ↓
    AI draft returned and saved to proposals table
            ↓
    User edits draft in Tiptap rich text editor
            ↓
    User submits proposal for admin review
            ↓
    Admin approves or rejects
            ↓
    Rejected → Recycle bin (auto-deleted after 30 days)
```

---

## Frontend Pages

### Dashboard (`/`)
- All scraped tenders in a responsive 3-column grid
- Stats bar: Total, Amended, Drafted counts
- Search by title or organization
- Amended and Drafted badges on cards
- Refresh Now button for manual scrape trigger

### Tender Detail (`/tenders/:reference_number`)
- Full tender information including description
- Direct link to original CanadaBuys listing
- Generate Proposal Draft button
- Returns existing draft if already generated

### Proposals (`/proposals`)
- All AI-generated proposal drafts
- Preview of first 150 characters
- View Draft modal with markdown rendering and Copy to Clipboard
- Edit & Submit button

### Proposal Editor (`/proposals/:reference_number/edit`)
- Tiptap rich text editor with full formatting toolbar
- Markdown auto-formatting on type
- Save Draft with visual confirmation
- Submit for Review with toast notification
- Read-only mode after submission

### Admin Panel (`/admin`) — Admin only
- Submitted tab: Review queue with Approve/Reject
- Recycle Bin tab: Rejected proposals with visual countdown
- Restore and Delete Forever actions

---

## Admin Panel

Only the user whose Clerk User ID matches `ADMIN_USER_ID` can access `/admin`. All other users are silently redirected to the dashboard.

**To find your Clerk User ID:**
- Go to [Clerk Dashboard](https://dashboard.clerk.com)
- Click **Users** → click your user
- Copy the **User ID** (format: `user_2abc123...`)

---

## Authentication

Powered by Clerk v5 with the following sign-in methods:
- Google OAuth
- Microsoft OAuth
- Apple OAuth
- Email + Password

All routes except `/sign-in` and `/sign-up` require authentication. Unauthenticated users are automatically redirected to the sign-in page.

---

## Daily Workflow

### Starting the project after a computer restart

```bash
# Step 1 — Open Docker Desktop, wait for "Engine running"

# Step 2 — Start backend containers
cd backend
docker-compose start

# Step 3 — Start frontend dev server
cd ../frontend
npm run dev
```

### Stopping the project

```bash
cd backend
docker-compose stop
```

### When to use `--build`

Only run `docker-compose up --build` when you:
- Add new Python libraries via `poetry add`
- Change `Dockerfile` or `docker-compose.yml`
- Change `models.py` and need to recreate tables (run `docker-compose down -v` first)
- First time setting up the project

### Viewing live logs

```bash
docker logs rfp_automation_pipeline_backend -f
docker logs rfp_automation_pipeline_postgres -f
```

---

## Docker Reference

### Container names
| Container | Purpose | Port |
|---|---|---|
| `rfp_automation_pipeline_backend` | FastAPI backend | `8000` |
| `rfp_automation_pipeline_postgres` | PostgreSQL 18 | `5433` (host) → `5432` (container) |

### Useful commands

```bash
# Start containers (after first build)
docker-compose start

# Stop containers
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop, remove containers AND volumes (wipes database)
docker-compose down -v

# Rebuild and start
docker-compose up --build

# View running containers
docker ps

# Connect to database directly
docker exec -it rfp_automation_pipeline_postgres psql -U postgres -d rfp_database

# List all databases
docker exec -it rfp_automation_pipeline_postgres psql -U postgres -c "\l"

# List all tables
docker exec -it rfp_automation_pipeline_postgres psql -U postgres -d rfp_database -c "\dt"
```

### Connecting pgAdmin4 to Docker Postgres

Register a new server in pgAdmin4:
```
Name:     RFP Pipeline (Docker)
Host:     localhost
Port:     5433
Database: rfp_database
Username: postgres
Password: yourpassword
```

### Port Reference

```
Backend API  → localhost:8000
PostgreSQL   → localhost:5433 (Docker) / localhost:5432 (local install)
Frontend     → localhost:5173
```

---

## Notes

- The scraper uses Playwright with stealth mode and randomized delays to avoid bot detection
- Tenders are deduplicated by `reference_number` — no duplicates in the database
- Tenders removed from the website are automatically deleted unless a proposal exists
- The `proposal_drafted` flag protects tenders from automatic deletion
- All API keys and passwords are stored in `.env` — never commit this file
- Admin panel is protected client-side by Clerk User ID — add backend JWT validation before deploying to production
- Clerk is in Development mode — switch to Production keys before deploying
