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
