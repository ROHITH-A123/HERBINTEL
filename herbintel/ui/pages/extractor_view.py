"""HERBINTEL AI Knowledge Extractor Page.
Uploads scientific literature PDFs or pastes text, runs botanical & chemical NER,
extracts medicinal claims, classifies scientific evidence tiers, preserves source
sentences, and commits verified records to the SQLite knowledge base.
"""

import streamlit as st
from pathlib import Path
import time
from ..components import render_header, render_disclaimer, render_trust_panel
from ..theme import render_evidence_badge, render_status_badge
from ...nlp.extractor import KnowledgeExtractor, PDFExtractor
from ...core.database import insert_plant, insert_compound, insert_paper, insert_claim, link_plant_compound
from ...core.config import SAMPLE_DATA_DIR


def render_extractor_page():
    render_header("AI Knowledge Extractor", "Extract & Verify Literature Claims into Knowledge Graph")
    render_disclaimer()

    st.markdown("""
    Upload a scientific publication PDF (e.g. ethnopharmacology study, clinical trial) or select a sample benchmark paper.
    The AI pipeline extracts **botanical entities**, **phytochemical compounds**, and **therapeutic assertions**,
    tagging each with its exact **source sentence**, **page**, and **evidence tier**.
    """)

    # Input method selection
    input_mode = st.radio("Choose Input Source:", ["📄 Upload Research PDF", "🧪 Preloaded Sample Research Papers", "📝 Paste Literature Text"], horizontal=True)

    pdf_bytes = None
    filename = "document.pdf"
    raw_text = None

    if input_mode == "📄 Upload Research PDF":
        uploaded_file = st.file_uploader("Upload Scientific Paper (PDF):", type=["pdf"])
        if uploaded_file is not None:
            pdf_bytes = uploaded_file.read()
            filename = uploaded_file.name

    elif input_mode == "🧪 Preloaded Sample Research Papers":
        sample_choice = st.selectbox(
            "Select Benchmark Scientific Paper:",
            [
                "sample_turmeric_curcumin_study.pdf (Curcuma longa & Osteoarthritis)",
                "sample_ashwagandha_neuroprotection.pdf (Withania somnifera & Cortisol)"
            ]
        )
        sample_filename = sample_choice.split(" ")[0]
        sample_path = SAMPLE_DATA_DIR / sample_filename
        if sample_path.exists():
            with open(sample_path, "rb") as f:
                pdf_bytes = f.read()
            filename = sample_filename
            st.success(f"Loaded benchmark publication: `{sample_filename}` ({round(len(pdf_bytes)/1024, 1)} KB)")
        else:
            st.error(f"Sample PDF not found at {sample_path}")

    else:
        raw_text = st.text_area(
            "Paste Scientific Literature Text (Abstract, Results, or Methods):",
            height=200,
            placeholder="Curcuma longa rhizome extract containing curcumin was evaluated in a randomized clinical trial..."
        )
        filename = "pasted_text_excerpt"

    # Action Trigger
    run_btn = st.button("🚀 Run AI Extraction Pipeline", type="primary")

    if run_btn:
        if not pdf_bytes and not raw_text:
            st.warning("Please upload a PDF, select a sample paper, or paste literature text first.")
            return

        # Security & Integrity Validations
        if pdf_bytes:
            MAX_PDF_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB limit
            if len(pdf_bytes) > MAX_PDF_SIZE_BYTES:
                st.error(f"Security Alert: Uploaded PDF exceeds the 25 MB file limit ({round(len(pdf_bytes)/(1024*1024), 2)} MB).")
                return
            if not pdf_bytes.startswith(b"%PDF"):
                st.error("Security Alert: Invalid document format. The file signature does not match a valid PDF document.")
                return

        if raw_text:
            if len(raw_text.strip()) < 15:
                st.warning("Input text is too short. Please provide a complete scientific sentence or paragraph.")
                return
            if len(raw_text) > 500_000:
                st.error("Input text exceeds the maximum character threshold (500,000 characters).")
                return

        with st.spinner("Analyzing scientific literature and extracting claims..."):
            t0 = time.time()
            if pdf_bytes:
                results = KnowledgeExtractor.extract_from_pdf_data(pdf_bytes, filename)
            else:
                claims = KnowledgeExtractor.extract_claims_from_text(raw_text)
                results = {
                    "document_info": {"title": "Pasted Literature Excerpt", "author": "Manual Input"},
                    "filename": filename,
                    "page_count": 1,
                    "claims": claims,
                    "plants": [{"scientific_name": c["plant_name"], "occurrences": 1} for c in claims],
                    "compounds": [{"name": c["compound_name"], "occurrences": 1} for c in claims if c.get("compound_name")],
                    "full_text": raw_text
                }
            t_elapsed = round(time.time() - t0, 3)

        st.session_state["extraction_results"] = results
        st.session_state["extraction_time"] = t_elapsed
        st.success(f"Extraction completed in {t_elapsed}s! Found {len(results['plants'])} plants, {len(results['compounds'])} compounds, and {len(results['claims'])} claims.")

    # Render Results if available in session state
    if "extraction_results" in st.session_state:
        results = st.session_state["extraction_results"]
        claims = results["claims"]

        st.markdown("---")
        st.subheader("Extraction Summary")

        sum_col1, sum_col2, sum_col3, sum_col4 = st.columns(4)
        with sum_col1:
            st.metric("Total Pages", results.get("page_count", 1))
        with sum_col2:
            st.metric("Botanical Taxa Found", len(results["plants"]))
        with sum_col3:
            st.metric("Phytocompounds Found", len(results["compounds"]))
        with sum_col4:
            st.metric("Extracted Claims", len(claims))

        # Show extracted entities badges
        if results["plants"]:
            st.markdown("**Identified Plants:** " + " ".join([f"`{p['scientific_name']}`" for p in results["plants"]]))
        if results["compounds"]:
            st.markdown("**Identified Compounds:** " + " ".join([f"`{c['name']}`" for c in results["compounds"]]))

        st.markdown("### Review & Verify Extracted Claims")
        st.caption(
            "Every claim preserves its exact source sentence. "
            "Under the scientific constraint guidelines, all newly extracted claims start as 'Unverified' until reviewed."
        )

        if not claims:
            st.info("No therapeutic claims matching evidence patterns were identified in this document.")
            return

        # Checkbox selection for committing
        selected_claim_indices = []

        with st.expander("Traditional knowledge stewardship (applies to selected claims)"):
            st.caption("Record provenance and access expectations. Do not upload restricted, sacred, or community-controlled knowledge without appropriate permission.")
            knowledge_community = st.text_input("Knowledge community / source (optional)")
            consent_status = st.selectbox("Consent / access status", ["Not recorded", "Public literature", "Community permission documented", "Restricted — do not publish"])
            benefit_sharing_notes = st.text_area("Benefit-sharing or attribution notes (optional)")
            sensitivity_level = st.selectbox("Sensitivity level", ["Standard", "Community-attributed", "Sensitive — restricted"])

        for idx, claim in enumerate(claims):
            with st.container():
                st.markdown(f"#### Claim #{idx+1}: {claim['condition_or_use']}")
                
                tier_badge = render_evidence_badge(claim["evidence_tier"])
                status_badge = render_status_badge(claim["verification_status"])
                st.markdown(f"{tier_badge} {status_badge}", unsafe_allow_html=True)

                c_info = f"🌿 **Plant:** *{claim['plant_name']}*"
                if claim.get("compound_name"):
                    c_info += f" | 🧪 **Compound:** `{claim['compound_name']}`"
                st.markdown(c_info)

                st.markdown(f"""
                <div class="citation-box">
                    "{claim['source_sentence']}"
                </div>
                """, unsafe_allow_html=True)

                st.caption(
                    f"Page: {claim['page_number']} | "
                    f"Section: {claim.get('section', 'N/A')} | "
                    f"Extraction Confidence: {round(claim['extraction_confidence']*100, 1)}% "
                    f"(Note: confidence represents NLP precision, not therapeutic efficacy)"
                )
                render_trust_panel(claim)

                col_chk, col_ver = st.columns([1, 3])
                with col_chk:
                    approve = st.checkbox("Include in Commit", value=True, key=f"chk_claim_{idx}")
                    if approve:
                        selected_claim_indices.append(idx)
                with col_ver:
                    mark_as = st.selectbox(
                        "Review Status:",
                        ["Verified", "Unverified", "Disputed"],
                        index=0,
                        key=f"status_claim_{idx}"
                    )
                    claim["verification_status"] = mark_as

                st.markdown("---")

        # Commit button
        if st.button("💾 Commit Selected Claims to Knowledge Base", type="primary"):
            if not selected_claim_indices:
                st.warning("No claims selected for commitment.")
                return

            with st.spinner("Saving records and establishing graph relations in SQLite..."):
                # 1. Insert Paper
                doc_meta = results.get("document_info", {})
                paper_id = insert_paper({
                    "title": doc_meta.get("title") or results.get("filename", "Extracted Scientific Document"),
                    "authors": doc_meta.get("author", "Literature Extraction"),
                    "journal": "Extracted Research Literature",
                    "year": 2024,
                    "doi": f"10.extract/{int(time.time())}",
                    "abstract": results.get("full_text", "")[:400],
                    "license": "Fair Use / Open Extraction",
                    "pdf_path": results.get("filename"),
                    "is_demo": 0
                })

                # 2. Insert Plants and Compounds
                plant_map = {}
                for p in results["plants"]:
                    p_id = insert_plant({
                        "scientific_name": p["scientific_name"],
                        "common_names": p.get("common_names", ""),
                        "is_demo": 0
                    })
                    plant_map[p["scientific_name"]] = p_id

                comp_map = {}
                for c in results["compounds"]:
                    c_id = insert_compound({
                        "name": c["name"],
                        "chemical_class": c.get("chemical_class", "Bioactive Constituent"),
                        "pubchem_cid": c.get("pubchem_cid"),
                        "is_demo": 0
                    })
                    comp_map[c["name"]] = c_id

                # 3. Insert Claims
                committed_count = 0
                for idx in selected_claim_indices:
                    c_data = claims[idx]
                    p_id = plant_map.get(c_data["plant_name"]) or insert_plant({"scientific_name": c_data["plant_name"]})
                    
                    c_id = None
                    if c_data.get("compound_name"):
                        c_id = comp_map.get(c_data["compound_name"]) or insert_compound({"name": c_data["compound_name"]})
                        link_plant_compound(p_id, c_id, is_demo=0)

                    insert_claim({
                        "plant_id": p_id,
                        "compound_id": c_id,
                        "condition_or_use": c_data["condition_or_use"],
                        "evidence_tier": c_data["evidence_tier"],
                        "source_sentence": c_data["source_sentence"],
                        "section": c_data.get("section", "Literature"),
                        "page_number": c_data.get("page_number", 1),
                        "extraction_confidence": c_data.get("extraction_confidence", 0.85),
                        "verification_status": c_data["verification_status"],
                        "knowledge_community": knowledge_community or None,
                        "consent_status": consent_status,
                        "benefit_sharing_notes": benefit_sharing_notes or None,
                        "sensitivity_level": sensitivity_level,
                        "paper_id": paper_id,
                        "is_demo": 0
                    })
                    committed_count += 1

            st.success(f"Successfully committed {committed_count} claims to the Knowledge Base!")
            st.balloons()
            st.info("You can now visualize these new connections in the **Knowledge Graph** tab or search them in the **Evidence Explorer**.")

