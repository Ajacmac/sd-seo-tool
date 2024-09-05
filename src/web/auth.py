import logging
from typing import Optional

from authlib.integrations.starlette_client import OAuth
from config import (
    AUTHORIZED_DOMAIN,
    AUTHORIZED_EMAILS,
    GOOGLE_OAUTH_CLIENT_ID,
    GOOGLE_OAUTH_CLIENT_SECRET,
)
from fastapi import HTTPException, Request
from pydantic import BaseModel

oauth = OAuth()

oauth.register(
    name="google",
    client_id=GOOGLE_OAUTH_CLIENT_ID,
    client_secret=GOOGLE_OAUTH_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

logger = logging.getLogger(__name__)


class User(BaseModel):
    email: str
    full_name: Optional[str] = None


def get_current_user(request: Request) -> User:
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    email = user.get("email")
    if not email:
        raise HTTPException(status_code=401, detail="Invalid user data")

    if not email.endswith(f"@{AUTHORIZED_DOMAIN}") and email not in AUTHORIZED_EMAILS:
        raise HTTPException(status_code=403, detail="Unauthorized email")

    return User(email=email, full_name=user.get("name"))


async def authenticate_user(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)

        if "id_token" not in token:
            raise ValueError("ID token is missing from the token response")

        nonce = request.session.get("oauth_nonce")
        if not nonce:
            raise ValueError("Nonce is missing from the session")

        user_info = await oauth.google.parse_id_token(token, nonce=nonce)

        email = user_info.get("email")
        if not email:
            raise ValueError("Email is missing from user info")

        if not isinstance(email, str):
            raise ValueError("Email is not a valid string")

        if (
            not email.endswith(f"@{AUTHORIZED_DOMAIN}")
            and email not in AUTHORIZED_EMAILS
        ):
            raise HTTPException(status_code=403, detail="Unauthorized email domain")

        return user_info

    except ValueError as ve:
        logger.error(f"Authentication error: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Unexpected authentication error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


def get_oauth_client():
    return oauth.google
