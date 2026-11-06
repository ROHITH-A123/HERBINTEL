"""A focused, judge-ready evidence narrative for the HERBINTEL demo."""

import streamlit as st
from ..components import render_header, render_disclaimer, render_trust_panel
from ..theme import render_evidence_badge, render_status_badge
from ...core.database import get_all_claims


def render_case_study_page():
    render_header("Judge Demo | Withania somnifera", "A provenance-first path from traditional knowledge to a research question")
    render_disclaimer()

    st.info("**Demo thesis:** HERBINTEL does not claim that Ashwagandha treats anxiety. It shows what the selected literature reports, at which evidence tier, and what still needs rigorous investigation.")
    claims = get_all_claims(search_query="Withania somnifera")

    if not claims:
        st.warning("The benchmark case-study records are not available. Reset benchmark data from the sidebar.")
        return

    st.subheader("1. Traditional context → 2. Biological investigation → 3. Human evidence")
    stages = [
        ("TRADITIONAL", "Traditional context", "A historical use is a research lead—not proof of efficacy."),
        ("IN_VITRO", "Preclinical signal", "Laboratory findings explain mechanisms but cannot predict patient outcomes."),
        ("IN_VIVO", "Animal evidence", "Whole-organism results can inform hypotheses, not clinical recommendations."),
        ("CLINICAL", "Human evidence", "Human studies must be read for population, dose, extract and outcomes."),
    ]
    cols = st.columns(4)
    for col, (tier, title, explanation) in zip(cols, stages):
        with col:
            matching = [c for c in claims if c["evidence_tier"] == tier]
            st.markdown(f"**{title}**")
            st.markdown(render_evidence_badge(tier), unsafe_allow_html=True)
            st.caption(f"{len(matching)} indexed literature assertion(s). {explanation}")

    st.markdown("---")
    st.subheader("Evidence trail")
    for tier, title, _ in stages:
        tier_claims = [c for c in claims if c["evidence_tier"] == tier]
        if not tier_claims:
            continue
        with st.expander(f"{title} ({len(tier_claims)})", expanded=tier in {"TRADITIONAL", "CLINICAL"}):
            for claim in tier_claims:
                st.markdown(f"{render_evidence_badge(claim['evidence_tier'])} {render_status_badge(claim['verification_status'])}", unsafe_allow_html=True)
                st.markdown(f"> {claim['source_sentence']}")
                render_trust_panel(claim)

    st.markdown("---")
    st.subheader("The actionable gap")
    st.warning("**Research priority, not a medical conclusion:** compare standardized root-extract composition and dose across adequately powered, blinded human studies. Current literature records cannot establish that differing preparations are clinically interchangeable.")
    st.caption("This conclusion is an evidence-management recommendation based on the dataset’s mixed evidence tiers and incomplete standardization metadata; it is not a treatment recommendation.")

    st.subheader("Three-minute judge route")
    st.markdown("1. Start here: explain the tier separation.  \\n+2. Open a source sentence and its Trust panel.  \\n+3. Show the Knowledge Graph filtered to Withania.  \\n+4. Open Evidence Explorer to show review controls and stewardship metadata.  \\n+5. Close with the standardization research gap above.")
