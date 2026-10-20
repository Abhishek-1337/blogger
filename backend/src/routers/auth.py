from fastapi import APIRouter, Depends, HTTPException

from src.auth import (
    create_access_token,
    get_current_user,
    get_or_create_user,
    verify_google_token,
)
from src.db import SessionLocal
from src.models import User
from src.types import GoogleLoginRequest, LoginResponse, UserOut

from .shared import to_user_out

router = APIRouter()


@router.post("/auth/google", response_model=LoginResponse)
async def google_login(req: GoogleLoginRequest):
    try:
        claims = verify_google_token(req.id_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    async with SessionLocal() as session:
        user = await get_or_create_user(session, claims)
    return LoginResponse(token=create_access_token(user.id), user=to_user_out(user))


@router.get("/auth/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return to_user_out(user)
