from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.utils.logging import logger
import os
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import HumanMessage, SystemMessage
from backend.config import settings

# ================= Structured Pydantic Output Models =================

class RecommendationOutput(BaseModel):
    decision: str = Field(..., description="APPROVE, REFER, DECLINE")
    reasons: List[str] = Field(default_factory=list, description="Reasons justifying the underwriting decision")
    policy_citations: List[str] = Field(default_factory=list, description="Citations of matching policy clauses")
    confidence: float = Field(..., description="Confidence score (0.0 to 1.0) based on credit profile strength")


# ================= Core Implementations =================

class RecommendationEngine:
    @staticmethod
    def run_multi_agent_review_loop(
        validation_result: Dict[str, Any],
        score_result: Dict[str, Any],
        retrieved_policy: Dict[str, Any]
    ) -> Optional[RecommendationOutput]:
        """
        Executes a Multi-Agent Debate Loop simulating Document, Risk, and Compliance Auditors,
        with an Underwriting Supervisor Agent generating the final consensus decision.
        """
        # 1. Check if mock key is configured. If so, return None to fallback to programmatic rules.
        is_mock_key = (
            not settings.OPENAI_API_KEY 
            or settings.OPENAI_API_KEY == "mock-key-for-development"
            or not settings.OPENAI_API_KEY.startswith("sk-")
        )
        if is_mock_key:
            return None

        try:
            llm = ChatOpenAI(
                openai_api_key=settings.OPENAI_API_KEY,
                openai_api_base=settings.OPENAI_API_BASE,
                model_name=settings.OPENAI_MODEL,
                temperature=0.0,
                max_retries=2
            )
        except Exception as e:
            logger.error("Failed to initialize ChatOpenAI for recommendation engine: %s", str(e))
            return None

        # Build prompt inputs
        val_summary = {
            "is_complete": validation_result.get("is_complete"),
            "missing_documents": validation_result.get("missing_documents"),
            "consistency_discrepancies": validation_result.get("consistency", {}).get("discrepancies")
        }
        score_summary = {
            "credit_score": score_result.get("credit_score"),
            "has_active_defaults": score_result.get("has_active_defaults"),
            "dti_ratio": score_result.get("dti_ratio"),
            "risk_rating": score_result.get("risk_rating")
        }
        policy_matches = []
        for m in retrieved_policy.get("matches", []):
            policy_matches.append({
                "parameter": m.get("parameter"),
                "clause_cited": m.get("clause_cited"),
                "status": m.get("status"),
                "reasoning": m.get("reasoning")
            })

        prompt_text = (
            "You are an AI Credit Underwriting Committee overseeing a loan application.\n"
            "The committee consists of the following agent personas:\n"
            "1. Document Auditor Agent: Focuses on verification, completeness, and consistency of government IDs (PAN, Aadhaar) and financial proofs.\n"
            "2. Financial Risk Auditor Agent: Focuses on credit scores, DTI ratios, and liability parameters.\n"
            "3. Compliance Auditor Agent: Focuses on RAG-retrieved policies, fairness indicators, and regulatory guidelines.\n"
            "4. Underwriting Supervisor Agent: Facilitates the review, debates conflicts, resolves differences, and renders the final recommendation.\n\n"
            "INPUT DATA SUMMARY:\n"
            f"- Document Validation: {json.dumps(val_summary, indent=2)}\n"
            f"- Credit Scoring: {json.dumps(score_summary, indent=2)}\n"
            f"- Policy Matches: {json.dumps(policy_matches, indent=2)}\n\n"
            "INSTRUCTIONS FOR DEBATE LOOP:\n"
            "1. Document Auditor Agent: Audit documents, identify mismatches/gaps, cast a vote (APPROVE, REFER, DECLINE), and explain your audit logic.\n"
            "2. Financial Risk Auditor Agent: Audit credit scores, liabilities, DTI ratio, and risk points, cast a vote (APPROVE, REFER, DECLINE), and explain.\n"
            "3. Compliance Auditor Agent: Check guidelines, fairness, and exceptions, cast a vote (APPROVE, REFER, DECLINE), and explain.\n"
            "4. Underwriting Supervisor Agent: Facilitate the review, weigh conflicting views (e.g. if documents have minor mismatches but credit is excellent, or if DTI is borderline), resolve debates, and output the final committee decision, confidence, and combined reasoning.\n\n"
            "Your output MUST be a JSON object matching the following structure:\n"
            "{\n"
            "  \"debate_transcript\": {\n"
            "    \"doc_auditor\": { \"vote\": \"APPROVE/REFER/DECLINE\", \"reasoning\": \"...\" },\n"
            "    \"risk_auditor\": { \"vote\": \"APPROVE/REFER/DECLINE\", \"reasoning\": \"...\" },\n"
            "    \"compliance_auditor\": { \"vote\": \"APPROVE/REFER/DECLINE\", \"reasoning\": \"...\" }\n"
            "  },\n"
            "  \"supervisor_decision\": {\n"
            "    \"decision\": \"APPROVE / REFER / DECLINE\",\n"
            "    \"reasons\": [\"Why approved/declined/referred...\", \"mitigating factor...\"],\n"
            "    \"policy_citations\": [\"CP-CS-01\", \"CP-DTI-01\"],\n"
            "    \"confidence\": 0.85\n"
            "  }\n"
            "}"
        )

        try:
            logger.info("Invoking Multi-Agent Underwriting Committee Debate Loop...")
            messages = [
                SystemMessage(content="You are a professional credit underwriting agentic system running in JSON mode."),
                HumanMessage(content=prompt_text)
            ]
            response = llm.invoke(messages)
            
            # Clean content if enclosed in markdown code blocks
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            parsed = json.loads(content)
            
            # Format the reasons list to include the debate transcript first for the underwriter's view
            transcript = parsed.get("debate_transcript", {})
            supervisor = parsed.get("supervisor_decision", {})
            
            formatted_reasons = []
            formatted_reasons.append("=== COMMITTEE DEBATE TRANSCRIPT ===")
            formatted_reasons.append(f"[Document Auditor ({transcript.get('doc_auditor', {}).get('vote')})]: {transcript.get('doc_auditor', {}).get('reasoning')}")
            formatted_reasons.append(f"[Financial Risk Auditor ({transcript.get('risk_auditor', {}).get('vote')})]: {transcript.get('risk_auditor', {}).get('reasoning')}")
            formatted_reasons.append(f"[Compliance Auditor ({transcript.get('compliance_auditor', {}).get('vote')})]: {transcript.get('compliance_auditor', {}).get('reasoning')}")
            formatted_reasons.append("=== SUPERVISOR FINAL RECOMMENDATION ===")
            for r in supervisor.get("reasons", []):
                formatted_reasons.append(r)
                
            return RecommendationOutput(
                decision=supervisor.get("decision", "REFER").upper(),
                reasons=formatted_reasons,
                policy_citations=supervisor.get("policy_citations", ["General Policy"]),
                confidence=float(supervisor.get("confidence", 0.75))
            )
        except Exception as e:
            logger.warning("Multi-Agent Review Loop failed: %s. Falling back to rule-based engine.", str(e))
            return None

    @staticmethod
    def generate_recommendation(
        validation_result: Dict[str, Any],
        score_result: Dict[str, Any],
        retrieved_policy: Dict[str, Any]
    ) -> RecommendationOutput:
        """
        Synthesizes validation results, credit scores, and RAG policy decisions 
        to produce a structured recommendation with citations and confidence metrics.
        """
        logger.info("Generating lending recommendation...")
        
        # Try Multi-Agent Review Loop first
        reco = RecommendationEngine.run_multi_agent_review_loop(
            validation_result=validation_result,
            score_result=score_result,
            retrieved_policy=retrieved_policy
        )
        
        if not reco:
            # Programmatic Rule Fallback
            decision = "APPROVE"
            reasons = []
            citations = []
            
            # 1. Evaluate Document Completeness & Consistency
            is_complete = validation_result.get("is_complete", True)
            missing_docs = validation_result.get("missing_documents", [])
            consistency = validation_result.get("consistency", {})
            is_consistent = consistency.get("is_consistent", True)
            discrepancies = consistency.get("discrepancies", [])
            
            if not is_complete:
                decision = "DECLINE"
                reasons.append(f"Incomplete documentation. Missing: {', '.join(missing_docs)}")
                citations.append("FP-DOC-01")
                
            if not is_consistent:
                if decision != "DECLINE":
                    decision = "REFER"
                reasons.append(f"Document discrepancies detected: {', '.join(discrepancies)}")
                citations.append("FP-DOC-02")

            # 2. Evaluate Credit Bureau & Debt checks
            credit_score = score_result.get("credit_score", 700)
            has_defaults = score_result.get("has_active_defaults", False)
            dti_ratio = score_result.get("dti_ratio", 0.0)
            
            if has_defaults:
                decision = "DECLINE"
                reasons.append("Active defaults or write-offs reported in the last 12 months.")
                citations.append("CP-CS-02")
                
            if credit_score < 650:
                decision = "DECLINE"
                reasons.append(f"Bureau credit score of {credit_score} is below minimum approval threshold of 650.")
                citations.append("CP-CS-01")
            elif credit_score < 750:
                if decision != "DECLINE":
                    decision = "REFER"
                reasons.append(f"Credit score of {credit_score} is in the referral range (650-749).")
                citations.append("CP-CS-01")
                
            if dti_ratio > 0.45:
                decision = "DECLINE"
                reasons.append(f"Debt-to-Income (DTI) ratio of {dti_ratio:.2%} exceeds maximum allowed 45%.")
                citations.append("CP-DTI-01")
            elif dti_ratio > 0.40:
                if decision != "DECLINE":
                    decision = "REFER"
                reasons.append(f"DTI ratio of {dti_ratio:.2%} is in borderline range (40%-45%).")
                citations.append("CP-DTI-01")

            # 3. Incorporate RAG-based Credit Policy overrides
            matches = retrieved_policy.get("matches", [])
            
            for m in matches:
                citation_code = m.get("clause_cited")
                status = m.get("status")
                reasoning = m.get("reasoning")
                
                if status == "FAILED":
                    decision = "DECLINE"
                    reasons.append(f"Policy check failed for {m.get('parameter')}: {reasoning}")
                    if citation_code not in citations:
                        citations.append(citation_code)
                elif status == "REFER":
                    if decision != "DECLINE":
                        decision = "REFER"
                    reasons.append(f"Policy check referred for {m.get('parameter')}: {reasoning}")
                    if citation_code not in citations:
                        citations.append(citation_code)
                else:
                    if citation_code not in citations:
                        citations.append(citation_code)

            # 4. Calculate Underwriting Confidence Score
            if decision == "APPROVE":
                if credit_score >= 780 and dti_ratio <= 0.35:
                    confidence = 0.95
                else:
                    confidence = 0.88
            elif decision == "DECLINE":
                if has_defaults or credit_score < 600 or dti_ratio > 0.50:
                    confidence = 0.98
                else:
                    confidence = 0.90
            else:
                confidence = 0.75

            if not citations:
                citations.append("General Underwriting Policy")

            if not reasons:
                reasons.append("All underwriting checks, document validations, and RAG policies successfully satisfied.")

            reco = RecommendationOutput(
                decision=decision,
                reasons=reasons,
                policy_citations=citations,
                confidence=confidence
            )

        # ================= Output Guardrails Safety Override =================
        credit_score = score_result.get("credit_score", 700)
        has_defaults = score_result.get("has_active_defaults", False)
        dti_ratio = score_result.get("dti_ratio", 0.0)

        if reco.decision != "DECLINE":
            if has_defaults:
                logger.warning("Output Guardrail Triggered: Overriding decision to DECLINE due to active default.")
                reco.decision = "DECLINE"
                reco.reasons.append("Output Guardrail override: Strict risk parameters (defaults) violated.")
            elif credit_score < 600:
                logger.warning("Output Guardrail Triggered: Overriding decision to DECLINE due to low credit score (%d).", credit_score)
                reco.decision = "DECLINE"
                reco.reasons.append("Output Guardrail override: Credit score is below strict absolute minimum threshold of 600.")
            elif dti_ratio > 0.50:
                logger.warning("Output Guardrail Triggered: Overriding decision to DECLINE due to excessive DTI (%f).", dti_ratio)
                reco.decision = "DECLINE"
                reco.reasons.append("Output Guardrail override: DTI ratio exceeds strict absolute maximum threshold of 50%.")

        return reco
