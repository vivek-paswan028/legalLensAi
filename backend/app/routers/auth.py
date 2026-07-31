import logging
import re
from fastapi import APIRouter, HTTPException, Depends, Response, Request
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from app.database import get_db
from app.services.limiter import limiter
from app.config import settings
from app.models.db_models import User, AuditLog
log = logging.getLogger("legallens")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter()


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", v):
            raise ValueError("Invalid email address")
        return v.lower().strip()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    created_at: str


COOKIE_NAME = "legallens_token"
COOKIE_MAX_AGE = settings.JWT_EXPIRY_HOURS * 60 * 60


def create_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRY_HOURS)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


@router.post("/register", response_model=UserResponse)
@limiter.limit("3/minute")
async def register(request: Request, req_data: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == req_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=req_data.email,
        hashed_password=pwd_context.hash(req_data.password),
        name=req_data.name
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_token(user.id)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=settings.is_production,
        samesite="strict",
    )
    audit = AuditLog(
        user_id=user.id,
        action="register",
        resource_type="user",
        resource_id=user.id,
        ip_address=request.headers.get("x-forwarded-for", "").split(",")[0].strip(),
        user_agent=request.headers.get("user-agent", ""),
    )
    db.add(audit)
    db.commit()
    log.info("auth.register", extra={"user_id": user.id, "email": user.email})
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        created_at=user.created_at.isoformat()
    )


@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, req_data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req_data.email.lower().strip()).first()
    if not user or not pwd_context.verify(req_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token(user.id)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=settings.is_production,
        samesite="strict",
    )
    audit = AuditLog(
        user_id=user.id,
        action="login",
        resource_type="user",
        resource_id=user.id,
        ip_address=request.headers.get("x-forwarded-for", "").split(",")[0].strip(),
        user_agent=request.headers.get("user-agent", ""),
    )
    db.add(audit)
    db.commit()
    log.info("auth.login", extra={"user_id": user.id, "email": user.email})
    return {"id": user.id, "email": user.email, "name": user.name}


@router.post("/logout")
async def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    from app.deps import get_current_user_from_cookie
    try:
        user = await get_current_user_from_cookie(request, db)
        audit = AuditLog(
            user_id=user.id,
            action="logout",
            resource_type="user",
            resource_id=user.id,
            ip_address=request.headers.get("x-forwarded-for", "").split(",")[0].strip(),
            user_agent=request.headers.get("user-agent", ""),
        )
        db.add(audit)
        db.commit()
    except HTTPException:
        pass
    response.delete_cookie(key=COOKIE_NAME)
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(request: Request, db: Session = Depends(get_db)):
    from app.deps import get_current_user_from_cookie
    user = await get_current_user_from_cookie(request, db)
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        created_at=user.created_at.isoformat()
    )
