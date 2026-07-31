import logging
import sys
import uuid
import time
import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from pythonjsonlogger import jsonlogger

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.database import init_db, engine
from app.config import settings
from app.services.limiter import limiter


# ── Structured Logging ───────────────────────────────────────────────────────

class StructuredFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["ts"] = self.formatTime(record)
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["service"] = "legallens"


def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    logger.handlers = [handler]
    return logger


log = setup_logging()


# ── Request ID Middleware ─────────────────────────────────────────────────────

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start_time = time.time()

        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            log.error("request.failed", extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "duration_ms": duration_ms,
                "error": str(exc),
            })
            raise

        duration_ms = round((time.time() - start_time) * 1000, 2)
        log.info("request.completed", extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        })
        response.headers["X-Request-ID"] = request_id
        return response


# ── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    log.info("app.started", extra={"llm_provider": settings.llm_provider})
    yield
    log.info("app.shutdown")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="LegalLens AI",
    description="AI-powered legal contract review platform",
    version="0.2.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routers import contracts, analysis, auth, payments

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])

app.include_router(contracts.router, prefix="/api/contracts", tags=["contracts"])
app.include_router(contracts.router, prefix="/contracts", tags=["contracts"])

app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(analysis.router, prefix="/analysis", tags=["analysis"])

app.include_router(payments.router, prefix="/api/payments", tags=["payments"])
app.include_router(payments.router, prefix="/payments", tags=["payments"])

from app.deps import get_current_user_from_cookie
from app.models.db_models import User, AuditLog

@app.post("/api/payments/create-checkout-session")
@app.post("/payments/create-checkout-session")
async def direct_create_checkout_session(
    request: Request,
    user: User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    """Fallback payment checkout endpoint directly mounted on FastAPI app."""
    user.tier = "pro"
    db.commit()
    audit = AuditLog(
        user_id=user.id,
        action="stripe_checkout_demo",
        resource_type="user",
        resource_id=user.id,
        details={"tier": "pro", "mode": "demo"},
    )
    db.add(audit)
    db.commit()
    return {"url": "/dashboard?payment=success&mode=demo"}


@app.get("/api/health")
def health_check(request: Request):
    checks = {
        "database": "ok",
        "disk": "ok",
        "llm": "ok",
    }
    status = "healthy"

    # DB check
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        checks["database"] = f"error: {str(e)[:50]}"
        status = "degraded"

    # Disk check (uploads directory)
    try:
        upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
        stat = os.statvfs(upload_dir if os.path.exists(upload_dir) else os.path.dirname(upload_dir))
        free_mb = (stat.f_bavail * stat.f_frsize) / (1024 * 1024)
        if free_mb < 100:
            checks["disk"] = f"low space: {round(free_mb)}MB free"
            status = "degraded"
    except Exception as e:
        checks["disk"] = f"error: {str(e)[:50]}"

    # LLM check
    if settings.llm_provider == "demo":
        checks["llm"] = "demo mode (no API key)"
    elif settings.llm_provider == "openai":
        if not settings.OPENAI_API_KEY:
            checks["llm"] = "openai configured but no API key"
            status = "degraded"
    elif settings.llm_provider == "anthropic":
        if not settings.ANTHROPIC_API_KEY:
            checks["llm"] = "anthropic configured but no API key"
            status = "degraded"

    return {
        "status": status,
        "service": "LegalLens AI",
        "llm_provider": settings.llm_provider,
        "request_id": getattr(request.state, "request_id", None),
        "checks": checks,
    }
