from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text, JSON, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime
import uuid
import enum


class RiskLevelEnum(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    tier = Column(String, default="free")  # free, pro, enterprise
    monthly_analysis_count = Column(String, default="0")
    last_quota_reset = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    contracts = relationship("Contract", back_populates="user", cascade="all, delete-orphan")


class Contract(Base):
    __tablename__ = "contracts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    status = Column(String, default="uploaded")
    contract_type = Column(String, default="other")
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="contracts")
    analysis = relationship("Analysis", back_populates="contract", uselist=False, cascade="all, delete-orphan")


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    contract_id = Column(String, ForeignKey("contracts.id"), nullable=False, unique=True)
    overall_risk_score = Column(Float, nullable=False)
    overall_risk_level = Column(String, nullable=False)
    summary = Column(Text)
    executive_summary = Column(Text)
    key_terms = Column(JSON)
    parties = Column(JSON)
    effective_date = Column(String)
    expiration_date = Column(String)
    governing_law = Column(String)
    analyzed_at = Column(DateTime, default=datetime.utcnow)

    contract = relationship("Contract", back_populates="analysis")
    clauses = relationship("Clause", back_populates="analysis", cascade="all, delete-orphan")


class Clause(Base):
    __tablename__ = "clauses"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    analysis_id = Column(String, ForeignKey("analyses.id"), nullable=False, index=True)
    clause_title = Column(String, nullable=False)
    clause_text = Column(Text, nullable=False)
    risk_level = Column(String, nullable=False)
    risk_score = Column(Float, nullable=False)
    explanation = Column(Text)
    suggested_revision = Column(Text)

    analysis = relationship("Analysis", back_populates="clauses")
    decisions = relationship("RedlineDecision", back_populates="clause", cascade="all, delete-orphan")


class RedlineDecision(Base):
    __tablename__ = "redline_decisions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    clause_id = Column(String, ForeignKey("clauses.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    decision = Column(String, nullable=False)  # "accepted", "rejected", "modified"
    modified_text = Column(Text, nullable=True)
    decided_at = Column(DateTime, default=datetime.utcnow)

    clause = relationship("Clause", back_populates="decisions")
    user = relationship("User")


class AnalysisTask(Base):
    __tablename__ = "analysis_tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    contract_id = Column(String, ForeignKey("contracts.id"), nullable=False, unique=True, index=True)
    status = Column(String, default="pending")  # pending, running, completed, failed
    attempts = Column(String, default="0")
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    contract = relationship("Contract")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    action = Column(String, nullable=False)  # login, logout, register, contract_upload, contract_delete, analysis_start, analysis_complete
    resource_type = Column(String, nullable=True)  # contract, user
    resource_id = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    details = Column(JSON, nullable=True)

    user = relationship("User")
