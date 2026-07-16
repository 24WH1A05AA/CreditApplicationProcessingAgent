import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import streamlit as st

def render_application_status_pie(data):
    """
    Renders Donut chart showing application statuses.
    """
    aggregates = data.get("aggregates", {})
    categories = ['Approved', 'Referred', 'Declined', 'Pending']
    values = [
        aggregates.get("approved", 0),
        aggregates.get("referred", 0),
        aggregates.get("declined", 0),
        aggregates.get("pending", 0)
    ]
    
    colors = ['#10B981', '#F59E0B', '#EF4444', '#64748B']
    
    fig = go.Figure(data=[go.Pie(
        labels=categories,
        values=values,
        hole=.5,
        marker=dict(colors=colors, line=dict(color='#0F172A', width=2)),
        textinfo='percent+label',
        hoverinfo='label+value'
    )])
    
    fig.update_layout(
        margin=dict(t=10, b=10, l=10, r=10),
        height=260,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False,
        font=dict(color='#F8FAFC')
    )
    
    return fig

def render_applications_over_time(data):
    """
    Renders bar / line chart showing applications received per day.
    """
    apps_per_day = data.get("apps_per_day", {})
    if not apps_per_day:
        apps_per_day = {"2026-07-15": 5}
        
    df = pd.DataFrame(list(apps_per_day.items()), columns=["Date", "Applications"]).sort_values("Date")
    
    fig = px.area(
        df,
        x="Date",
        y="Applications",
        color_discrete_sequence=['#6366F1'],
        labels={"Applications": "Applications Submitted"}
    )
    
    fig.update_layout(
        margin=dict(t=20, b=10, l=10, r=10),
        height=220,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, color='#94A3B8'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', color='#94A3B8'),
        font=dict(color='#F8FAFC')
    )
    
    return fig

def render_applications_per_hour(data):
    """
    Renders bar chart showing applications received per hour.
    """
    apps_per_hour = data.get("apps_per_hour", {})
    if not apps_per_hour:
        apps_per_hour = {"09:00": 2, "10:00": 4, "11:00": 6, "12:00": 3, "13:00": 1, "14:00": 5}
        
    df = pd.DataFrame(list(apps_per_hour.items()), columns=["Hour", "Applications"]).sort_values("Hour")
    
    fig = px.bar(
        df,
        x="Hour",
        y="Applications",
        color_discrete_sequence=['#8B5CF6'],
        labels={"Applications": "Load count"}
    )
    
    fig.update_layout(
        margin=dict(t=20, b=10, l=10, r=10),
        height=220,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, color='#94A3B8'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', color='#94A3B8'),
        font=dict(color='#F8FAFC')
    )
    
    return fig

def render_turnaround_time_line(data):
    """
    Renders latency turnaround line.
    """
    apps = data.get("applications", [])
    if not apps:
        return None
        
    # Pick last 15 applications that have workflow run latency
    plot_data = []
    for app in reversed(apps):
        timings = app.get("node_timings", {})
        latency = sum(timings.values())
        if latency > 0:
            plot_data.append({
                "App ID": app["id"][:8],
                "Turnaround Time (ms)": latency,
                "Credit Score": app.get("credit_score") or 700
            })
        if len(plot_data) >= 15:
            break
            
    if not plot_data:
        plot_data = [{"App ID": "ClearApprove", "Turnaround Time (ms)": 322.0, "Credit Score": 750}]
        
    df = pd.DataFrame(plot_data)
    
    fig = px.line(
        df,
        x="App ID",
        y="Turnaround Time (ms)",
        markers=True,
        color_discrete_sequence=['#F59E0B'],
        hover_data=["Credit Score"]
    )
    
    fig.update_layout(
        margin=dict(t=20, b=10, l=10, r=10),
        height=220,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, color='#94A3B8'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', color='#94A3B8'),
        font=dict(color='#F8FAFC')
    )
    
    return fig

