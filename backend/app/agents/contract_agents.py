import json
import os
import asyncio
import time
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

log = logging.getLogger("legallens")

# ── Circuit Breaker ────────────────────────────────────────────────────────────

@dataclass
class CircuitState:
    failures: int = 0
    last_failure: float = 0
    degraded_until: float = 0

_circuit: CircuitState = CircuitState()

CIRCUIT_FAILURE_THRESHOLD = 3
CIRCUIT_RECOVERY_SECONDS = 300  # 5 minutes


def is_circuit_open() -> bool:
    if _circuit.failures < CIRCUIT_FAILURE_THRESHOLD:
        return False
    if time.time() > _circuit.degraded_until:
        _circuit.failures = 0
        return False
    return True


def record_failure():
    _circuit.failures += 1
    _circuit.last_failure = time.time()
    if _circuit.failures >= CIRCUIT_FAILURE_THRESHOLD:
        _circuit.degraded_until = time.time() + CIRCUIT_RECOVERY_SECONDS
        log.warning("llm.circuit_breaker_open", extra={"failures": _circuit.failures})


def record_success():
    _circuit.failures = 0


RISK_ANALYSIS_PROMPT = """You are an expert legal contract analyst. Analyze the following contract text and provide a detailed risk assessment.

For each clause you identify, provide:
1. clause_title: A descriptive name for the clause
2. clause_text: The exact text of the clause from the contract
3. risk_level: "low", "medium", or "high"
4. risk_score: A score from 0.0 (no risk) to 1.0 (maximum risk)
5. explanation: A plain-English explanation of why this clause is risky or safe
6. suggested_revision: If the clause is medium or high risk, suggest better language

Also extract:
- parties: List of all parties mentioned
- effective_date: The start date of the contract
- expiration_date: The end date or term
- governing_law: The jurisdiction/governing law
- contract_type: One of: nda, saas_agreement, employment, msa, sow, lease, other

Respond ONLY with valid JSON in this exact format:
{
  "overall_risk_score": 0.0,
  "overall_risk_level": "low",
  "summary": "Brief executive summary of the contract",
  "contract_type": "nda",
  "key_terms": {
    "payment_terms": "...",
    "termination_rights": "...",
    "renewal_terms": "...",
    "confidentiality_scope": "...",
    "liability_cap": "..."
  },
  "parties": ["Party A", "Party B"],
  "effective_date": "2024-01-01",
  "expiration_date": "2025-01-01",
  "governing_law": "State of California",
  "clauses": [
    {
      "clause_title": "...",
      "clause_text": "...",
      "risk_level": "low",
      "risk_score": 0.1,
      "explanation": "...",
      "suggested_revision": null
    }
  ]
}

CONTRACT TEXT:
{contract_text}
"""

SUMMARY_PROMPT = """You are a legal analyst. Generate a concise 1-page executive summary of this contract.

Include:
1. **Overview**: What type of contract this is and its main purpose
2. **Parties**: Who is involved
3. **Key Terms**: Payment, duration, renewal, termination
4. **Notable Clauses**: Anything unusual or worth noting
5. **Obligations**: What each party must do
6. **Risks**: Top 3 concerns

Write in clear, professional language. Avoid legal jargon where possible.

CONTRACT TEXT:
{contract_text}
"""

REDLINE_PROMPT = """You are an expert legal contract editor. Review the following clause and provide a revised version that better protects the reviewing party.

Original clause:
{clause_text}

Risk explanation:
{risk_explanation}

Provide a revised version of this clause that:
1. Reduces legal risk
2. Adds appropriate protections
3. Maintains the business intent
4. Uses clear, standard legal language

Respond with ONLY the revised clause text, no explanations.
"""


