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
import pandas as pd
import frontend.dashboard_components as db_comp
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
            "Audit History",
            "Evaluation Dashboard",
            "Policy Chatbot"
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
    backend_online = False
    try:
        r_health = requests.get(f"{BACKEND_URL}/health", timeout=2)
        if r_health.status_code == 200:
            st.markdown("🟢 **Backend API:** Online")
            st.markdown("🟢 **Database:** SQLite Connected")
            backend_online = True
        else:
            st.markdown("🔴 **Backend API:** Error Response")
            st.markdown("🔴 **Database:** Status Error")
    except Exception:
        st.markdown("🔴 **Backend API:** Offline")
        st.markdown("🔴 **Database:** Disconnected")

    if backend_online:
        st.markdown("---")
        st.markdown("### Database Administration")
        if st.button("🌱 Seed Demo Data", key="sidebar_seed_btn", use_container_width=True):
            try:
                r_seed = requests.post(f"{BACKEND_URL}/database/seed")
                if r_seed.status_code == 200:
                    st.success("Seeding completed successfully!")
                    st.rerun()
                else:
                    st.error(f"Seeding failed: {r_seed.text}")
            except Exception as seed_ex:
                st.error(f"Error connecting: {str(seed_ex)}")


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
                loan_amt = app.get('loan_amount')
                loan_amt = loan_amt if loan_amt is not None else 0.0
                st.write(f"INR {loan_amt:,.2f}")
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
                    comp_score = reco_det.get('composite_score')
                    comp_score = comp_score if comp_score is not None else 0.0
                    dti_ratio = app_det.get('dti_ratio')
                    dti_ratio = dti_ratio if dti_ratio is not None else 0.0
                    st.write(f"📊 **Composite Risk Score:** `{comp_score:.2f}`")
                    st.write(f"📈 **Credit Bureau Score:** `{app_det.get('credit_score') or 'N/A'}`")
                    st.write(f"📉 **Debt-To-Income (DTI) Ratio:** `{dti_ratio:.2%}`")
                    
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
                        
                # 5. Risk Factor Waterfall Chart Explainability
                st.markdown("---")
                st.markdown("### 📊 Credit Risk Explainability Breakdown")
                fig_waterfall = db_comp.render_risk_waterfall_chart(app_det)
                st.plotly_chart(fig_waterfall, use_container_width=True)
                
                st.markdown("---")
                st.markdown("### 🔍 Agent Observability & Telemetry Traces")
                
                # Fetch observability details
                r_obs = requests.get(f"{BACKEND_URL}/applications/{app_id}/observability")
                if r_obs.status_code == 200:
                    obs_data = r_obs.json()
                    
                    # Display timing and token usage in columns
                    ocol1, ocol2, ocol3 = st.columns(3)
                    with ocol1:
                        total_latency = obs_data.get('total_latency_ms')
                        total_latency = total_latency if total_latency is not None else 0.0
                        st.metric("Total Latency", f"{total_latency:.2f} ms")
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
                        <div class="mermaid" style="color: #F8FAFC;">
                        {obs_data.get('mermaid_chart')}
                        </div>
                    </div>
                    <script src="https://cdn.jsdelivr.net/npm/mermaid@10.2.4/dist/mermaid.min.js"></script>
                    <script>
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
                    monthly_inc = app_det.get('applicant', {}).get('monthly_income')
                    monthly_inc = monthly_inc if monthly_inc is not None else 0.0
                    existing_emi = app_det.get('applicant', {}).get('existing_emi')
                    existing_emi = existing_emi if existing_emi is not None else 0.0
                    loan_amt = app_det.get('loan_amount')
                    loan_amt = loan_amt if loan_amt is not None else 0.0
                    st.write(f"💰 **Monthly Income:** INR {monthly_inc:,.2f}")
                    st.write(f"💳 **Existing EMI:** INR {existing_emi:,.2f}")
                    st.write(f"🏦 **Loan Requested:** INR {loan_amt:,.2f}")
                    
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


