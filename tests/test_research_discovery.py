"""Automated Tests for HERBINTEL Phase 6: AI Research Discovery Engine.
Tests multi-paper retrieval, deduplication, cross-paper analysis, evidence grouping,
contradiction detection safeguards, research summary generation, exports, and offline resilience.
"""

import pytest
import json
import csv
import io
import networkx as nx
from pathlib import Path

from herbintel.discovery.discovery_engine import ResearchDiscoveryEngine
from herbintel.discovery.export_service import ResearchExportService
from herbintel.graph.knowledge_graph import HerbKnowledgeGraph
from herbintel.core.database import init_db, seed_benchmark_data

TEST_DB_PATH = Path("data/test_discovery.db")


@pytest.fixture(scope="module", autouse=True)
def setup_test_discovery_db():
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass
    init_db(TEST_DB_PATH)
    seed_benchmark_data(TEST_DB_PATH)
    yield
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass


def test_multi_paper_retrieval():
    engine = ResearchDiscoveryEngine(db_path=TEST_DB_PATH)
    
    # 1. Search by plant
    results_plant = engine.search_papers("Curcuma longa", search_type="plant", limit=10)
    assert len(results_plant) > 0
    assert any("Curcuma" in p["title"] or "Turmeric" in p["title"] or "Curcumin" in p["title"] for p in results_plant)

    # 2. Search by compound
    results_comp = engine.search_papers("Curcumin", search_type="phytochemical", limit=10)
    assert len(results_comp) > 0

    # 3. Search by condition
    results_cond = engine.search_papers("Osteoarthritis", search_type="condition", limit=10)
    assert len(results_cond) > 0


def test_duplicate_paper_handling():
    engine = ResearchDiscoveryEngine(db_path=TEST_DB_PATH)
    # Search for an item that exists in both DB and potentially external
    results = engine.search_papers("Curcuma longa", search_type="plant", limit=25)
    
    # Assert all DOIs and titles are unique in returned list
    seen_dois = set()
    for p in results:
        doi = p.get("doi")
        if doi:
            assert doi.lower() not in seen_dois, f"Duplicate DOI found: {doi}"
            seen_dois.add(doi.lower())


def test_cross_paper_analysis_and_evidence_grouping():
    engine = ResearchDiscoveryEngine(db_path=TEST_DB_PATH)
    papers = engine.search_papers("Curcuma longa", search_type="plant", limit=3)
    assert len(papers) >= 1

    analysis = engine.analyze_cross_papers(papers, focal_plant="Curcuma longa")
    assert len(analysis["claims"]) > 0
    assert "Curcumin" in analysis["compounds"] or len(analysis["compounds"]) > 0
    
    # Verify evidence grouping
    grouped = analysis["grouped_findings"]
    assert len(grouped) > 0
    # Inflammation or general should be in groups
    assert any("Inflammation" in g or "General" in g for g in grouped.keys())


def test_contradiction_detection_safeguards():
    engine = ResearchDiscoveryEngine(db_path=TEST_DB_PATH)
    
    # Case 1: In Vitro vs Clinical (Different tiers) should NEVER be a contradiction
    claims_cross_tier = [
        {
            "condition_or_use": "Osteoarthritis and joint pain",
            "evidence_tier": "IN_VITRO",
            "source_sentence": "In cell cultures, curcumin at high concentrations failed to reduce cellular inflammatory markers.",
            "paper_title": "Study 1 (In Vitro)"
        },
        {
            "condition_or_use": "Osteoarthritis and joint pain",
            "evidence_tier": "CLINICAL",
            "source_sentence": "Curcumin extract produced significant reduction in human osteoarthritis pain scores.",
            "paper_title": "Study 2 (Clinical)"
        }
    ]
    divergences = engine._detect_scientific_divergences(claims_cross_tier)
    # Must NOT flag as contradiction because tiers differ (translational gap, not contradiction)
    assert len(divergences) == 0

    # Case 2: Same evidence tier (both Clinical) with opposing outcomes
    claims_same_tier = [
        {
            "condition_or_use": "Joint pain in arthritis",
            "evidence_tier": "CLINICAL",
            "source_sentence": "In a double-blind trial, the herbal extract failed to reduce joint pain significantly.",
            "paper_title": "Trial A",
            "paper_authors": "Smith et al.",
            "paper_year": 2023,
            "paper_doi": "10.1001/a"
        },
        {
            "condition_or_use": "Joint pain in arthritis",
            "evidence_tier": "CLINICAL",
            "source_sentence": "A randomized trial reported significant reduction in joint pain scores superior to placebo.",
            "paper_title": "Trial B",
            "paper_authors": "Jones et al.",
            "paper_year": 2024,
            "paper_doi": "10.1001/b"
        }
    ]
    divergences_same = engine._detect_scientific_divergences(claims_same_tier)
    assert len(divergences_same) == 1
    assert divergences_same[0]["evidence_tier"] == "CLINICAL"
    assert "Safeguard" in divergences_same[0]["safeguard_rationale"] or "safeguard" in divergences_same[0]["safeguard_rationale"].lower()


