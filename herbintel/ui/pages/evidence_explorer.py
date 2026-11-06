"""HERBINTEL Evidence Explorer & Claims Matrix.
Provides searchable, filterable matrix of all extracted and benchmark medicinal claims,
source sentences, publication references, and curatorial verification workflows.
"""

import streamlit as st
import pandas as pd
from ..components import render_header, render_disclaimer, render_trust_panel
from ..theme import render_evidence_badge, render_status_badge
from ...core.database import get_all_claims, update_claim_verification
from ...core.config import EVIDENCE_TIERS, VERIFICATION_STATUSES


def render_evidence_explorer_page():
    render_header("Evidence Explorer", "Literature Claims, Source Sentences & Curatorial Verification")
    render_disclaimer()

    st.markdown("""
    Explore literature assertions connecting botanical taxa to therapeutic indications.
    Inspect the exact **source sentences**, **scientific papers**, and **evidence tiers**.
    Curators can verify or dispute claims to maintain scientific rigor.
    """)

    # Filter Controls
    f_col1, f_col2, f_col3 = st.columns(3)

    with f_col1:
        tier_opts = ["ALL"] + list(EVIDENCE_TIERS.keys())
        filter_tier = st.selectbox(
            "Evidence Tier:",
            tier_opts,
            format_func=lambda x: "All Evidence Tiers" if x == "ALL" else EVIDENCE_TIERS[x]["label"]
        )

    with f_col2:
        status_opts = ["ALL"] + VERIFICATION_STATUSES
        filter_status = st.selectbox("Verification Status:", status_opts)

    with f_col3:
        search_kw = st.text_input("Search Claims / Text / Plant / Compound:", placeholder="e.g. pain, curcumin, arthritis")

    # Fetch Claims
    claims = get_all_claims(
        filter_tier=filter_tier,
        filter_status=filter_status,
        search_query=search_kw or None
    )

    st.markdown(f"**Found {len(claims)} claim records matching criteria.**")

    # Quick Export options
    if claims:
        df_export = pd.DataFrame([
            {
                "Claim ID": c["id"],
                "Plant": c["plant_name"],
                "Compound": c.get("compound_name") or "None",
                "Indication": c["condition_or_use"],
                "Evidence Tier": c["evidence_tier"],
                "Status": c["verification_status"],
                "Confidence": c["extraction_confidence"],
                "Source Sentence": c["source_sentence"],
                "Section": c.get("section", ""),
                "Page": c.get("page_number", 1),
                "DOI": c.get("paper_doi", ""),
                "Journal": c.get("paper_journal", ""),
                "Year": c.get("paper_year", "")
            }
            for c in claims
        ])

        exp_c1, exp_c2 = st.columns([1, 4])
        with exp_c1:
            csv_data = df_export.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export Claims (CSV)",
                data=csv_data,
                file_name="herbintel_claims_export.csv",
                mime="text/csv"
            )

    st.markdown("---")

    # Render Claim Cards
    if not claims:
        st.info("No claims matched your current filter criteria.")
        return

    for c in claims:
        with st.container():
            st.markdown(f"### Claim #{c['id']}: {c['condition_or_use']}")
            
            tb = render_evidence_badge(c["evidence_tier"])
            sb = render_status_badge(c["verification_status"])
            demo_badge = '<span class="badge badge-demo">BENCHMARK</span>' if c.get("is_demo") else ''
            st.markdown(f"{tb} {sb} {demo_badge}", unsafe_allow_html=True)

            meta_str = f"🌿 **Plant:** *{c['plant_name']}*"
            if c.get("plant_common_names"):
                meta_str += f" ({c['plant_common_names'].split(',')[0]})"
            if c.get("compound_name"):
                meta_str += f" | 🧪 **Bioactive Compound:** `{c['compound_name']}`"
            st.markdown(meta_str)

            # Source sentence
            st.markdown(f"""
            <div class="citation-box">
                "{c['source_sentence']}"
            </div>
            """, unsafe_allow_html=True)

            # Paper / Attribution
            p_info = f"📄 **Source:** *{c.get('paper_title', 'Literature Extraction')}*"
            if c.get("paper_journal"):
                p_info += f" &bull; {c['paper_journal']}"
            if c.get("paper_year"):
                p_info += f" ({c['paper_year']})"
            st.markdown(p_info)

            c_meta_col, action_col = st.columns([3, 2])
            with c_meta_col:
                st.caption(
                    f"Section: `{c.get('section', 'N/A')}` | "
                    f"Page: {c.get('page_number', 1)} | "
                    f"Extraction Confidence: {round(c['extraction_confidence']*100, 1)}%"
                )
                if c.get("paper_doi"):
                    st.caption(f"DOI: [{c['paper_doi']}](https://doi.org/{c['paper_doi']})")

                render_trust_panel(c)

            with action_col:
                act1, act2, act3 = st.columns(3)
                with act1:
                    if st.button("Verify ✅", key=f"btn_ver_{c['id']}"):
                        update_claim_verification(c["id"], "Verified")
                        st.rerun()
                with act2:
                    if st.button("Dispute ⚠️", key=f"btn_disp_{c['id']}"):
                        update_claim_verification(c["id"], "Disputed")
                        st.rerun()
                with act3:
                    if st.button("Reset 🔄", key=f"btn_rst_{c['id']}"):
                        update_claim_verification(c["id"], "Unverified")
                        st.rerun()

            st.markdown("---")