elif menu == "Evaluation Dashboard":
    st.markdown("# 📈 Enterprise Evaluation & Governance Dashboard")
    st.markdown("Real-time AI telemetry, model governance, and trace evaluations.")
    
    # 1. Query dashboard aggregate data
    try:
        r = requests.get(f"{BACKEND_URL}/evaluation/dashboard-data")
        if r.status_code == 200:
            data = r.json()
            
            # --- 1. HEADER SECTION ---
            col_h1, col_h2, col_h3 = st.columns([2, 1, 1])
            with col_h1:
                st.markdown(f"🤖 **Model:** `gpt-4o` | **Engine:** `LangGraph 2.0` | **Version:** `1.0.0` | **Env:** `Development Sandbox`")
            with col_h2:
                st.write(f"🕒 **System Time:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
            with col_h3:
                if st.button("🔄 Refresh Data", key="dash_refresh"):
                    st.rerun()
                    
            st.markdown("---")
            
            # --- 2. KPI GRID ---
            db_comp.render_kpis_grid(data)
            st.markdown("---")
            
            # --- 3. WORKSPACE TABS ---
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "📊 Performance & Load", 
                "🧠 AI Evaluation & RAG", 
                "🔍 Agent Tracing & Validation", 
                "🧑‍✈️ Governance & Compliance", 
                "📋 Applications Queue"
            ])
            
            with tab1:
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    st.markdown("#### Application Status Share")
                    status_pie = db_comp.render_application_status_pie(data)
                    st.plotly_chart(status_pie, use_container_width=True)
                with col_c2:
                    st.markdown("#### Turnaround Time Latency (TAT)")
                    tat_line = db_comp.render_turnaround_time_line(data)
                    if tat_line:
                        st.plotly_chart(tat_line, use_container_width=True)
                    else:
                        st.info("No turnaround data to plot.")
                    
                col_c3, col_c4 = st.columns(2)
                with col_c3:
                    st.markdown("#### Submissions Over Time")
                    time_area = db_comp.render_applications_over_time(data)
                    st.plotly_chart(time_area, use_container_width=True)
                with col_c4:
                    st.markdown("#### Hourly Load Distribution")
                    hour_bar = db_comp.render_applications_per_hour(data)
                    st.plotly_chart(hour_bar, use_container_width=True)
                    
                col_sys1, col_sys2, col_sys3 = st.columns(3)
                with col_sys1:
                    cpu_gauge = db_comp.render_system_perf_gauge(data["system_performance"]["cpu_usage_percent"], "CPU Usage")
                    st.plotly_chart(cpu_gauge, use_container_width=True)
                with col_sys2:
                    mem_gauge = db_comp.render_system_perf_gauge(data["system_performance"]["memory_usage_percent"], "Memory Usage", color='#10B981')
                    st.plotly_chart(mem_gauge, use_container_width=True)
                with col_sys3:
                    st.markdown("#### System Database Metrics")
                    st.write(f"⚙️ **Vector DB Latency:** `{data['system_performance']['vector_db_latency_ms']} ms`")
                    st.write(f"⏱️ **API Avg Latency:** `{data['system_performance']['api_response_time_ms']} ms`")
                    st.write(f"🔍 **Database Queries Count:** `{data['system_performance']['database_queries_count']}`")
                    
            with tab2:
                col_eval1, col_eval2 = st.columns(2)
                with col_eval1:
                    st.markdown("#### LangSmith AI Evaluation Dimensions")
                    radar_chart = db_comp.render_radar_eval_metrics(data)
                    st.plotly_chart(radar_chart, use_container_width=True)
                with col_eval2:
                    st.markdown("#### Model Token Usage & Cost (Est)")
                    db_comp.render_model_metrics(data)
                    
                st.markdown("#### Core Evaluation Metrics")
                db_comp.render_evaluation_metrics_cards(data)
                
            with tab3:
                # Active app selector for traces
                apps = data.get("applications", [])
                app_ids = [a["id"] for a in apps]
                
                selected_app_id = st.selectbox(
                    "Select Application Context for Detailed Tracing:",
                    app_ids,
                    key="trace_app_select"
                )
                
                selected_app = next((a for a in apps if a["id"] == selected_app_id), None)
                
                col_tr1, col_tr2 = st.columns(2)
                with col_tr1:
                    db_comp.render_agent_execution_trace(selected_app)
                with col_tr2:
                    st.markdown("#### Document validation & Forgery Checks")
                    db_comp.render_document_validation_analytics(selected_app)
                    
                    st.markdown("#### Credit Evaluation Risk Breakdown")
                    db_comp.render_credit_score_evaluation_cards(selected_app)
                    
                    st.markdown("#### Demographic Fairness Assessment")
                    db_comp.render_fairness_dashboard(selected_app)
                    
            with tab4:
                col_gov1, col_gov2 = st.columns(2)
                with col_gov1:
                    st.markdown("#### Human Gate & Decisions Override")
                    trace_app_select = st.selectbox(
                        "Select Application Context for Governance Audit:",
                        app_ids,
                        key="gov_app_select"
                    )
                    selected_gov_app = next((a for a in apps if a["id"] == trace_app_select), None)
                    db_comp.render_human_approval_gate(selected_gov_app)
                with col_gov2:
                    st.markdown("#### RAG Policy Context Retrieved")
                    db_comp.render_rag_eval_details(data, selected_gov_app)
                    
                st.markdown("---")
                db_comp.render_export_section(data)
                
            with tab5:
                st.markdown("#### Search & Filter Queue")
                col_f1, col_f2, col_f3 = st.columns(3)
                with col_f1:
                    search_q = st.text_input("🔍 Search by Applicant Name or Email", placeholder="e.g. John")
                with col_f2:
                    rec_filt = st.selectbox("AI Recommendation Filter", ["All", "Approve", "Refer", "Decline"])
                with col_f3:
                    status_filt = st.selectbox("Final Status Filter", ["All", "Intake", "Doc_Validation", "Approved", "Declined", "Refer"])
                    
                filters = {
                    "recommendation": rec_filt,
                    "status": status_filt
                }
                
                db_comp.render_advanced_applications_table(data, search_query=search_q, filters=filters)
                
        else:
            st.error("Failed to load evaluation aggregates from the backend server API.")
    except Exception as e:
        st.error(f"Failed to connect to the backend server: {str(e)}")

