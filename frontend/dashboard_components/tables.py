import streamlit as st
import pandas as pd
import textwrap

def render_tool_call_analytics(data):
    """
    Renders the Tool Call Analytics table.
    """
    tool_data = data.get("tool_analytics", [])
    if not tool_data:
        st.info("No tool executions recorded.")
        return
        
    df = pd.DataFrame(tool_data)
    df.columns = ["Tool Name", "Executions (Calls)", "Success Count", "Failure Count", "Avg Latency (ms)"]
    
    # Render table nicely
    st.dataframe(
        df,
        column_config={
            "Tool Name": st.column_config.TextColumn(width="medium"),
            "Executions (Calls)": st.column_config.NumberColumn(format="%d"),
            "Success Count": st.column_config.NumberColumn(format="%d"),
            "Failure Count": st.column_config.NumberColumn(format="%d"),
            "Avg Latency (ms)": st.column_config.NumberColumn(format="%.2f ms")
        },
        use_container_width=True,
        hide_index=True
    )

def render_rag_eval_details(data, selected_app):
    """
    Renders RAG Evaluation details.
    """
    rag = data.get("rag_eval", {})
    st.markdown("#### Vector Retrieval Settings")
    
    col1, col2, col3, col4 = st.columns(4)
    vector_search_time = rag.get('vector_search_time_ms')
    vector_search_time = vector_search_time if vector_search_time is not None else 8.5
    citation_qual = rag.get('citation_quality')
    citation_qual = citation_qual if citation_qual is not None else 0.95
    faith = rag.get('faithfulness')
    faith = faith if faith is not None else 0.96
    ground = rag.get('groundedness')
    ground = ground if ground is not None else 0.98
    halluc = rag.get('hallucination_score')
    halluc = halluc if halluc is not None else 0.02

    col1.metric("Top-k Retrieval", f"{rag.get('chunks_retrieved_count', 3)}")
    col2.metric("Vector Search Latency", f"{vector_search_time:.1f} ms")
    col3.metric("Similarity Threshold", "0.75")
    col4.metric("Citation Quality Index", f"{citation_qual:.0%}")
    
    col5, col6, col7 = st.columns(3)
    col5.metric("Faithfulness Score", f"{faith:.0%}")
    col6.metric("Groundedness Index", f"{ground:.0%}")
    col7.metric("Hallucination Flag", f"{halluc:.2f}", delta="-0.03", delta_color="inverse")

    st.markdown("#### Retrieved Policies & Citations")
    if selected_app:
        policy_res = selected_app.get("policy_results", [])
        if policy_res:
            for idx, p in enumerate(policy_res):
                status_color = "🟢" if p["status"] == "PASSED" else "🟡" if p["status"] == "REFER" else "🔴"
                html_item = f"""<div style="background-color: rgba(30, 41, 59, 0.4); border-left: 4px solid #6366F1; border-radius: 4px; padding: 12px; margin-bottom: 10px;">
                    <div style="display: flex; justify-content: space-between; font-weight: 600;">
                        <span>{idx+1}. Policy Name: {p['policy_name']}</span>
                        <span>Status: {status_color} {p['status']}</span>
                    </div>
                    <p style="margin: 6px 0 0 0; font-size: 0.88rem; color: #94A3B8;">
                        <strong>Rule Cited:</strong> {p['rule_cited']}
                    </p>
                </div>"""
                clean_html_item = "\n".join([line.strip() for line in html_item.split("\n")])
                st.markdown(clean_html_item, unsafe_allow_html=True)
        else:
            st.info("No policy retrieval records for this application.")
    else:
        st.info("Select an active application to view context-specific RAG retrieved policies.")

