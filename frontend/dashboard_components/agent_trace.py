import streamlit as st
import textwrap

def render_agent_execution_trace(app_details):
    """
    Renders an interactive, enterprise-grade execution timeline trace for a single application.
    """
    if not app_details:
        st.warning("Select an application in the dropdown below to view its execution trace details.")
        return
        
    timings = app_details.get("node_timings", {})
    path = app_details.get("execution_path", [])
    tokens = app_details.get("token_usage", {})
    
    # List of all timeline steps we want to display
    steps = [
        {"id": "loan_intake_node", "name": "Loan Intake", "tool": "Audit Logger / Applicant Repo", "desc": "Ingest and structure applicant data profile"},
        {"id": "ocr_processor", "name": "OCR Extraction", "tool": "OCR Processor / pytesseract", "desc": "Extract raw text from uploaded ID & income proofs"},
        {"id": "document_validation_node", "name": "Document Validation", "tool": "Document Validator", "desc": "Validate PAN format, Aadhaar, and Salary slips"},
        {"id": "consistency_checker", "name": "Consistency Check", "tool": "Consistency Checker", "desc": "Verify details match across identity and income docs"},
        {"id": "policy_retrieval_node", "name": "RAG Policy Retrieval", "tool": "RAG Retriever / ChromaDB", "desc": "Fetch credit policy clauses relevant to application context"},
        {"id": "credit_scoring_node", "name": "Credit Scoring & DTI", "tool": "Credit Scoring Engine", "desc": "Calculate Debt-to-Income and composite scoring"},
        {"id": "recommendation_node", "name": "Recommendation Engine", "tool": "Recommendation Engine / LLM", "desc": "Generate Approve/Refer/Decline lending recommendation"},
        {"id": "fairness_check_node", "name": "Demographic Fairness Check", "tool": "Fairness Checker", "desc": "Re-evaluate recommendation with blinded parameters"},
        {"id": "human_approval_node", "name": "Human-in-the-Loop Approval", "tool": "Human Gate UI / Underwriter", "desc": "Capture underwriter final override and sign-off decision"},
        {"id": "audit_logging_node", "name": "Audit Logging", "tool": "Audit Logger / DB", "desc": "Write immutable execution records to compliance DB"}
    ]
    
    st.markdown("### 🗺️ Trace Timelines & DAG Telemetry")
    
    timeline_html = """
    <style>
    .timeline-container {
        font-family: 'Outfit', sans-serif;
        margin: 20px 0;
        position: relative;
        padding-left: 30px;
        border-left: 2px solid rgba(255,255,255,0.06);
    }
    .timeline-item {
        position: relative;
        margin-bottom: 24px;
    }
    .timeline-badge {
        position: absolute;
        left: -40px;
        top: 2px;
        width: 18px;
        height: 18px;
        border-radius: 50%;
        background-color: #1E293B;
        border: 3px solid #64748B;
        z-index: 100;
        transition: all 0.3s ease;
    }
    .timeline-badge.completed {
        background-color: #0F172A;
        border-color: #10B981;
        box-shadow: 0 0 8px rgba(16,185,129,0.4);
    }
    .timeline-badge.failed {
        background-color: #0F172A;
        border-color: #EF4444;
        box-shadow: 0 0 8px rgba(239,68,68,0.4);
    }
    .timeline-card {
        background: rgba(30, 41, 59, 0.35);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 8px;
        padding: 14px 18px;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .timeline-card:hover {
        border-color: rgba(99, 102, 241, 0.3);
        transform: translateX(2px);
    }
    .timeline-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 4px;
    }
    .timeline-title {
        font-weight: 600;
        color: #F8FAFC;
        font-size: 1rem;
    }
    .timeline-meta {
        font-size: 0.8rem;
        color: #94A3B8;
    }
    .timeline-desc {
        font-size: 0.85rem;
        color: #64748B;
        margin: 4px 0;
    }
    .timeline-footer {
        display: flex;
        gap: 12px;
        margin-top: 8px;
        font-size: 0.75rem;
    }
    .trace-tag {
        background-color: rgba(99,102,241,0.08);
        border: 1px solid rgba(99,102,241,0.15);
        color: #818CF8;
        padding: 2px 8px;
        border-radius: 4px;
    }
    </style>
    <div class="timeline-container">
    """
    
    for step in steps:
        step_id = step["id"]
        # Determine step latency and completeness status
        latency_val = 0.0
        is_completed = False
        
        # Mapping rules to read raw node timings
        if step_id in timings:
            latency_val = timings[step_id]
            is_completed = True
        elif step_id == "ocr_processor" and "document_validation_node" in timings:
            # Sub-operation inside document validation
            latency_val = timings["document_validation_node"] * 0.3
            is_completed = True
        elif step_id == "consistency_checker" and "document_validation_node" in timings:
            # Sub-operation inside document validation
            latency_val = timings["document_validation_node"] * 0.2
            is_completed = True
        elif step_id == "human_approval_node":
            h_dec = app_details.get("human_decision", {})
            if h_dec and h_dec.get("decision") != "PENDING":
                dur = h_dec.get("duration_seconds")
                dur = dur if dur is not None else 0.0
                latency_val = dur * 1000.0
                is_completed = True
                
        # Status styling
        latency_val = latency_val if latency_val is not None else 0.0
        badge_class = "completed" if is_completed else ""
        status_text = f"🟢 COMPLETED ({latency_val:.1f} ms)" if is_completed else "⚪ NOT EXECUTED"
        
        # Estimate token usage
        token_info = ""
        if step_id == "policy_retrieval_node" and is_completed:
            token_info = f"<span class='trace-tag'>Est Tokens: {tokens.get('total_tokens', 80)}</span>"
        elif step_id == "recommendation_node" and is_completed:
            token_info = f"<span class='trace-tag'>Est Tokens: 420</span>"
            
        timeline_html += f"""
        <div class="timeline-item">
            <div class="timeline-badge {badge_class}"></div>
            <div class="timeline-card">
                <div class="timeline-header">
                    <span class="timeline-title">{step['name']}</span>
                    <span class="timeline-meta" style="color: {'#10B981' if is_completed else '#64748B'}; font-weight: 500;">{status_text}</span>
                </div>
                <div class="timeline-desc">{step['desc']}</div>
                <div class="timeline-footer">
                    <span class="trace-tag" style="background-color: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); color: #94A3B8;">🔧 Tool: {step['tool']}</span>
                    {token_info}
                </div>
            </div>
        </div>
        """
        
    timeline_html += "</div>"
    clean_html = "\n".join([line.strip() for line in timeline_html.split("\n")])
    st.markdown(clean_html, unsafe_allow_html=True)
