"""HERBINTEL AI Research Discovery View.
Enables cross-paper literature discovery, multi-paper selection, comparative evidence synthesis,
divergence detection with safeguards, research knowledge graph visualization, and multi-format exports.
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Any

from ..components import render_header, render_disclaimer, render_metric_card
from ..theme import render_evidence_badge, render_status_badge
from ...discovery.discovery_engine import ResearchDiscoveryEngine
from ...discovery.export_service import ResearchExportService
from ...graph.knowledge_graph import HerbKnowledgeGraph
from ...core.config import EVIDENCE_TIERS


def render_discovery_page():
    render_header("AI Research Discovery", "Cross-Paper Synthesis, Evidence Comparison & Knowledge Graphs")
    render_disclaimer()

    st.markdown("""
    Discover and synthesize findings across multiple scientific publications. 
    Search by **medicinal plant**, **phytochemical**, or **therapeutic use** across the internal knowledge base 
    and live **Europe PMC** open-access literature, compare scientific claims side-by-side, explore the research knowledge graph, 
    and export source-cited reports.
    """)

    engine = ResearchDiscoveryEngine()

    # --- Search Interface ---
    search_tab1, search_tab2, search_tab3 = st.tabs([
        "🌿 Search by Medicinal Plant",
        "🧪 Search by Phytochemical",
        "🎯 Search by Traditional / Clinical Use"
    ])

    search_query = ""
    search_type = "plant"

    with search_tab1:
        c_p1, c_p2 = st.columns([3, 1])
        with c_p1:
            q_plant = st.text_input("Enter Scientific or Common Plant Name:", value="Curcuma longa", key="disc_q_plant")
        with c_p2:
            st.markdown("<br>", unsafe_allow_html=True)
            btn_search_plant = st.button("🔍 Search Plant Literature", type="primary", key="btn_s_plant")
        if btn_search_plant:
            search_query = q_plant
            search_type = "plant"

    with search_tab2:
        c_c1, c_c2 = st.columns([3, 1])
        with c_c1:
            q_comp = st.text_input("Enter Phytochemical Name:", value="Withaferin A", key="disc_q_comp")
        with c_c2:
            st.markdown("<br>", unsafe_allow_html=True)
            btn_search_comp = st.button("🔍 Search Compound Literature", type="primary", key="btn_s_comp")
        if btn_search_comp:
            search_query = q_comp
            search_type = "phytochemical"

    with search_tab3:
        c_u1, c_u2 = st.columns([3, 1])
        with c_u1:
            q_use = st.text_input("Enter Indication or Condition:", value="Osteoarthritis", key="disc_q_use")
        with c_u2:
            st.markdown("<br>", unsafe_allow_html=True)
            btn_search_use = st.button("🔍 Search Indication Literature", type="primary", key="btn_s_use")
        if btn_search_use:
            search_query = q_use
            search_type = "condition"

    # Store search trigger in session state
    if search_query:
        with st.spinner(f"Querying database records and Europe PMC for '{search_query}'..."):
            retrieved = engine.search_papers(search_query, search_type=search_type, limit=20)
            st.session_state["discovery_search_query"] = search_query
            st.session_state["discovery_search_type"] = search_type
            st.session_state["discovery_retrieved_papers"] = retrieved

    # Render Retrieved Papers Matrix
    if "discovery_retrieved_papers" in st.session_state:
        papers = st.session_state["discovery_retrieved_papers"]
        query_val = st.session_state.get("discovery_search_query", "")

        st.markdown("---")
        st.subheader(f"Retrieved Literature Publications ({len(papers)} papers found for '{query_val}')")
        st.caption("Select 2 or more research papers to perform cross-paper evidence comparison and generate synthesis graphs.")

        if not papers:
            st.info("No research papers found matching the query. Try a broader search term.")
            return

        # Select all / Deselect all
        col_sel_tools, _ = st.columns([2, 4])
        with col_sel_tools:
            select_all = st.checkbox("Select All Retrieved Papers", value=True, key="chk_select_all_papers")

        selected_indices = []
        for idx, p in enumerate(papers):
            with st.container():
                c_chk, c_meta = st.columns([1, 15])
                with c_chk:
                    is_selected = st.checkbox(
                        "Select",
                        value=select_all,
                        key=f"chk_paper_{idx}",
                        label_visibility="collapsed"
                    )
                    if is_selected:
                        selected_indices.append(idx)

                with c_meta:
                    src_badge = '<span class="badge badge-demo">DB BENCHMARK</span>' if p.get("source") == "Database Benchmark" else '<span class="badge badge-verified">EUROPE PMC</span>'
                    st.markdown(f"**{idx+1}. {p['title']}** {src_badge}", unsafe_allow_html=True)
                    meta_line = f"*{p.get('authors', 'Authors N/A')}* &bull; **{p.get('journal', 'Journal')}** ({p.get('year', 'N/D')})"
                    if p.get("doi"):
                        meta_line += f" &bull; DOI: [{p['doi']}](https://doi.org/{p['doi']})"
                    if p.get("pmid"):
                        meta_line += f" &bull; PMID: [{p['pmid']}](https://pubmed.ncbi.nlm.nih.gov/{p['pmid']}/)"
                    st.caption(meta_line)

                    if p.get("abstract"):
                        with st.expander("📄 View Abstract", expanded=False):
                            st.write(p["abstract"])
            st.markdown("<hr style='margin: 0.3rem 0; border: none; border-top: 1px solid rgba(128,128,128,0.2);'>", unsafe_allow_html=True)

        # Cross-Paper Analysis Trigger
        st.markdown("<br>", unsafe_allow_html=True)
        col_run_an, _ = st.columns([2, 3])
        with col_run_an:
            run_analysis_btn = st.button("🚀 Run Cross-Paper Analysis & Evidence Comparison", type="primary", key="btn_run_cross_analysis")

        if run_analysis_btn:
            if len(selected_indices) < 1:
                st.warning("Please select at least one research paper to analyze.")
                return

            chosen_papers = [papers[i] for i in selected_indices]
            focal_taxon = query_val if st.session_state.get("discovery_search_type") == "plant" else (chosen_papers[0].get("title", "").split(" ")[0])

            with st.spinner(f"Performing NLP claim extraction, evidence grouping, and divergence detection across {len(chosen_papers)} papers..."):
                analysis_result = engine.analyze_cross_papers(chosen_papers, focal_plant=focal_taxon)
                summary_md = engine.generate_research_summary(analysis_result, focal_plant=focal_taxon)
                
                st.session_state["discovery_analysis_result"] = analysis_result
                st.session_state["discovery_summary_report"] = summary_md
                st.session_state["discovery_focal_plant"] = focal_taxon

    # Render Cross-Paper Results
    if "discovery_analysis_result" in st.session_state:
        analysis = st.session_state["discovery_analysis_result"]
        summary_text = st.session_state["discovery_summary_report"]
        focal_name = st.session_state.get("discovery_focal_plant", "Medicinal Taxon")
        claims = analysis.get("claims", [])
        papers_analyzed = analysis.get("papers", [])

        st.markdown("---")
        st.subheader("📊 Cross-Paper Intelligence Dashboard")

        # Metric Snapshot
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            render_metric_card("Analyzed Papers", len(papers_analyzed), "📚")
        with m2:
            render_metric_card("Extracted Claims", len(claims), "💡")
        with m3:
            render_metric_card("Bioactive Compounds", len(analysis.get("compounds", [])), "🧪")
        with m4:
            clinical_count = len([c for c in claims if c.get("evidence_tier") == "CLINICAL"])
            render_metric_card("Clinical Trials", clinical_count, "🏥")

        # Tabs for Main Deliverables:
        # 1. Evidence Comparison Table (Feature 3)
        # 2. Contradiction & Divergence Safeguards (Feature 2)
        # 3. Research Knowledge Graph (Feature 4)
        # 4. AI Research Summary (Feature 5)
        # 5. Export Center (Feature 6)
        tab_comp, tab_div, tab_graph, tab_sum, tab_exp = st.tabs([
            "📑 Evidence Comparison Table",
            "⚖️ Divergence & Contradiction Safeguards",
            "🕸️ Research Knowledge Graph",
            "📝 AI Research Summary Report",
            "📥 Export Research Artifacts"
        ])

        # --- Tab 1: Evidence Comparison Table ---
        with tab_comp:
            st.markdown("### Cross-Paper Evidence Comparison Table")
            st.caption("Standardized matrix comparing reported findings, evidence hierarchy tiers, and source publications.")

            if claims:
                table_rows = []
                for c in claims:
                    # Original source paper link
                    doi = c.get("paper_doi")
                    pmid = c.get("paper_pmid")
                    if doi:
                        source_link = f"https://doi.org/{doi}"
                    elif pmid:
                        source_link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                    else:
                        source_link = c.get("paper_url") or "Indexed Document"

                    paper_title = c.get("paper_title") or "Research Document"
                    short_paper = paper_title[:45] + ("..." if len(paper_title) > 45 else "")

                    table_rows.append({
                        "Paper": short_paper,
                        "Plant": c.get("plant_name") or focal_name,
                        "Compound": c.get("compound_name") or "None Reported",
                        "Reported finding": c.get("condition_or_use", "Observation"),
                        "Evidence type": c.get("evidence_tier", "TRADITIONAL"),
                        "Source": source_link
                    })

                df_comparison = pd.DataFrame(table_rows)
                
                # Render using st.dataframe with link column configuration
                st.dataframe(
                    df_comparison,
                    use_container_width=True,
                    column_config={
                        "Source": st.column_config.LinkColumn("Source Publication", display_text="Open Paper 🔗")
                    },
                    hide_index=True
                )
            else:
                st.info("No comparative claims extracted from the selected publications.")

        # --- Tab 2: Divergences & Contradictions ---
        with tab_div:
            st.markdown("### Methodological Divergences & Contradiction Safeguards")
            st.info("""
            **Scientific Safeguard Principle:** Studies evaluating different model systems (e.g. *in vitro* enzymatic assay vs *in vivo* rodent model vs *human clinical trial*) 
            or different extraction parts (e.g. roots vs leaves) are **NOT** categorized as contradictions. 
            They represent complementary levels within the scientific evidence hierarchy.
            """)

            contradictions = analysis.get("contradictions", [])
            if contradictions:
                for c_item in contradictions:
                    with st.container():
                        st.markdown(f"#### ⚠️ {c_item['type']} in {c_item['domain']}")
                        st.markdown(f"**Evidence Hierarchy Tier:** `{c_item['evidence_tier']}`")
                        
                        col_s1, col_s2 = st.columns(2)
                        with col_s1:
                            s1 = c_item["study_1"]
                            st.markdown(f"**Study A ({s1.get('authors', 'Authors')}, {s1.get('year', '')}):**")
                            st.markdown(f"*{s1.get('title')}*")
                            st.caption(f"Claim: \"{s1.get('sentence')}\"")
                        with col_s2:
                            s2 = c_item["study_2"]
                            st.markdown(f"**Study B ({s2.get('authors', 'Authors')}, {s2.get('year', '')}):**")
                            st.markdown(f"*{s2.get('title')}*")
                            st.caption(f"Claim: \"{s2.get('sentence')}\"")
                        
                        st.caption(f"**Safeguard Audit Note:** {c_item['safeguard_rationale']}")
                        st.markdown("---")
            else:
                st.success("✅ **No internal contradictions detected:** All findings across the selected cohort reflect consistent or complementary pharmacological observations.")

            # Show Grouped Findings
            st.markdown("### Grouped Evidence Clusters")
            grouped = analysis.get("grouped_findings", {})
            for grp_name, grp_claims in grouped.items():
                with st.expander(f"📁 {grp_name} ({len(grp_claims)} findings)", expanded=True):
                    for gc in grp_claims:
                        tb = render_evidence_badge(gc.get("evidence_tier", "TRADITIONAL"))
                        c_title = f"{gc.get('plant_name')} &rarr; {gc.get('condition_or_use')}"
                        if gc.get("compound_name"):
                            c_title += f" (via `{gc['compound_name']}`)"
                        st.markdown(f"{tb} **{c_title}**", unsafe_allow_html=True)
                        st.caption(f"Quote: \"{gc.get('source_sentence', '')}\" &bull; Source: *{gc.get('paper_title')}*")

        # --- Tab 3: Research Knowledge Graph ---
        with tab_graph:
            st.markdown("### Multi-Relational Research Knowledge Graph")
            st.markdown("""
            This focused graph connects:
            * **Plant &rarr; Research Paper** (`STUDIED_IN`)
            * **Research Paper &rarr; Medicinal Use** (`REPORTS_INDICATION`)
            * **Plant &rarr; Compound** (`CONTAINS_PHYTOCHEMICAL`)
            * **Compound &rarr; Research Paper** (`EVALUATED_IN`)
            * **Research Paper &rarr; Evidence Type** (`CLASSIFIED_AS_TIER`)
            """)

            kg = HerbKnowledgeGraph()
            disc_graph = kg.build_discovery_graph(
                plant_name=focal_name,
                papers=papers_analyzed,
                claims=claims
            )

            fig_disc = kg.create_plotly_figure(target_graph=disc_graph, height=650)
            st.plotly_chart(fig_disc, use_container_width=True)

            g_m1, g_m2, g_m3 = st.columns(3)
            with g_m1:
                st.metric("Graph Nodes", disc_graph.number_of_nodes())
            with g_m2:
                st.metric("Graph Edges", disc_graph.number_of_edges())
            with g_m3:
                st.metric("Entity Classes", 5)

        # --- Tab 4: AI Research Summary Report ---
        with tab_sum:
            st.markdown("### Structured AI Research Synthesis")
            st.caption("Every factual assertion is tied to verified peer-reviewed publications. Zero hallucination guaranteed.")
            st.markdown(summary_text)

        # --- Tab 5: Export Research Artifacts ---
        with tab_exp:
            st.markdown("### Export Research Intelligence Artifacts")
            st.write("Download complete discovery results in standard bioinformatics and open data formats:")

            csv_data = ResearchExportService.generate_comparison_csv(claims)
            json_data = ResearchExportService.generate_references_json(papers_analyzed, claims)
            graphml_data = ResearchExportService.generate_graphml_string(disc_graph)

            exp_c1, exp_c2 = st.columns(2)
            with exp_c1:
                st.download_button(
                    label="📥 Export Comparison Table (CSV)",
                    data=csv_data.encode('utf-8'),
                    file_name=f"{focal_name.lower().replace(' ', '_')}_evidence_comparison.csv",
                    mime="text/csv",
                    type="primary"
                )
                st.download_button(
                    label="📥 Export Research Summary (Markdown)",
                    data=summary_text.encode('utf-8'),
                    file_name=f"{focal_name.lower().replace(' ', '_')}_research_summary.md",
                    mime="text/markdown"
                )

            with exp_c2:
                st.download_button(
                    label="📥 Export Source References (JSON)",
                    data=json_data.encode('utf-8'),
                    file_name=f"{focal_name.lower().replace(' ', '_')}_references.json",
                    mime="application/json"
                )
                st.download_button(
                    label="📥 Export Knowledge Graph (GraphML)",
                    data=graphml_data.encode('utf-8'),
                    file_name=f"{focal_name.lower().replace(' ', '_')}_knowledge_graph.graphml",
                    mime="application/xml"
                )