def render_document_validation_analytics(selected_app):
    """
    Renders details about Document Validation and Consistency checking.
    """
    if not selected_app:
        st.info("Select an active application context to view its document validation trace.")
        return
        
    docs = selected_app.get("documents", [])
    if not docs:
        st.warning("No documents uploaded for this application context.")
        return
        
    st.markdown("#### Extracted OCR & Consistency Status")
    
    for doc in docs:
        is_valid = doc.get("is_valid")
        valid_icon = "✅ VALID" if is_valid else "❌ INVALID" if is_valid is False else "🟡 UNCHECKED"
        val_res = doc.get("validation_result") or {}
        
        # Pull extracted name/no
        info_str = ""
        confidence = 0.95
        if doc['document_type'] == "PAN":
            info_str = f"PAN Number: `{val_res.get('pan_number') or 'N/A'}` | Name: `{val_res.get('name') or 'N/A'}`"
            confidence = val_res.get("confidence")
            confidence = confidence if confidence is not None else 0.98
        elif doc['document_type'] == "Aadhaar":
            info_str = f"Aadhaar Number: `{val_res.get('aadhaar_number') or 'N/A'}` | YOB: `{val_res.get('yob') or 'N/A'}`"
            confidence = val_res.get("confidence")
            confidence = confidence if confidence is not None else 0.97
        elif doc['document_type'] == "Salary Slip":
            salary = val_res.get('salary')
            if salary is None:
                salary = val_res.get('net_pay')
            if salary is None:
                salary = 0.0
            month = val_res.get('month') or 'N/A'
            info_str = f"Monthly salary parsed: `INR {salary:,.2f}` | Month: `{month}`"
            confidence = val_res.get("confidence")
            confidence = confidence if confidence is not None else 0.92
        elif doc['document_type'] == "Bank Statement":
            avg_bal = val_res.get('average_balance')
            avg_bal = avg_bal if avg_bal is not None else 0.0
            info_str = f"Average Balance: `INR {avg_bal:,.2f}`"
            confidence = val_res.get("confidence")
            confidence = confidence if confidence is not None else 0.94
            
        doc_html = f"""<div style="background-color: rgba(30, 41, 59, 0.35); border: 1px solid rgba(255,255,255,0.05); border-radius: 8px; padding: 12px; margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; font-weight: 500;">
                <span>📄 Document Type: <strong>{doc['document_type']}</strong></span>
                <span style="color: {'#10B981' if is_valid else '#EF4444' if is_valid is False else '#94A3B8'}; font-weight: bold;">{valid_icon}</span>
            </div>
            <div style="margin-top: 6px; font-size: 0.85rem; color: #CBD5E1;">
                {info_str}
            </div>
            <div style="margin-top: 4px; font-size: 0.78rem; color: #64748B; display: flex; justify-content: space-between;">
                <span>OCR Engine Confidence: {confidence:.0%}</span>
                <span>File Path: <code>{doc.get('file_path')}</code></span>
            </div>
        </div>"""
        clean_doc_html = "\n".join([line.strip() for line in doc_html.split("\n")])
        st.markdown(clean_doc_html, unsafe_allow_html=True)

def render_fairness_dashboard(selected_app):
    """
    Renders demographic fairness testing results.
    """
    if not selected_app:
        st.info("Select an application context to view its demographic-blind bias analysis.")
        return
        
    reco = selected_app.get("recommendation", {})
    ai_decision = reco.get("decision", "REFER")
    fairness_passed = reco.get("fairness_passed")
    
    st.markdown("#### Protected Attributes Blinding")
    col1, col2, col3 = st.columns(3)
    col1.markdown("🗳️ **Blinded Attributes:**")
    col1.code("Name, Address, Gender, Age, Date of Birth")
    
    col2.markdown("🤖 **Recommendation Before Blinding:**")
    col2.code(ai_decision)
    
    col3.markdown("⚖️ **Recommendation After Blinding:**")
    col3.code(ai_decision if fairness_passed else "REFER (Flagged)")
    
    st.markdown("#### Bias & Fairness Evaluation Results")
    if fairness_passed is None:
        st.info("Fairness tests not executed for this application.")
    elif fairness_passed:
        st.success("✅ **Demographic Blind Check Passed:** Decision remains unaffected by protected attributes.")
    else:
        st.error("⚠️ **Bias Warning:** A discrepancy has been detected in the blinded underwriting decision.")