def render_radar_eval_metrics(data):
    """
    Renders Radar Chart of evaluation metrics (resembles LangSmith / Azure AI studio dashboard).
    """
    eval_m = data.get("evaluation_metrics", {})
    categories = [
        'Trace Correctness', 'Task Completion', 'Retrieval Acc',
        'Citation Acc', 'Recommendation Acc', 'Tool Accuracy',
        'Faithfulness', 'Groundedness', 'Answer Relevancy'
    ]
    
    values = [
        eval_m.get("trace_correctness", 1.0) * 100,
        eval_m.get("task_completion", 1.0) * 100,
        eval_m.get("retrieval_accuracy", 1.0) * 100,
        eval_m.get("citation_accuracy", 0.98) * 100,
        eval_m.get("recommendation_accuracy", 1.0) * 100,
        eval_m.get("tool_accuracy", 1.0) * 100,
        eval_m.get("faithfulness", 0.96) * 100,
        eval_m.get("groundedness", 0.98) * 100,
        eval_m.get("answer_relevancy", 0.94) * 100
    ]
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        fillcolor='rgba(99, 102, 241, 0.25)',
        line=dict(color='#6366F1', width=2),
        marker=dict(color='#818CF8', size=6)
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], color='#64748B', gridcolor='rgba(255,255,255,0.05)'),
            angularaxis=dict(color='#94A3B8', gridcolor='rgba(255,255,255,0.05)'),
            bgcolor='rgba(0,0,0,0)'
        ),
        margin=dict(t=30, b=10, l=10, r=10),
        height=280,
        paper_bgcolor='rgba(0,0,0,0)',
        showlegend=False
    )
    
    return fig

def render_risk_distribution_bar(data):
    """
    Renders bar chart showing risk distribution (High, Medium, Low).
    """
    risk = data.get("risk_analytics", {})
    categories = ['Low Risk (>700)', 'Medium Risk (600-700)', 'High Risk (<600)']
    values = [
        risk.get("risk_low", 0),
        risk.get("risk_medium", 0),
        risk.get("risk_high", 0)
    ]
    
    colors = ['#10B981', '#F59E0B', '#EF4444']
    
    fig = go.Figure(data=[go.Bar(
        x=categories,
        y=values,
        marker_color=colors,
        text=values,
        textposition='auto',
        hoverinfo='x+y'
    )])
    
    fig.update_layout(
        margin=dict(t=20, b=10, l=10, r=10),
        height=220,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, color='#94A3B8'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', color='#94A3B8'),
        font=dict(color='#F8FAFC')
    )
    
    return fig

def render_system_perf_gauge(metric_val, name, max_val=100, color='#6366F1'):
    """
    Generates a radial gauge chart for CPU or memory.
    """
    metric_val = metric_val if metric_val is not None else 0.0
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=metric_val,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': name, 'font': {'color': '#94A3B8', 'size': 14}},
        gauge={
            'axis': {'range': [None, max_val], 'tickcolor': "#94A3B8"},
            'bar': {'color': color},
            'bgcolor': "rgba(30, 41, 59, 0.4)",
            'borderwidth': 1,
            'bordercolor': "rgba(255,255,255,0.1)"
        }
    ))
    
    fig.update_layout(
        margin=dict(t=30, b=10, l=10, r=10),
        height=180,
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#F8FAFC')
    )
    
    return fig


