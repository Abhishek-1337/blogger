# Blogger

AI-assisted blog generator: enter a topic, get a web-researched,
outlined, and written blog post. Per-user history plus LLM usage
(tokens, cost, latency) observability.

## Architecture

| Part | Stack | Purpose |
| --- | --- | --- |
| `backend/` | FastAPI, LangGraph, SQLAlchemy (async), Alembic, Celery + Redis | Auth, blog pipeline, storage, usage tracking |
| `frontend/` | React 18, Vite, Tailwind, react-markdown | User app: sign in, generate blogs, browse history |
| `admin-frontend/` | React 18, Vite, Tailwind | Admin app: usage summaries, recent queries, per-search call detail |

## How it works

1. The frontend signs the user in with Google Identity Services and
   sends the Google ID token to `POST /auth/google`.
2. The backend verifies the token against `GOOGLE_CLIENT_ID`, upserts
   the user, and returns a short-lived app JWT. All blog/search
   endpoints require that JWT and are scoped to its user.
3. `POST /blog` runs the LangGraph pipeline (`backend/src/graph.py`):
   research agent (live web search, 3–5 angles) → research brief →
   structured outline (4–6 sections) → LLM editor review (up to 2
   revisions) → section writing. Results are stored as a search entry.
4. Every LLM call is captured by a per-run `UsageCollector` (LangChain
   callback), including calls hidden inside the research agent, and
   persisted as `llm_usage_events` with model, stage, token counts,
   and latency. Cost is estimated from `gpt-4o-mini` pricing.

## API

Auth: `POST /auth/google`, `GET /auth/me`.
Blog: `GET /searches`, `GET /searches/{id}`, `POST /blog`.
Usage (own): `GET /usage/summary`, `GET /usage/overview`,
`GET /usage/recent`, `GET /searches/{entry_id}/usage`.
Admin: `GET /admin/usage/summary`, `GET /admin/usage/recent`,
`GET /admin/searches/{entry_id}/usage`.
Health: `GET /health`.

## Setup

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in values below
alembic upgrade head
uvicorn main:app --reload
```

Required env (`backend/.env`):

| Var | Purpose |
| --- | --- |
| `DATABASE_URL` | Postgres URL (asyncpg driver added automatically) |
| `OPENAI_API_KEY` | Blog pipeline + research agent model calls |
| `GOOGLE_CLIENT_ID` | Verify Google ID tokens |
| `JWT_SECRET_KEY` | Sign app session JWTs |
| `ADMIN_EMAILS` | Comma-separated admin allowlist; unset = any user is admin (local dev only) |

### Frontend (user app)

```bash
cd frontend
npm install
npm run dev
```

Set `VITE_API_URL` (backend URL) and `VITE_GOOGLE_CLIENT_ID` (same
Google OAuth client) in `frontend/.env`.

### Admin frontend

```bash
cd admin-frontend
npm install
npm run dev
```

Same env vars as the user app (`VITE_API_URL`,
`VITE_GOOGLE_CLIENT_ID`); sign in with an `ADMIN_EMAILS` address.

## Background jobs

`backend/src/services/celery_app.py` defines the Celery app
(Redis broker `localhost:6379/0`, backend `localhost:6379/1`).
No tasks are wired to it yet; blog generation currently runs inline
via `POST /blog`.

## Tests

```bash
cd backend
pytest
```
