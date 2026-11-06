"""End-to-End Integration Workflow Test for HERBINTEL (EthnoHack 2026).
Verifies the complete 11-step pipeline from PDF upload to Knowledge Graph rendering:
1. Upload a research PDF.
2. Extract text.
3. Identify scientific plant names.
4. Identify phytochemical names.
5. Extract medicinal-use statements.
6. Classify evidence types.
7. Display exact source sentences and page numbers.
8. Show extraction confidence.
9. Save extracted claims into SQLite.
10. Verify saved claims appear in Evidence Explorer query.
11. Verify corresponding relationships appear in Knowledge Graph.
"""

import pytest
from pathlib import Path
from herbintel.nlp.extractor import KnowledgeExtractor
from herbintel.core.database import (
    init_db, insert_paper, insert_plant, insert_compound,
    insert_claim, link_plant_compound, get_all_claims, get_dashboard_metrics
)
from herbintel.graph.knowledge_graph import HerbKnowledgeGraph

TEST_INTEGRATION_DB = Path("data/test_integration_workflow.db")
SAMPLE_PDF_PATH = Path("sample_data/sample_turmeric_curcumin_study.pdf")


@pytest.fixture(autouse=True)
def setup_integration_db():
    if TEST_INTEGRATION_DB.exists():
        TEST_INTEGRATION_DB.unlink()
    init_db(TEST_INTEGRATION_DB)
    yield
    if TEST_INTEGRATION_DB.exists():
        try:
            TEST_INTEGRATION_DB.unlink()
        except Exception:
            pass


def test_complete_pdf_to_knowledge_graph_workflow():
    # 1. Ingest PDF
    assert SAMPLE_PDF_PATH.exists(), "Sample research PDF must be present"
    with open(SAMPLE_PDF_PATH, "rb") as f:
        pdf_bytes = f.read()

    # 2. Extract Text & Metadata
    results = KnowledgeExtractor.extract_from_pdf_data(pdf_bytes, SAMPLE_PDF_PATH.name)
    assert results["page_count"] == 2
    assert len(results["full_text"]) > 100

    # 3. Identify Scientific Plant Names
    plant_names = [p["scientific_name"] for p in results["plants"]]
    assert "Curcuma longa" in plant_names

    # 4. Identify Phytochemical Names
    comp_names = [c["name"].lower() for c in results["compounds"]]
    assert "curcumin" in comp_names

    # 5. Extract Medicinal-Use Statements
    claims = results["claims"]
    assert len(claims) >= 3

    # 6. Classify Evidence Types (Hierarchy)
    tiers = {c["evidence_tier"] for c in claims}
    assert "TRADITIONAL" in tiers
    assert any(t in tiers for t in ["CLINICAL", "IN_VITRO", "IN_VIVO"])

    # 7. Exact Source Sentence & Page Numbers
    for claim in claims:
        assert len(claim["source_sentence"]) > 20
        assert claim["page_number"] in [1, 2]
        assert "Curcuma longa" in claim["plant_name"]

    # 8. Extraction Confidence Score (distinct from clinical strength)
    for claim in claims:
        assert 0.70 <= claim["extraction_confidence"] <= 1.0

    # 9. Save Extracted Claims into SQLite
    paper_id = insert_paper({
        "title": "Evaluation of Curcuma longa in Osteoarthritis",
        "authors": "Daily JW, Park S, Hewlings SJ",
        "journal": "Journal of Ethnopharmacology",
        "year": 2024,
        "doi": "10.1016/j.jep.2024.118999",
        "abstract": results["full_text"][:300],
        "pdf_path": SAMPLE_PDF_PATH.name,
        "is_demo": 0
    }, TEST_INTEGRATION_DB)
    assert paper_id > 0

    p_id = insert_plant({"scientific_name": "Curcuma longa", "is_demo": 0}, TEST_INTEGRATION_DB)
    c_id = insert_compound({"name": "Curcumin", "chemical_class": "Curcuminoid", "is_demo": 0}, TEST_INTEGRATION_DB)
    link_plant_compound(p_id, c_id, plant_part="Rhizome", is_demo=0, db_path=TEST_INTEGRATION_DB)

    saved_claim_ids = []
    for c in claims:
        cid = insert_claim({
            "plant_id": p_id,
            "compound_id": c_id if c.get("compound_name") else None,
            "condition_or_use": c["condition_or_use"],
            "evidence_tier": c["evidence_tier"],
            "source_sentence": c["source_sentence"],
            "section": c.get("section", "Literature"),
            "page_number": c["page_number"],
            "extraction_confidence": c["extraction_confidence"],
            "verification_status": "Unverified",
            "paper_id": paper_id,
            "is_demo": 0
        }, TEST_INTEGRATION_DB)
        saved_claim_ids.append(cid)

    assert len(saved_claim_ids) == len(claims)

    # 10. Verify Saved Claims Appear in Evidence Explorer Query
    retrieved_claims = get_all_claims(db_path=TEST_INTEGRATION_DB)
    assert len(retrieved_claims) == len(claims)
    
    # Check that retrieved claims have proper plant name and paper title joined
    first_retrieved = retrieved_claims[0]
    assert first_retrieved["plant_name"] == "Curcuma longa"
    assert first_retrieved["paper_title"] == "Evaluation of Curcuma longa in Osteoarthritis"
    assert first_retrieved["verification_status"] == "Unverified"
    assert len(first_retrieved["source_sentence"]) > 20

    # 11. Verify Relationships Appear in Knowledge Graph
    kg = HerbKnowledgeGraph()
    G = kg.build_graph(db_path=TEST_INTEGRATION_DB)
    
    assert G.number_of_nodes() >= 3  # At least Plant, Compound, Condition nodes
    assert G.number_of_edges() >= 2  # CONTAINS_PHYTOCHEMICAL, MEDICINAL_USE

    # Verify plant node exists
    plant_nodes = [n for n, attr in G.nodes(data=True) if attr.get("entity_type") == "Plant"]
    assert len(plant_nodes) == 1
    assert G.nodes[plant_nodes[0]]["label"] == "Curcuma longa"

    # Verify compound node exists
    comp_nodes = [n for n, attr in G.nodes(data=True) if attr.get("entity_type") == "Compound"]
    assert len(comp_nodes) == 1
    assert G.nodes[comp_nodes[0]]["label"] == "Curcumin"

    # Verify edges exist connecting plant to condition and compound
    edge_relations = [data.get("relation") for u, v, data in G.edges(data=True)]
    assert "CONTAINS_PHYTOCHEMICAL" in edge_relations
    assert "MEDICINAL_USE" in edge_relations or "BIOACTIVE_TREATS" in edge_relations

    # Verify Plotly figure renders correctly from graph
    fig = kg.create_plotly_figure()
    assert fig is not None
    assert len(fig.data) > 0


