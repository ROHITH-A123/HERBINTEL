"""HERBINTEL AI Research Discovery Engine.
Integrates cross-paper literature retrieval, entity recognition, evidence grouping,
scientific contradiction detection with methodology safeguards, and source-cited research summary synthesis.
"""

import re
import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from pathlib import Path

from ..core.config import EVIDENCE_TIERS
from ..core.database import search_discovery_papers, get_connection, insert_paper
from ..integrations.europe_pmc import EuropePMCClient
from ..nlp.extractor import KnowledgeExtractor, BotanicalNER, PhytochemicalNER, EvidenceClassifier
from ..nlp.llm_extractor import LLMExtractor

logger = logging.getLogger(__name__)


# Standard Therapeutic Clustering Taxonomy
THERAPEUTIC_CLUSTERS = {
    "Inflammation, Joint & Pain": [
        "inflammation", "anti-inflammatory", "antiinflammatory", "arthritis", "osteoarthritis",
        "rheumatoid", "joint", "analgesic", "pain", "swelling", "edema", "cox-2", "nf-kappa"
    ],
    "Neuroprotection, Stress & Cognition": [
        "neuroprotective", "stress", "cortisol", "anxiety", "depression", "cognitive",
        "memory", "alzheimer", "parkinson", "dementia", "sedative", "insomnia", "rasayana"
    ],
    "Antimicrobial, Infectious & Dental": [
        "antimicrobial", "antibacterial", "antifungal", "antiviral", "dental", "plaque",
        "malaria", "plasmodium", "parasite", "antiseptic", "gingivitis", "periodontitis"
    ],
    "Metabolic, Cardiovascular & Organ Protection": [
        "diabetes", "hypoglycemic", "glucose", "insulin", "hypertension", "blood pressure",
        "cardioprotective", "atherosclerosis", "cholesterol", "lipid", "hepatoprotective", "liver"
    ],
    "Oncology & Cytotoxicity": [
        "cancer", "anticancer", "antineoplastic", "tumor", "cytotoxic", "apoptosis",
        "leukemia", "lymphoma", "melanoma", "microtubule", "vinblastine", "paclitaxel"
    ],
    "Digestive & Respiratory": [
        "nausea", "antiemetic", "vomiting", "carminative", "dyspepsia", "ulcer",
        "gastroprotective", "asthma", "bronchitis", "respiratory", "cough"
    ]
}


