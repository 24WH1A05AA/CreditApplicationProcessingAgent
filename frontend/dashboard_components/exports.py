import streamlit as st
import json
import pandas as pd

def render_export_section(data, selected_app_df=None):
    """
    Renders export buttons for downloading PDF, CSV, JSON, and evaluation logs.
    """
    st.markdown("### 📥 Compliance Reports & Data Exports")
    
    col1, col2, col3 = st.columns(3)
    
    # 1. Export JSON Data
    json_str = json.dumps(data, default=str, indent=2)
    col1.download_button(
        label="📥 Export Dashboard JSON",
        data=json_str,
        file_name="techvest_dashboard_metrics.json",
        mime="application/json",
        use_container_width=True
    )
    
    # 2. Export CSV Table of Applications
    apps = data.get("applications", [])
    if apps:
        csv_df = pd.DataFrame([
            {
                "id": a["id"],
                "loan_amount": a["loan_amount"],
                "loan_purpose": a["loan_purpose"],
                "status": a["status"],
                "credit_score": a["credit_score"],
                "dti_ratio": a["dti_ratio"],
                "created_at": a["created_at"],
                "ai_decision": a["recommendation"]["decision"],
                "human_decision": a["human_decision"]["decision"]
            } for a in apps
        ])
        csv_data = csv_df.to_csv(index=False)
        col2.download_button(
            label="📥 Export Applications CSV",
            data=csv_data,
            file_name="techvest_applications_list.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        col2.button("📥 Export Applications CSV", disabled=True, use_container_width=True)
        
    # 3. Export PDF/Markdown Audit & Evaluation Report
    markdown_report = f"""# TechVest Loan Underwriting AI Agent Evaluation Report
Generated: {pd.Timestamp.now()}
Environment: Sandbox / Development

## 1. Executive Summary
- Total Applications Processed: {data['aggregates']['total_processed']}
- Auto-Approval Success Rate: {data['aggregates']['success_rate']:.2%}
- Avg Processing Time (TAT): {data['aggregates']['avg_processing_time_ms']:.2f} ms
- Fairness Compliance Pass Rate: {data['aggregates']['fairness_pass_rate']:.2%}

## 2. Evaluation Metrics
- Precision: {data['evaluation_metrics']['precision']:.4f}
- Recall: {data['evaluation_metrics']['recall']:.4f}
- F1 Score: {data['evaluation_metrics']['f1_score']:.4f}
- Trace Correctness: {data['evaluation_metrics']['trace_correctness']:.2%}
- Retrieval (RAG) Accuracy: {data['evaluation_metrics']['retrieval_accuracy']:.2%}
- Tool Execution Accuracy: {data['evaluation_metrics']['tool_accuracy']:.2%}

## 3. System and Model Metrics
- CPU Load: {data['system_performance']['cpu_usage_percent']}%
- Memory Load: {data['system_performance']['memory_usage_percent']}%
- LLM Estimated Token Usage: {data['model_metrics']['total_tokens']}
- Estimated Model Costs (USD): ${data['model_metrics']['total_cost_usd']:.4f}

---
CONFIDENTIAL - FOR INTERNAL COMPLIANCE AUDITING ONLY.
"""
    
    col3.download_button(
        label="📥 Download Compliance Report",
        data=markdown_report,
        file_name="techvest_compliance_report.txt",
        mime="text/plain",
        use_container_width=True
    )
    
    col4, col5, col6 = st.columns(3)
    
    # Extra downloads requested
    col4.download_button(
        label="📄 Download Evaluation Matrix",
        data=json.dumps(data.get("evaluation_metrics", {}), indent=2),
        file_name="evaluation_metrics.json",
        mime="application/json",
        use_container_width=True
    )
    
    col5.download_button(
        label="📄 Download Audit Trails Log",
        data=json.dumps([a.get("node_timings") for a in apps], default=str, indent=2),
        file_name="system_audit_logs.json",
        mime="application/json",
        use_container_width=True
    )
    
    col6.download_button(
        label="📄 Recommendation Report",
        data=json.dumps([{"id": a["id"], "reco": a["recommendation"]} for a in apps], default=str, indent=2),
        file_name="recommendation_report.json",
        mime="application/json",
        use_container_width=True
    )
