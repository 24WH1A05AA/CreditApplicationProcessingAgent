from typing import Dict, Any
from langgraph.graph import StateGraph, END
from backend.agents.state import UnderwritingState
from backend.agents.nodes import WorkflowNodes
from backend.utils.logging import logger

# 1. Build and configure the State Graph
workflow = StateGraph(UnderwritingState)

# 2. Add all workflow nodes
workflow.add_node("loan_intake_node", WorkflowNodes.loan_intake)
workflow.add_node("document_validation_node", WorkflowNodes.document_validation)
workflow.add_node("policy_retrieval_node", WorkflowNodes.policy_retrieval)
workflow.add_node("credit_scoring_node", WorkflowNodes.credit_scoring)
workflow.add_node("recommendation_node", WorkflowNodes.recommendation)
workflow.add_node("fairness_check_node", WorkflowNodes.fairness_check)
workflow.add_node("human_approval_node", WorkflowNodes.human_approval)
workflow.add_node("audit_logging_node", WorkflowNodes.audit_logging)

# 3. Define linear sequence edges (from intake through to audit and completion)
workflow.set_entry_point("loan_intake_node")
workflow.add_edge("loan_intake_node", "document_validation_node")
workflow.add_edge("document_validation_node", "policy_retrieval_node")
workflow.add_edge("policy_retrieval_node", "credit_scoring_node")
workflow.add_edge("credit_scoring_node", "recommendation_node")
workflow.add_edge("recommendation_node", "fairness_check_node")
workflow.add_edge("fairness_check_node", "human_approval_node")
workflow.add_edge("human_approval_node", "audit_logging_node")
workflow.add_edge("audit_logging_node", END)

# 4. Compile the workflow graph
underwriting_workflow = workflow.compile()

# 5. Safe entry-point runner with graceful exception handling
def run_underwriting_workflow(initial_state: UnderwritingState) -> Dict[str, Any]:
    """
    Executes the compiled LangGraph workflow with robust exception safety checks.
    """
    try:
        logger.info("Invoking compiled LangGraph Loan Underwriting Workflow...")
        result = underwriting_workflow.invoke(initial_state)
        return result
    except Exception as e:
        logger.error("LangGraph Underwriting Workflow crashed during execution: %s", str(e))
        # Graceful fallback return payload
        fallback_state = {**initial_state}
        fallback_state["metadata"] = {
            **initial_state.get("metadata", {}),
            "workflow_execution_error": str(e),
            "workflow_status": "FAILED"
        }
        return fallback_state
