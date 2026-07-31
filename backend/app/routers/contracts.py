import logging
import os
import re
import shutil
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import get_current_user_from_cookie as get_current_user
from app.models.db_models import User, Contract, AuditLog
from app.models.schemas import ContractUploadResponse

router = APIRouter()
log = logging.getLogger("legallens")

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
ALLOWED_MIME_TYPES = {
    ".pdf": b"%PDF-",
    ".docx": b"PK\x03\x04",  # DOCX is a ZIP file
    ".txt": None,  # Text files have no magic bytes
}


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal and enforce safe characters."""
    name, ext = os.path.splitext(filename)
    name = re.sub(r"[^\w\s.-]", "", name)
    name = re.sub(r"\.+/", "", name)
    name = name.strip()[:200]
    ext = ext.lower()
    return f"{name}{ext}"


async def validate_file_content(file: UploadFile, ext: str) -> None:
    """Validate file content matches extension using magic bytes."""
    if ext == ".txt":
        return

    magic = ALLOWED_MIME_TYPES.get(ext)
    if magic is None:
        return

    header = file.file.read(len(magic))
    file.file.seek(0)
    if not header.startswith(magic):
        raise HTTPException(status_code=400, detail=f"File content does not match extension: {ext}")


@router.post("/upload", response_model=ContractUploadResponse)
async def upload_contract(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ext = os.path.splitext(file.filename)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)

    if size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
        )

    await validate_file_content(file, ext)

    safe_filename = sanitize_filename(file.filename)
    contract_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{contract_id}{ext}")

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    contract = Contract(
        id=contract_id,
        user_id=user.id,
        filename=safe_filename,
        file_path=file_path,
        status="uploaded"
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)

    audit = AuditLog(
        user_id=user.id,
        action="contract_upload",
        resource_type="contract",
        resource_id=contract.id,
        ip_address=request.headers.get("x-forwarded-for", "").split(",")[0].strip(),
        user_agent=request.headers.get("user-agent", ""),
        details={"filename": safe_filename, "size_bytes": size},
    )
    db.add(audit)
    db.commit()

    log.info("contract.uploaded", extra={
        "user_id": user.id,
        "contract_id": contract.id,
        "file_name": safe_filename,
        "size_bytes": size,
    })

    return ContractUploadResponse(
        id=contract.id,
        filename=contract.filename,
        status=contract.status,
        uploaded_at=contract.uploaded_at
    )


@router.get("")
async def list_contracts(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    contracts = db.query(Contract).filter(Contract.user_id == user.id).order_by(Contract.uploaded_at.desc()).all()
    return [
        {
            "id": c.id,
            "filename": c.filename,
            "status": c.status,
            "contract_type": c.contract_type,
            "uploaded_at": c.uploaded_at.isoformat(),
            "has_analysis": c.analysis is not None,
            "risk_level": c.analysis.overall_risk_level if c.analysis else None,
            "risk_score": c.analysis.overall_risk_score if c.analysis else None,
        }
        for c in contracts
    ]


@router.get("/{contract_id}")
async def get_contract(
    contract_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    contract = db.query(Contract).filter(Contract.id == contract_id, Contract.user_id == user.id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    analysis_data = None
    if contract.analysis:
        a = contract.analysis
        analysis_data = {
            "overall_risk_score": a.overall_risk_score,
            "overall_risk_level": a.overall_risk_level,
            "summary": a.summary,
            "executive_summary": a.executive_summary,
            "key_terms": a.key_terms,
            "parties": a.parties,
            "effective_date": a.effective_date,
            "expiration_date": a.expiration_date,
            "governing_law": a.governing_law,
            "analyzed_at": a.analyzed_at.isoformat() if a.analyzed_at else None,
            "clauses": [
                {
                    "id": cl.id,
                    "clause_title": cl.clause_title,
                    "clause_text": cl.clause_text,
                    "risk_level": cl.risk_level,
                    "risk_score": cl.risk_score,
                    "explanation": cl.explanation,
                    "suggested_revision": cl.suggested_revision,
                }
                for cl in a.clauses
            ]
        }

    return {
        "id": contract.id,
        "filename": contract.filename,
        "status": contract.status,
        "contract_type": contract.contract_type,
        "uploaded_at": contract.uploaded_at.isoformat(),
        "analysis": analysis_data
    }


@router.delete("/{contract_id}")
async def delete_contract(
    contract_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    contract = db.query(Contract).filter(Contract.id == contract_id, Contract.user_id == user.id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    if os.path.exists(contract.file_path):
        os.remove(contract.file_path)

    audit = AuditLog(
        user_id=user.id,
        action="contract_delete",
        resource_type="contract",
        resource_id=contract_id,
        ip_address=request.headers.get("x-forwarded-for", "").split(",")[0].strip(),
        user_agent=request.headers.get("user-agent", ""),
    )
    db.add(audit)
    db.delete(contract)
    db.commit()

    log.info("contract.deleted", extra={
        "user_id": user.id,
        "contract_id": contract_id,
    })

    return {"message": "Contract deleted successfully"}
