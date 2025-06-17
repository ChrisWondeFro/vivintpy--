from __future__ import annotations

from pydantic import BaseModel, Field

from .system import SystemResponse


class LoginRequest(BaseModel):
    """Request model for user login."""

    username: str = Field(..., description="Vivint username")
    password: str = Field(..., description="Vivint password")


class MfaRequest(BaseModel):
    """Request model for MFA verification."""

    code: str = Field(..., description="Multi-factor authentication code")


class Token(BaseModel):
    """Pydantic model for the authentication token."""

    access_token: str
    token_type: str
    vivint_refresh_token: str | None = None


class TokenData(BaseModel):
    """Pydantic model for data encoded in the token."""

    username: str | None = None
    vivint_refresh_token: str | None = None


class RefreshTokenRequest(BaseModel):
    """Request model for refreshing an API token."""
    refresh_token: str = Field(..., description="The API refresh token")


class AuthUserResponse(BaseModel):
    """Pydantic model for the authenticated user's data."""

    id: str = Field(..., alias="uid", description="User ID")
    email: str = Field(..., description="User's email address")
    systems: list[SystemResponse] = Field(..., description="List of systems accessible to the user")

    class Config:
        from_attributes = True
        populate_by_name = True
