import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import get_current_user_from_cookie as get_current_user
from app.models.db_models import User, Contract, Analysis, Clause, AnalysisTask, AuditLog, RedlineDecision
from app.services.document_parser import parse_document

router = APIRouter()
log = logging.getLogger("legallens")

QUOTA_LIMITS = {
    "free": 100, # Increased for development/testing
    "pro": 250,
    "enterprise": float("inf"),
}

MAX_RETRIES = 3


def get_llm_client():
    from app.config import settings
    if settings.llm_provider == "openai":
        from openai import AsyncOpenAI
        return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    elif settings.llm_provider == "anthropic":
        import anthropic
        return anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    elif settings.llm_provider == "gemini":
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        return genai
    return None


def check_and_increment_quota(user: User, db: Session) -> None:
    """Check quota limits and reset if new month. Raises HTTPException if over quota."""
    from datetime import datetime

    now = datetime.utcnow()
    if user.last_quota_reset is None or (
        now.year > user.last_quota_reset.year or
        now.month > user.last_quota_reset.month
    ):
        user.monthly_analysis_count = "0"
        user.last_quota_reset = now
        db.commit()

    count = int(user.monthly_analysis_count or 0)
    limit = QUOTA_LIMITS.get(user.tier, 3)
    if count >= limit:
        raise HTTPException(
            status_code=402,
            detail=f"Monthly analysis quota exceeded ({count}/{limit}). Upgrade your plan to analyze more contracts."
        )


def increment_quota(user: User, db: Session) -> None:
    count = int(user.monthly_analysis_count or 0)
    user.monthly_analysis_count = str(count + 1)
    db.commit()


