"""Automated Tests for PDF parsing, text extraction, and end-to-end extraction pipeline."""

import pytest
from pathlib import Path
from herbintel.nlp.extractor import PDFExtractor, KnowledgeExtractor

SAMPLE_DIR = Path("sample_data")


def test_pdf_extractor_page_and_text():
    pdf_path = SAMPLE_DIR / "sample_turmeric_curcumin_study.pdf"
    assert pdf_path.exists(), "Sample PDF must exist"
    
    with open(pdf_path, "rb") as f:
        data = f.read()

    doc = PDFExtractor.extract_from_bytes(data, filename="sample_turmeric_curcumin_study.pdf")
    assert doc["page_count"] == 2
    assert len(doc["pages"]) == 2
    assert "Curcuma longa" in doc["pages"][0]["text"]
    assert "osteoarthritis" in doc["pages"][1]["text"].lower()


def test_end_to_end_turmeric_pdf_extraction():
    pdf_path = SAMPLE_DIR / "sample_turmeric_curcumin_study.pdf"
    with open(pdf_path, "rb") as f:
        data = f.read()

    result = KnowledgeExtractor.extract_from_pdf_data(data, "sample_turmeric_curcumin_study.pdf")
    
    # Check document info
    assert result["page_count"] == 2
    
    # Check plants found
    plant_names = [p["scientific_name"] for p in result["plants"]]
    assert "Curcuma longa" in plant_names

    # Check compounds found
    comp_names = [c["name"].lower() for c in result["compounds"]]
    assert "curcumin" in comp_names

    # Check claims extracted
    claims = result["claims"]
    assert len(claims) >= 3

    # Check evidence tiers presence
    tiers = {c["evidence_tier"] for c in claims}
    assert "TRADITIONAL" in tiers
    assert "CLINICAL" in tiers or "IN_VITRO" in tiers or "IN_VIVO" in tiers

    # Check exact source sentence preservation
    for c in claims:
        assert len(c["source_sentence"]) > 20
        assert c["verification_status"] == "Unverified"
        assert 0.70 <= c["extraction_confidence"] <= 1.0


def test_end_to_end_ashwagandha_pdf_extraction():
    pdf_path = SAMPLE_DIR / "sample_ashwagandha_neuroprotection.pdf"
    with open(pdf_path, "rb") as f:
        data = f.read()

    result = KnowledgeExtractor.extract_from_pdf_data(data, "sample_ashwagandha_neuroprotection.pdf")
    assert result["page_count"] == 2
    
    plant_names = [p["scientific_name"] for p in result["plants"]]
    assert "Withania somnifera" in plant_names

    comp_names = [c["name"].lower() for c in result["compounds"]]
    assert "withaferin a" in comp_names

    claims = result["claims"]
    assert len(claims) >= 2
