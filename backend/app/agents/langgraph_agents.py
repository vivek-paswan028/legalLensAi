import logging
import re
from typing import TypedDict, List, Optional, Dict, Any
from pydantic import BaseModel, Field

log = logging.getLogger("legallens")

# ── 1. LangGraph State Memory Schema ──────────────────────────────────────────

class ContractState(TypedDict):
    contract_text: str
    gemini_api_key: Optional[str]
    overall_risk_score: float
    overall_risk_level: str
    summary: str
    executive_summary: str
    contract_type: str
    parties: List[str]
    effective_date: Optional[str]
    expiration_date: Optional[str]
    governing_law: Optional[str]
    key_terms: Dict[str, str]
    clauses: List[Dict[str, Any]]
    error: Optional[str]
    use_fallback: bool


# ── 2. Pydantic Structured Output Schemas for Gemini ──────────────────────────

class ClauseSchema(BaseModel):
    clause_title: str = Field(description="Descriptive title of clause")
    clause_text: str = Field(description="Exact snippet text from contract")
    risk_level: str = Field(description="low, medium, or high")
    risk_score: float = Field(description="Risk score between 0.0 and 1.0")
    explanation: str = Field(description="Plain English risk explanation")
    suggested_revision: Optional[str] = Field(default=None, description="Suggested safer language for medium or high risk clauses")


class RiskAnalysisSchema(BaseModel):
    overall_risk_score: float = Field(description="Average risk score between 0.0 and 1.0")
    overall_risk_level: str = Field(description="low, medium, or high")
    summary: str = Field(description="Brief executive summary")
    contract_type: str = Field(description="nda, saas_agreement, employment, msa, sow, lease, or other")
    parties: List[str] = Field(default_factory=list, description="Named parties")
    effective_date: Optional[str] = Field(default=None, description="Start date")
    expiration_date: Optional[str] = Field(default=None, description="End date")
    governing_law: Optional[str] = Field(default=None, description="Governing law/jurisdiction")
    key_terms: Dict[str, str] = Field(default_factory=dict, description="Key terms map")
    clauses: List[ClauseSchema] = Field(default_factory=list, description="Analyzed clauses")


# ── 3. Rule-Based Fallback Engine ─────────────────────────────────────────────

