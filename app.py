"""HERBINTEL: AI-Powered Traditional Medicine Intelligence Platform.
EthnoHack 2026 Submission.
Main Streamlit Application Entrypoint.
"""

import streamlit as st
from pathlib import Path
import logging

# Configure Streamlit page settings
st.set_page_config(
    page_title="HERBINTEL | Traditional Medicine Intelligence",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Core imports
from herbintel.core.config import DATABASE_PATH, SCIENTIFIC_DISCLAIMER
from herbintel.core.database import init_db, seed_benchmark_data, get_dashboard_metrics
from herbintel.ui.components import inject_theme
from herbintel.ui.pages.dashboard import render_dashboard_page
from herbintel.ui.pages.plant_explorer import render_plant_explorer_page
from herbintel.ui.pages.extractor_view import render_extractor_page
from herbintel.ui.pages.knowledge_graph_view import render_knowledge_graph_page
from herbintel.ui.pages.evidence_explorer import render_evidence_explorer_page
from herbintel.ui.pages.validator_view import render_validator_page
from herbintel.ui.pages.discovery_view import render_discovery_page
from herbintel.ui.pages.case_study import render_case_study_page
from herbintel.ui.pages.validation_view import render_validation_page

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("herbintel")

# Inject theme CSS
inject_theme()

# Ensure Database is initialized and seeded on first run
if not DATABASE_PATH.exists():
    init_db()
    seed_benchmark_data()
else:
    # Ensure tables exist
    init_db()
    seed_benchmark_data()


def render_methodology_page():
    """Renders scientific methodology, provenance, and constraints."""
    st.markdown('<div class="brand-title">🌿 HERBINTEL | Scientific Methodology & Constraints</div>', unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("""
    ### Scientific & Methodological Framework

    Traditional medicine systems (e.g. Ayurveda, Traditional Chinese Medicine, Unani, indigenous ethnobotany) represent
    millennia of observational human knowledge. However, translating folkloric indications into verified biomedical applications
    requires rigorous, multi-tiered evidence synthesis.

    HERBINTEL implements a strict **Evidence Hierarchy**:

    ```
                      ┌───────────────────────────────────────┐
                      │  Level 5: Human Clinical Trials (RCT) │
                      ├───────────────────────────────────────┤
                      │  Level 4: Systematic Reviews / Meta   │
                      ├───────────────────────────────────────┤
                      │  Level 3: In Vivo Animal Models       │
                      ├───────────────────────────────────────┤
                      │  Level 2: In Vitro Laboratory Assays  │
                      ├───────────────────────────────────────┤
                      │  Level 1: Traditional / Ethnobotanical│
                      └───────────────────────────────────────┘
    ```

    #### Guiding Scientific Constraints
    1. **Provenance-first extraction:** Entity and evidence extraction is assistive, never authoritative. Every output retains its source context and requires human review.
    2. **Evidence Tier Partitioning:** Traditional folkloric uses are never conflated with in vitro assays or human clinical evidence.
    3. **NLP Confidence vs Scientific Efficacy:** Extraction confidence scores strictly reflect natural language syntactic certainty, NOT biological potency or clinical efficacy.
    4. **Source Sentence Preservation:** Every claim retains its verbatim source sentence, page number, and publication DOI.
    5. **Curatorial Verification:** Extracted claims remain labeled `Unverified` until explicitly reviewed by qualified researchers.
    6. **Non-Diagnostic Policy:** HERBINTEL is a research platform, strictly not intended for clinical diagnosis or prescription.

    #### Traditional Knowledge Stewardship
    HERBINTEL records a knowledge community, consent/access status, benefit-sharing notes, and sensitivity level for every curator-submitted claim when available. Sensitive or community-controlled knowledge must not be published or commercialized by default.

    #### Integrated Open Bioinformatics Databases
    * **NCBI PubChem:** Chemical identifiers, Canonical SMILES, 2D molecular structures.
    * **Europe PMC & PubMed:** Open-access biomedical publications and citation metadata.
    * **Kew Plants of the World Online (POWO):** Botanical nomenclature and taxonomic status.
    * **GBIF (Global Biodiversity Information Facility):** Georeferenced botanical occurrences and distributions.
    """)


def main():
    # Sidebar Navigation
    st.sidebar.markdown("""
    <div style="text-align: center; padding: 0.5rem 0 1rem 0;">
        <h2 style="color: #1B5E20; margin: 0;">🌿 HERBINTEL</h2>
        <span style="font-size: 0.82rem; color: #666; font-weight: 600;">Traditional Medicine AI Platform</span><br>
        <span style="font-size: 0.72rem; color: #2E7D32; background: #E8F5E9; padding: 2px 6px; border-radius: 4px; font-weight: 700;">EthnoHack 2026</span>
    </div>
    """, unsafe_allow_html=True)

    menu_options = [
        "📊 Research Dashboard",
        "🎯 Judge Demo: Withania Case Study",
        "🌿 Plant Explorer",
        "🔬 AI Knowledge Extractor",
        "🔎 AI Research Discovery",
        "🕸️ Knowledge Graph",
        "📑 Evidence Explorer",
        "✅ Validation & Audit",
        "🌍 Biodiversity Explorer",
        "ℹ️ Methodology & Constraints",
    ]

    # Support deep-linking via URL query params (e.g. ?page=plant)
    query_page = st.query_params.get("page", "").lower()
    default_index = 0
    if "plant" in query_page:
        default_index = 2
    elif "case" in query_page or "demo" in query_page:
        default_index = 1
    elif "extract" in query_page:
        default_index = 3
    elif "discovery" in query_page or "search" in query_page:
        default_index = 4
    elif "graph" in query_page:
        default_index = 5
    elif "evidence" in query_page:
        default_index = 6
    elif "validation" in query_page or "audit" in query_page:
        default_index = 7
    elif "biodiversity" in query_page or "validator" in query_page:
        default_index = 8
    elif "method" in query_page:
        default_index = 9

    nav_selection = st.sidebar.radio(
        "Navigation Menu:",
        menu_options,
        index=default_index
    )

    # Sidebar Database Metrics Snapshot
    st.sidebar.markdown("---")
    st.sidebar.caption("📊 **Knowledge Base Snapshot**")
    try:
        metrics = get_dashboard_metrics()
        st.sidebar.markdown(f"""
        * **Plants:** `{metrics['plants']}`
        * **Compounds:** `{metrics['compounds']}`
        * **Claims:** `{metrics['claims']}`
        * **Papers:** `{metrics['papers']}`
        """)
    except Exception as e:
        st.sidebar.caption(f"Status: {e}")

    # Database Maintenance Controls
    with st.sidebar.expander("⚙️ Knowledge Base Tools"):
        if st.button("Reset Benchmark Data"):
            seed_benchmark_data(force=True)
            st.success("Re-seeded benchmark data!")
            st.rerun()

    # Route to selected page
    if nav_selection == "📊 Research Dashboard":
        render_dashboard_page()
    elif nav_selection == "🎯 Judge Demo: Withania Case Study":
        render_case_study_page()
    elif nav_selection == "🌿 Plant Explorer":
        render_plant_explorer_page()
    elif nav_selection == "🔬 AI Knowledge Extractor":
        render_extractor_page()
    elif nav_selection == "🔎 AI Research Discovery":
        render_discovery_page()
    elif nav_selection == "🕸️ Knowledge Graph":
        render_knowledge_graph_page()
    elif nav_selection == "📑 Evidence Explorer":
        render_evidence_explorer_page()
    elif nav_selection == "✅ Validation & Audit":
        render_validation_page()
    elif nav_selection == "🌍 Biodiversity Explorer":
        render_validator_page()
    elif nav_selection == "ℹ️ Methodology & Constraints":
        render_methodology_page()


if __name__ == "__main__":
    main()

