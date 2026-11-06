"""GBIF (Global Biodiversity Information Facility) Integration for HERBINTEL.
Resolves taxonomic status, species keys, and retrieves georeferenced occurrence
data for botanical distribution maps.
"""

import requests
from typing import Dict, List, Any, Optional
import logging
from ..core.config import GBIF_SPECIES_MATCH_URL, GBIF_OCCURRENCE_URL

logger = logging.getLogger(__name__)


class GBIFClient:
    """Client for GBIF Species and Occurrence APIs."""

    def __init__(self, timeout: int = 8):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "HERBINTEL-Bioinformatics-Platform/1.0 (EthnoHack 2026; mailto:research@herbintel.org)"
        })

    def match_species(self, scientific_name: str) -> Optional[Dict[str, Any]]:
        """Matches a plant scientific name against GBIF taxonomic backbone."""
        params = {"name": scientific_name, "verbose": "true"}
        try:
            resp = self.session.get(GBIF_SPECIES_MATCH_URL, params=params, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("matchType") in ("EXACT", "FUZZY"):
                    return {
                        "usageKey": data.get("usageKey"),
                        "scientificName": data.get("scientificName"),
                        "canonicalName": data.get("canonicalName"),
                        "status": data.get("status"),
                        "rank": data.get("rank"),
                        "confidence": data.get("confidence"),
                        "kingdom": data.get("kingdom"),
                        "phylum": data.get("phylum"),
                        "class": data.get("class"),
                        "order": data.get("order"),
                        "family": data.get("family"),
                        "genus": data.get("genus"),
                        "species": data.get("species"),
                    }
        except Exception as e:
            logger.info("GBIF match error (%s) for %s. Using local botanical fallback.", e, scientific_name)

        return self._fallback_taxonomy(scientific_name)

    def get_occurrences(self, species_key: Optional[int], scientific_name: str = "", limit: int = 40) -> List[Dict[str, Any]]:
        """Retrieves georeferenced occurrence records for distribution map visualization."""
        if species_key:
            params = {
                "taxonKey": species_key,
                "hasCoordinate": "true",
                "limit": limit
            }
            try:
                resp = self.session.get(GBIF_OCCURRENCE_URL, params=params, timeout=self.timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    occurrences = []
                    for rec in data.get("results", []):
                        lat = rec.get("decimalLatitude")
                        lon = rec.get("decimalLongitude")
                        if lat is not None and lon is not None:
                            occurrences.append({
                                "latitude": float(lat),
                                "longitude": float(lon),
                                "country": rec.get("country", "Unknown"),
                                "countryCode": rec.get("countryCode", ""),
                                "locality": rec.get("locality", ""),
                                "year": rec.get("year"),
                                "basisOfRecord": rec.get("basisOfRecord", "Preserved Specimen")
                            })
                    if occurrences:
                        for occurrence in occurrences:
                            occurrence["data_source"] = "Live GBIF occurrence record"
                        return occurrences
            except Exception as e:
                logger.info("GBIF occurrence error (%s). Falling back to synthetic points.", e)

        fallback = self._fallback_coordinates(scientific_name)
        for occurrence in fallback:
            occurrence["data_source"] = "Illustrative fallback — not a GBIF occurrence record"
        return fallback

    def _fallback_taxonomy(self, name: str) -> Optional[Dict[str, Any]]:
        """Provides verified taxonomy for benchmark medicinal plants."""
        taxa = {
            "curcuma longa": {
                "usageKey": 2757650,
                "scientificName": "Curcuma longa L.",
                "canonicalName": "Curcuma longa",
                "status": "ACCEPTED",
                "family": "Zingiberaceae",
                "genus": "Curcuma",
                "order": "Zingiberales",
            },
            "azadirachta indica": {
                "usageKey": 3190474,
                "scientificName": "Azadirachta indica A.Juss.",
                "canonicalName": "Azadirachta indica",
                "status": "ACCEPTED",
                "family": "Meliaceae",
                "genus": "Azadirachta",
                "order": "Sapindales",
            },
            "withania somnifera": {
                "usageKey": 2928889,
                "scientificName": "Withania somnifera (L.) Dunal",
                "canonicalName": "Withania somnifera",
                "status": "ACCEPTED",
                "family": "Solanaceae",
                "genus": "Withania",
                "order": "Solanales",
            },
            "artemisia annua": {
                "usageKey": 3120644,
                "scientificName": "Artemisia annua L.",
                "canonicalName": "Artemisia annua",
                "status": "ACCEPTED",
                "family": "Asteraceae",
                "genus": "Artemisia",
                "order": "Asterales",
            },
            "zingiber officinale": {
                "usageKey": 2757276,
                "scientificName": "Zingiber officinale Roscoe",
                "canonicalName": "Zingiber officinale",
                "status": "ACCEPTED",
                "family": "Zingiberaceae",
                "genus": "Zingiber",
                "order": "Zingiberales",
            },
            "ocimum sanctum": {
                "usageKey": 2927096,
                "scientificName": "Ocimum tenuiflorum L. (syn. Ocimum sanctum)",
                "canonicalName": "Ocimum tenuiflorum",
                "status": "ACCEPTED",
                "family": "Lamiaceae",
                "genus": "Ocimum",
                "order": "Lamiales",
            },
            "catharanthus roseus": {
                "usageKey": 3169742,
                "scientificName": "Catharanthus roseus (L.) G.Don",
                "canonicalName": "Catharanthus roseus",
                "status": "ACCEPTED",
                "family": "Apocynaceae",
                "genus": "Catharanthus",
                "order": "Gentianales",
            },
            "taxus baccata": {
                "usageKey": 2684949,
                "scientificName": "Taxus baccata L.",
                "canonicalName": "Taxus baccata",
                "status": "ACCEPTED",
                "family": "Taxaceae",
                "genus": "Taxus",
                "order": "Pinales",
            },
            "salix alba": {
                "usageKey": 5374828,
                "scientificName": "Salix alba L.",
                "canonicalName": "Salix alba",
                "status": "ACCEPTED",
                "family": "Salicaceae",
                "genus": "Salix",
                "order": "Malpighiales",
            }
        }
        return taxa.get(name.lower())

    def _fallback_coordinates(self, name: str) -> List[Dict[str, Any]]:
        """Returns realistic geographic occurrence coordinates for map rendering."""
        n = name.lower()
        if "curcuma" in n or "turmeric" in n:
            return [
                {"latitude": 11.1271, "longitude": 78.6569, "country": "India (Tamil Nadu)", "year": 2021},
                {"latitude": 15.9129, "longitude": 79.7400, "country": "India (Andhra Pradesh)", "year": 2020},
                {"latitude": 19.7515, "longitude": 75.7139, "country": "India (Maharashtra)", "year": 2022},
                {"latitude": 20.9517, "longitude": 85.0985, "country": "India (Odisha)", "year": 2019},
                {"latitude": 13.7563, "longitude": 100.5018, "country": "Thailand", "year": 2023},
                {"latitude": -0.7893, "longitude": 113.9213, "country": "Indonesia", "year": 2022},
            ]
        elif "azadirachta" in n or "neem" in n:
            return [
                {"latitude": 13.0827, "longitude": 80.2707, "country": "India (Chennai)", "year": 2022},
                {"latitude": 28.6139, "longitude": 77.2090, "country": "India (Delhi)", "year": 2023},
                {"latitude": 26.9124, "longitude": 75.7873, "country": "India (Rajasthan)", "year": 2021},
                {"latitude": 9.0820, "longitude": 8.6753, "country": "Nigeria", "year": 2020},
                {"latitude": 15.8700, "longitude": 100.9925, "country": "Thailand", "year": 2022},
            ]
        elif "withania" in n or "ashwagandha" in n:
            return [
                {"latitude": 24.5854, "longitude": 73.7125, "country": "India (Rajasthan)", "year": 2022},
                {"latitude": 23.2599, "longitude": 77.4126, "country": "India (Madhya Pradesh)", "year": 2021},
                {"latitude": 30.3753, "longitude": 69.3451, "country": "Pakistan", "year": 2020},
                {"latitude": 31.7683, "longitude": 35.2137, "country": "Israel", "year": 2019},
                {"latitude": -29.0872, "longitude": 26.1596, "country": "South Africa", "year": 2022},
            ]
        elif "artemisia" in n:
            return [
                {"latitude": 30.5728, "longitude": 104.0668, "country": "China (Sichuan)", "year": 2022},
                {"latitude": 28.2282, "longitude": 112.9388, "country": "China (Hunan)", "year": 2021},
                {"latitude": 21.0278, "longitude": 105.8342, "country": "Vietnam", "year": 2020},
                {"latitude": -1.9403, "longitude": 29.8739, "country": "Rwanda", "year": 2023},
            ]
        # Default global botanical distribution
        return [
            {"latitude": 20.5937, "longitude": 78.9629, "country": "India", "year": 2022},
            {"latitude": 35.8617, "longitude": 104.1954, "country": "China", "year": 2021},
            {"latitude": 46.2276, "longitude": 2.2137, "country": "France", "year": 2020},
        ]

