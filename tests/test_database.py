"""Automated Tests for SQLite database CRUD and benchmark seeding."""

import pytest
import os
from pathlib import Path
from herbintel.core.database import (
    init_db, seed_benchmark_data, get_connection, insert_plant,
    insert_compound, insert_paper, insert_claim, get_dashboard_metrics,
    get_all_plants, get_plant_details, get_all_claims, update_claim_verification
)

TEST_DB_PATH = Path("data/test_herbintel.db")


@pytest.fixture(autouse=True)
def setup_test_db():
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    init_db(TEST_DB_PATH)
    yield
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass


def test_database_initialization():
    conn = get_connection(TEST_DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {r[0] for r in cur.fetchall()}
    conn.close()
    assert {"plants", "compounds", "papers", "claims", "plant_compounds"}.issubset(tables)


def test_plant_and_compound_insert():
    p_id = insert_plant({
        "scientific_name": "Panax ginseng",
        "common_names": "Asian Ginseng",
        "family": "Araliaceae",
        "genus": "Panax",
        "is_demo": 0
    }, TEST_DB_PATH)
    assert p_id > 0

    c_id = insert_compound({
        "name": "Ginsenoside Rg1",
        "chemical_class": "Triterpenoid Saponin",
        "pubchem_cid": 441923,
        "is_demo": 0
    }, TEST_DB_PATH)
    assert c_id > 0

    # Ensure idempotency / uniqueness
    p_id_dup = insert_plant({"scientific_name": "Panax ginseng"}, TEST_DB_PATH)
    assert p_id_dup == p_id


def test_claim_insertion_and_verification():
    p_id = insert_plant({"scientific_name": "Ginkgo biloba"}, TEST_DB_PATH)
    c_id = insert_compound({"name": "Bilobalide"}, TEST_DB_PATH)
    
    claim_id = insert_claim({
        "plant_id": p_id,
        "compound_id": c_id,
        "condition_or_use": "Cognitive Decline and Neuroprotection",
        "evidence_tier": "CLINICAL",
        "source_sentence": "Ginkgo biloba extract demonstrated improvement in cognitive assessments in randomized human trials.",
        "section": "Clinical Results",
        "page_number": 4,
        "extraction_confidence": 0.94,
        "verification_status": "Unverified",
        "is_demo": 0
    }, TEST_DB_PATH)
    assert claim_id > 0

    # Verify update status
    success = update_claim_verification(claim_id, "Verified", TEST_DB_PATH)
    assert success is True

    claims = get_all_claims(filter_status="Verified", db_path=TEST_DB_PATH)
    assert len(claims) == 1
    assert claims[0]["condition_or_use"] == "Cognitive Decline and Neuroprotection"
    assert claims[0]["verification_status"] == "Verified"


def test_benchmark_seeding():
    seed_benchmark_data(TEST_DB_PATH)
    metrics = get_dashboard_metrics(TEST_DB_PATH)
    assert metrics["plants"] >= 10
    assert metrics["compounds"] >= 10
    assert metrics["claims"] >= 15
    assert "CLINICAL" in metrics["evidence_breakdown"]
    assert "TRADITIONAL" in metrics["evidence_breakdown"]

