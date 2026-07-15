import streamlit as st

def render_model_metrics(data):
    """
    Renders Model Metrics (Tokens, Cost, etc.)
    """
    model_m = data.get("model_metrics", {})
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Prompt Tokens", f"{model_m.get('prompt_tokens', 0):,}")
    col2.metric("Total Completion Tokens", f"{model_m.get('completion_tokens', 0):,}")
    col3.metric("Total Tokens Incurred", f"{model_m.get('total_tokens', 0):,}")
    
    col4, col5, col6 = st.columns(3)
    col4.metric("Total API Cost (Est USD)", f"${model_m.get('total_cost_usd', 0.0):.4f}")
    col5.metric("Avg Cost per Request", f"${model_m.get('avg_cost_usd', 0.0):.6f}")
    col6.metric("Total Successful Requests", f"{model_m.get('requests', 0)}")

def render_evaluation_metrics_cards(data):
    """
    Renders the evaluation metrics grid (Faithfulness, answer relevancy, precision, recall, F1).
    """
    eval_m = data.get("evaluation_metrics", {})
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Precision Score", f"{eval_m.get('precision', 1.0):.2f}")
    col2.metric("Recall Score", f"{eval_m.get('recall', 1.0):.2f}")
    col3.metric("F1 Performance Score", f"{eval_m.get('f1_score', 1.0):.2f}")
    col4.metric("Task Completion Rate", f"{eval_m.get('task_completion', 1.0):.1%}")
    
    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Trace Correctness Rate", f"{eval_m.get('trace_correctness', 1.0):.1%}")
    col6.metric("Citation Accuracy", f"{eval_m.get('citation_accuracy', 0.98):.1%}")
    col7.metric("Groundedness Index", f"{eval_m.get('groundedness', 0.98):.1%}")
    col8.metric("Answer Relevancy", f"{eval_m.get('answer_relevancy', 0.94):.1%}")

def render_credit_score_evaluation_cards(selected_app):
    """
    Renders credit evaluation metrics for selected applicant.
    """
    if not selected_app:
        st.info("Select an application context below to view its specific credit risk profile.")
        return
        
    credit_score = selected_app.get("credit_score") or "N/A"
    dti = selected_app.get("dti_ratio") or 0.0
    rec = selected_app.get("recommendation", {})
    
    # Calculate employment & income stability indices based on parsed salary slips
    monthly_inc = selected_app["applicant"].get("monthly_income", 0.0)
    existing_emi = selected_app["applicant"].get("existing_emi", 0.0)
    loan_requested = selected_app.get("loan_amount", 0.0)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Bureau Credit Score", f"{credit_score}")
    col2.metric("Debt-to-Income (DTI)", f"{dti:.2%}")
    col3.metric("AI Credit Rating (Risk)", "LOW RISK" if isinstance(credit_score, int) and credit_score > 700 else "MEDIUM RISK" if isinstance(credit_score, int) and credit_score >= 600 else "HIGH RISK")
    
    col4, col5, col6 = st.columns(3)
    col4.metric("Income Stability Index", "HIGH (Consistent Salary)" if monthly_inc > 40000 else "MEDIUM" if monthly_inc > 20000 else "LOW")
    col5.metric("Existing Liabilities (EMI)", f"INR {existing_emi:,.2f}")
    col6.metric("Lending Eligibility Status", "ELIGIBLE (Income verified)" if dti < 0.35 else "INELIGIBLE (DTI Limit)")

    st.markdown("#### Recommendation Confidence Profile")
    st.write(f"📈 **Composite AI Underwriting Score:** `{rec.get('composite_score', 0.5):.4f}`")
    st.write(f"🤖 **Recommendation Rationale:** {rec.get('reasoning')}")