def run_rule_based_fallback(contract_text: str) -> Dict[str, Any]:
    text_lower = contract_text.lower()
    clauses = []
    risk_scores = []

    patterns = [
        {
            "keyword": "indemnif",
            "title": "Indemnification Clause",
            "risk": "high",
            "score": 0.85,
            "explanation": "Broad indemnification clause may expose you to unlimited liability for third-party claims.",
            "revision": "Each party shall indemnify the other only for direct damages arising from its own negligence or willful misconduct, subject to the liability cap set forth herein."
        },
        {
            "keyword": "non-compete",
            "title": "Non-Compete Restriction",
            "risk": "high",
            "score": 0.9,
            "explanation": "Non-compete clauses may restrict your ability to work in your field after contract termination.",
            "revision": None
        },
        {
            "keyword": "auto-renew",
            "title": "Auto-Renewal Terms",
            "risk": "medium",
            "score": 0.6,
            "explanation": "Contract automatically renews — you must actively cancel or provide written notice to terminate.",
            "revision": "This Agreement shall not automatically renew. Any renewal requires mutual written consent of both parties at least 30 days before expiration."
        },
        {
            "keyword": "intellectual property",
            "title": "IP Assignment Clause",
            "risk": "high",
            "score": 0.8,
            "explanation": "This clause may transfer ownership of your pre-existing intellectual property to the other party.",
            "revision": "Work Product IP shall be owned by the Client. Pre-existing IP shall remain the property of the originating party, with a non-exclusive license granted."
        },
        {
            "keyword": "confidential",
            "title": "Confidentiality Obligations",
            "risk": "low",
            "score": 0.2,
            "explanation": "Standard confidentiality clause with reasonable terms and duration.",
            "revision": None
        },
        {
            "keyword": "terminat",
            "title": "Termination Rights",
            "risk": "medium",
            "score": 0.5,
            "explanation": "Termination rights appear one-sided. Review notice period carefully.",
            "revision": "Either party may terminate this Agreement with 30 days' written notice."
        },
        {
            "keyword": "liability",
            "title": "Limitation of Liability",
            "risk": "medium",
            "score": 0.55,
            "explanation": "Liability cap is set, but check for excluded damage categories.",
            "revision": None
        },
        {
            "keyword": "governing law",
            "title": "Governing Law & Jurisdiction",
            "risk": "low",
            "score": 0.15,
            "explanation": "Standard governing law clause.",
            "revision": None
        },
    ]

    for p in patterns:
        if p["keyword"] in text_lower:
            start = text_lower.find(p["keyword"])
            snippet = contract_text[max(0, start - 40): min(len(contract_text), start + 200)].strip()
            clauses.append({
                "clause_title": p["title"],
                "clause_text": f"...{snippet}...",
                "risk_level": p["risk"],
                "risk_score": p["score"],
                "explanation": p["explanation"],
                "suggested_revision": p["revision"],
            })
            risk_scores.append(p["score"])

    if not clauses:
        clauses.append({
            "clause_title": "General Terms",
            "clause_text": contract_text[:200] + "...",
            "risk_level": "low",
            "risk_score": 0.2,
            "explanation": "No high-risk keywords detected in initial scan.",
            "suggested_revision": None,
        })
        risk_scores.append(0.2)

    overall_score = sum(risk_scores) / len(risk_scores)
    overall_level = "low" if overall_score < 0.4 else "medium" if overall_score < 0.7 else "high"

    word_count = len(contract_text.split())
    executive_summary = f"""## Executive Summary (LangGraph Fallback Engine)

**Contract Type:** General Agreement
**Word Count:** {word_count} words

### Overview
Conducted legal clause scan across {len(clauses)} key sections. Overall contract risk profile is rated **{overall_level.upper()}** ({round(overall_score * 100)}%).

### Primary Concerns
- Identified key clauses governing liability, termination, and intellectual property.
- Review highlighted medium and high risk sections prior to signature.
"""

    return {
        "overall_risk_score": round(overall_score, 2),
        "overall_risk_level": overall_level,
        "summary": f"Analyzed {len(clauses)} clauses. Overall risk score: {round(overall_score, 2)} ({overall_level}).",
        "executive_summary": executive_summary,
        "contract_type": "other",
        "parties": ["Party A", "Party B"],
        "effective_date": None,
        "expiration_date": None,
        "governing_law": None,
        "key_terms": {
            "payment_terms": "As specified in contract",
            "termination_rights": "Review termination section",
            "renewal_terms": "Check for auto-renewal provisions",
            "confidentiality_scope": "Standard confidentiality terms apply",
            "liability_cap": "Review limitation of liability section",
        },
        "clauses": clauses,
    }


# ── 4. LangGraph Node Definitions ──────────────────────────────────────────────

async def risk_analysis_node(state: ContractState) -> Dict[str, Any]:
    """LangGraph Node: Structured Risk Analysis using ChatGoogleGenerativeAI (Gemini)."""
    api_key = state.get("gemini_api_key")
    contract_text = state["contract_text"]

    if not api_key:
        log.info("langgraph.risk_analysis: No Gemini key provided, routing to fallback node")
        return {"use_fallback": True}

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=api_key,
            temperature=0.1,
        )

        structured_llm = llm.with_structured_output(RiskAnalysisSchema)

        prompt = f"""You are an expert legal contract analyst. Analyze this contract text and return detailed risk assessments:

CONTRACT TEXT:
{contract_text[:15000]}
"""

        result: RiskAnalysisSchema = await structured_llm.ainvoke(prompt)

        return {
            "overall_risk_score": result.overall_risk_score,
            "overall_risk_level": result.overall_risk_level,
            "summary": result.summary,
            "contract_type": result.contract_type,
            "parties": result.parties,
            "effective_date": result.effective_date,
            "expiration_date": result.expiration_date,
            "governing_law": result.governing_law,
            "key_terms": result.key_terms,
            "clauses": [c.model_dump() for c in result.clauses],
            "use_fallback": False,
        }

    except Exception as exc:
        log.warning(f"langgraph.risk_analysis_failed: {exc}. Routing to fallback node.")
        return {"use_fallback": True}


