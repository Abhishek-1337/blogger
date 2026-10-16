"""Request/response types for the auth routes."""

from pydantic import BaseModel, Field


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    picture: str


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(min_length=1, description="Google ID token from GIS")


class LoginResponse(BaseModel):
    token: str
    user: UserOut