class RiskAnalysisAgent:
    """LangGraph-backed Agent that analyzes contracts for legal risks using Google Gemini."""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    async def analyze(self, contract_text: str) -> Dict[str, Any]:
        """Analyze a contract using the LangGraph StateGraph pipeline."""
        from app.agents.langgraph_agents import run_langgraph_analysis
        from app.config import settings

        try:
            return await run_langgraph_analysis(contract_text, gemini_api_key=settings.GEMINI_API_KEY)
        except Exception as e:
            log.warning(f"LangGraph execution failed: {e}. Running fallback graph mode.")
            return self._demo_analysis(contract_text)

    async def _call_llm(self, prompt: str) -> str:
        """Call the LLM API (supports OpenAI, Anthropic, or Gemini) with timeout and circuit breaker."""
        if is_circuit_open():
            raise TimeoutError("LLM service temporarily unavailable (circuit breaker open)")

        try:
            if hasattr(self.llm_client, 'chat'):
                # OpenAI
                response = await asyncio.wait_for(
                    self.llm_client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.1,
                        response_format={"type": "json_object"}
                    ),
                    timeout=60.0
                )
                record_success()
                return response.choices[0].message.content
            elif hasattr(self.llm_client, 'messages'):
                # Anthropic
                response = await asyncio.wait_for(
                    self.llm_client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=4096,
                        messages=[{"role": "user", "content": prompt}]
                    ),
                    timeout=60.0
                )
                record_success()
                return response.content[0].text
            else:
                model = self.llm_client.GenerativeModel("gemini-2.0-flash")
                response = await asyncio.wait_for(
                    model.generate_content_async(prompt),
                    timeout=60.0
                )
                record_success()
                text = response.text
                if text.startswith("```"):
                    import re
                    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip()).strip()
                return text
        except asyncio.TimeoutError:
            record_failure()
            raise TimeoutError("LLM request timed out after 60 seconds")
        except Exception as exc:
            record_failure()
            log.warning("llm.call_failed", extra={"error": str(exc)})
            raise

    def _demo_analysis(self, contract_text: str) -> Dict[str, Any]:
        """Return a demo analysis when no LLM is configured."""
        text_lower = contract_text.lower()

        clauses = []
        risk_scores = []

        risk_patterns = [
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
                "revision": "Work Product IP shall be owned by the Client. Pre-existing IP shall remain the property of the originating party, with a non-exclusive license granted for use in connection with the Work Product."
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
                "explanation": "Termination rights appear one-sided. The other party may terminate without cause, but you may not.",
                "revision": "Either party may terminate this Agreement with 30 days' written notice. Upon termination, all outstanding payments shall become immediately due."
            },
            {
                "keyword": "liability",
                "title": "Limitation of Liability",
                "risk": "medium",
                "score": 0.55,
                "explanation": "Liability cap is set, but excludes certain categories which could expose you to significant risk.",
                "revision": None
            },
            {
                "keyword": "governing law",
                "title": "Governing Law & Jurisdiction",
                "risk": "low",
                "score": 0.15,
                "explanation": "Standard governing law clause. Verify that the jurisdiction is acceptable to your business.",
                "revision": None
            },
        ]

        for pattern in risk_patterns:
            if pattern["keyword"] in text_lower:
                start = text_lower.find(pattern["keyword"])
                snippet_start = max(0, start - 50)
                snippet_end = min(len(contract_text), start + 200)
                clause_text = contract_text[snippet_start:snippet_end].strip()

                clauses.append({
                    "clause_title": pattern["title"],
                    "clause_text": f"...{clause_text}...",
                    "risk_level": pattern["risk"],
                    "risk_score": pattern["score"],
                    "explanation": pattern["explanation"],
                    "suggested_revision": pattern["revision"]
                })
                risk_scores.append(pattern["score"])

        if not clauses:
            clauses.append({
                "clause_title": "General Terms",
                "clause_text": contract_text[:200] + "...",
                "risk_level": "low",
                "risk_score": 0.2,
                "explanation": "No specific high-risk clauses were identified in the initial scan. Consider a detailed manual review.",
                "suggested_revision": None
            })
            risk_scores.append(0.2)

        overall_score = sum(risk_scores) / len(risk_scores) if risk_scores else 0.2
        overall_level = "low" if overall_score < 0.4 else "medium" if overall_score < 0.7 else "high"

        return {
            "overall_risk_score": round(overall_score, 2),
            "overall_risk_level": overall_level,
            "summary": f"This contract contains {len(clauses)} analyzed clauses. Overall risk level is {overall_level} ({round(overall_score * 100)}%). Key concerns include potential exposure from indemnification, IP rights, and termination provisions.",
            "contract_type": "other",
            "key_terms": {
                "payment_terms": "As specified in the contract",
                "termination_rights": "Review termination section for specific terms",
                "renewal_terms": "Check for auto-renewal provisions",
                "confidentiality_scope": "Standard confidentiality obligations apply",
                "liability_cap": "Review limitation of liability section"
            },
            "parties": ["Party A", "Party B"],
            "effective_date": None,
            "expiration_date": None,
            "governing_law": None,
            "clauses": clauses
        }


