from __future__ import annotations

from dataclasses import dataclass

import requests
from fastapi import Header, HTTPException, status

from config import get_settings


@dataclass(frozen=True)
class AuthenticatedUser:
    """
    Authenticated Supabase user details needed by the API.
    """

    id: str
    email: str
    raw_user: dict


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization bearer token.",
        )

    scheme, _, token = authorization.partition(" ")

    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must be a Bearer token.",
        )

    return token.strip()


def get_authenticated_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> AuthenticatedUser:
    """
    Validates the browser's Supabase Auth JWT with Supabase Auth.

    The service role key is used only as the server-side API key. The user's
    bearer token remains the token being validated.
    """

    token = _extract_bearer_token(authorization)
    settings = get_settings()

    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase backend configuration is missing.",
        )

    auth_url = f"{settings.supabase_url.rstrip('/')}/auth/v1/user"

    try:
        response = requests.get(
            auth_url,
            headers={
                "apikey": settings.supabase_service_role_key,
                "Authorization": f"Bearer {token}",
            },
            timeout=30,
        )
    except requests.RequestException as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not validate Supabase session.",
        ) from error

    if response.status_code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Supabase session.",
        )

    if not response.ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase Auth validation failed.",
        )

    user = response.json()
    user_id = user.get("id")
    email = (user.get("email") or "").strip().lower()

    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student login must have a verified email address.",
        )

    return AuthenticatedUser(
        id=str(user_id),
        email=email,
        raw_user=user,
    )