def compute_risk_breakdown(credit_score, dti_ratio, monthly_income, has_active_defaults=False):
    # Credit Score Points (Max 35)
    if credit_score >= 750:
        cs_pts = 0
    elif credit_score >= 700:
        cs_pts = 10
    elif credit_score >= 650:
        cs_pts = 20
    elif credit_score >= 600:
        cs_pts = 30
    else:
        cs_pts = 35

    # DTI Ratio Points (Max 35)
    if dti_ratio <= 0.30:
        dti_pts = 0
    elif dti_ratio <= 0.40:
        dti_pts = 10
    elif dti_ratio <= 0.45:
        dti_pts = 20
    else:
        dti_pts = 35

    # Income Points (Max 30)
    if monthly_income >= 100000.0:
        inc_pts = 0
    elif monthly_income >= 50000.0:
        inc_pts = 10
    elif monthly_income >= 25000.0:
        inc_pts = 20
    else:
        inc_pts = 30

    if has_active_defaults:
        # If defaults are active, the total score is set to 100.
        total_prev = cs_pts + dti_pts + inc_pts
        default_pts = max(0, 100 - total_prev)
    else:
        default_pts = 0

    return cs_pts, dti_pts, inc_pts, default_pts


def render_risk_waterfall_chart(app_details, score_details=None):
    """
    Renders an interactive Waterfall Chart explaining how the composite risk score was calculated.
    """
    # 1. Try to get parameters from score_details if provided, else compute from app_details
    credit_score = None
    dti_ratio = None
    monthly_income = None
    has_active_defaults = False
    
    if score_details:
        credit_score = score_details.get("credit_score")
        dti_ratio = score_details.get("dti_ratio")
        has_active_defaults = score_details.get("has_active_defaults", False)
        
    if credit_score is None:
        credit_score = app_details.get("credit_score") or 700
    if dti_ratio is None:
        dti_ratio = app_details.get("dti_ratio") or 0.35
        
    applicant = app_details.get("applicant", {})
    monthly_income = applicant.get("monthly_income") or 50000.0
    
    # Check defaults from documents validation if present
    if not score_details:
        docs = app_details.get("documents", [])
        for doc in docs:
            val_res = doc.get("validation_result") or {}
            if "default" in str(val_res).lower() or (val_res.get("error_message") and "default" in val_res["error_message"].lower()):
                has_active_defaults = True
                
    # 2. Compute points breakdown
    cs_pts, dti_pts, inc_pts, default_pts = compute_risk_breakdown(
        credit_score, dti_ratio, monthly_income, has_active_defaults
    )
    
    total_score = cs_pts + dti_pts + inc_pts + default_pts
    
    # 3. Create Waterfall elements
    x_data = ["Base Score", "Credit Score Penalty", "DTI Ratio Penalty", "Income Penalty"]
    y_data = [0, cs_pts, dti_pts, inc_pts]
    measure_data = ["absolute", "relative", "relative", "relative"]
    text_data = ["0", f"+{cs_pts}", f"+{dti_pts}", f"+{inc_pts}"]
    
    if has_active_defaults or default_pts > 0:
        x_data.append("Active Defaults Penalty")
        y_data.append(default_pts)
        measure_data.append("relative")
        text_data.append(f"+{default_pts}")
        
    x_data.append("Final Risk Score")
    y_data.append(total_score)
    measure_data.append("total")
    text_data.append(f"{total_score}")
    
    fig = go.Figure(go.Waterfall(
        name="Risk Score Breakdown",
        orientation="v",
        measure=measure_data,
        x=x_data,
        y=y_data,
        text=text_data,
        textposition="outside",
        decreasing={"marker":{"color":"#10B981"}},
        increasing={"marker":{"color":"#EF4444"}},
        totals={"marker":{"color":"#6366F1"}},
        connector={"line":{"color":"rgba(255, 255, 255, 0.2)", "width": 1, "dash": "dot"}},
    ))
    
    fig.update_layout(
        title={
            'text': "Credit Risk Penalty Points Waterfall (Lower is Better)",
            'y':0.95,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'color': '#F8FAFC', 'size': 16}
        },
        waterfallgap=0.3,
        margin=dict(t=50, b=20, l=20, r=20),
        height=320,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, color='#94A3B8'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', color='#94A3B8', title="Points (Max 100)"),
        font=dict(color='#F8FAFC')
    )
    
    return fig
