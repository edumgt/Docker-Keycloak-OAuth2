from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from .auth import build_authorization_url, fetch_userinfo, issue_token, keycloak_alive
from .config import get_settings
from .db import Base, engine, get_db
from .models import Consent, Member
from .schemas import (
    ConsentCreate,
    ConsentRead,
    HealthResponse,
    MemberCreate,
    MemberRead,
    MemberStatusUpdate,
    TokenRequest,
    TokenResponse,
    UserInfoResponse,
)


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Python backend for Keycloak OAuth2/OIDC integration demo.",
)
security = HTTPBearer()
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/")
def root() -> dict:
    return {
        "message": "Unified Auth Backend is running.",
        "docs": "/docs",
        "frontend": "/app-ui",
        "api_prefix": settings.api_prefix,
    }


@app.get("/app-ui", include_in_schema=False)
def app_ui() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get(f"{settings.api_prefix}/health", response_model=HealthResponse)
async def health_check(
    db: Annotated[Session, Depends(get_db)],
) -> HealthResponse:
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "unhealthy"

    kc_status = "ok" if await keycloak_alive() else "unreachable"
    service_status = "ok" if db_status == "ok" and kc_status == "ok" else "degraded"

    return HealthResponse(status=service_status, database=db_status, keycloak=kc_status)


@app.get(f"{settings.api_prefix}/auth/login-url")
def get_login_url() -> dict:
    return {"authorization_url": build_authorization_url()}


@app.post(f"{settings.api_prefix}/auth/token", response_model=TokenResponse)
async def token_exchange(body: TokenRequest) -> TokenResponse:
    token = await issue_token(body.username, body.password)
    return TokenResponse(**token)


@app.get(f"{settings.api_prefix}/auth/userinfo", response_model=UserInfoResponse)
async def user_info(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> UserInfoResponse:
    payload = await fetch_userinfo(credentials.credentials)
    return UserInfoResponse(payload=payload)


@app.post(
    f"{settings.api_prefix}/members",
    response_model=MemberRead,
    status_code=status.HTTP_201_CREATED,
)
def create_member(
    body: MemberCreate,
    db: Annotated[Session, Depends(get_db)],
) -> MemberRead:
    existing = db.query(Member).filter(
        (Member.customer_id == body.customer_id) | (Member.email == body.email)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Member with same customer_id or email already exists.",
        )

    member = Member(
        customer_id=body.customer_id,
        email=body.email,
        stage=body.stage,
        account_status=body.account_status,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return MemberRead.model_validate(member)


@app.get(f"{settings.api_prefix}/members", response_model=list[MemberRead])
def list_members(
    db: Annotated[Session, Depends(get_db)],
) -> list[MemberRead]:
    members = db.query(Member).order_by(Member.id.asc()).all()
    return [MemberRead.model_validate(item) for item in members]


@app.patch(f"{settings.api_prefix}/members/{{customer_id}}/status", response_model=MemberRead)
def update_member_status(
    customer_id: str,
    body: MemberStatusUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> MemberRead:
    member = db.query(Member).filter(Member.customer_id == customer_id).first()
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found.")

    member.account_status = body.account_status
    db.commit()
    db.refresh(member)
    return MemberRead.model_validate(member)


@app.post(
    f"{settings.api_prefix}/consents",
    response_model=ConsentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_consent(
    body: ConsentCreate,
    db: Annotated[Session, Depends(get_db)],
) -> ConsentRead:
    member = db.query(Member).filter(Member.customer_id == body.customer_id).first()
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found.")

    consent = Consent(
        member_id=member.id,
        consent_type=body.consent_type,
        service_name=body.service_name,
        purpose=body.purpose,
        is_required=body.is_required,
        is_agreed=body.is_agreed,
        consent_version=body.consent_version,
        country_code=body.country_code,
        language_code=body.language_code,
    )
    db.add(consent)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Consent with same member/purpose/version already exists.",
        ) from None

    db.refresh(consent)
    return ConsentRead.model_validate(consent)


@app.get(f"{settings.api_prefix}/members/{{customer_id}}/consents", response_model=list[ConsentRead])
def list_member_consents(
    customer_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> list[ConsentRead]:
    member = db.query(Member).filter(Member.customer_id == customer_id).first()
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found.")

    consents = db.query(Consent).filter(Consent.member_id == member.id).order_by(Consent.id.asc()).all()
    return [ConsentRead.model_validate(item) for item in consents]
