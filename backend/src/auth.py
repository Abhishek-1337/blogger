"""Google OAuth login + app JWT sessions.

Flow: the frontend signs the user in with Google Identity Services and sends
the Google ID token to POST /auth/google. We verify it against
GOOGLE_CLIENT_ID, upsert the user, and return a short-lived app JWT. All
blog/search endpoints require that JWT and are scoped to its user.
"""

import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User

load_dotenv()

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "43200"))  # 30 days

_bearer = HTTPBearer(auto_error=False)


def _google_client_id() -> str:
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    if not client_id:
        raise ValueError(
            "GOOGLE_CLIENT_ID is not set — add your Google OAuth client ID "
            "to backend/.env (and VITE_GOOGLE_CLIENT_ID for the frontend)."
        )
    return client_id


def _jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET_KEY", "").strip()
    if not secret:
        raise ValueError(
            "JWT_SECRET_KEY is not set — add a long random string "
            "to backend/.env."
        )
    return secret


def verify_google_token(id_token: str) -> dict:
    """Verify a Google ID token; return sub/email/name/picture."""
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token as google_id_token

    try:
        info = google_id_token.verify_oauth2_token(
            id_token, google_requests.Request(), _google_client_id()
        )
    except Exception as e:
        raise ValueError(f"Google token verification failed: {e}")
    sub = info.get("sub", "")
    if not sub:
        raise ValueError("Google token has no subject.")
    return {
        "sub": sub,
        "email": info.get("email", "") or "",
        "name": info.get("name", "") or "",
        "picture": info.get("picture", "") or "",
    }


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> int:
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=[JWT_ALGORITHM])
        return int(payload["sub"])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session. Please sign in again.",
        )


async def get_or_create_user(session: AsyncSession, claims: dict) -> User:
    result = await session.execute(
        select(User).where(User.google_sub == claims["sub"])
    )
    user = result.scalars().first()
    if user is None:
        user = User(
            google_sub=claims["sub"],
            email=claims.get("email", ""),
            name=claims.get("name", ""),
            picture=claims.get("picture", ""),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> User:
    """FastAPI dependency: the JWT-authenticated user, else 401."""
    if creds is None or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not signed in.",
        )
    user_id = decode_access_token(creds.credentials)
    from src.db import SessionLocal

    async with SessionLocal() as session:
        user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account no longer exists. Please sign in again.",
        )
    return user
