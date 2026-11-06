"""HERBINTEL Knowledge Graph Engine.
Constructs NetworkX multi-relational graphs connecting medicinal plants,
phytochemical compounds, therapeutic uses, and scientific publications.
Computes graph centrality metrics and renders interactive Plotly visualizations.
"""

import networkx as nx
import plotly.graph_objects as go
from typing import Dict, List, Any, Optional, Tuple
import math
import logging
from ..core.config import ENTITY_COLORS, EVIDENCE_TIERS
from ..core.database import get_knowledge_graph_data

logger = logging.getLogger(__name__)


class HerbKnowledgeGraph:
    """Manages NetworkX graph construction, analytics, and Plotly rendering."""

    def __init__(self):
        self.graph = nx.DiGraph()

    def build_graph(self, tier_filter: Optional[str] = None, db_path=None, include_papers: bool = False) -> nx.DiGraph:
        """Builds directed knowledge graph from SQLite database."""
        data = get_knowledge_graph_data(tier_filter=tier_filter, db_path=db_path)
        G = nx.DiGraph()

        # 1. Add Plant Nodes
        for p in data["plants"]:
            node_id = f"P_{p['id']}"
            G.add_node(
                node_id,
                entity_type="Plant",
                label=p["scientific_name"],
                family=p.get("family", "Unknown"),
                is_demo=p.get("is_demo", 0),
                raw_id=p["id"],
                color=ENTITY_COLORS["Plant"],
            )

        # 2. Add Compound Nodes
        for c in data["compounds"]:
            node_id = f"C_{c['id']}"
            G.add_node(
                node_id,
                entity_type="Compound",
                label=c["name"],
                chemical_class=c.get("chemical_class", "Bioactive"),
                pubchem_cid=c.get("pubchem_cid"),
                is_demo=c.get("is_demo", 0),
                raw_id=c["id"],
                color=ENTITY_COLORS["Compound"],
            )

        # 3. Add Plant -> Compound Edges (Contains)
        for pc in data["plant_compounds"]:
            p_node = f"P_{pc['plant_id']}"
            c_node = f"C_{pc['compound_id']}"
            if G.has_node(p_node) and G.has_node(c_node):
                G.add_edge(
                    p_node,
                    c_node,
                    relation="CONTAINS_PHYTOCHEMICAL",
                    plant_part=pc.get("plant_part", "Whole plant"),
                    color="#00838F"
                )

        # 4. Optional Paper & EvidenceTier Nodes
        if include_papers:
            for paper in data.get("papers", []):
                doc_node = f"DOC_{paper['id']}"
                G.add_node(
                    doc_node,
                    entity_type="Paper",
                    label=paper["title"][:30] + ("..." if len(paper["title"]) > 30 else ""),
                    full_title=paper["title"],
                    authors=paper.get("authors", ""),
                    year=paper.get("year"),
                    doi=paper.get("doi", ""),
                    pmid=paper.get("pmid", ""),
                    raw_id=paper["id"],
                    color=ENTITY_COLORS["Paper"],
                )

            for tier_k, tier_v in EVIDENCE_TIERS.items():
                tier_node = f"TIER_{tier_k}"
                G.add_node(
                    tier_node,
                    entity_type="EvidenceTier",
                    label=tier_v["label"],
                    tier_code=tier_k,
                    color=ENTITY_COLORS["EvidenceTier"],
                )

        # 5. Add Claims & Relationships
        condition_node_map = {}
        for claim in data["claims"]:
            cond = claim["condition_or_use"].strip()
            cond_key = f"U_{cond.lower().replace(' ', '_')[:30]}"
            
            if cond_key not in condition_node_map:
                condition_node_map[cond_key] = cond
                G.add_node(
                    cond_key,
                    entity_type="Condition",
                    label=cond,
                    color=ENTITY_COLORS["Condition"],
                )

            # Edge color based on evidence tier
            tier = claim.get("evidence_tier", "TRADITIONAL")
            tier_info = EVIDENCE_TIERS.get(tier, EVIDENCE_TIERS["TRADITIONAL"])
            edge_color = tier_info["color"]

            p_node = f"P_{claim['plant_id']}"
            c_node = f"C_{claim['compound_id']}" if claim.get("compound_id") else None
            paper_id = claim.get("paper_id")
            doc_node = f"DOC_{paper_id}" if paper_id and include_papers else None

            # Direct relationships
            if c_node and G.has_node(c_node):
                G.add_edge(
                    c_node,
                    cond_key,
                    relation="BIOACTIVE_TREATS",
                    evidence_tier=tier,
                    tier_label=tier_info["label"],
                    confidence=claim.get("extraction_confidence", 0.85),
                    status=claim.get("verification_status", "Unverified"),
                    paper_title=claim.get("paper_title", ""),
                    claim_id=claim["id"],
                    color=edge_color
                )

            if G.has_node(p_node):
                G.add_edge(
                    p_node,
                    cond_key,
                    relation="MEDICINAL_USE",
                    evidence_tier=tier,
                    tier_label=tier_info["label"],
                    confidence=claim.get("extraction_confidence", 0.85),
                    status=claim.get("verification_status", "Unverified"),
                    paper_title=claim.get("paper_title", ""),
                    claim_id=claim["id"],
                    color=edge_color
                )

            # Extended Paper & EvidenceTier relationships (Phase 6 Feature 4)
            if include_papers and doc_node and G.has_node(doc_node):
                # 1. Plant -> Research paper
                if G.has_node(p_node):
                    G.add_edge(p_node, doc_node, relation="STUDIED_IN", color=ENTITY_COLORS["Paper"])
                # 2. Research paper -> Medicinal use
                G.add_edge(doc_node, cond_key, relation="REPORTS_INDICATION", evidence_tier=tier, color=edge_color)
                # 3. Compound -> Research paper
                if c_node and G.has_node(c_node):
                    G.add_edge(c_node, doc_node, relation="EVALUATED_IN", color=ENTITY_COLORS["Compound"])
                # 4. Research paper -> Evidence type
                tier_node = f"TIER_{tier}"
                if G.has_node(tier_node):
                    G.add_edge(doc_node, tier_node, relation="CLASSIFIED_AS_TIER", color=edge_color)

        self.graph = G
        return G

    def build_discovery_graph(self, plant_name: str, papers: List[Dict[str, Any]], claims: List[Dict[str, Any]]) -> nx.DiGraph:
        """Constructs focused research-paper discovery graph highlighting the 5 key relationships."""
        G = nx.DiGraph()

        # 1. Plant Node
        p_node = f"PLANT_{plant_name.replace(' ', '_')}"
        G.add_node(p_node, entity_type="Plant", label=plant_name, color=ENTITY_COLORS["Plant"])

        # 2. Evidence Tier Nodes
        for tier_k, tier_v in EVIDENCE_TIERS.items():
            t_node = f"TIER_{tier_k}"
            G.add_node(t_node, entity_type="EvidenceTier", label=tier_v["label"], color=ENTITY_COLORS["EvidenceTier"])

        # 3. Paper Nodes & Plant -> Paper (STUDIED_IN)
        paper_lookup = {}
        for p in papers:
            p_id = str(p.get("id") or p.get("doi") or p.get("title", ""))[:30]
            doc_node = f"DOC_{p_id}"
            title = p.get("title", "Research Publication")
            short_title = title[:35] + ("..." if len(title) > 35 else "")
            G.add_node(
                doc_node,
                entity_type="Paper",
                label=short_title,
                full_title=title,
                authors=p.get("authors", ""),
                year=p.get("year", ""),
                doi=p.get("doi", ""),
                color=ENTITY_COLORS["Paper"],
            )
            paper_lookup[p_id] = doc_node
            G.add_edge(p_node, doc_node, relation="STUDIED_IN", color=ENTITY_COLORS["Paper"])

        # 4. Compounds and Conditions
        comp_node_map = {}
        cond_node_map = {}

        for c in claims:
            comp_name = c.get("compound_name")
            if comp_name:
                comp_key = f"COMP_{comp_name.replace(' ', '_')}"
                if comp_key not in comp_node_map:
                    comp_node_map[comp_key] = comp_name
                    G.add_node(comp_key, entity_type="Compound", label=comp_name, color=ENTITY_COLORS["Compound"])
                # Plant -> Compound
                G.add_edge(p_node, comp_key, relation="CONTAINS_PHYTOCHEMICAL", color=ENTITY_COLORS["Compound"])

            cond_name = c.get("condition_or_use", "").strip()
            if cond_name:
                cond_key = f"COND_{cond_name.replace(' ', '_')[:25]}"
                if cond_key not in cond_node_map:
                    cond_node_map[cond_key] = cond_name
                    G.add_node(cond_key, entity_type="Condition", label=cond_name, color=ENTITY_COLORS["Condition"])

            tier = c.get("evidence_tier", "TRADITIONAL")
            tier_info = EVIDENCE_TIERS.get(tier, EVIDENCE_TIERS["TRADITIONAL"])
            edge_color = tier_info["color"]

            # Connect with paper
            paper_ref = str(c.get("paper_id") or c.get("paper_doi") or c.get("paper_title", ""))[:30]
            doc_node = paper_lookup.get(paper_ref) or (list(paper_lookup.values())[0] if paper_lookup else None)

            if doc_node and G.has_node(doc_node):
                if cond_name:
                    # Research paper -> Medicinal use
                    G.add_edge(doc_node, cond_key, relation="REPORTS_INDICATION", evidence_tier=tier, color=edge_color)
                if comp_name:
                    # Compound -> Research paper
                    G.add_edge(comp_key, doc_node, relation="EVALUATED_IN", color=ENTITY_COLORS["Compound"])
                # Research paper -> Evidence type
                t_node = f"TIER_{tier}"
                if G.has_node(t_node):
                    G.add_edge(doc_node, t_node, relation="CLASSIFIED_AS_TIER", color=edge_color)

        self.graph = G
        return G

    def get_metrics(self) -> Dict[str, Any]:
        """Calculates graph metrics: node counts, density, degree and betweenness centrality."""
        G = self.graph
        if len(G) == 0:
            return {"nodes": 0, "edges": 0, "density": 0, "top_plants": [], "top_compounds": []}

        degrees = dict(G.degree())
        betweenness = nx.betweenness_centrality(G)

        # Find top connected plants
        plant_nodes = [n for n, attr in G.nodes(data=True) if attr.get("entity_type") == "Plant"]
        compound_nodes = [n for n, attr in G.nodes(data=True) if attr.get("entity_type") == "Compound"]

        top_plants = sorted(
            [{"name": G.nodes[n]["label"], "degree": degrees[n], "centrality": round(betweenness[n], 4)} for n in plant_nodes],
            key=lambda x: x["degree"],
            reverse=True
        )[:5]

        top_compounds = sorted(
            [{"name": G.nodes[n]["label"], "degree": degrees[n], "centrality": round(betweenness[n], 4)} for n in compound_nodes],
            key=lambda x: x["degree"],
            reverse=True
        )[:5]

        return {
            "node_count": G.number_of_nodes(),
            "edge_count": G.number_of_edges(),
            "density": round(nx.density(G), 4),
            "top_plants": top_plants,
            "top_compounds": top_compounds,
            "is_weakly_connected": nx.is_weakly_connected(G) if len(G) > 0 else False,
        }

    def filter_subgraph(self, plant_name: Optional[str] = None, condition_keyword: Optional[str] = None) -> nx.DiGraph:
        """Extracts an ego-subgraph or thematic subgraph."""
        G = self.graph
        if not plant_name and not condition_keyword:
            return G

        selected_nodes = set()
        if plant_name:
            for n, attr in G.nodes(data=True):
                if attr.get("entity_type") == "Plant" and plant_name.lower() in attr.get("label", "").lower():
                    selected_nodes.add(n)
                    # Add 1st and 2nd degree neighbors
                    selected_nodes.update(G.neighbors(n))
                    selected_nodes.update(G.predecessors(n))
                    for nbr in list(selected_nodes):
                        selected_nodes.update(G.neighbors(nbr))

        if condition_keyword:
            for n, attr in G.nodes(data=True):
                if attr.get("entity_type") == "Condition" and condition_keyword.lower() in attr.get("label", "").lower():
                    selected_nodes.add(n)
                    selected_nodes.update(G.predecessors(n))

        if not selected_nodes:
            return G

        return G.subgraph(selected_nodes).copy()

    def create_plotly_figure(self, target_graph: Optional[nx.DiGraph] = None, height: int = 700) -> go.Figure:
        """Renders 2D interactive Plotly visualization of the knowledge graph."""
        G = target_graph if target_graph is not None else self.graph
        
        if len(G) == 0:
            fig = go.Figure()
            fig.update_layout(
                annotations=[{
                    "text": "No graph data available for current filters.",
                    "xref": "paper", "yref": "paper",
                    "showarrow": False, "font": {"size": 16}
                }],
                height=height
            )
            return fig

        # Compute force-directed spring layout
        pos = nx.spring_layout(G, k=0.55, iterations=60, seed=42)

        # 1. Build Edge Traces grouped by evidence tier / relationship
        edge_traces = []
        for u, v, data in G.edges(data=True):
            x0, y0 = pos[u]
            x1, y1 = pos[v]
            tier = data.get("evidence_tier", "PHYTOCHEM")
            color = data.get("color", "#888888")
            tier_label = data.get("tier_label", data.get("relation", "Linked"))
            
            trace = go.Scatter(
                x=[x0, x1, None],
                y=[y0, y1, None],
                line=dict(width=1.8, color=color),
                hoverinfo="text",
                text=f"{G.nodes[u].get('label')} &rarr; {G.nodes[v].get('label')}<br>Tier: {tier_label}<br>Status: {data.get('status', 'Verified')}",
                mode="lines",
                showlegend=False,
            )
            edge_traces.append(trace)

        # 2. Build Node Traces partitioned by Entity Type for crisp legend
        node_types = ["Plant", "Compound", "Condition", "Paper", "EvidenceTier"]
        node_traces = []

        degrees = dict(G.degree())

        for ent_type in node_types:
            type_nodes = [n for n, attr in G.nodes(data=True) if attr.get("entity_type") == ent_type]
            if not type_nodes:
                continue

            node_x = []
            node_y = []
            node_text = []
            node_hover = []
            node_sizes = []
            color = ENTITY_COLORS.get(ent_type, "#999999")

            for n in type_nodes:
                x, y = pos[n]
                node_x.append(x)
                node_y.append(y)
                attr = G.nodes[n]
                label = attr.get("label", n)
                deg = degrees.get(n, 1)
                
                # Size scaled by degree
                size = max(14, min(38, 12 + deg * 2.5))
                node_sizes.append(size)
                node_text.append(label if len(label) < 18 else label[:15] + "...")

                # Hover text
                if ent_type == "Plant":
                    hover = f"<b>🌿 Plant: {label}</b><br>Family: {attr.get('family', 'N/A')}<br>Degree: {deg}"
                elif ent_type == "Compound":
                    hover = f"<b>🧪 Compound: {label}</b><br>Class: {attr.get('chemical_class', 'N/A')}<br>PubChem CID: {attr.get('pubchem_cid', 'N/A')}<br>Degree: {deg}"
                elif ent_type == "Paper":
                    hover = f"<b>📄 Paper: {attr.get('full_title', label)}</b><br>Authors: {attr.get('authors', 'N/A')}<br>Year: {attr.get('year', 'N/A')}<br>Degree: {deg}"
                elif ent_type == "EvidenceTier":
                    hover = f"<b>📊 Evidence Tier: {label}</b><br>Code: {attr.get('tier_code', 'N/A')}<br>Degree: {deg}"
                else:
                    hover = f"<b>🎯 Medicinal Target: {label}</b><br>Degree: {deg}"
                node_hover.append(hover)

            trace = go.Scatter(
                x=node_x,
                y=node_y,
                mode="markers+text",
                text=node_text,
                textposition="top center",
                textfont=dict(size=10, family="Inter, Arial, sans-serif", color="#333333"),
                hoverinfo="text",
                hovertext=node_hover,
                name=f"{ent_type}s ({len(type_nodes)})",
                marker=dict(
                    size=node_sizes,
                    color=color,
                    line=dict(width=2, color="#FFFFFF"),
                    opacity=0.92,
                )
            )
            node_traces.append(trace)

        # Compose Figure
        fig = go.Figure(data=edge_traces + node_traces)
        fig.update_layout(
            title=dict(
                text="HERBINTEL Multi-Relational Knowledge Graph",
                font=dict(size=18, family="Inter, Arial, sans-serif")
            ),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                bgcolor="rgba(255, 255, 255, 0.8)"
            ),
            hovermode="closest",
            margin=dict(b=20, l=20, r=20, t=60),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor="rgba(248, 249, 250, 0.95)",
            paper_bgcolor="rgba(255, 255, 255, 1.0)",
            height=height,
        )

        return fig

    def export_graphml(self, output_path: str) -> None:
        """Exports graph to standard GraphML for Cytoscape or Gephi."""
        # Convert non-primitive attributes to string for GraphML compatibility
        export_G = nx.DiGraph()
        for n, attr in self.graph.nodes(data=True):
            clean_attr = {k: str(v) if not isinstance(v, (int, float, str)) else v for k, v in attr.items()}
            export_G.add_node(n, **clean_attr)
        for u, v, attr in self.graph.edges(data=True):
            clean_attr = {k: str(v) if not isinstance(v, (int, float, str)) else v for k, v in attr.items()}
            export_G.add_edge(u, v, **clean_attr)

        nx.write_graphml(export_G, output_path)
        logger.info("Knowledge Graph exported to %s", output_path)