def test_ashwagandha_pdf_to_knowledge_graph_workflow():
    ashwa_pdf = Path("sample_data/sample_ashwagandha_neuroprotection.pdf")
    assert ashwa_pdf.exists()
    with open(ashwa_pdf, "rb") as f:
        pdf_bytes = f.read()

    # Extract
    results = KnowledgeExtractor.extract_from_pdf_data(pdf_bytes, ashwa_pdf.name)
    assert results["page_count"] == 2
    assert "Withania somnifera" in [p["scientific_name"] for p in results["plants"]]
    assert "withaferin a" in [c["name"].lower() for c in results["compounds"]]
    assert len(results["claims"]) >= 2

    # Save to SQLite
    paper_id = insert_paper({
        "title": "Neuroprotective Mechanisms of Withania somnifera in Stress Models",
        "authors": "Chandrasekhar K, Kapoor J",
        "journal": "Neuropharmacology & Ethnobotany",
        "year": 2024,
        "doi": "10.1016/j.neuro.2024.99812",
        "abstract": results["full_text"][:300],
        "pdf_path": ashwa_pdf.name,
        "is_demo": 0
    }, TEST_INTEGRATION_DB)

    p_id = insert_plant({"scientific_name": "Withania somnifera", "is_demo": 0}, TEST_INTEGRATION_DB)
    c_id = insert_compound({"name": "Withaferin A", "chemical_class": "Withanolide", "is_demo": 0}, TEST_INTEGRATION_DB)
    link_plant_compound(p_id, c_id, plant_part="Roots", is_demo=0, db_path=TEST_INTEGRATION_DB)

    for c in results["claims"]:
        insert_claim({
            "plant_id": p_id,
            "compound_id": c_id if c.get("compound_name") else None,
            "condition_or_use": c["condition_or_use"],
            "evidence_tier": c["evidence_tier"],
            "source_sentence": c["source_sentence"],
            "section": c.get("section", "Literature"),
            "page_number": c["page_number"],
            "extraction_confidence": c["extraction_confidence"],
            "verification_status": "Unverified",
            "paper_id": paper_id,
            "is_demo": 0
        }, TEST_INTEGRATION_DB)

    # Verify query in Evidence Explorer
    claims = get_all_claims(db_path=TEST_INTEGRATION_DB)
    assert len(claims) >= 2
    assert any("Withania" in c["plant_name"] for c in claims)

    # Verify Knowledge Graph reflects Withania somnifera and Withaferin A
    kg = HerbKnowledgeGraph()
    G = kg.build_graph(db_path=TEST_INTEGRATION_DB)
    assert G.number_of_nodes() >= 3
    assert G.number_of_edges() >= 2
    plant_labels = [attr.get("label") for n, attr in G.nodes(data=True) if attr.get("entity_type") == "Plant"]
    assert "Withania somnifera" in plant_labels
    comp_labels = [attr.get("label") for n, attr in G.nodes(data=True) if attr.get("entity_type") == "Compound"]
    assert "Withaferin A" in comp_labels


