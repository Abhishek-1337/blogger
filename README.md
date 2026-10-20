# Blogger

Blogger is an AI-assisted blog generator. A user signs in, enters a
topic, and receives a complete blog post grounded in live web research,
with a visible research brief, structured outline, and editor review
before the final draft. Every post is saved to the user's personal
history, and every model call behind it is metered for tokens, cost,
and latency.

## Project description

The product has three parts: a user-facing web app, an admin
observability app, and a backend API that owns authentication, blog
generation, storage, and usage tracking.

Users authenticate with their Google account and receive a short-lived
app session. From there they can generate blogs, reopen past searches,
and inspect the research and outline behind each result. Admins get a
separate view over aggregate usage and recent queries across users,
plus per-post cost and latency detail.

Blog generation is a multi-stage pipeline rather than a single prompt.
A research agent runs several focused web searches across distinct
angles of the topic and distills the findings into a brief. An
outliner turns the brief into a structured multi-section plan, an
editor model critiques it and requests revisions when needed, and
section writers then draft the full post against the approved plan.

Usage tracking is first-class: each pipeline run carries its own usage
collector, so even model calls nested inside the research agent are
attributed to the right stage with token counts and timing. Costs are
estimated from the active model's public pricing, giving both users
and admins a clear picture of what each post cost to produce.

## Architectural overview

The backend is a Python API service backed by Postgres for users,
stored blog posts, and a per-call usage event log. Schema changes are
versioned through database migrations. Authentication is split into
two layers: Google verifies identity, and the backend issues its own
session tokens that scope every request to the signed-in user, with an
allowlist gating the admin surface.

The generation pipeline is built as a graph of stages — research,
briefing, outlining, review, and writing — orchestrated on a language
model graph framework with a chat model for reasoning and a live
search tool for grounding. Generation currently runs inline with the
request lifecycle; a background job queue backed by Redis is scaffolded
for moving long-running work out of the request path.

The two web apps are single-page React applications. The user app owns
sign-in, the generation composer with staged progress, markdown
rendering of results, and search history. The admin app is a separate
surface focused on usage summaries and drill-downs rather than content
creation, keeping everyday use and operational oversight cleanly
separated.

## Local setup

You need Python 3.11+, Node 18+, and a Postgres database. A Google
OAuth client ID and an OpenAI API key are required for sign-in and
generation.

Start with the backend. From the project root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Then fill in the backend environment with your own values: your OpenAI
API key, your Google OAuth client ID, a long random string for session
signing, and optionally a comma-separated list of admin emails (when
unset, every signed-in user is treated as admin, which is fine for
local development only). Also add a line for your Postgres connection
string, which the example file does not include yet:

```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/blogger
```
After that, apply the database migrations and start the API:

```bash
alembic upgrade head
uvicorn main:app --reload
```

The API serves on `http://localhost:8000`.

Next, the user app. In a new terminal, from the project root:

```bash
cd frontend
npm install
npm run dev
```

It serves on `http://localhost:5173` and forwards API calls to the
backend automatically. It needs two values in its own environment: the
backend URL (`http://localhost:8000`) and the same Google OAuth client
ID the backend verifies against. Make sure the Google client allows
`http://localhost:5173` as an authorized origin.

The admin app follows the same pattern on its own port:

```bash
cd admin-frontend
npm install
npm run dev
```

It serves on `http://localhost:5174`, points at the same backend URL,
uses the same Google client ID (allowing `http://localhost:5174` as
well), and must be opened with an account on the admin allowlist.

## Using the app

Open the user app, sign in with Google, and type a topic into the
composer. Generation takes a while — watch the staged progress from
web search through research brief, outline draft, and editor review to
the finished post. The result shows the research brief, the outline,
and the review verdict alongside the final markdown article, and it is
kept in history so you can reopen any past post.

A usage view shows what your generations cost in tokens and estimated
spend. Open the admin app with an admin account to see aggregate usage
across users, recent queries, and a per-post breakdown of each model
call with its stage, token counts, and latency.

