from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status

from .config import get_settings


settings = get_settings()


async def issue_token(username: str, password: str) -> dict:
    payload = {
        "grant_type": "password",
        "client_id": settings.keycloak_client_id,
        "client_secret": settings.keycloak_client_secret,
        "username": username,
        "password": password,
        "scope": "openid profile email",
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            settings.keycloak_token_endpoint,
            data=payload,
            headers=headers,
        )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Keycloak token issuance failed: {response.text}",
        )

    return response.json()


async def fetch_userinfo(access_token: str) -> dict:
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(settings.keycloak_userinfo_endpoint, headers=headers)

    if response.status_code >= 400:
        detail = response.text or f"status={response.status_code}"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Keycloak userinfo request failed: {detail}",
        )
    return response.json()


async def keycloak_alive() -> bool:
    health_url = f"{settings.keycloak_base_url}/realms/{settings.keycloak_realm}"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(health_url)
        return response.status_code == 200
    except (httpx.HTTPError, TimeoutError):
        return False


def build_authorization_url(state: str = "demo-state") -> str:
    query = urlencode(
        {
            "client_id": settings.keycloak_client_id,
            "redirect_uri": settings.keycloak_redirect_uri,
            "response_type": "code",
            "scope": "openid profile email",
            "state": state,
        }
    )
    return f"{settings.keycloak_auth_endpoint}?{query}"
