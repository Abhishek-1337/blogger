"""Blogger API composition root: app, middleware, and router wiring."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.routers import admin, auth, blog, usage

app = FastAPI(title="Blogger API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(blog.router)
app.include_router(usage.router)
app.include_router(admin.router)
