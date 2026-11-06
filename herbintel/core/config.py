"""HERBINTEL Configuration and Constants.
Defines database paths, evidence taxonomy, API endpoints, and scientific constants.
"""

import os
from pathlib import Path

# Sanitize corrupted system TLS CA bundle environment variables if they point to non-existent paths
for cert_var in ["CURL_CA_BUNDLE", "REQUESTS_CA_BUNDLE", "SSL_CERT_FILE"]:
    if cert_var in os.environ and not os.path.exists(os.environ[cert_var]):
        del os.environ[cert_var]

# Base Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SAMPLE_DATA_DIR = PROJECT_ROOT / "sample_data"
DATABASE_PATH = DATA_DIR / "herbintel.db"

# Ensure runtime directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Evidence Tiers (Scientific Evidence Hierarchy)
EVIDENCE_TIERS = {
    "TRADITIONAL": {
        "label": "Traditional / Ethnobotanical",
        "description": "Historical, folkloric, Ayurvedic, TCM, or indigenous preparation usage.",
        "color": "#E65100",  # Amber orange
        "level_rank": 1,
    },
    "IN_VITRO": {
        "label": "In Vitro / Laboratory",
        "description": "Cellular assays, enzyme inhibition, antimicrobial MIC, receptor binding.",
        "color": "#0288D1",  # Cyan blue
        "level_rank": 2,
    },
    "IN_VIVO": {
        "label": "In Vivo / Animal Model",
        "description": "Rodent models, animal toxicity, pharmacokinetic animal studies.",
        "color": "#303F9F",  # Indigo
        "level_rank": 3,
    },
    "CLINICAL": {
        "label": "Clinical Trial / Human",
        "description": "Randomized controlled trials, human volunteer studies, phase trials.",
        "color": "#2E7D32",  # Emerald green
        "level_rank": 5,
    },
    "REVIEW_META": {
        "label": "Systematic Review / Meta-Analysis",
        "description": "Systematic review or meta-analysis synthesizing multiple studies.",
        "color": "#6A1B9A",  # Deep purple
        "level_rank": 4,
    },
}

VERIFICATION_STATUSES = ["Unverified", "Verified", "Disputed"]

# External API endpoints (All free / open access)
PUBMED_ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
EUROPE_PMC_API_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
PUBCHEM_REST_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
GBIF_SPECIES_MATCH_URL = "https://api.gbif.org/v1/species/match"
GBIF_OCCURRENCE_URL = "https://api.gbif.org/v1/occurrence/search"
KEW_POWO_API_URL = "https://powo.science.kew.org/api/2"

# Color Palette for Knowledge Graph & UI
ENTITY_COLORS = {
    "Plant": "#2E7D32",       # Green
    "Compound": "#00838F",    # Cyan / Teal
    "Condition": "#7B1FA2",   # Purple
    "Paper": "#D84315",       # Deep Amber/Rust
    "EvidenceTier": "#1565C0", # Blue
}

# Scientific Disclaimer
SCIENTIFIC_DISCLAIMER = (
    "HERBINTEL is an AI-powered bioinformatics research tool created for EthnoHack 2026. "
    "It organizes literature claims connecting traditional ethnobotany, phytochemistry, and scientific studies. "
    "This tool does NOT provide medical advice, diagnosis, or treatment plans. "
    "Claims are literature assertions, never treatment recommendations; each requires human review before it can be treated as verified. "
    "Confidence scores reflect NLP extraction certainty, NOT clinical efficacy."
)

