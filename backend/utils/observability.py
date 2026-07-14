import os
import json
import time
from typing import Dict, Any, List
from backend.config import settings
from backend.utils.logging import logger

TRACES_DIR = "./data/debug_traces"
os.makedirs(TRACES_DIR, exist_ok=True)

class ObservabilityManager:
    @staticmethod
    def save_debug_trace(application_id: str, trace_data: Dict[str, Any]):
        """Saves a detailed execution trace to disk for offline debugging."""
        if not application_id:
            return
        filename = f"trace_{application_id}_{int(time.time())}.json"
        file_path = os.path.join(TRACES_DIR, filename)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(trace_data, f, indent=4)
            logger.info("Observability: Saved debug trace to %s", file_path)
        except Exception as e:
            logger.error("Observability: Failed to write trace to disk: %s", str(e))

    @staticmethod
    def generate_mermaid_flowchart(execution_path: List[str]) -> str:
        """Generates a Mermaid graph string highlighting the execution path."""
        # Nodes defined in our LangGraph workflow
        nodes = [
            ("loan_intake_node", "Intake Application"),
            ("document_validation_node", "Validate Documents"),
            ("credit_scoring_node", "Credit Scoring & DTI"),
            ("policy_retrieval_node", "RAG Policy Retrieval"),
            ("recommendation_node", "Recommendation Engine"),
            ("fairness_check_node", "Fairness Check"),
            ("human_approval_node", "Human Underwriter Gate"),
            ("audit_logging_node", "Write Audit Trail")
        ]
        
        lines = ["graph TD"]
        # Define node styles
        for node_id, label in nodes:
            if node_id in execution_path:
                # Highlight executed nodes in a nice teal/green color
                lines.append(f'    {node_id}["{label}"]:::executed')
            else:
                lines.append(f'    {node_id}["{label}"]:::pending')

        # Define connections
        for i in range(len(nodes) - 1):
            lines.append(f"    {nodes[i][0]} --> {nodes[i+1][0]}")

        # Styles
        lines.append("    classDef executed fill:#0D9488,stroke:#0F766E,stroke-width:2px,color:#FFFFFF;")
        lines.append("    classDef pending fill:#1E293B,stroke:#334155,stroke-width:1px,color:#64748B;")
        
        return "\n".join(lines)