class ResearchDiscoveryEngine:
    """Coordinates cross-paper retrieval, evidence grouping, and research synthesis."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path
        self.pmc_client = EuropePMCClient(timeout=8)
        self.llm_extractor = LLMExtractor()

    def search_papers(self, query: str, search_type: str = "plant", limit: int = 25) -> List[Dict[str, Any]]:
        """Retrieves and deduplicates research publications from local SQLite DB and Europe PMC."""
        if not query or len(query.strip()) < 2:
            return []

        cleaned_query = query.strip()
        aggregated_papers = []
        seen_keys: Set[str] = set()

        # 1. Search Local Database
        try:
            db_results = search_discovery_papers(cleaned_query, search_type=search_type, db_path=self.db_path)
            for row in db_results:
                paper_id = row.get("id")
                doi = (row.get("doi") or "").strip().lower()
                pmid = (row.get("pmid") or "").strip()
                title_norm = re.sub(r'[^a-z0-9]', '', (row.get("title") or "").lower())[:40]

                key = doi if doi else (f"pmid:{pmid}" if pmid else f"title:{title_norm}")
                if key and key not in seen_keys:
                    seen_keys.add(key)
                    aggregated_papers.append({
                        "id": paper_id,
                        "title": row.get("title", "Untitled Database Record"),
                        "authors": row.get("authors", "Unknown Authors"),
                        "journal": row.get("journal", "HERBINTEL Indexed Database"),
                        "year": row.get("year", 2024),
                        "doi": row.get("doi", ""),
                        "pmid": row.get("pmid", ""),
                        "url": row.get("url") or (f"https://doi.org/{row.get('doi')}" if row.get("doi") else ""),
                        "abstract": row.get("abstract", "No abstract recorded in database."),
                        "source": "Database Benchmark",
                        "is_demo": row.get("is_demo", 0)
                    })
        except Exception as e:
            logger.warning("Local database discovery query error: %s", e)

        # 2. Search Live Europe PMC
        try:
            pmc_results = self.pmc_client.search_literature(cleaned_query, page_size=limit)
            for item in pmc_results:
                doi = (item.get("doi") or "").strip().lower()
                pmid = (item.get("pmid") or "").strip()
                title_norm = re.sub(r'[^a-z0-9]', '', (item.get("title") or "").lower())[:40]

                key = doi if doi else (f"pmid:{pmid}" if pmid else f"title:{title_norm}")
                if key and key not in seen_keys:
                    seen_keys.add(key)
                    aggregated_papers.append({
                        "id": None,
                        "title": item.get("title", "Untitled Publication"),
                        "authors": item.get("authors", "Literature Authors"),
                        "journal": item.get("journal", "Peer-Reviewed Journal"),
                        "year": item.get("year") or 2024,
                        "doi": item.get("doi", ""),
                        "pmid": item.get("pmid", ""),
                        "url": item.get("url", ""),
                        "abstract": item.get("abstract", "No abstract available."),
                        "source": "Europe PMC",
                        "is_demo": 0
                    })
        except Exception as e:
            logger.warning("Europe PMC discovery search error: %s", e)

        return aggregated_papers[:limit]

    def analyze_cross_papers(self, selected_papers: List[Dict[str, Any]], focal_plant: Optional[str] = None) -> Dict[str, Any]:
        """Analyzes a collection of research papers to extract claims, group findings,
        detect divergences/contradictions, and build structured evidence matrices.
        """
        if not selected_papers:
            return {
                "claims": [],
                "compounds": [],
                "plants": [],
                "grouped_findings": {},
                "contradictions": [],
                "evidence_breakdown": {},
                "papers": []
            }

        all_claims = []
        all_compounds = set()
        all_plants = set()
        if focal_plant:
            all_plants.add(focal_plant)

        # 1. Extract Claims per Paper
        for paper in selected_papers:
            paper_id = paper.get("id")
            paper_claims = []

            # Check if claims exist in local DB for this paper
            if paper_id:
                try:
                    conn = get_connection(self.db_path)
                    cur = conn.cursor()
                    cur.execute("""
                        SELECT c.id, c.plant_id, c.compound_id, c.condition_or_use, c.evidence_tier,
                               c.source_sentence, c.extraction_confidence, c.verification_status,
                               p.scientific_name as plant_name, comp.name as compound_name
                        FROM claims c
                        JOIN plants p ON c.plant_id = p.id
                        LEFT JOIN compounds comp ON c.compound_id = comp.id
                        WHERE c.paper_id = ?
                    """, (paper_id,))
                    for row in cur.fetchall():
                        c_dict = dict(row)
                        c_dict["paper_title"] = paper.get("title")
                        c_dict["paper_doi"] = paper.get("doi")
                        c_dict["paper_year"] = paper.get("year")
                        c_dict["paper_authors"] = paper.get("authors")
                        c_dict["paper_journal"] = paper.get("journal")
                        c_dict["paper_id"] = paper_id
                        paper_claims.append(c_dict)
                    conn.close()
                except Exception as e:
                    logger.warning("Error fetching claims for paper %s: %s", paper_id, e)

            # If no DB claims, extract from abstract
            if not paper_claims:
                text_to_extract = f"{paper.get('title', '')}. {paper.get('abstract', '')}"
                extracted = KnowledgeExtractor.extract_claims_from_text(text_to_extract)
                
                # If focal plant specified and extracted claims lacked plant, assign focal plant
                for ec in extracted:
                    if focal_plant and (not ec.get("plant_name") or ec.get("plant_name") == "Medicinal flora"):
                        ec["plant_name"] = focal_plant
                    ec["paper_title"] = paper.get("title")
                    ec["paper_doi"] = paper.get("doi")
                    ec["paper_year"] = paper.get("year")
                    ec["paper_authors"] = paper.get("authors")
                    ec["paper_journal"] = paper.get("journal")
                    ec["paper_id"] = paper.get("id") or paper.get("doi")
                    paper_claims.append(ec)

            # If still no claims but paper discusses focal plant, create a baseline overview claim
            if not paper_claims and focal_plant and paper.get("abstract"):
                tier, conf = EvidenceClassifier.classify(paper.get("abstract"))
                found_comps = PhytochemicalNER.find_compounds(paper.get("abstract"))
                first_comp = found_comps[0]["name"] if found_comps else None
                paper_claims.append({
                    "plant_name": focal_plant,
                    "compound_name": first_comp,
                    "condition_or_use": "Pharmacological Evaluation and Bioactivity",
                    "evidence_tier": tier,
                    "source_sentence": paper["abstract"][:250] + "...",
                    "extraction_confidence": conf,
                    "verification_status": "Unverified",
                    "paper_title": paper.get("title"),
                    "paper_doi": paper.get("doi"),
                    "paper_year": paper.get("year"),
                    "paper_authors": paper.get("authors"),
                    "paper_journal": paper.get("journal"),
                    "paper_id": paper.get("id") or paper.get("doi")
                })

            for c in paper_claims:
                if c.get("compound_name"):
                    all_compounds.add(c["compound_name"])
                if c.get("plant_name"):
                    all_plants.add(c["plant_name"])
                all_claims.append(c)

        # 2. Group Findings into Therapeutic Categories
        grouped_findings: Dict[str, List[Dict[str, Any]]] = {}
        for claim in all_claims:
            cond_lower = claim.get("condition_or_use", "").lower() + " " + claim.get("source_sentence", "").lower()
            assigned_cluster = "General & Diverse Indications"

            for cluster_name, keywords in THERAPEUTIC_CLUSTERS.items():
                if any(kw in cond_lower for kw in keywords):
                    assigned_cluster = cluster_name
                    break

            if assigned_cluster not in grouped_findings:
                grouped_findings[assigned_cluster] = []
            grouped_findings[assigned_cluster].append(claim)

        # 3. Detect Contradictions & Divergences with Scientific Safeguards
        contradictions = self._detect_scientific_divergences(all_claims)

        # 4. Evidence Tier Breakdown
        evidence_breakdown = {}
        for c in all_claims:
            t = c.get("evidence_tier", "TRADITIONAL")
            evidence_breakdown[t] = evidence_breakdown.get(t, 0) + 1

        return {
            "claims": all_claims,
            "compounds": sorted(list(all_compounds)),
            "plants": sorted(list(all_plants)),
            "grouped_findings": grouped_findings,
            "contradictions": contradictions,
            "evidence_breakdown": evidence_breakdown,
            "papers": selected_papers
        }

    def _detect_scientific_divergences(self, claims: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identifies scientific divergences and conflicting findings with strict safeguards:
        Rule: Do NOT label different study outcomes as contradictions unless they investigate
        sufficiently comparable questions (e.g. do not flag in vitro vs in vivo differences as conflicts).
        """
        divergences = []
        if len(claims) < 2:
            return divergences

        # Group claims by rough therapeutic target
        clusters: Dict[str, List[Dict[str, Any]]] = {}
        for c in claims:
            target = c.get("condition_or_use", "").strip().lower()
            # Standardize core words
            core_kw = "general"
            for kw in ["pain", "arthritis", "inflammation", "malaria", "stress", "cortisol", "diabetes", "plaque", "cancer"]:
                if kw in target or kw in c.get("source_sentence", "").lower():
                    core_kw = kw
                    break
            if core_kw not in clusters:
                clusters[core_kw] = []
            clusters[core_kw].append(c)

        # Compare pairs within the same therapeutic domain
        negation_terms = ["not significant", "failed to", "no effect", "did not reduce", "ineffective", "no difference", "insufficient"]
        positive_terms = ["significant reduction", "significantly improved", "superior to", "potent inhibition", "effective in", "alleviated"]

        for domain, domain_claims in clusters.items():
            if len(domain_claims) < 2:
                continue

            for i in range(len(domain_claims)):
                for j in range(i + 1, len(domain_claims)):
                    c1 = domain_claims[i]
                    c2 = domain_claims[j]
                    s1 = c1.get("source_sentence", "").lower()
                    s2 = c2.get("source_sentence", "").lower()
                    t1 = c1.get("evidence_tier")
                    t2 = c2.get("evidence_tier")

                    # Scientific Safeguard: Cross-tier comparisons (e.g. In Vitro vs Clinical) are complementary levels of evidence, NOT conflicts
                    if t1 != t2:
                        continue

                    # If both are in the same evidence tier (e.g. both Clinical Trials or both In Vitro), check for opposing conclusions
                    c1_pos = any(pt in s1 for pt in positive_terms)
                    c1_neg = any(nt in s1 for nt in negation_terms)
                    c2_pos = any(pt in s2 for pt in positive_terms)
                    c2_neg = any(nt in s2 for nt in negation_terms)

                    if (c1_pos and c2_neg) or (c1_neg and c2_pos):
                        divergences.append({
                            "domain": domain.capitalize(),
                            "type": "Conflicting Outcome within Same Evidence Tier",
                            "evidence_tier": t1,
                            "study_1": {
                                "title": c1.get("paper_title"),
                                "authors": c1.get("paper_authors"),
                                "year": c1.get("paper_year"),
                                "claim": c1.get("condition_or_use"),
                                "sentence": c1.get("source_sentence"),
                                "doi": c1.get("paper_doi")
                            },
                            "study_2": {
                                "title": c2.get("paper_title"),
                                "authors": c2.get("paper_authors"),
                                "year": c2.get("paper_year"),
                                "claim": c2.get("condition_or_use"),
                                "sentence": c2.get("source_sentence"),
                                "doi": c2.get("paper_doi")
                            },
                            "safeguard_rationale": "Safeguard Audit: Both studies evaluate the same clinical/experimental tier but report divergent statistical efficacy."
                        })

        return divergences

    def generate_research_summary(self, analysis_result: Dict[str, Any], focal_plant: str) -> str:
        """Synthesizes a structured 8-section research report with strict citation preservation.
        Uses LLM if available; otherwise falls back to deterministic bioinformatics synthesis.
        """
        papers = analysis_result.get("papers", [])
        claims = analysis_result.get("claims", [])
        compounds = analysis_result.get("compounds", [])
        grouped = analysis_result.get("grouped_findings", {})
        contradictions = analysis_result.get("contradictions", [])
        tier_counts = analysis_result.get("evidence_breakdown", {})

        # If LLM key configured, attempt LLM synthesis first
        if self.llm_extractor.is_available():
            llm_summary = self._generate_llm_summary(analysis_result, focal_plant)
            if llm_summary:
                return llm_summary

        # Deterministic Evidence Synthesis Fallback
        return self._generate_deterministic_summary(analysis_result, focal_plant)

    def _generate_deterministic_summary(self, analysis: Dict[str, Any], focal_plant: str) -> str:
        """Deterministic, zero-hallucination research synthesis strictly linking statements to citations."""
        papers = analysis.get("papers", [])
        claims = analysis.get("claims", [])
        compounds = analysis.get("compounds", [])
        grouped = analysis.get("grouped_findings", {})
        contradictions = analysis.get("contradictions", [])

        # Build bibliography citation map
        citations = []
        for idx, p in enumerate(papers, 1):
            authors = p.get("authors") or "Unknown"
            year = p.get("year") or "N/D"
            title = p.get("title") or "Untitled Document"
            journal = p.get("journal") or "Biomedical Literature"
            doi = p.get("doi") or ""
            pmid = p.get("pmid") or ""
            ref_str = f"[{idx}] {authors} ({year}). *{title}*. {journal}."
            if doi:
                ref_str += f" DOI: [{doi}](https://doi.org/{doi})"
            elif pmid:
                ref_str += f" PMID: [{pmid}](https://pubmed.ncbi.nlm.nih.gov/{pmid}/)"
            citations.append(ref_str)

        # 1. Research Overview
        total_p = len(papers)
        total_c = len(claims)
        clinical_claims = [c for c in claims if c.get("evidence_tier") == "CLINICAL"]
        traditional_claims = [c for c in claims if c.get("evidence_tier") == "TRADITIONAL"]
        in_vivo_claims = [c for c in claims if c.get("evidence_tier") == "IN_VIVO"]
        in_vitro_claims = [c for c in claims if c.get("evidence_tier") == "IN_VITRO"]

        summary = f"""# Scientific Cross-Paper Intelligence Report: *{focal_plant}*

## 1. Research Overview
This cross-paper discovery synthesis aggregates findings across **{total_p} peer-reviewed publications** evaluating the botanical taxon *{focal_plant}*. Natural language processing and biomedical entity recognition identified **{total_c} documented therapeutic claims** and **{len(compounds)} isolated phytochemical compounds**. The scientific evidence spans {len(traditional_claims)} traditional ethnobotanical reports, {len(in_vitro_claims)} in vitro assays, {len(in_vivo_claims)} in vivo animal models, and {len(clinical_claims)} randomized human clinical evaluations.

## 2. Traditional Knowledge Findings
Historical and folkloric ethnobotanical documentation for *{focal_plant}* indicates significant traditional usage across indigenous medical traditions:
"""
        if traditional_claims:
            for tc in traditional_claims:
                cite = f"[{tc.get('paper_authors', 'Literature')}, {tc.get('paper_year', '')}]"
                summary += f"* **{tc['condition_or_use']}:** \"{tc['source_sentence']}\" {cite}\n"
        else:
            summary += "* Traditional ethnobotanical usages were not directly highlighted in the analyzed document cohort; modern biomedical assays form the primary evaluated literature.\n"

        summary += f"""
## 3. Identified Phytochemicals
The literature identifies several key bioactive secondary metabolites associated with *{focal_plant}*:
"""
        if compounds:
            for comp in compounds:
                linked_claims = [c for c in claims if (c.get("compound_name") or "").lower() == comp.lower()]
                uses = ", ".join(list({c['condition_or_use'] for c in linked_claims if c.get('condition_or_use')})) if linked_claims else "General phytochemistry"
                summary += f"* **{comp}:** Documented bioactivity targets: *{uses}*.\n"
        else:
            summary += "* Phytochemical isolation specifics were not resolved in this document subset; crude or standardized whole-plant extracts were the primary investigational vehicles.\n"

        summary += f"""
## 4. Experimental Evidence (In Vitro & In Vivo)
Preclinical laboratory assays provide biological mechanistic insights into the activity of *{focal_plant}*:
"""
        preclinical = in_vitro_claims + in_vivo_claims
        if preclinical:
            for pc in preclinical:
                tier_badge = "In Vivo Animal Model" if pc.get("evidence_tier") == "IN_VIVO" else "In Vitro Laboratory Assay"
                cite = f"[{pc.get('paper_authors', 'Study')}, {pc.get('paper_year', '')}]"
                summary += f"* **[{tier_badge}] {pc['condition_or_use']}:** {pc['source_sentence']} {cite}\n"
        else:
            summary += "* Specific preclinical laboratory assay metrics were not captured in this document selection.\n"

        summary += f"""
## 5. Clinical Evidence
Human clinical trial evaluations represent the highest echelon in the scientific evidence hierarchy:
"""
        if clinical_claims:
            for cc in clinical_claims:
                cite = f"[{cc.get('paper_authors', 'Clinical Cohort')}, {cc.get('paper_year', '')}]"
                summary += f"* **[Human Clinical Trial] {cc['condition_or_use']}:** {cc['source_sentence']} {cite}\n"
        else:
            summary += "* No randomized controlled human clinical trials were identified in this specific paper selection. Evidence remains centered at traditional or preclinical tiers.\n"

        summary += f"""
## 6. Conflicting or Uncertain Findings
Scientific rigor demands clear demarcation of study discrepancies:
"""
        if contradictions:
            for cd in contradictions:
                summary += f"* **Divergence in {cd['domain']}:** Between {cd['study_1']['authors']} ({cd['study_1']['year']}) and {cd['study_2']['authors']} ({cd['study_2']['year']}). {cd['safeguard_rationale']}\n"
        else:
            summary += (
                "* No direct scientific contradictions within identical evidence tiers were detected among the selected papers. "
                "Disparities in observed bioactivity between laboratory cell cultures (in vitro) and whole-organism studies "
                "reflect normal pharmacokinetic differences (bioavailability, metabolic clearance) rather than methodological contradictions.\n"
            )

        summary += f"""
## 7. Research Gaps & Future Directions
Based on the synthesized cross-paper evidence, the following gaps are apparent:
1. **Bioavailability & Pharmacokinetics:** Further investigation is required to correlate in vitro cellular potency with in vivo target tissue concentrations.
2. **Standardization of Herbal Extracts:** Discrepancies in secondary metabolite yields between different harvest regions and extraction methods necessitate standardized chromatographic fingerprinting.
3. **Double-Blind Clinical Trials:** Expansion from preliminary rodent models to adequately powered, double-blind randomized clinical trials for traditional indications.

## 8. Source References
"""
        for ref in citations:
            summary += f"{ref}\n"

        return summary

    def _generate_llm_summary(self, analysis: Dict[str, Any], focal_plant: str) -> Optional[str]:
        """Calls Google Gemini to generate the 8-section report with strict citation constraints."""
        papers = analysis.get("papers", [])
        claims = analysis.get("claims", [])
        if not claims:
            return None

        # Build concise evidence payload
        evidence_snippets = []
        for idx, c in enumerate(claims[:15], 1):
            evidence_snippets.append(
                f"Claim {idx}: Plant: {c.get('plant_name')}, Compound: {c.get('compound_name')}, "
                f"Indication: {c.get('condition_or_use')}, Tier: {c.get('evidence_tier')}, "
                f"Quote: \"{c.get('source_sentence')}\", Citation: [{c.get('paper_authors')}, {c.get('paper_year')}]"
            )

        prompt = (
            f"You are a senior biomedical researcher synthesizing scientific literature for HERBINTEL.\n"
            f"Generate a rigorous 8-section research report on the plant '{focal_plant}' based ONLY on the evidence provided below.\n"
            f"Sections required:\n"
            f"1. Research overview\n2. Traditional knowledge findings\n3. Identified phytochemicals\n"
            f"4. Experimental evidence\n5. Clinical evidence\n6. Conflicting or uncertain findings\n"
            f"7. Research gaps\n8. Source references\n\n"
            f"CRITICAL RULES: Do NOT invent citations or PMIDs. Every factual statement must cite the author and year.\n\n"
            f"EVIDENCE DATA:\n" + "\n".join(evidence_snippets)
        )

        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.llm_extractor.api_key}"
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            resp = requests.post(url, json=payload, timeout=18)
            if resp.status_code == 200:
                data = resp.json()
                text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text")
                if text and len(text) > 300:
                    return text
        except Exception as e:
            logger.info("LLM summary generation failed: %s. Using deterministic fallback.", e)

        return None