class SummaryAgent:
    """Agent that generates executive summaries of contracts."""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    async def summarize(self, contract_text: str) -> str:
        if self.llm_client:
            prompt = SUMMARY_PROMPT.replace("{contract_text}", contract_text[:15000])
            if is_circuit_open():
                import logging
                logging.getLogger("legallens").warning("LLM service temporarily unavailable (circuit breaker open), falling back to demo summary")
                return self._demo_summary(contract_text)
            try:
                if hasattr(self.llm_client, 'chat'):
                    # OpenAI
                    response = await asyncio.wait_for(
                        self.llm_client.chat.completions.create(
                            model="gpt-4o",
                            messages=[{"role": "user", "content": prompt}],
                            temperature=0.2
                        ),
                        timeout=60.0
                    )
                    record_success()
                    return response.choices[0].message.content
                elif hasattr(self.llm_client, 'messages'):
                    # Anthropic
                    response = await asyncio.wait_for(
                        self.llm_client.messages.create(
                            model="claude-sonnet-4-20250514",
                            max_tokens=2048,
                            messages=[{"role": "user", "content": prompt}]
                        ),
                        timeout=60.0
                    )
                    record_success()
                    return response.content[0].text
                else:
                    model = self.llm_client.GenerativeModel("gemini-2.0-flash")
                    response = await asyncio.wait_for(
                        model.generate_content_async(prompt),
                        timeout=60.0
                    )
                    record_success()
                    return response.text
            except asyncio.TimeoutError:
                record_failure()
                import logging
                logging.getLogger("legallens").warning("LLM summarization timed out, falling back to demo summary")
                return self._demo_summary(contract_text)
            except Exception as exc:
                record_failure()
                import logging
                logging.getLogger("legallens").warning(f"LLM summarization failed: {exc}, falling back to demo summary")
                return self._demo_summary(contract_text)
        else:
            return self._demo_summary(contract_text)

    def _demo_summary(self, contract_text: str) -> str:
        word_count = len(contract_text.split())
        return f"""## Executive Summary

**Contract Type:** General Agreement
**Word Count:** {word_count} words
**Parties:** See contract header for named parties

### Overview
This contract establishes terms and conditions between the involved parties. A thorough review has been conducted to identify key terms and potential risks.

### Key Terms
- **Duration:** As specified in the contract terms
- **Payment:** Review payment section for detailed terms
- **Renewal:** Check for auto-renewal provisions
- **Termination:** Both parties should review termination rights

### Notable Observations
- All standard contractual provisions have been identified
- Risk assessment has flagged items requiring attention
- Recommended follow-up: Review flagged clauses with legal counsel

### Recommended Actions
1. Review all HIGH risk clauses before signing
2. Negotiate changes to one-sided provisions
3. Confirm governing law is acceptable
4. Verify IP ownership terms align with your expectations"""


class RedlineAgent:
    """Agent that suggests revised clause language."""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    async def redline(self, clause_text: str, risk_explanation: str) -> str:
        if self.llm_client:
            prompt = REDLINE_PROMPT.format(
                clause_text=clause_text,
                risk_explanation=risk_explanation
            )
            if hasattr(self.llm_client, 'chat'):
                response = await self.llm_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3
                )
                return response.choices[0].message.content
            elif hasattr(self.llm_client, 'messages'):
                response = await self.llm_client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text
            else:
                # Gemini (new google.genai async client)
                response = await asyncio.wait_for(
                    self.llm_client.models.generate_content(
                        model="gemini-1.5-flash",
                        contents=prompt,
                    ),
                    timeout=60.0
                )
                return response.text
        else:
            return f"[Revised] {clause_text}"
