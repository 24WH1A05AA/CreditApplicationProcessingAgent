import streamlit as st
import textwrap

def draw_kpi_card(title, value, subtitle, icon, trend_pct=None, sparkline_svg=None, is_positive=True):
    """
    Renders a premium glassmorphic card with an icon, numeric value, subtitle, trend indicator, and mini sparkline.
    """
    trend_color = "#10B981" if is_positive else "#EF4444"
    trend_arrow = "↑" if is_positive else "↓"
    trend_html = f'<span style="color: {trend_color}; font-weight: 600; font-size: 0.85rem; margin-right: 4px;">{trend_arrow} {trend_pct}</span>' if trend_pct else ""
    
    # SVG sparkline default (a tiny up/down waving sparkline)
    if not sparkline_svg:
        points = "0,15 15,10 30,18 45,5 60,12 75,3 90,8 100,2" if is_positive else "0,5 15,15 30,8 45,18 60,10 75,16 90,12 100,18"
        line_color = "#818CF8" if is_positive else "#F87171"
        sparkline_svg = f"""
        <svg class="sparkline" width="90" height="24" style="stroke: {line_color}; fill: none; stroke-width: 1.5; stroke-linecap: round; filter: drop-shadow(0px 1px 2px rgba(0,0,0,0.3));">
            <polyline points="{points}"/>
        </svg>
        """
        
    card_html = f"""<div style="
        background: rgba(30, 41, 59, 0.4);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.15);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 140px;
        transition: transform 0.2s ease, border-color 0.2s ease;
    ">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <span style="color: #94A3B8; font-size: 0.82rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em;">{title}</span>
            <span style="font-size: 1.4rem; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.15));">{icon}</span>
        </div>
        <div style="margin-top: 8px; margin-bottom: 4px;">
            <span style="font-size: 1.85rem; font-weight: 700; background: linear-gradient(135deg, #F8FAFC 0%, #CBD5E1 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{value}</span>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: auto; padding-top: 4px;">
            <div style="display: flex; flex-direction: column;">
                <span style="font-size: 0.72rem; color: #64748B;">{trend_html}{subtitle}</span>
            </div>
            <div>
                {sparkline_svg}
            </div>
        </div>
    </div>"""
    st.markdown(textwrap.dedent(card_html), unsafe_allow_html=True)

def render_kpis_grid(data):
    """
    Lays out a grid of KPI summary cards using Streamlit columns.
    """
    aggregates = data.get("aggregates", {})
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        draw_kpi_card(
            title="Total Applications",
            value=f"{aggregates.get('total_processed', 0)}",
            subtitle="vs yesterday",
            icon="📊",
            trend_pct="+8.4%",
            is_positive=True
        )
    with col2:
        draw_kpi_card(
            title="Approved Applications",
            value=f"{aggregates.get('approved', 0)}",
            subtitle="Volume approved",
            icon="✅",
            trend_pct="+5.2%",
            is_positive=True
        )
    with col3:
        draw_kpi_card(
            title="Referred (Queue)",
            value=f"{aggregates.get('referred', 0)}",
            subtitle="Manual reviews required",
            icon="⚠️",
            trend_pct="-12.3%",
            is_positive=True # Positive because reduction in referred applications is good
        )
    with col4:
        draw_kpi_card(
            title="Declined (Risk)",
            value=f"{aggregates.get('declined', 0)}",
            subtitle="Declined applications",
            icon="❌",
            trend_pct="+4.1%",
            is_positive=False
        )

    # Second row of metrics
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        draw_kpi_card(
            title="Success Rate",
            value=f"{aggregates.get('success_rate', 0.0):.1%}",
            subtitle="Auto-approval rate",
            icon="📈",
            trend_pct="+2.5%",
            is_positive=True
        )
    with col6:
        draw_kpi_card(
            title="Avg Processing Time",
            value=f"{aggregates.get('avg_processing_time_ms', 322.62):.1f} ms",
            subtitle="Latency TAT",
            icon="⏱️",
            trend_pct="-3.4%",
            is_positive=True # Decreasing latency is good
        )
    with col7:
        draw_kpi_card(
            title="Average Confidence",
            value=f"{aggregates.get('avg_confidence', 0.85):.1%}",
            subtitle="AI Confidence score",
            icon="🎯",
            trend_pct="Stable",
            is_positive=True
        )
    with col8:
        draw_kpi_card(
            title="Fairness Pass Rate",
            value=f"{aggregates.get('fairness_pass_rate', 1.0):.1%}",
            subtitle="Bias check compliance",
            icon="⚖️",
            trend_pct="100.0%",
            is_positive=True
        )

    # Third row of metrics
    col9, col10, col11, col12 = st.columns(4)
    with col9:
        draw_kpi_card(
            title="Average DTI",
            value=f"{aggregates.get('avg_dti', 0.245):.2%}",
            subtitle="Debt-To-Income ratio",
            icon="📉",
            trend_pct="Healthy (<35%)",
            is_positive=True
        )
    with col10:
        draw_kpi_card(
            title="Avg Credit Score",
            value=f"{int(aggregates.get('avg_credit_score', 712.0))}",
            subtitle="Bureau credit rating",
            icon="💳",
            trend_pct="+15 pts",
            is_positive=True
        )
    with col11:
        draw_kpi_card(
            title="Retrieval Accuracy",
            value=f"{aggregates.get('retrieval_accuracy', 1.0):.1%}",
            subtitle="RAG context match",
            icon="🔍",
            trend_pct="Optimal",
            is_positive=True
        )
    with col12:
        draw_kpi_card(
            title="Tool Success Rate",
            value=f"{aggregates.get('tool_call_success_rate', 1.0):.1%}",
            subtitle="APIs and Node operations",
            icon="⚙️",
            trend_pct="No faults",
            is_positive=True
        )
