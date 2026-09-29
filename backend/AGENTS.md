# AGENTS.md — Backend (Sage / SIH Harness)

## What this service is
This is the **Backend** microservice for the SIH Harness project (an agentic
farming assistant). This service does NOT contain any LLM/agent logic and does
NOT touch the Rust Codex fork. It exposes clean REST APIs that the Rust/Harness
team wraps as tool handlers later. See `docs/PRD.md` for full project context.

## Stack
- FastAPI (async)
- Beanie (ODM) + Motor + MongoDB — for the CENTRAL/shared database only
  (crop info, fertilizers, seeds, gov schemes, MSP, mandi reference data)
- Per-farmer data (fields, sensor readings, expenses, harvests) is NOT
  this service's concern — that lives in a local SQLite DB on the client.
  Do not build farmer-personal-data models here unless explicitly told to.

## Project structure
backend/app/
├── main.py          # FastAPI app + lifespan (init_beanie)
├── core/
│   ├── config.py    # Pydantic Settings, reads .env
│   └── database.py  # Motor client + init_beanie
├── models/          # Beanie Document classes (DB schema)
├── schemas/         # Plain Pydantic models (API request/response shapes)
└── routers/         # APIRouter endpoints, one file per domain

## Rules for every change
1. Every new collection needs: a model in `models/`, a schema in `schemas/`,
   a router in `routers/`, and must be registered in `main.py`.
2. Follow the existing pattern in the codebase before inventing a new one —
   check an existing model/router pair first (e.g. `models/farmer.py` +
   `routers/farmer.py`) and match its style.
3. Functions should map to the tool functions named in the PRD where
   applicable (e.g. `get_soil_moisture`, `get_market_price`,
   `recommend_fertilizer`) — these names matter because the Harness team
   wraps them 1:1 as tool handlers. Don't rename them arbitrarily.
4. Never invent data. Per PRD section 28, weather/MSP/mandi/sensor values
   must come from real sources or clearly-marked mock data — never silently
   fabricated numbers in a response.
5. After ANY change: update `ChangeLog.md`, and if a non-obvious choice was
   made, add an entry to `Decisions.md`. Update `Flow.md` if you added/changed
   how a function or module connects to others.
6. Don't touch `frontend/` or `codex-rs/` — out of scope for this service.

## Before finishing any task
Read back the diff. Confirm it matches existing patterns. Confirm the three
memory files (ChangeLog, Decisions, Flow) are updated.

 build compare_mandis(). Write out the Pydantic response schema and the FastAPI router logic based on the exact math Net
  Realisation = Sale Revenue − Transport − Loading − Unloading − Market Fees − Storage − Expected Spoilage

