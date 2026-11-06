"""HERBINTEL Knowledge Graph View Page.
Interactive multi-relational network connecting medicinal plants,
phytocompounds, therapeutic uses, and evidence hierarchies using NetworkX & Plotly.
"""

import streamlit as st
import json
import networkx as nx
from pathlib import Path
from ..components import render_header, render_disclaimer
from ..theme import render_evidence_badge
from ...graph.knowledge_graph import HerbKnowledgeGraph
from ...core.config import EVIDENCE_TIERS, DATA_DIR


def render_knowledge_graph_page():
    render_header("Knowledge Graph", "Interactive Network of Plants, Compounds & Scientific Evidence")
    render_disclaimer()

    st.markdown("""
    Explore the multi-relational graph connecting traditional medicinal taxa with isolated phytochemicals
    and modern clinical endpoints. **Nodes** represent Plants (Green), Compounds (Teal), and Conditions (Purple).
    **Edges** are color-coded by the scientific evidence hierarchy.
    """)

    # Filter Controls
    col_f1, col_f2, col_f3 = st.columns(3)
    
    with col_f1:
        tier_options = ["ALL"] + list(EVIDENCE_TIERS.keys())
        selected_tier = st.selectbox(
            "Filter by Evidence Tier:",
            tier_options,
            format_func=lambda x: "All Evidence Tiers" if x == "ALL" else EVIDENCE_TIERS[x]["label"]
        )

    with col_f2:
        filter_plant = st.text_input("Filter Subgraph by Plant Name (optional):", placeholder="e.g. Curcuma, Withania")

    with col_f3:
        filter_cond = st.text_input("Filter Subgraph by Condition (optional):", placeholder="e.g. pain, inflammation, malaria")

    # Build and visualize graph
    kg = HerbKnowledgeGraph()
    with st.spinner("Constructing multi-relational network from knowledge base..."):
        kg.build_graph(tier_filter=selected_tier)

    # Filter subgraph if requested
    if filter_plant or filter_cond:
        active_graph = kg.filter_subgraph(plant_name=filter_plant or None, condition_keyword=filter_cond or None)
        st.info(f"Displaying focused subgraph: {active_graph.number_of_nodes()} nodes, {active_graph.number_of_edges()} edges.")
    else:
        active_graph = kg.graph

    # Render Plotly interactive figure
    fig = kg.create_plotly_figure(target_graph=active_graph, height=720)
    st.plotly_chart(fig, use_container_width=True)

    # Graph Analytics & Network Topology
    st.markdown("---")
    st.subheader("Network Metrics & Discovery Hubs")
    metrics = kg.get_metrics()

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Graph Nodes", metrics["node_count"])
    with m2:
        st.metric("Total Graph Edges", metrics["edge_count"])
    with m3:
        st.metric("Network Density", metrics["density"])
    with m4:
        st.metric("Connected Structure", "Weakly Connected" if metrics["is_weakly_connected"] else "Modular Clusters")

    st.markdown("<br>", unsafe_allow_html=True)

    col_hubs1, col_hubs2 = st.columns(2)
    with col_hubs1:
        st.markdown("#### 🌿 Top Therapeutic Hub Plants (by Degree)")
        if metrics["top_plants"]:
            for p in metrics["top_plants"]:
                st.markdown(f"- **{p['name']}**: `{p['degree']} links` (Betweenness Centrality: `{p['centrality']}`)")
        else:
            st.write("No plant hubs calculated.")

    with col_hubs2:
        st.markdown("#### 🧪 Top Multi-Target Phytocompounds (by Degree)")
        if metrics["top_compounds"]:
            for c in metrics["top_compounds"]:
                st.markdown(f"- **{c['name']}**: `{c['degree']} links` (Betweenness Centrality: `{c['centrality']}`)")
        else:
            st.write("No compound hubs calculated.")

    # Graph Export
    st.markdown("---")
    st.subheader("Export Knowledge Graph")
    exp_col1, exp_col2 = st.columns(2)

    with exp_col1:
        graphml_path = DATA_DIR / "herbintel_graph.graphml"
        if st.button("Export GraphML (for Cytoscape / Gephi)"):
            kg.export_graphml(str(graphml_path))
            with open(graphml_path, "r", encoding="utf-8") as f:
                st.download_button(
                    label="📥 Download GraphML File",
                    data=f.read(),
                    file_name="herbintel_knowledge_graph.graphml",
                    mime="application/xml"
                )

    with exp_col2:
        # JSON export for web/D3
        nodes_data = [{"id": n, **attr} for n, attr in active_graph.nodes(data=True)]
        edges_data = [{"source": u, "target": v, **attr} for u, v, attr in active_graph.edges(data=True)]
        json_export = json.dumps({"nodes": nodes_data, "edges": edges_data}, indent=2)
        st.download_button(
            label="📥 Download JSON Graph (for D3.js / Web)",
            data=json_export,
            file_name="herbintel_graph.json",
            mime="application/json"
        )

