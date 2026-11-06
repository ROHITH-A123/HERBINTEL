"""Comprehensive Reliability Tests for External Bioinformatics APIs.
Verifies graceful handling of invalid inputs, timeouts, empty responses,
and fallback logic for PubChem, Europe PMC, GBIF, and Kew POWO.
"""

import pytest
from herbintel.integrations.pubchem import PubChemClient
from herbintel.integrations.europe_pmc import EuropePMCClient
from herbintel.integrations.gbif import GBIFClient
from herbintel.integrations.powo import POWOClient


# --- PubChem Reliability ---

def test_pubchem_invalid_input():
    client = PubChemClient(timeout=3)
    # Non-existent compound should not crash, returns None or graceful fallback
    res = client.get_compound_by_name("nonexistent_phytochemical_xyz_99999")
    assert res is None or isinstance(res, dict)


def test_pubchem_special_characters():
    client = PubChemClient(timeout=3)
    res = client.get_compound_by_name("!@#$%^&*()_+=~`{}[]|")
    assert res is None


def test_pubchem_empty_input():
    client = PubChemClient(timeout=3)
    res = client.get_compound_by_name("")
    assert res is None


def test_pubchem_invalid_cid():
    client = PubChemClient(timeout=3)
    res = client.get_compound_by_cid(-9999)
    assert res is None


# --- Europe PMC Reliability ---

def test_europe_pmc_empty_query():
    client = EuropePMCClient(timeout=3)
    res = client.search_literature("")
    assert isinstance(res, list)


def test_europe_pmc_gibberish_query():
    client = EuropePMCClient(timeout=3)
    res = client.search_literature("xqkzlwjkq_random_nonexistent_query_98765")
    assert isinstance(res, list)
    assert len(res) == 0


def test_europe_pmc_special_characters():
    client = EuropePMCClient(timeout=3)
    res = client.search_literature("<script>alert('xss')</script>")
    assert isinstance(res, list)


# --- GBIF Reliability ---

def test_gbif_invalid_species():
    client = GBIFClient(timeout=3)
    res = client.match_species("Fakeus hallucinatious nonexistus")
    assert res is None or isinstance(res, dict)


def test_gbif_empty_query():
    client = GBIFClient(timeout=3)
    res = client.match_species("")
    assert res is None


def test_gbif_invalid_species_key_occurrences():
    client = GBIFClient(timeout=3)
    res = client.get_occurrences(species_key=-999999, scientific_name="Nonexistent plant")
    assert isinstance(res, list)


# --- Kew POWO Reliability ---

def test_powo_invalid_plant():
    client = POWOClient(timeout=3)
    res = client.search_taxon("Nonexistentus botanica xyz")
    assert res is None or isinstance(res, dict)


def test_powo_empty_query():
    client = POWOClient(timeout=3)
    res = client.search_taxon("")
    assert res is None


def test_powo_special_characters():
    client = POWOClient(timeout=3)
    res = client.search_taxon("###$$$%%%&&&")
    assert res is None