def test_research_summary_generation_and_citation_preservation():
    engine = ResearchDiscoveryEngine(db_path=TEST_DB_PATH)
    papers = engine.search_papers("Curcuma longa", search_type="plant", limit=2)
    analysis = engine.analyze_cross_papers(papers, focal_plant="Curcuma longa")
    
    summary = engine.generate_research_summary(analysis, focal_plant="Curcuma longa")
    
    # Verify all 8 required sections are present
    assert "## 1. Research Overview" in summary
    assert "## 2. Traditional Knowledge Findings" in summary
    assert "## 3. Identified Phytochemicals" in summary
    assert "## 4. Experimental Evidence" in summary
    assert "## 5. Clinical Evidence" in summary
    assert "## 6. Conflicting or Uncertain Findings" in summary
    assert "## 7. Research Gaps & Future Directions" in summary
    assert "## 8. Source References" in summary

    # Verify citation preservation
    assert "[1]" in summary
    assert "Curcuma longa" in summary


def test_expanded_research_knowledge_graph():
    engine = ResearchDiscoveryEngine(db_path=TEST_DB_PATH)
    papers = engine.search_papers("Curcuma longa", search_type="plant", limit=2)
    analysis = engine.analyze_cross_papers(papers, focal_plant="Curcuma longa")

    kg = HerbKnowledgeGraph()
    G = kg.build_discovery_graph("Curcuma longa", papers, analysis["claims"])

    # Verify node types present
    node_types = {attr.get("entity_type") for n, attr in G.nodes(data=True)}
    assert "Plant" in node_types
    assert "Paper" in node_types
    assert "EvidenceTier" in node_types

    # Verify relationships present
    relations = {data.get("relation") for u, v, data in G.edges(data=True)}
    assert "STUDIED_IN" in relations  # Plant -> Paper
    assert "REPORTS_INDICATION" in relations or "CONTAINS_PHYTOCHEMICAL" in relations
    assert "CLASSIFIED_AS_TIER" in relations  # Paper -> EvidenceTier

    # Verify Plotly figure renders correctly with Paper and Tier nodes
    fig = kg.create_plotly_figure(G)
    assert fig is not None
    assert len(fig.data) > 0


def test_export_functionality():
    claims = [
        {
            "paper_title": "Study of Turmeric Efficacy",
            "plant_name": "Curcuma longa",
            "compound_name": "Curcumin",
            "condition_or_use": "Osteoarthritis Pain",
            "evidence_tier": "CLINICAL",
            "paper_doi": "10.1089/jmf.2016.3705",
            "paper_authors": "Daily JW et al.",
            "paper_year": 2016,
            "source_sentence": "Standardized Curcuma longa extracts reduced pain."
        }
    ]
    papers = [
        {
            "title": "Study of Turmeric Efficacy",
            "authors": "Daily JW et al.",
            "journal": "J Med Food",
            "year": 2016,
            "doi": "10.1089/jmf.2016.3705",
            "pmid": "27533649",
            "abstract": "Curcumin is effective."
        }
    ]

    # 1. CSV Export
    csv_str = ResearchExportService.generate_comparison_csv(claims)
    reader = list(csv.reader(io.StringIO(csv_str)))
    assert reader[0] == ["Paper", "Plant", "Compound", "Reported finding", "Evidence type", "Source"]
    assert len(reader) == 2
    assert "Curcuma longa" in reader[1]
    assert "https://doi.org/10.1089/jmf.2016.3705" in reader[1]

    # 2. JSON Export
    json_str = ResearchExportService.generate_references_json(papers, claims)
    parsed_json = json.loads(json_str)
    assert parsed_json["paper_count"] == 1
    assert parsed_json["publications"][0]["doi"] == "10.1089/jmf.2016.3705"
    assert len(parsed_json["publications"][0]["associated_claims"]) == 1

    # 3. GraphML Export
    kg = HerbKnowledgeGraph()
    G = kg.build_discovery_graph("Curcuma longa", papers, claims)
    graphml_str = ResearchExportService.generate_graphml_string(G)
    assert "<graphml" in graphml_str
    assert "STUDIED_IN" in graphml_str


def test_offline_operation():
    # Simulate completely offline environment (Europe PMC raises connection error or times out)
    engine = ResearchDiscoveryEngine(db_path=TEST_DB_PATH)
    # Point client to invalid unreachable endpoint to simulate network partition
    engine.pmc_client.session.get = lambda *args, **kwargs: (_ for _ in ()).throw(Exception("Simulated Offline Network Partition"))

    # Must fall back gracefully to local database records without raising unhandled exception
    offline_results = engine.search_papers("Curcuma longa", search_type="plant")
    assert isinstance(offline_results, list)
    assert len(offline_results) > 0  # DB records returned
    assert offline_results[0]["source"] == "Database Benchmark"

    # Cross-paper analysis must also succeed offline
    analysis = engine.analyze_cross_papers(offline_results[:2], focal_plant="Curcuma longa")
    assert len(analysis["claims"]) > 0

    # Summary synthesis must generate complete 8-section report offline
    summary = engine.generate_research_summary(analysis, focal_plant="Curcuma longa")
    assert "## 1. Research Overview" in summary
    assert "## 8. Source References" in summary
