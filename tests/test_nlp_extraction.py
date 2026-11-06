"""Automated Tests for HERBINTEL NLP, Botanical NER, and Evidence Classification."""

import pytest
from herbintel.nlp.extractor import BotanicalNER, PhytochemicalNER, EvidenceClassifier, KnowledgeExtractor


def test_botanical_ner_binomial():
    text = "Extracts of Curcuma longa and Withania somnifera were evaluated alongside Taxus baccata."
    plants = BotanicalNER.find_plants(text)
    names = [p["scientific_name"] for p in plants]
    assert "Curcuma longa" in names
    assert "Withania somnifera" in names
    assert "Taxus baccata" in names


def test_botanical_ner_vernacular():
    text = "Turmeric paste and Neem leaf decoctions are staple household remedies across South Asia."
    plants = BotanicalNER.find_plants(text)
    names = [p["scientific_name"] for p in plants]
    assert "Curcuma longa" in names
    assert "Azadirachta indica" in names


def test_phytochemical_ner():
    text = "The isolate contained high concentrations of curcumin, withaferin A, and artemisinin."
    compounds = PhytochemicalNER.find_compounds(text)
    comp_names = [c["name"].lower() for c in compounds]
    assert "curcumin" in comp_names
    assert "withaferin a" in comp_names
    assert "artemisinin" in comp_names


def test_evidence_tier_classification():
    # Clinical trial
    tier, conf = EvidenceClassifier.classify(
        "A randomized double-blind placebo-controlled clinical trial in 85 patients demonstrated pain relief."
    )
    assert tier == "CLINICAL"
    assert conf >= 0.80

    # In Vivo animal
    tier, conf = EvidenceClassifier.classify(
        "In Wistar rats subjected to carrageenan paw edema, oral administration at 100 mg/kg reduced swelling."
    )
    assert tier == "IN_VIVO"

    # In Vitro lab
    tier, conf = EvidenceClassifier.classify(
        "Cell culture assays indicated strong free radical scavenging with an IC50 of 12.4 ug/mL against DPPH."
    )
    assert tier == "IN_VITRO"

    # Traditional report
    tier, conf = EvidenceClassifier.classify(
        "Historically documented in Charaka Samhita as an Ayurvedic decoction for treating chronic fevers."
    )
    assert tier == "TRADITIONAL"


def test_knowledge_extractor_claim_preservation():
    sample_text = (
        "In a double-blind clinical trial involving 60 osteoarthritis patients, "
        "Curcuma longa extract containing curcumin significantly reduced joint inflammation."
    )
    claims = KnowledgeExtractor.extract_claims_from_text(sample_text)
    assert len(claims) >= 1
    claim = claims[0]
    assert claim["plant_name"] == "Curcuma longa"
    assert claim["compound_name"] == "Curcumin"
    assert claim["evidence_tier"] == "CLINICAL"
    assert claim["source_sentence"] == sample_text
    assert claim["verification_status"] == "Unverified"

