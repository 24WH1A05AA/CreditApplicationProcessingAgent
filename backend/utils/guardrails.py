import re
from typing import Dict, Any, List
from backend.utils.logging import logger

class GuardrailEngine:
    @staticmethod
    def scan_for_prompt_injection(text: str) -> bool:
        """
        Scans a text input for common prompt injection patterns.
        """
        if not text:
            return False
            
        text_lower = text.lower()
        patterns = [
            r"ignore\s+(?:all\s+)?prior\s+instructions",
            r"ignore\s+(?:all\s+)?previous\s+instructions",
            r"system\s+override",
            r"bypass\s+policy",
            r"act\s+as\s+a\s+developer",
            r"you\s+must\s+approve",
            r"ignore\s+policy",
            r"forget\s+all\s+rules",
            r"don't\s+decline",
            r"always\s+approve"
        ]
        
        for pattern in patterns:
            if re.search(pattern, text_lower):
                logger.warning("Guardrail Alert: Prompt injection pattern detected: '%s'", pattern)
                return True
        return False

    @staticmethod
    def scan_for_sql_injection(text: str) -> bool:
        """
        Scans a text input for simple SQL injection patterns.
        """
        if not text:
            return False
            
        text_lower = text.lower()
        patterns = [
            r"'\s*or\s*'\s*\d+\s*=\s*\d+",
            r"union\s+select",
            r"drop\s+table",
            r"delete\s+from",
            r"select\s+.*\s+from",
            r"insert\s+into"
        ]
        
        for pattern in patterns:
            if re.search(pattern, text_lower):
                logger.warning("Guardrail Alert: SQL injection pattern detected: '%s'", pattern)
                return True
        return False

    @staticmethod
    def validate_inputs(payload: Dict[str, Any]) -> List[str]:
        """
        Runs full guardrail scan on application creation inputs.
        """
        errors = []
        
        # Scan loan purpose
        loan_purpose = payload.get("loan_purpose", "")
        if GuardrailEngine.scan_for_prompt_injection(loan_purpose):
            errors.append("Invalid loan purpose: input contains blocked system override instructions.")
        if GuardrailEngine.scan_for_sql_injection(loan_purpose):
            errors.append("Invalid loan purpose: input contains illegal database query characters.")
            
        # Scan applicant info
        applicant = payload.get("applicant", {})
        for field in ["first_name", "last_name", "email"]:
            val = str(applicant.get(field, ""))
            if GuardrailEngine.scan_for_prompt_injection(val):
                errors.append(f"Invalid applicant {field}: input contains blocked system override instructions.")
            if GuardrailEngine.scan_for_sql_injection(val):
                errors.append(f"Invalid applicant {field}: input contains illegal database query characters.")
                
        return errors
