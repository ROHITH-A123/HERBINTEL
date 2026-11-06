"""Optional LLM-Enhanced Literature Extraction for HERBINTEL.
Leverages Google Gemini (or OpenAI-compatible APIs) when an API key is provided
to complement the deterministic rule-based NLP pipeline with semantic extraction.
Falls back safely to local extraction when no key is configured.
"""

import os
import json
import requests
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class LLMExtractor:
    """Optional Cloud LLM Extractor using Google Gemini REST API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    def is_available(self) -> bool:
        """Checks if a Gemini API key is configured."""
        return bool(self.api_key)

    def extract_structured_claims(self, text_excerpt: str) -> Optional[List[Dict[str, Any]]]:
        """Queries Gemini 1.5 Flash to extract structured ethnobotanical claims from text."""
        if not self.is_available():
            logger.info("No Gemini API key configured. Skipping LLM extraction.")
            return None

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        
        system_instruction = (
            "You are an expert bioinformatics ethnopharmacology extractor for HERBINTEL. "
            "Extract structured medicinal claims from the provided scientific text. "
            "Return ONLY a valid JSON array of objects with these exact keys: "
            "plant_name (scientific binomial), compound_name (or null), "
            "condition_or_use, evidence_tier (must be one of: CLINICAL, REVIEW_META, IN_VIVO, IN_VITRO, TRADITIONAL), "
            "source_sentence (verbatim exact sentence from text), extraction_confidence (float 0.70-0.99). "
            "Do NOT hallucinate or extrapolate findings."
        )

        prompt = f"{system_instruction}\n\nSCIENTIFIC TEXT:\n{text_excerpt[:4000]}"

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json"
            }
        }

        try:
            resp = requests.post(url, json=payload, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                raw_text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                parsed = json.loads(raw_text)
                if isinstance(parsed, list):
                    for item in parsed:
                        item["verification_status"] = "Unverified"
                        item["is_demo"] = 0
                    return parsed
            else:
                logger.warning("Gemini API returned status %s: %s", resp.status_code, resp.text[:200])
        except Exception as e:
            logger.info("Gemini API call failed (%s). Continuing with local pipeline.", e)

        return None