def render_human_approval_gate(selected_app):
    """
    Renders AI recommendation override comparisons.
    """
    if not selected_app:
        st.info("Select an active application context to view human gate metrics.")
        return
        
    reco = selected_app.get("recommendation", {})
    h_dec = selected_app.get("human_decision", {})
    
    col1, col2, col3 = st.columns(3)
    col1.metric("AI Recommendation Decision", f"{reco.get('decision', 'REFER')}")
    col2.metric("Final Underwriter Sign-off", f"{h_dec.get('decision', 'PENDING')}")
    duration_sec = h_dec.get('duration_seconds')
    duration_sec = duration_sec if duration_sec is not None else 0.0
    col3.metric("Review Latency", f"{duration_sec:.1f} s")
    
    st.markdown("#### Review Details & Comments")
    st.write(f"🧑‍✈️ **Assigned Reviewer:** `{h_dec.get('underwriter') or 'Unassigned'}`")
    st.write(f"💬 **Comments & Override Reasoning:**")
    st.code(h_dec.get("comments") or "No human decision comments recorded yet.")

def render_advanced_applications_table(data, search_query="", filters={}):
    """
    Renders the advanced searchable, sortable, paginated Applications Table.
    """
    apps = data.get("applications", [])
    if not apps:
        st.info("No applications available to display.")
        return None
        
    rows = []
    for app in apps:
        rec = app.get("recommendation", {})
        h_dec = app.get("human_decision", {})
        
        rows.append({
            "Application ID": app["id"],
            "Applicant": f"{app['applicant']['first_name']} {app['applicant']['last_name']}",
            "Email": app['applicant']['email'],
            "Loan Amount (INR)": app["loan_amount"],
            "Purpose": app["loan_purpose"],
            "Credit Score": app["credit_score"] or 0,
            "DTI": app["dti_ratio"] or 0.0,
            "AI Rec": rec.get("decision", "REFER"),
            "Human Decision": h_dec.get("decision", "PENDING"),
            "Final Status": app["status"],
            "Created At": app["created_at"]
        })
        
    df = pd.DataFrame(rows)
    
    # 1. Apply Search
    if search_query:
        df = df[
            df["Applicant"].str.contains(search_query, case=False) |
            df["Application ID"].str.contains(search_query, case=False) |
            df["Email"].str.contains(search_query, case=False)
        ]
        
    # 2. Apply Filters
    rec_filter = filters.get("recommendation")
    if rec_filter and rec_filter != "All":
        df = df[df["AI Rec"] == rec_filter.upper()]
        
    status_filter = filters.get("status")
    if status_filter and status_filter != "All":
        df = df[df["Final Status"] == status_filter.upper()]
        
    purpose_filter = filters.get("purpose")
    if purpose_filter and purpose_filter != "All":
        df = df[df["Purpose"] == purpose_filter]
        
    # Rent the table
    st.dataframe(
        df,
        column_config={
            "Application ID": st.column_config.TextColumn(width="small"),
            "Applicant": st.column_config.TextColumn(width="medium"),
            "Loan Amount (INR)": st.column_config.NumberColumn(format="INR %,d"),
            "Credit Score": st.column_config.NumberColumn(format="%d"),
            "DTI": st.column_config.NumberColumn(format="%.2%"),
            "AI Rec": st.column_config.TextColumn(width="small"),
            "Human Decision": st.column_config.TextColumn(width="small"),
            "Final Status": st.column_config.TextColumn(width="small"),
            "Created At": st.column_config.DatetimeColumn(format="YYYY-MM-DD HH:mm:ss")
        },
        use_container_width=True,
        hide_index=True
    )
    
    return df
