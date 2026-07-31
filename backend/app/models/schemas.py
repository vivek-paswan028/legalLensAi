from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ContractType(str, Enum):
    NDA = "nda"
    SAAS_AGREEMENT = "saas_agreement"
    EMPLOYMENT = "employment"
    MSA = "msa"
    SOW = "sow"
    LEASE = "lease"
    OTHER = "other"


class ClauseAnalysis(BaseModel):
    clause_title: str
    clause_text: str
    risk_level: RiskLevel
    risk_score: float
    explanation: str
    suggested_revision: Optional[str] = None


class ContractUploadResponse(BaseModel):
    id: str
    filename: str
    status: str
    uploaded_at: datetime


class ContractAnalysisResponse(BaseModel):
    contract_id: str
    overall_risk_score: float
    overall_risk_level: RiskLevel
    summary: str
    key_terms: dict
    clauses: List[ClauseAnalysis]
    parties: List[str]
    effective_date: Optional[str] = None
    expiration_date: Optional[str] = None
    governing_law: Optional[str] = None


class ContractSummary(BaseModel):
    id: str
    filename: str
    contract_type: ContractType
    overall_risk_level: RiskLevel
    overall_risk_score: float
    parties: List[str]
    uploaded_at: datetime
    analyzed_at: Optional[datetime] = None
