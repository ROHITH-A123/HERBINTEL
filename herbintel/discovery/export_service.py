"""HERBINTEL Research Export Service.
Generates research comparison CSVs, Markdown summaries, JSON source references,
and GraphML network exports.
"""

import json
import csv
import io
import networkx as nx
from typing import Dict, List, Any, Optional


class ResearchExportService:
    """Exports structured research discovery artifacts in multiple standard scientific formats."""

    @staticmethod
    def generate_comparison_csv(claims: List[Dict[str, Any]]) -> str:
        """Generates CSV with columns:
        Paper | Plant | Compound | Reported finding | Evidence type | Source
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header matching Feature 3 specification
        writer.writerow(["Paper", "Plant", "Compound", "Reported finding", "Evidence type", "Source"])

        for c in claims:
            paper_title = c.get("paper_title") or "Literature Extraction"
            plant = c.get("plant_name") or "Medicinal Plant"
            compound = c.get("compound_name") or "None"
            finding = c.get("condition_or_use") or "Pharmacological Observation"
            evidence_type = c.get("evidence_tier") or "TRADITIONAL"
            
            # Source reference link or citation string
            doi = c.get("paper_doi")
            pmid = c.get("paper_pmid")
            if doi:
                source = f"https://doi.org/{doi}"
            elif pmid:
                source = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            else:
                authors = c.get("paper_authors") or "Unknown"
                year = c.get("paper_year") or ""
                source = f"{authors} ({year})".strip()

            writer.writerow([paper_title, plant, compound, finding, evidence_type, source])

        return output.getvalue()

    @staticmethod
    def generate_references_json(papers: List[Dict[str, Any]], claims: List[Dict[str, Any]]) -> str:
        """Generates JSON payload of source publications and their linked extracted findings."""
        refs_payload = {
            "platform": "HERBINTEL",
            "version": "1.0-Phase6",
            "paper_count": len(papers),
            "claim_count": len(claims),
            "publications": [
                {
                    "title": p.get("title"),
                    "authors": p.get("authors"),
                    "journal": p.get("journal"),
                    "year": p.get("year"),
                    "doi": p.get("doi"),
                    "pmid": p.get("pmid"),
                    "url": p.get("url"),
                    "abstract": p.get("abstract"),
                    "source": p.get("source", "Indexed Database"),
                    "associated_claims": [
                        {
                            "plant": c.get("plant_name"),
                            "compound": c.get("compound_name"),
                            "finding": c.get("condition_or_use"),
                            "evidence_tier": c.get("evidence_tier"),
                            "source_sentence": c.get("source_sentence"),
                            "confidence": c.get("extraction_confidence")
                        }
                        for c in claims
                        if str(c.get("paper_doi") or c.get("paper_title", "")) == str(p.get("doi") or p.get("title", ""))
                    ]
                }
                for p in papers
            ]
        }
        return json.dumps(refs_payload, indent=2)

    @staticmethod
    def generate_graphml_string(graph: nx.DiGraph) -> str:
        """Serializes NetworkX discovery graph into XML GraphML string."""
        clean_G = nx.DiGraph()
        for n, attr in graph.nodes(data=True):
            cleaned = {k: str(v) if not isinstance(v, (int, float, str)) else v for k, v in attr.items()}
            clean_G.add_node(n, **cleaned)
        for u, v, attr in graph.edges(data=True):
            cleaned = {k: str(v) if not isinstance(v, (int, float, str)) else v for k, v in attr.items()}
            clean_G.add_edge(u, v, **cleaned)

        lines = list(nx.generate_graphml(clean_G))
        return "\n".join(lines)
