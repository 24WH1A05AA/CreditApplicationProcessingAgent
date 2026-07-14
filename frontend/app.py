import sys
import os

# Ensure the project root is on sys.path so `backend` is importable
# regardless of which directory Streamlit is launched from
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st
import requests
import shutil
from typing import List, Dict, Any

# Backend URL configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Set page config
st.set_page_config(
    page_title="Credit Processing Underwriting Assistant",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Theme CSS Injection
st.markdown("""
    <style>
    /* Import Premium Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    
    /* Apply globally */
    * {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Main container background */
    .stApp {
        background: radial-gradient(circle at 10% 20%, rgb(15, 23, 42) 0%, rgb(9, 15, 29) 90%);
        color: #F8FAFC;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #0F172A !important;
        border-right: 1px solid #1E293B;
    }
    
    /* Title text */
    h1, h2, h3, h4, h5, h6 {
        color: #F8FAFC !important;
        font-weight: 600;
        letter-spacing: -0.025em;
    }
    
    /* Custom Card for metrics and layout */
    .glass-card {
        background: rgba(30, 41, 59, 0.45);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    
    .glass-card:hover {
        transform: translateY(-2px);
        border-color: rgba(99, 102, 241, 0.4);
    }
    
    /* Metric styling */
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #818CF8 0%, #C084FC 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .metric-label {
        font-size: 0.875rem;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
    }
    
    /* Custom button styles */
    div.stButton > button {
        background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%) !important;
        color: #FFFFFF !important;
        border: None !important;
        border-radius: 8px !important;
        padding: 10px 24px !important;
        font-weight: 500 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3) !important;
    }
    
    div.stButton > button:hover {
        background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%) !important;
        box-shadow: 0 6px 18px rgba(79, 70, 229, 0.5) !important;
        transform: translateY(-1px) !important;
    }
    
    /* Status Badges */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .badge-approved { background-color: rgba(16, 185, 129, 0.15); color: #10B981; border: 1px solid rgba(16, 185, 129, 0.3); }
    .badge-refer { background-color: rgba(245, 158, 11, 0.15); color: #F59E0B; border: 1px solid rgba(245, 158, 11, 0.3); }
    .badge-decline { background-color: rgba(239, 68, 68, 0.15); color: #EF4444; border: 1px solid rgba(239, 68, 68, 0.3); }
    .badge-other { background-color: rgba(148, 163, 184, 0.15); color: #94A3B8; border: 1px solid rgba(148, 163, 184, 0.3); }
    </style>
""", unsafe_allow_html=True)

# Initialize Session State
# Initialize Session State dynamically via API
if "applications" not in st.session_state:
    st.session_state.applications = []
    try:
        r = requests.get(f"{BACKEND_URL}/applications")
        if r.status_code == 200:
            st.session_state.applications = [app["id"] for app in r.json()]
    except Exception:
        pass

if "selected_app_id" not in st.session_state:
    st.session_state.selected_app_id = st.session_state.applications[0] if st.session_state.applications else ""

# Sidebar / Navigation
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🛡️ TechVest</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748B;'>Credit Underwriting Hub</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    menu = st.radio(
        "Navigation",
        [
            "Dashboard",
            "New Application",
            "Upload Documents",
            "Recommendation",
            "Approval Gate",
            "Audit History"
        ]
    )
    
    st.markdown("---")
    
    # Refresh applications list from API dynamically to keep context selector in sync
    try:
        r = requests.get(f"{BACKEND_URL}/applications")
        if r.status_code == 200:
            st.session_state.applications = [app["id"] for app in r.json()]
    except Exception:
        pass

    # Active Application Selector
    if st.session_state.applications:
        st.subheader("Active Context")
        if st.session_state.selected_app_id not in st.session_state.applications:
            st.session_state.selected_app_id = st.session_state.applications[0]
        selected_id = st.selectbox(
            "Select Application",
            st.session_state.applications,
            index=st.session_state.applications.index(st.session_state.selected_app_id) if st.session_state.selected_app_id in st.session_state.applications else 0
        )
        st.session_state.selected_app_id = selected_id
    else:
        st.info("No applications in database. Create one to get started.")

    st.markdown("---")
    st.markdown("### System Status")
    
    # Query Backend API Health
    try:
        r_health = requests.get(f"{BACKEND_URL}/health", timeout=2)
        if r_health.status_code == 200:
            st.markdown("🟢 **Backend API:** Online")
            st.markdown("🟢 **Database:** SQLite Connected")
        else:
            st.markdown("🔴 **Backend API:** Error Response")
            st.markdown("🔴 **Database:** Status Error")
    except Exception:
        st.markdown("🔴 **Backend API:** Offline")
        st.markdown("🔴 **Database:** Disconnected")