async def _process_contract(contract_id: str, task_id: str, db_url: str) -> None:
    """Background task that processes a contract analysis with retry logic."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.agents.contract_agents import RiskAnalysisAgent, SummaryAgent
    from app.config import settings

    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        task = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
        if not task:
            return

        task.status = "running"
        task.updated_at = datetime.utcnow()
        db.commit()

        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        if not contract:
            task.status = "failed"
            task.error = "Contract not found"
            db.commit()
            return

        # Parse document
        try:
            text, file_type = parse_document(contract.file_path)
        except Exception as e:
            task.status = "failed"
            task.error = f"Document parsing failed: {str(e)}"
            contract.status = "failed"
            db.commit()
            return

        # Run AI analysis
        llm = get_llm_client()
        risk_agent = RiskAnalysisAgent(llm_client=llm)
        summary_agent = SummaryAgent(llm_client=llm)

        try:
            analysis_data = await risk_agent.analyze(text)
            summary_text = await summary_agent.summarize(text)
        except Exception as e:
            db.rollback()
            task.status = "failed"
            task.error = f"Analysis failed: {str(e)}"
            contract.status = "failed"
            try:
                db.commit()
            except Exception:
                db.rollback()
            return

        # Store results
        if contract.analysis:
            db.delete(contract.analysis)

        analysis = Analysis(
            contract_id=contract.id,
            overall_risk_score=analysis_data.get("overall_risk_score", 0),
            overall_risk_level=analysis_data.get("overall_risk_level", "low"),
            summary=analysis_data.get("summary", ""),
            executive_summary=summary_text,
            key_terms=analysis_data.get("key_terms", {}),
            parties=analysis_data.get("parties", []),
            effective_date=analysis_data.get("effective_date"),
            expiration_date=analysis_data.get("expiration_date"),
            governing_law=analysis_data.get("governing_law"),
        )
        db.add(analysis)
        db.flush()

        for clause_data in analysis_data.get("clauses", []):
            clause = Clause(
                analysis_id=analysis.id,
                clause_title=clause_data.get("clause_title", ""),
                clause_text=clause_data.get("clause_text", ""),
                risk_level=clause_data.get("risk_level", "low"),
                risk_score=clause_data.get("risk_score", 0),
                explanation=clause_data.get("explanation", ""),
                suggested_revision=clause_data.get("suggested_revision"),
            )
            db.add(clause)

        contract.status = "analyzed"
        contract.contract_type = analysis_data.get("contract_type", "other")
        task.status = "completed"
        db.commit()

        # Audit log for completed analysis
        audit = AuditLog(
            user_id=contract.user_id,
            action="analysis_complete",
            resource_type="contract",
            resource_id=contract_id,
            details={
                "risk_score": analysis_data.get("overall_risk_score", 0),
                "risk_level": analysis_data.get("overall_risk_level", "low"),
                "clause_count": len(analysis_data.get("clauses", [])),
            }
        )
        db.add(audit)
        db.commit()

    except Exception as e:
        db.rollback()
        task.status = "failed"
        task.error = str(e)
        if contract:
            contract.status = "failed"
        try:
            db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()


@router.post("/{contract_id}/analyze")
async def analyze_contract(
    contract_id: str,
    background_tasks: BackgroundTasks,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    contract = db.query(Contract).filter(Contract.id == contract_id, Contract.user_id == user.id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    # Check quota
    check_and_increment_quota(user, db)

    # Delete old analysis if exists
    if contract.analysis:
        db.delete(contract.analysis)

    contract.status = "analyzing"
    db.commit()

    # Create task record
    task = AnalysisTask(
        contract_id=contract_id,
        status="pending",
        attempts="0",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # Log audit
    audit = AuditLog(
        user_id=user.id,
        action="analysis_start",
        resource_type="contract",
        resource_id=contract_id,
        ip_address=request.headers.get("x-forwarded-for", "").split(",")[0].strip(),
        user_agent=request.headers.get("user-agent", ""),
    )
    db.add(audit)
    db.commit()

    # Increment quota now (so they can't spam)
    increment_quota(user, db)

    # Enqueue background task
    from app.config import settings
    background_tasks.add_task(
        _process_contract,
        contract_id,
        task.id,
        settings.DATABASE_URL,
    )

    return {
        "task_id": task.id,
        "status": "pending",
        "message": "Analysis queued. Poll /api/analysis/{contract_id}/task for status."
    }


@router.get("/{contract_id}/task")
async def get_task_status(
    contract_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    contract = db.query(Contract).filter(Contract.id == contract_id, Contract.user_id == user.id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    task = db.query(AnalysisTask).filter(AnalysisTask.contract_id == contract_id).first()
    if not task:
        if contract.status == "analyzed":
            return {
                "id": None,
                "contract_id": contract_id,
                "status": "completed",
                "attempts": "0",
                "error": None,
                "created_at": contract.uploaded_at.isoformat(),
                "updated_at": contract.uploaded_at.isoformat(),
            }
        raise HTTPException(status_code=404, detail="No analysis task found")

    return {
        "id": task.id,
        "contract_id": task.contract_id,
        "status": task.status,
        "attempts": task.attempts,
        "error": task.error,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
    }


@router.get("/{contract_id}/summary")
async def get_summary(
    contract_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    contract = db.query(Contract).filter(Contract.id == contract_id, Contract.user_id == user.id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    if not contract.analysis:
        raise HTTPException(status_code=400, detail="Contract has not been analyzed yet")

    return {
        "summary": contract.analysis.summary,
        "executive_summary": contract.analysis.executive_summary
    }


@router.get("/{contract_id}/clauses")
async def get_clauses(
    contract_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    contract = db.query(Contract).filter(Contract.id == contract_id, Contract.user_id == user.id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    if not contract.analysis:
        raise HTTPException(status_code=400, detail="Contract has not been analyzed yet")

    return {
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
            for cl in contract.analysis.clauses
        ]
    }


@router.patch("/{contract_id}/clauses/{clause_id}/decision")
async def save_clause_decision(
    contract_id: str,
    clause_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    body = await request.json()
    decision = body.get("decision")
    modified_text = body.get("modified_text")

    if decision not in ("accepted", "rejected", "modified"):
        raise HTTPException(status_code=400, detail="decision must be: accepted, rejected, or modified")

    contract = db.query(Contract).filter(Contract.id == contract_id, Contract.user_id == user.id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    clause = db.query(Clause).filter(
        Clause.id == clause_id,
        Clause.analysis_id == contract.analysis.id
    ).first()
    if not clause:
        raise HTTPException(status_code=404, detail="Clause not found")

    existing = db.query(RedlineDecision).filter(
        RedlineDecision.clause_id == clause_id,
        RedlineDecision.user_id == user.id
    ).first()

    if existing:
        existing.decision = decision
        existing.modified_text = modified_text if decision == "modified" else None
        existing.decided_at = datetime.utcnow()
    else:
        decision_record = RedlineDecision(
            clause_id=clause_id,
            user_id=user.id,
            decision=decision,
            modified_text=modified_text if decision == "modified" else None,
        )
        db.add(decision_record)

    db.commit()
    return {"message": "Decision saved"}


@router.get("/{contract_id}/decisions")
async def get_decisions(
    contract_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    contract = db.query(Contract).filter(Contract.id == contract_id, Contract.user_id == user.id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    decisions = db.query(RedlineDecision).filter(RedlineDecision.user_id == user.id).all()
    clause_decisions = {d.clause_id: {"decision": d.decision, "modified_text": d.modified_text} for d in decisions}

    if not contract.analysis:
        return {"decisions": []}

    return {
        "decisions": [
            {
                "clause_id": cl.id,
                "decision": clause_decisions.get(cl.id, {}).get("decision"),
                "modified_text": clause_decisions.get(cl.id, {}).get("modified_text"),
            }
            for cl in contract.analysis.clauses
        ]
    }
