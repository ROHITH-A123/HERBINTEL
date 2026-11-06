"""HERBINTEL Reusable UI Components.
Renders medical disclaimers, metric cards, attribution footers, and badges.
"""

from typing import Any, Optional
import streamlit as st
from .theme import render_evidence_badge, render_status_badge, CUSTOM_CSS
from ..core.config import SCIENTIFIC_DISCLAIMER


def inject_theme():
    """Injects custom CSS stylesheets into Streamlit head."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_header(title: str, subtitle: str = ""):
    """Renders page header with branding."""
    st.markdown(f'<div class="brand-title">🌿 HERBINTEL | {title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="brand-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def render_disclaimer():
    """Renders mandatory scientific and medical disclaimer banner."""
    st.markdown(f"""
    <div class="disclaimer-card">
        <div class="disclaimer-title">⚠️ SCIENTIFIC ETHNOBOTANY & MEDICAL DISCLAIMER</div>
        {SCIENTIFIC_DISCLAIMER}
    </div>
    """, unsafe_allow_html=True)


def render_metric_card(label: str, value: Any, icon: str = ""):
    """Renders an aesthetic summary metric card."""
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{icon} {value}</div>
        <div class="metric-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def render_trust_panel(claim: dict):
    """Renders a compact, reusable provenance panel for any literature claim."""
    source = "Curated benchmark — human review required" if claim.get("is_demo") else "User-supplied / live literature extraction"
    doi = claim.get("paper_doi")
    pmid = claim.get("paper_pmid")
    ref = f"DOI: [{doi}](https://doi.org/{doi})" if doi else (f"PMID: [{pmid}](https://pubmed.ncbi.nlm.nih.gov/{pmid}/)" if pmid else "Identifier: not available")
    st.markdown("#### Trust panel")
    st.caption(
        f"**Evidence:** {claim.get('evidence_tier', 'Not classified')}  ·  "
        f"**Review:** {claim.get('verification_status', 'Unverified')}  ·  "
        f"**NLP confidence:** {round(claim.get('extraction_confidence', 0) * 100, 1)}%  ·  "
        f"**Location:** p. {claim.get('page_number', 'N/A')}, {claim.get('section', 'Literature')}"
    )
    st.caption(f"**Data source:** {source}  ·  {ref}")
    if claim.get("knowledge_community") or claim.get("consent_status") not in (None, "Not recorded"):
        st.caption(
            f"**Knowledge stewardship:** {claim.get('knowledge_community') or 'Community not recorded'} · "
            f"Consent: {claim.get('consent_status', 'Not recorded')} · "
            f"Sensitivity: {claim.get('sensitivity_level', 'Standard')}"
        )