# ================= Navigation Pages =================

if menu == "Dashboard":
    st.markdown("# 📊 Underwriting Dashboard")
    st.markdown("Real-time portfolio metrics and queue management.")
    
    # Fetch details for all applications to compile stats
    app_details_list = []
    total_count = 0
    pending_count = 0
    approved_count = 0
    declined_count = 0
    
    try:
        r = requests.get(f"{BACKEND_URL}/applications")
        if r.status_code == 200:
            app_details_list = r.json()
            total_count = len(app_details_list)
            for det in app_details_list:
                status = det.get("status", "INTAKE").upper()
                if status == "REFER" or status == "PENDING_APPROVAL":
                    pending_count += 1
                elif status == "APPROVED" or status == "APPROVED":
                    approved_count += 1
                elif status == "DECLINED" or status == "DECLINED":
                    declined_count += 1
    except Exception as e:
        st.error(f"Failed to fetch application queue: {str(e)}")

    # Grid Layout for metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
            <div class="glass-card">
                <div class="metric-label">Total Applications</div>
                <div class="metric-value">{total_count}</div>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
            <div class="glass-card">
                <div class="metric-label">Pending Approval (Refer)</div>
                <div class="metric-value">{pending_count}</div>
            </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
            <div class="glass-card">
                <div class="metric-label">Approved Applications</div>
                <div class="metric-value">{approved_count}</div>
            </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
            <div class="glass-card">
                <div class="metric-label">Declined Applications</div>
                <div class="metric-value">{declined_count}</div>
            </div>
        """, unsafe_allow_html=True)

    # Display underwriting queue table
    st.subheader("Underwriting Queue")
    if app_details_list:
        # Build tabular layout
        for app in app_details_list:
            cols = st.columns([2, 2, 2, 1.5, 1.5, 1.5, 1.5])
            with cols[0]:
                st.markdown(f"**ID:** `{app['id'][:8]}...`")
            with cols[1]:
                st.write(f"{app['applicant']['first_name']} {app['applicant']['last_name']}")
            with cols[2]:
                st.write(f"INR {app['loan_amount']:,.2f}")
            with cols[3]:
                st.write(app["loan_purpose"])
            with cols[4]:
                status = app["status"].upper()
                if status == "APPROVED":
                    st.markdown('<span class="badge badge-approved">Approved</span>', unsafe_allow_html=True)
                elif status == "DECLINED":
                    st.markdown('<span class="badge badge-decline">Declined</span>', unsafe_allow_html=True)
                elif status == "REFER":
                    st.markdown('<span class="badge badge-refer">Refer</span>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<span class="badge badge-other">{status}</span>', unsafe_allow_html=True)
            with cols[5]:
                if st.button("Analyze", key=f"proc_{app['id']}"):
                    with st.spinner("Executing LangGraph underwriting workflow..."):
                        pr = requests.post(f"{BACKEND_URL}/applications/{app['id']}/process")
                        if pr.status_code == 200:
                            st.success("Workflow executed successfully!")
                            st.rerun()
                        else:
                            st.error(f"Execution failed: {pr.text}")
            with cols[6]:
                if st.button("Select Context", key=f"sel_{app['id']}"):
                    st.session_state.selected_app_id = app["id"]
                    st.success(f"Context set to application {app['id'][:8]}")
            st.markdown("---")
    else:
        st.info("The application queue is empty. Submit a new application to get started.")


elif menu == "New Application":
    st.markdown("# 📝 Start New Credit Application")
    st.markdown("Submit borrower details to initiate risk evaluation.")
    
    with st.form("new_application_form"):
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input("First Name", placeholder="e.g. John")
            last_name = st.text_input("Last Name", placeholder="e.g. Smith")
            dob = st.text_input("Date of Birth (YYYY-MM-DD)", placeholder="e.g. 1989-10-15")
            email = st.text_input("Email Address", placeholder="e.g. john.smith@example.com")
        with col2:
            monthly_income = st.number_input("Monthly Income (INR)", min_value=0.0, step=5000.0, value=65000.0)
            existing_emi = st.number_input("Existing Monthly EMIs (INR)", min_value=0.0, step=1000.0, value=5000.0)
            loan_amount = st.number_input("Requested Loan Amount (INR)", min_value=0.0, step=10000.0, value=150000.0)
            loan_purpose = st.selectbox("Loan Purpose", ["Debt Consolidation", "Home Improvement", "Medical Expense", "Education Loan", "Business expansion"])
            
        submitted = st.form_submit_button("Submit Application")
        if submitted:
            if not first_name or not last_name or not email or not dob:
                st.error("Please fill in all mandatory applicant details.")
            else:
                payload = {
                    "loan_amount": loan_amount,
                    "loan_purpose": loan_purpose,
                    "applicant": {
                        "first_name": first_name,
                        "last_name": last_name,
                        "email": email,
                        "dob": dob,
                        "monthly_income": monthly_income,
                        "existing_emi": existing_emi
                    }
                }
                
                try:
                    r = requests.post(f"{BACKEND_URL}/applications", json=payload)
                    if r.status_code == 200:
                        res = r.json()
                        app_id = res["application_id"]
                        st.session_state.applications.insert(0, app_id)
                        st.session_state.selected_app_id = app_id
                        st.success(f"Application created successfully! ID: `{app_id}`")
                    else:
                        st.error(f"Error creating application: {r.text}")
                except Exception as e:
                    st.error(f"Connection failed: {str(e)}")


elif menu == "Upload Documents":
    st.markdown("# 📁 Document Upload Center")
    st.markdown("Upload government identification, salary slips, and bank statements for OCR processing.")
    
    app_id = st.session_state.selected_app_id
    if not app_id:
        st.warning("Please create or select an application from the sidebar first.")
    else:
        st.markdown(f"**Target Application Context:** `{app_id}`")
        
        # Display current uploaded files status
        r = requests.get(f"{BACKEND_URL}/applications/{app_id}")
        if r.status_code == 200:
            app_details = r.json()
            docs = app_details.get("documents", [])
            st.markdown("### Uploaded Documents Status")
            if docs:
                for doc in docs:
                    st.write(f"📄 **{doc['document_type']}** - Path: `{doc['file_path']}`")
            else:
                st.info("No documents uploaded yet.")
        
        st.markdown("---")
        st.markdown("### Upload New Document")
        doc_type = st.selectbox("Document Type", ["PAN", "Aadhaar", "Salary Slip", "Bank Statement"])
        uploaded_file = st.file_uploader("Select PDF / Image file", type=["pdf", "jpg", "png", "jpeg"])
        
        if st.button("Upload Document"):
            if uploaded_file is None:
                st.error("Please select a file to upload.")
            else:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                data = {"document_type": doc_type}
                with st.spinner(f"Uploading and registering {doc_type}..."):
                    try:
                        ur = requests.post(f"{BACKEND_URL}/applications/{app_id}/documents", data=data, files=files)
                        if ur.status_code == 200:
                            st.success(f"Successfully uploaded {doc_type}!")
                            st.rerun()
                        else:
                            st.error(f"Failed to upload: {ur.text}")
                    except Exception as e:
                        st.error(f"Connection error: {str(e)}")


elif menu == "Recommendation":
    st.markdown("# 🔍 AI Decision Analysis & RAG Citations")
    st.markdown("Detailed breakdown of risk recommendations, credit checks, and policy matching.")
    
    app_id = st.session_state.selected_app_id
    if not app_id:
        st.warning("Please select an application context first.")
    else:
        try:
            r_app = requests.get(f"{BACKEND_URL}/applications/{app_id}")
            r_reco = requests.get(f"{BACKEND_URL}/applications/{app_id}/recommendation")
            
            if r_app.status_code != 200:
                st.error("Application not found.")
            elif r_reco.status_code == 404:
                st.info("No underwriting recommendation found. Run workflow analysis from the Dashboard first.")
            elif r_reco.status_code == 200:
                app_det = r_app.json()
                reco_det = r_reco.json()
                
                # 1. Recommendation Decision Card
                decision = reco_det.get("decision", "REFER").upper()
                bg_color = "rgba(16, 185, 129, 0.1)" if decision == "APPROVE" else "rgba(239, 68, 68, 0.1)" if decision == "DECLINE" else "rgba(245, 158, 11, 0.1)"
                border_color = "#10B981" if decision == "APPROVE" else "#EF4444" if decision == "DECLINE" else "#F59E0B"
                
                st.markdown(f"""
                    <div style="background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
                        <h2 style="margin: 0; color: {border_color} !important;">AI Recommendation: {decision}</h2>
                        <p style="margin-top: 12px; font-size: 1.1rem; color: #E2E8F0;">{reco_det.get('reasoning', '')}</p>
                    </div>
                """, unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    # 2. Risk Metrics Card
                    st.markdown("### Risk Analysis & Scoring")
                    st.write(f"📊 **Composite Risk Score:** `{reco_det.get('composite_score', 0.0):.2f}`")
                    st.write(f"📈 **Credit Bureau Score:** `{app_det.get('credit_score') or 'N/A'}`")
                    st.write(f"📉 **Debt-To-Income (DTI) Ratio:** `{app_det.get('dti_ratio', 0.0):.2%}`")
                    
                    # 3. Fairness Validation Card
                    st.markdown("### Fairness Check Results")
                    is_fair = reco_det.get("fairness_passed")
                    if is_fair is None:
                        st.info("Fairness metrics not calculated.")
                    elif is_fair:
                        st.success("✅ **Fairness Passed:** Identity-blind recommendation matches non-blind decision.")
                    else:
                        st.error("⚠️ **Fairness Discrepancy Flagged:** Disparity in decision when demographics are blinded.")
                        
                with col2:
                    # 4. RAG Citations
                    st.markdown("### RAG Policy Citations & Clauses")
                    # Fetch audit execution details for policy citations
                    r_audit = requests.get(f"{BACKEND_URL}/audit/{app_id}")
                    if r_audit.status_code == 200:
                        audit_logs = r_audit.json().get("logs", [])
                        wf_log = next((log for log in audit_logs if log["action"] == "WORKFLOW_EXECUTION"), None)
                        if wf_log and "retrieved_policy" in wf_log["details"]:
                            matches = wf_log["details"]["retrieved_policy"].get("matches", [])
                            if matches:
                                for match in matches:
                                    status = match.get("status")
                                    badge_class = "badge-approved" if status == "PASSED" else "badge-refer" if status == "REFER" else "badge-decline"
                                    st.markdown(f"""
                                        <div style="background-color: rgba(30, 41, 59, 0.6); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 12px; margin-bottom: 12px;">
                                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                                <strong>{match.get('clause_cited')}</strong>
                                                <span class="badge {badge_class}">{status}</span>
                                            </div>
                                            <p style="margin: 8px 0 0 0; font-size: 0.9rem; color: #94A3B8;">{match.get('reasoning')}</p>
                                        </div>
                                    """, unsafe_allow_html=True)
                            else:
                                st.info("No policy overrides triggered.")
                        else:
                            st.write("Citations list:")
                            st.write(reco_det.get("citations", ["General Policy"]))
                    else:
                        st.info("Audit logs unavailable.")
                        
                st.markdown("---")
                st.markdown("### 🔍 Agent Observability & Telemetry Traces")
                
                # Fetch observability details
                r_obs = requests.get(f"{BACKEND_URL}/applications/{app_id}/observability")
                if r_obs.status_code == 200:
                    obs_data = r_obs.json()
                    
                    # Display timing and token usage in columns
                    ocol1, ocol2, ocol3 = st.columns(3)
                    with ocol1:
                        st.metric("Total Latency", f"{obs_data.get('total_latency_ms', 0.0):.2f} ms")
                    with ocol2:
                        st.metric("Estimated Tokens", f"{obs_data.get('token_usage', {}).get('total_tokens', 0)} tokens")
                    with ocol3:
                        st.metric("Steps Executed", f"{len(obs_data.get('execution_path', []))}/8 steps")
                        
                    # Show node timings table/dictionary
                    with st.expander("⏱️ Node-by-Node Latency Metrics"):
                        st.json(obs_data.get("node_timings_ms", {}))
                        
                    # Show Mermaid Graph Visualization
                    st.markdown("#### 🗺️ Agent Execution Path Visualization")
                    html_code = f"""
                    <div style="background-color: #0f172a; border-radius: 8px; padding: 15px; border: 1px solid #1e293b; display: flex; justify-content: center;">
                        <pre class="mermaid" style="background: transparent; border: none; font-family: inherit;">
                        {obs_data.get('mermaid_chart')}
                        </pre>
                    </div>
                    <script type="module">
                        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
                        mermaid.initialize({{ startOnLoad: true, theme: 'dark' }});
                    </script>
                    """
                    st.components.v1.html(html_code, height=450)
                else:
                    st.info("Run analysis first to view agent execution traces and timings.")
        except Exception as e:
            st.error(f"Error loading details: {str(e)}")


elif menu == "Approval Gate":
    st.markdown("# 🛡️ Human Underwriting Approval Gate")
    st.markdown("Underwriter human-in-the-loop governance sign-off.")
    
    app_id = st.session_state.selected_app_id
    if not app_id:
        st.warning("Please select an application context first.")
    else:
        try:
            r_app = requests.get(f"{BACKEND_URL}/applications/{app_id}")
            r_reco = requests.get(f"{BACKEND_URL}/applications/{app_id}/recommendation")
            
            if r_app.status_code == 200:
                app_det = r_app.json()
                
                # Check status
                current_status = app_det.get("status", "INTAKE").upper()
                st.info(f"Current Application Status: **{current_status}**")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("### Applicant Profile")
                    st.write(f"👤 **Name:** {app_det['applicant']['first_name']} {app_det['applicant']['last_name']}")
                    st.write(f"📧 **Email:** {app_det['applicant']['email']}")
                    st.write(f"💰 **Monthly Income:** INR {app_det['applicant']['monthly_income']:,.2f}")
                    st.write(f"💳 **Existing EMI:** INR {app_det['applicant']['existing_emi']:,.2f}")
                    st.write(f"🏦 **Loan Requested:** INR {app_det['loan_amount']:,.2f}")
                    
                with col2:
                    st.markdown("### AI Analysis Summary")
                    if r_reco.status_code == 200:
                        reco_det = r_reco.json()
                        st.write(f"🤖 **Decision:** `{reco_det['decision']}`")
                        st.write(f"📝 **Reasoning:** {reco_det['reasoning']}")
                        st.write(f"⚖️ **Fairness Passed:** `{reco_det['fairness_passed']}`")
                    else:
                        st.write("AI analysis has not been executed yet.")
                        
                st.markdown("---")
                st.markdown("### Submit Final Underwriter Decision")
                
                with st.form("human_approval_form"):
                    h_decision = st.selectbox("Underwriting Decision", ["APPROVED", "DECLINED", "REFER"])
                    comments = st.text_area("Reviewer Comments", placeholder="State detailed justification here...")
                    email = st.text_input("Underwriter Email", placeholder="underwriter@techvest.com")
                    
                    submitted = st.form_submit_button("Record Decision")
                    if submitted:
                        if not email or "@" not in email:
                            st.error("Please enter a valid underwriter email.")
                        elif not comments:
                            st.error("Please enter reviewer comments.")
                        else:
                            payload = {
                                "application_id": app_id,
                                "decision": h_decision,
                                "comments": comments,
                                "underwriter_email": email
                            }
                            
                            try:
                                r = requests.post(f"{BACKEND_URL}/approval", json=payload)
                                if r.status_code == 200:
                                    st.success("Human underwriting decision successfully logged!")
                                    st.rerun()
                                else:
                                    st.error(f"Error submitting decision: {r.text}")
                            except Exception as e:
                                st.error(f"Connection failure: {str(e)}")
            else:
                st.error("Application not found.")
        except Exception as e:
            st.error(f"Error loading approval details: {str(e)}")


elif menu == "Audit History":
    st.markdown("# 📜 Chronological Governance Audit Trail")
    st.markdown("Immutable logs of system executions, tool calls, and human approvals.")
    
    app_id = st.session_state.selected_app_id
    if not app_id:
        st.warning("Please select an application context first.")
    else:
        try:
            r = requests.get(f"{BACKEND_URL}/audit/{app_id}")
            if r.status_code == 200:
                audit_data = r.json()
                logs = audit_data.get("logs", [])
                
                if logs:
                    # Chronological tracing
                    for idx, log in enumerate(logs):
                        with st.expander(f"Step {idx+1}: {log['action']} - Performed by {log['performed_by']} ({log['timestamp']})"):
                            st.json(log["details"])
                else:
                    st.info("No audit logs found for this application ID. Upload documents and run analysis to populate logs.")
            else:
                st.error("Failed to fetch audit logs.")
        except Exception as e:
            st.error(f"Connection failure: {str(e)}")