async def summary_node(state: ContractState) -> Dict[str, Any]:
    """LangGraph Node: Generates Executive Summary using ChatGoogleGenerativeAI."""
    if state.get("use_fallback"):
        return {}

    api_key = state.get("gemini_api_key")
    contract_text = state["contract_text"]

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=api_key,
            temperature=0.2,
        )

        prompt = f"""You are an executive legal advisor. Write a 1-page structured Executive Summary in Markdown:

Include:
1. **Overview**: Purpose and contract category
2. **Parties**: Parties involved
3. **Key Obligations & Terms**: Payment, duration, termination
4. **Top Concerns**: 3 main risks

CONTRACT TEXT:
{contract_text[:15000]}
"""

        res = await llm.ainvoke(prompt)
        return {"executive_summary": str(res.content)}

    except Exception as exc:
        log.warning(f"langgraph.summary_node_failed: {exc}")
        word_count = len(contract_text.split())
        return {
            "executive_summary": f"## Executive Summary\n\nWord count: {word_count}\n\nReview flagged clauses for risk management."
        }


async def redline_node(state: ContractState) -> Dict[str, Any]:
    """LangGraph Node: Refines high/medium risk clause suggested revisions."""
    if state.get("use_fallback"):
        return {}

    clauses = state.get("clauses", [])
    api_key = state.get("gemini_api_key")

    if not api_key:
        return {}

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=api_key,
            temperature=0.2,
        )

        updated_clauses = []
        for cl in clauses:
            if cl.get("risk_level") in ("medium", "high") and not cl.get("suggested_revision"):
                prompt = f"""Revise this legal clause to protect the reviewing party while preserving business intent:

Clause: {cl.get('clause_text')}
Risk: {cl.get('explanation')}

Return ONLY the revised clause text:"""
                res = await llm.ainvoke(prompt)
                cl["suggested_revision"] = str(res.content).strip()
            updated_clauses.append(cl)

        return {"clauses": updated_clauses}

    except Exception as exc:
        log.warning(f"langgraph.redline_node_failed: {exc}")
        return {}


async def fallback_node(state: ContractState) -> Dict[str, Any]:
    """LangGraph Node: Deterministic Fallback Execution."""
    log.info("langgraph.fallback_node: Executing rule-based analysis node")
    result = run_rule_based_fallback(state["contract_text"])
    return result


# ── 5. LangGraph Assembly & Compilation ───────────────────────────────────────

def build_legal_contract_graph():
    """Build and compile the LangGraph StateGraph for LegalLens AI."""
    from langgraph.graph import StateGraph, END

    builder = StateGraph(ContractState)

    builder.add_node("risk_analysis", risk_analysis_node)
    builder.add_node("summary", summary_node)
    builder.add_node("redline", redline_node)
    builder.add_node("fallback", fallback_node)

    builder.set_entry_point("risk_analysis")

    def route_after_risk(state: ContractState) -> str:
        if state.get("use_fallback"):
            return "fallback"
        return "summary"

    builder.add_conditional_edges(
        "risk_analysis",
        route_after_risk,
        {
            "fallback": "fallback",
            "summary": "summary",
        }
    )

    builder.add_edge("summary", "redline")
    builder.add_edge("redline", END)
    builder.add_edge("fallback", END)

    return builder.compile()


# Compile graph singleton
legal_contract_graph = build_legal_contract_graph()


async def run_langgraph_analysis(contract_text: str, gemini_api_key: Optional[str] = None) -> Dict[str, Any]:
    """Runner entrypoint to invoke the LangGraph pipeline."""
    initial_state: ContractState = {
        "contract_text": contract_text,
        "gemini_api_key": gemini_api_key,
        "overall_risk_score": 0.0,
        "overall_risk_level": "low",
        "summary": "",
        "executive_summary": "",
        "contract_type": "other",
        "parties": [],
        "effective_date": None,
        "expiration_date": None,
        "governing_law": None,
        "key_terms": {},
        "clauses": [],
        "error": None,
        "use_fallback": False,
    }

    final_state = await legal_contract_graph.ainvoke(initial_state)

    return {
        "overall_risk_score": final_state.get("overall_risk_score", 0.0),
        "overall_risk_level": final_state.get("overall_risk_level", "low"),
        "summary": final_state.get("summary", ""),
        "executive_summary": final_state.get("executive_summary", ""),
        "contract_type": final_state.get("contract_type", "other"),
        "parties": final_state.get("parties", []),
        "effective_date": final_state.get("effective_date"),
        "expiration_date": final_state.get("expiration_date"),
        "governing_law": final_state.get("governing_law"),
        "key_terms": final_state.get("key_terms", {}),
        "clauses": final_state.get("clauses", []),
    }
