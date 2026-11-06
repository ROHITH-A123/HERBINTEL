"""HERBINTEL Dashboard Page.
Displays high-level research intelligence metrics, scientific evidence distributions,
and ethnobotanical discovery highlights.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from ..components import render_header, render_disclaimer, render_metric_card
from ..theme import render_evidence_badge
from ...core.database import get_dashboard_metrics, get_all_plants, get_all_claims
from ...core.config import EVIDENCE_TIERS


def render_dashboard_page():
    render_header("Research Dashboard", "Ethnobotanical Intelligence, Phytochemistry & Evidence Analytics")
    render_disclaimer()

    metrics = get_dashboard_metrics()

    # Metric Row
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        render_metric_card("Medicinal Plants", metrics["plants"], "🌿")
    with c2:
        render_metric_card("Phytocompounds", metrics["compounds"], "🧪")
    with c3:
        render_metric_card("Research Papers", metrics["papers"], "📚")
    with c4:
        render_metric_card("Extracted Claims", metrics["claims"], "💡")
    with c5:
        verified_pct = round((metrics["verified_claims"] / max(1, metrics["claims"])) * 100, 1)
        render_metric_card("Human-Reviewed Claims", f"{metrics['verified_claims']} ({verified_pct}%)", "✅")

    st.markdown("<br>", unsafe_allow_html=True)

    # Visualizations Row
    col_chart1, col_chart2 = st.columns([3, 2])

    with col_chart1:
        st.subheader("Scientific Evidence Hierarchy Distribution")
        evidence_counts = metrics["evidence_breakdown"]
        
        if evidence_counts:
            tier_labels = []
            tier_values = []
            tier_colors = []
            
            for code, count in evidence_counts.items():
                info = EVIDENCE_TIERS.get(code, {})
                tier_labels.append(info.get("label", code))
                tier_values.append(count)
                tier_colors.append(info.get("color", "#888888"))

            fig = go.Figure(data=[go.Pie(
                labels=tier_labels,
                values=tier_values,
                hole=0.48,
                marker=dict(colors=tier_colors),
                textinfo="label+value+percent",
                insidetextorientation="radial"
            )])
            fig.update_layout(
                margin=dict(t=20, b=20, l=10, r=10),
                height=340,
                legend=dict(orientation="h", y=-0.15)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No evidence claims available in database.")

    with col_chart2:
        st.subheader("Curatorial Verification Status")
        verif_counts = metrics["verification_breakdown"]
        
        status_labels = list(verif_counts.keys())
        status_vals = list(verif_counts.values())
        status_colors = ["#2E7D32" if s == "Verified" else ("#E65100" if s == "Unverified" else "#C62828") for s in status_labels]

        fig_bar = go.Figure(data=[go.Bar(
            x=status_labels,
            y=status_vals,
            marker_color=status_colors,
            text=status_vals,
            textposition="auto"
        )])
        fig_bar.update_layout(
            margin=dict(t=20, b=20, l=10, r=10),
            height=340,
            xaxis_title="Status",
            yaxis_title="Claim Count",
            plot_bgcolor="rgba(245,245,245,0.4)"
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")

    # Ethnobotanical Benchmarks and Quick Navigation
    st.subheader("Featured Ethnobotanical Discovery Benchmarks")
    st.caption("Demonstrable historical breakthroughs bridging traditional plant lore to modern pharmaceutical medicine.")

    b1, b2, b3 = st.columns(3)
    with b1:
        st.markdown("""
        **🌱 Artemisia annua &rarr; Artemisinin**
        * Nobel Prize in Physiology/Medicine (2015 - Tu Youyou).
        * *Traditional source:* Ge Hong's 340 AD Chinese medical manual for malaria fevers.
        * *Status:* Global standard-of-care ACT antimalarial.
        """)
    with b2:
        st.markdown("""
        **🌿 Catharanthus roseus &rarr; Vinblastine**
        * First discovered from Jamaican traditional folk tea for diabetes.
        * Serendipitously revealed profound bone marrow suppression and antineoplastic efficacy.
        * *Status:* Essential chemotherapy for Hodgkin lymphoma and childhood leukemia.
        """)
    with b3:
        st.markdown("""
        **🌲 Salix alba &rarr; Salicin (Aspirin)**
        * Recorded in Egyptian Ebers Papyrus (~1500 BC) and Hippocratic texts for pain.
        * Precursor to synthetic Acetylsalicylic Acid.
        * *Status:* World's most widely consumed non-steroidal anti-inflammatory drug.
        """)