elif menu == "Policy Chatbot":
    st.markdown("# 💬 Compliance & Underwriting Policy Chatbot")
    st.markdown("Interact directly with the Credit Policy Knowledge Base (RAG) to check guidelines and exception clauses.")
    
    # Initialize message history
    if "chatbot_messages" not in st.session_state:
        st.session_state.chatbot_messages = [
            {"role": "assistant", "content": "Hello! I am your Compliance Assistant. Ask me any question about the lending policies (e.g. KYC OVDs, DTI limits, or Credit Score thresholds)."}
        ]
        
    # Render messages
    for msg in st.session_state.chatbot_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    # Handle user input
    if prompt := st.chat_input("Enter compliance policy question..."):
        # Append user message
        st.session_state.chatbot_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        # Call API
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("🔍 *Searching policies and formulating response...*")
            
            try:
                headers = {}
                if "token" in st.session_state:
                    headers["Authorization"] = f"Bearer {st.session_state.token}"
                    
                response = requests.post(
                    f"{BACKEND_URL}/rag/chat",
                    json={"query": prompt},
                    headers=headers
                )
                
                if response.status_code == 200:
                    res_data = response.json()
                    answer = res_data.get("answer", "No answer received.")
                    citations = res_data.get("citations", [])
                    
                    if citations:
                        answer += f"\n\n**Cited Clauses:** {', '.join([f'`{c}`' for c in citations])}"
                        
                    message_placeholder.markdown(answer)
                    # Append assistant response
                    st.session_state.chatbot_messages.append({"role": "assistant", "content": answer})
                else:
                    err_msg = f"❌ Request failed with status code {response.status_code}."
                    message_placeholder.error(err_msg)
                    st.session_state.chatbot_messages.append({"role": "assistant", "content": err_msg})
            except Exception as e:
                err_msg = f"❌ Connection error: {str(e)}"
                message_placeholder.error(err_msg)
                st.session_state.chatbot_messages.append({"role": "assistant", "content": err_msg})
