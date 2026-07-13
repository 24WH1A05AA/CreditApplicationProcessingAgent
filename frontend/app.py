import streamlit as st
import requests
import os

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
        background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
        color: #FFFFFF;
        border: None;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 500;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
    }
    
    div.stButton > button:hover {
        background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%);
        box-shadow: 0 6px 18px rgba(79, 70, 229, 0.5);
        transform: translateY(-1px);
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
    </style>
""", unsafe_allow_html=True)

# Application Sidebar / Navigation
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
            "Decision Details",
            "Human Approval Gate",
            "Audit Trail History"
        ]
    )
    
    st.markdown("---")
    st.markdown("### System Status")
    st.markdown("🟢 **Backend:** Connected")
    st.markdown("🟢 **DB Connection:** SQLite Active")
    st.markdown("🟢 **RAG Index:** Active (0 Documents)")

# Navigation Handlers
if menu == "Dashboard":
    st.markdown("# 📊 Underwriting Dashboard")
    st.markdown("Real-time metrics and application queues.")
    
    # Grid Layout for key metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("""
            <div class="glass-card">
                <div class="metric-label">Total Applications</div>
                <div class="metric-value">124</div>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
            <div class="glass-card">
                <div class="metric-label">Pending Approval</div>
                <div class="metric-value">12</div>
            </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
            <div class="glass-card">
                <div class="metric-label">Turnaround Time (Avg)</div>
                <div class="metric-value">8.2 min</div>
            </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown("""
            <div class="glass-card">
                <div class="metric-label">Fairness Pass Rate</div>
                <div class="metric-value">100%</div>
            </div>
        """, unsafe_allow_html=True)

    # Simple queue display
    st.subheader("Underwriting Queue")
    st.info("The application queue is empty. Submit a new application to get started.")

elif menu == "New Application":
    st.markdown("# 📝 Start New Credit Application")
    st.markdown("Submit borrower details to initiate evaluation.")
    
    with st.form("new_application_form"):
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input("First Name")
            last_name = st.text_input("Last Name")
            dob = st.date_input("Date of Birth")
            email = st.text_input("Email Address")
        with col2:
            monthly_income = st.number_input("Monthly Income (INR)", min_value=0, step=1000)
            existing_emi = st.number_input("Existing Monthly EMIs (INR)", min_value=0, step=500)
            loan_amount = st.number_input("Requested Loan Amount (INR)", min_value=0, step=10000)
            loan_purpose = st.selectbox("Loan Purpose", ["Home Loan", "Personal Loan", "Education Loan", "Car Loan", "Business Loan"])
            
        submitted = st.form_submit_button("Submit Application")
        if submitted:
            st.success(f"Application created successfully! (Mock submission for {first_name} {last_name})")

elif menu == "Upload Documents":
    st.markdown("# 📁 Document Upload Center")
    st.markdown("Upload government IDs, salary slips, and bank statements for validation.")
    
    app_id = st.text_input("Application ID")
    
    col1, col2 = st.columns(2)
    with col1:
        pan_card = st.file_uploader("PAN Card (PDF / Image)", type=["pdf", "jpg", "png"])
        aadhaar_card = st.file_uploader("Aadhaar Card (PDF / Image)", type=["pdf", "jpg", "png"])
    with col2:
        salary_slip = st.file_uploader("Salary Slip (PDF / Image)", type=["pdf", "jpg", "png"])
        bank_statement = st.file_uploader("Bank Statement (PDF)", type=["pdf"])
        
    if st.button("Validate Documents"):
        if app_id:
            st.info("Validating documents... (Processing via Document Validation Agent)")
        else:
            st.warning("Please provide a valid Application ID.")

elif menu == "Decision Details":
    st.markdown("# 🔍 AI Decision Analysis & Citations")
    st.markdown("Inspect RAG policy matching, scoring breakdown, and explanation details.")
    
    st.info("No active application selected. Inspect decision details from the Human Approval Gate or the Dashboard.")

elif menu == "Human Approval Gate":
    st.markdown("# 🛡️ Human-in-the-Loop Approval")
    st.markdown("Underwriter sign-off required for final loan commitment.")
    
    st.warning("No applications pending underwriter review.")

elif menu == "Audit Trail History":
    st.markdown("# 📜 Governance & Audit Logs")
    st.markdown("Traceable records of all tool execution, recommendations, fairness runs, and human decisions.")
    
    st.info("Audit logs are stored securely in SQLite database. Complete log history will appear here once applications are processed.")
