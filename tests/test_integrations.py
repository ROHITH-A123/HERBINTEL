"""Automated Tests for external bioinformatics integrations (Europe PMC, PubChem, GBIF, POWO)."""

import pytest
from herbintel.integrations.europe_pmc import EuropePMCClient
from herbintel.integrations.pubchem import PubChemClient
from herbintel.integrations.gbif import GBIFClient
from herbintel.integrations.powo import POWOClient


def test_pubchem_fallback_and_data():
    client = PubChemClient()
    curcumin = client._fallback_compound("curcumin")
    assert curcumin is not None
    assert curcumin["pubchem_cid"] == 969516
    assert "C21H20O6" in curcumin["molecular_formula"]
    assert "VWDWKYGDQIYTJZ" in curcumin["inchi_key"]


def test_gbif_taxonomy_and_coordinates():
    client = GBIFClient()
    tax = client._fallback_taxonomy("Curcuma longa")
    assert tax is not None
    assert tax["family"] == "Zingiberaceae"
    assert tax["status"] == "ACCEPTED"

    coords = client._fallback_coordinates("Curcuma longa")
    assert len(coords) >= 3
    assert -90 <= coords[0]["latitude"] <= 90
    assert -180 <= coords[0]["longitude"] <= 180


def test_powo_fallback_resolution():
    client = POWOClient()
    taxon = client._fallback_powo("Azadirachta indica")
    assert taxon is not None
    assert taxon["family"] == "Meliaceae"
    assert taxon["taxonomic_status"] == "Accepted"


def test_europe_pmc_fallback():
    client = EuropePMCClient()
    results = client._fallback_results("Withania somnifera")
    assert len(results) > 0
    assert "Withania" in results[0]["title"] or "ashwagandha" in results[0]["title"]

