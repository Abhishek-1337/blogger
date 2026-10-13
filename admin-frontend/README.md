# Blogger Admin — token & cost observability

A separate, deployable frontend for admin-only LLM observability. It talks to
the **same backend and database** as the main Blogger app — only the
`/admin/*` and `/auth/*` endpoints — so it can be hosted somewhere else
entirely (e.g. an internal Vercel project) while the main app shows no token
or cost data at all.

What it shows:

- Total / input / output tokens, estimated cost, query and call counts
- Tokens by pipeline stage, daily trend (last 14 days)
- Every query across all users, with per-query per-call drilldown

## Run locally

```bash
cd admin-frontend
cp .env.example .env   # point VITE_API_URL at the backend
npm install
npm run dev            # http://localhost:5174
```

Open [http://localhost:5174](http://localhost:5174) in a browser.

## Deploy elsewhere

This is a static Vite build — deploy the `dist/` output anywhere
(Vercel, Netlify, Cloudflare Pages, S3 + CDN):

```bash
npm run build   # emits dist/
```

Environment (set on the host, not in git):

| Variable | Purpose |
| --- | --- |
| `VITE_API_URL` | Public URL of the Blogger backend, e.g. `https://api.example.com` |
| `VITE_GOOGLE_CLIENT_ID` | Same Google OAuth client ID as the main frontend (add the admin origin to its authorized origins) |

Backend counterpart: set `ADMIN_EMAILS=you@example.com,teammate@example.com`
in `backend/.env`. When `ADMIN_EMAILS` is unset, any signed-in user counts as
admin (convenient for local dev, not for production). Non-admin accounts get
`403 Admin access required` from every usage endpoint.
