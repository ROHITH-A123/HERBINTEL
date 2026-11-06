"""HERBINTEL NLP and Document Extraction Pipeline.
Extracts text from research PDFs, segments sentences, recognizes botanical entities,
identifies phytochemical compounds, extracts medicinal-use claims, classifies scientific
evidence tiers, and preserves exact source sentences.
"""

import re
import io
from typing import List, Dict, Any, Optional, Tuple
import logging

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

logger = logging.getLogger(__name__)

# --- Botanical & Phytochemical Knowledge Lexicons ---

COMMON_MEDICINAL_PLANTS = {
    "turmeric": "Curcuma longa",
    "haridra": "Curcuma longa",
    "haldi": "Curcuma longa",
    "neem": "Azadirachta indica",
    "nimba": "Azadirachta indica",
    "ashwagandha": "Withania somnifera",
    "indian ginseng": "Withania somnifera",
    "sweet wormwood": "Artemisia annua",
    "qinghao": "Artemisia annua",
    "ginger": "Zingiber officinale",
    "adrak": "Zingiber officinale",
    "holy basil": "Ocimum sanctum",
    "tulsi": "Ocimum sanctum",
    "indian snakeroot": "Rauvolfia serpentina",
    "sarpagandha": "Rauvolfia serpentina",
    "madagascar periwinkle": "Catharanthus roseus",
    "sadabahar": "Catharanthus roseus",
    "english yew": "Taxus baccata",
    "white willow": "Salix alba",
    "willow bark": "Salix alba",
    "ginseng": "Panax ginseng",
    "asian ginseng": "Panax ginseng",
    "ginkgo": "Ginkgo biloba",
    "maidenhair tree": "Ginkgo biloba",
    "st john's wort": "Hypericum perforatum",
    "st. john's wort": "Hypericum perforatum",
    "echinacea": "Echinacea purpurea",
    "purple coneflower": "Echinacea purpurea",
    "garlic": "Allium sativum",
    "lahsun": "Allium sativum",
    "aloe vera": "Aloe vera",
    "chamomile": "Matricaria chamomilla",
    "milk thistle": "Silybum marianum",
    "valerian": "Valeriana officinalis",
    "feverfew": "Tanacetum parthenium",
    "green tea": "Camellia sinensis",
    "tea tree": "Melaleuca alternifolia",
    "black pepper": "Piper nigrum",
    "kali mirch": "Piper nigrum",
    "pippali": "Piper longum",
    "long pepper": "Piper longum",
    "licorice": "Glycyrrhiza glabra",
    "yashtimadhu": "Glycyrrhiza glabra",
    "cinnamon": "Cinnamomum verum",
    "clove": "Syzygium aromaticum",
    "lavender": "Lavandula angustifolia",
    "peppermint": "Mentha piperita",
    "frankincense": "Boswellia serrata",
    "shallaki": "Boswellia serrata",
    "guggulu": "Commiphora mukul",
    "brahmi": "Bacopa monnieri",
    "gotu kola": "Centella asiatica",
    "moringa": "Moringa oleifera",
    "drumstick tree": "Moringa oleifera",
    "amla": "Phyllanthus emblica",
    "indian gooseberry": "Phyllanthus emblica",
    "haritaki": "Terminalia chebula",
    "bibhitaki": "Terminalia bellirica",
    "shatavari": "Asparagus racemosus",
    "kutki": "Picrorhiza kurroa",
    "kalmegh": "Andrographis paniculata",
    "king of bitters": "Andrographis paniculata",
    "giloy": "Tinospora cordifolia",
    "guduchi": "Tinospora cordifolia",
    "cannabis": "Cannabis sativa",
    "hemp": "Cannabis sativa",
    "opium poppy": "Papaver somniferum",
    "belladonna": "Atropa belladonna",
    "deadly nightshade": "Atropa belladonna",
    "foxglove": "Digitalis purpurea",
    "cinchona": "Cinchona officinalis",
    "peruvian bark": "Cinchona officinalis",
}

# Known Bioactive Compounds and Classes
KNOWN_COMPOUNDS = {
    "curcumin": {"class": "Curcuminoid / Polyphenol", "cid": 969516},
    "demethoxycurcumin": {"class": "Curcuminoid", "cid": 5469424},
    "bisdemethoxycurcumin": {"class": "Curcuminoid", "cid": 5315472},
    "azadirachtin": {"class": "Limonoid / Terpenoid", "cid": 5281303},
    "nimbin": {"class": "Limonoid", "cid": 108058},
    "withaferin a": {"class": "Withanolide / Steroidal Lactone", "cid": 265237},
    "withanolide a": {"class": "Withanolide", "cid": 11294368},
    "artemisinin": {"class": "Sesquiterpene Lactone", "cid": 68827},
    "artemether": {"class": "Artemisinin Derivative", "cid": 68911},
    "artesunate": {"class": "Artemisinin Derivative", "cid": 6917864},
    "6-gingerol": {"class": "Gingerol / Phenol", "cid": 442793},
    "gingerol": {"class": "Gingerol / Phenol", "cid": 442793},
    "shogaol": {"class": "Phenolic Alkene", "cid": 5281794},
    "6-shogaol": {"class": "Phenolic Alkene", "cid": 5281794},
    "eugenol": {"class": "Phenylpropanoid", "cid": 3314},
    "reserpine": {"class": "Indole Alkaloid", "cid": 5770},
    "vinblastine": {"class": "Bisindole Alkaloid", "cid": 13342},
    "vincristine": {"class": "Bisindole Alkaloid", "cid": 5978},
    "paclitaxel": {"class": "Taxane Diterpenoid", "cid": 36314},
    "salicin": {"class": "Phenolic Glycoside", "cid": 439503},
    "quercetin": {"class": "Flavonol", "cid": 5280343},
    "kaempferol": {"class": "Flavonol", "cid": 5280863},
    "piperine": {"class": "Alkaloid", "cid": 638024},
    "berberine": {"class": "Isoquinoline Alkaloid", "cid": 2353},
    "glycyrrhizin": {"class": "Triterpenoid Saponin", "cid": 14982},
    "andrographolide": {"class": "Diterpenoid Lactone", "cid": 5318517},
    "bacoside a": {"class": "Dammarane Triterpenoid Saponin", "cid": 92043183},
    "asiaticoside": {"class": "Triterpenoid Saponin", "cid": 108062},
    "boswellic acid": {"class": "Pentacyclic Triterpene", "cid": 168928},
    "gallic acid": {"class": "Phenolic Acid", "cid": 370},
    "ellagic acid": {"class": "Polyphenol", "cid": 5281855},
    "epigallocatechin gallate": {"class": "Catechin / Flavonoid", "cid": 65064},
    "egcg": {"class": "Catechin / Flavonoid", "cid": 65064},
    "caffeine": {"class": "Purine Alkaloid", "cid": 2519},
    "cannabidiol": {"class": "Cannabinoid", "cid": 644019},
    "cbd": {"class": "Cannabinoid", "cid": 644019},
    "tetrahydrocannabinol": {"class": "Cannabinoid", "cid": 16078},
    "thc": {"class": "Cannabinoid", "cid": 16078},
    "morphine": {"class": "Opiate Alkaloid", "cid": 5288826},
    "codeine": {"class": "Opiate Alkaloid", "cid": 5284371},
    "atropine": {"class": "Tropane Alkaloid", "cid": 174174},
    "scopolamine": {"class": "Tropane Alkaloid", "cid": 3000322},
    "digoxin": {"class": "Cardiac Glycoside", "cid": 2724385},
    "digitoxin": {"class": "Cardiac Glycoside", "cid": 441207},
    "quinine": {"class": "Cinchona Alkaloid", "cid": 3034034},
    "silymarin": {"class": "Flavonolignan Complex", "cid": 1548994},
    "silybin": {"class": "Flavonolignan", "cid": 31553},
    "hypericin": {"class": "Naphthodianthrone", "cid": 5281228},
    "hyperforin": {"class": "Phloroglucinol Derivative", "cid": 6438062},
    "parthenolide": {"class": "Sesquiterpene Lactone", "cid": 6473881},
    "thymol": {"class": "Monoterpene Phenol", "cid": 6989},
    "menthol": {"class": "Monoterpene Alcohol", "cid": 16666},
    "capsaicin": {"class": "Capsaicinoid", "cid": 1548943},
    "allicin": {"class": "Organosulfur Compound", "cid": 65036},
    "resveratrol": {"class": "Stilbenoid", "cid": 445154},
    "genistein": {"class": "Isoflavone", "cid": 5280961},
    "daidzein": {"class": "Isoflavone", "cid": 5281708},
    "rutin": {"class": "Flavonoid Glycoside", "cid": 5280805},
    "luteolin": {"class": "Flavone", "cid": 5280445},
    "apigenin": {"class": "Flavone", "cid": 5280443},
    "ursolic acid": {"class": "Pentacyclic Triterpenoid", "cid": 64945},
    "oleanolic acid": {"class": "Pentacyclic Triterpenoid", "cid": 10494},
    "betulinic acid": {"class": "Pentacyclic Triterpenoid", "cid": 64971},
    "rosmarinic acid": {"class": "Polyphenol / Ester", "cid": 5281792},
    "caffeic acid": {"class": "Hydroxycinnamic Acid", "cid": 689043},
    "ferulic acid": {"class": "Hydroxycinnamic Acid", "cid": 445858},
    "chlorogenic acid": {"class": "Polyphenol", "cid": 1794427},
    "emodin": {"class": "Anthraquinone", "cid": 3220},
    "aloin": {"class": "Anthraquinone C-glycoside", "cid": 12305761},
    "forskolin": {"class": "Labdane Diterpene", "cid": 47936},
    "shatavarin": {"class": "Steroidal Saponin", "cid": 101662998},
    "tinocordiside": {"class": "Diterpene Glucoside", "cid": 44258957},
}

# Therapeutic Conditions / Indications dictionary
THERAPEUTIC_ACTIONS = [
    "anti-inflammatory", "antiinflammatory", "inflammation", "arthritis", "osteoarthritis", "rheumatoid arthritis",
    "antimicrobial", "antibacterial", "antifungal", "antiviral", "antiprotozoal", "antiseptic",
    "antimalarial", "malaria", "plasmodium", "fever", "antipyretic", "chills",
    "antidiabetic", "hypoglycemic", "diabetes", "hyperglycemia", "insulin resistance",
    "analgesic", "pain", "antinociceptive", "headache", "migraine", "dysmenorrhea",
    "antioxidant", "free radical scavenging", "oxidative stress", "lipid peroxidation",
    "wound healing", "skin lesions", "eczema", "psoriasis", "dermatitis", "burns",
    "hepatoprotective", "liver damage", "jaundice", "hepatitis", "cirrhosis",
    "cardioprotective", "hypertension", "antihypertensive", "blood pressure", "atherosclerosis", "hyperlipidemia",
    "neuroprotective", "alzheimer", "parkinson", "memory enhancement", "cognitive function", "dementia",
    "anticancer", "antineoplastic", "antitumor", "cytotoxic", "leukemia", "lymphoma", "apoptosis",
    "immunomodulatory", "immunosuppressive", "immune response", "immunostimulant",
    "adaptogen", "adaptogenic", "stress", "anxiety", "depression", "fatigue", "insomnia", "sedative",
    "antiemetic", "nausea", "vomiting", "motion sickness", "dyspepsia", "gastric ulcer", "gastroprotective",
    "respiratory", "asthma", "bronchitis", "cough", "expectorant",
    "antidiarrheal", "diarrhea", "dysentery", "anthelmintic", "parasitic infection",
    "dental plaque", "gingivitis", "periodontitis", "oral hygiene"
]

# Section Heuristics
SECTION_PATTERNS = [
    (r"\b(abstract)\b", "Abstract"),
    (r"\b(introduction|background)\b", "Introduction"),
    (r"\b(ethnobotanical|ethnopharmacolog|traditional uses?|folk medicine)\b", "Ethnopharmacology"),
    (r"\b(materials? and methods?|methodology|experimental)\b", "Materials and Methods"),
    (r"\b(in vitro|cell culture|assay)\b", "In Vitro Assays"),
    (r"\b(in vivo|animal models?|in-vivo)\b", "In Vivo Studies"),
    (r"\b(clinical trials?|human subjects?|clinical evaluation)\b", "Clinical Studies"),
    (r"\b(results?)\b", "Results"),
    (r"\b(discussion)\b", "Discussion"),
    (r"\b(conclusions?)\b", "Conclusion"),
]


class PDFExtractor:
    """Extracts text, metadata, and sentence units from scientific PDF documents."""

    @staticmethod
    def extract_from_bytes(pdf_bytes: bytes, filename: str = "uploaded_paper.pdf") -> Dict[str, Any]:
        """Extracts structured text per page from PDF bytes."""
        if fitz is None:
            raise RuntimeError("PyMuPDF (fitz) is required for PDF parsing.")

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages = []
        full_text_list = []
        metadata = doc.metadata or {}

        for page_idx in range(len(doc)):
            page = doc.load_page(page_idx)
            text = page.get_text("text")
            
            # Clean hyphenation across line breaks (e.g., 'anti-\ninflammatory' -> 'anti-inflammatory')
            cleaned_text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)
            cleaned_text = re.sub(r'\s*\n\s*', ' ', cleaned_text)
            
            pages.append({
                "page_number": page_idx + 1,
                "text": cleaned_text.strip(),
                "char_length": len(cleaned_text),
            })
            full_text_list.append(cleaned_text)

        doc.close()

        combined_text = "\n\n".join(full_text_list)
        return {
            "filename": filename,
            "page_count": len(pages),
            "pages": pages,
            "full_text": combined_text,
            "metadata": {
                "title": metadata.get("title") or filename.replace(".pdf", ""),
                "author": metadata.get("author", "Unknown"),
                "subject": metadata.get("subject", ""),
                "keywords": metadata.get("keywords", ""),
                "producer": metadata.get("producer", ""),
            }
        }

    @staticmethod
    def extract_from_path(file_path: str) -> Dict[str, Any]:
        """Extracts structured text from a file path."""
        with open(file_path, "rb") as f:
            data = f.read()
        return PDFExtractor.extract_from_bytes(data, filename=str(file_path).split("/")[-1].split("\\")[-1])


class BotanicalNER:
    """Identifies Latin binomials and common botanical names."""

    # Matches Latin binomial: Capitalized Genus followed by lowercase species epithet
    # (e.g. Curcuma longa, Azadirachta indica, Withania somnifera L.)
    BINOMIAL_PATTERN = re.compile(
        r'\b([A-Z][a-z]{2,20})\s+([a-z]{3,20}(?:-[a-z]{3,20})?)'
        r'(?:\s+(?:var\.|subsp\.|f\.)\s+[a-z]{3,20})?'
        r'(?:\s+(?:L\.|Mill\.|Roxb\.|DC\.|Lam\.|Hook\.f\.|Wall\.))?\b'
    )

    # Words that look like binomials but are common scientific English terms
    FALSE_POSITIVE_GENERA = {
        "Figure", "Table", "Method", "Results", "Discussion", "Author", "Journal",
        "Recent", "Several", "Various", "These", "Their", "Other", "Studies",
        "Section", "Volume", "Chapter", "However", "Although", "Between",
        "Extract", "Extracts", "Sample", "Samples", "Activity", "Effect", "Effects",
        "Standard", "Control", "Treatment", "Patient", "Patients", "Animal", "Animals",
        "Total", "Mean", "Standard", "Deviation", "Significantly", "Furthermore",
        "Therefore", "Department", "University", "Faculty", "Laboratory", "Institute",
        "Publishing", "Elsevier", "Springer", "Academic", "Press", "London", "China",
        "India", "National", "International", "American", "European",
        "Experimental", "Osteoarthritis", "Synovial", "Inflammation", "Evaluation",
        "Clinical", "Chemical", "Biological", "Medical", "Traditional", "Historical",
        "Pharmacological", "Therapeutic", "Phytochemical", "Extraction", "Isolation",
        "Analysis", "Identification", "Characterization", "Investigation", "Comparison",
        "Inhibition", "Activation", "Induction", "Reduction", "Expression", "Concentration",
        "Administration", "Suppression", "Enhancement", "Production", "Preparation",
        "Distribution", "Classification", "Conclusion", "Conclusions", "Abstract",
        "Introduction", "Summary", "Background", "Screening", "Evaluation",
        "Ayurvedic", "Herbal", "Complementary", "Alternative", "Western", "Eastern",
        "Modern", "Native", "Indigenous", "Folk", "Ancient", "Current", "Primary",
        "Wistar", "Sprague", "Dawley", "Murine", "Rodent", "Rats", "Mice", "Rabbits",
        "Guinea", "Zebrafish", "Drosophila"
    }

    FALSE_POSITIVE_SPECIES = {
        "and", "for", "the", "with", "from", "that", "this", "into", "over", "upon",
        "when", "were", "have", "been", "than", "also", "such", "most", "each", "both",
        "only", "used", "some", "more", "then", "them", "these", "those", "their", "will",
        "what", "which", "where", "while", "after", "before", "during", "since", "under",
        "about", "above", "below", "between", "through", "against", "without", "within",
        "because", "although", "whereas", "unless", "until", "could", "would", "should",
        "might", "must", "shall", "does", "done", "doing", "being", "having", "was",
        "are", "per", "via", "its", "not", "but", "all", "any", "can", "may", "our",
        "two", "one", "six", "ten", "few", "out", "off", "dry", "wet", "hot", "low",
        "medicine", "preparations", "extracts", "species", "plants", "remedies", "tissues",
        "formulations", "cohorts", "trials", "studies", "uses", "therapy", "treatment",
        "care", "health", "system", "systems", "practices", "findings", "methods", "models",
        "powder", "rhizome", "leaves", "roots", "bark", "seeds", "fruit", "flowers",
        "analysis", "study", "data", "integrity", "swelling", "edema", "lesions", "damage",
        "response", "action", "activity", "process", "mechanism", "receptor", "protein",
        "molecule", "compound", "fraction", "sample", "cohort", "patient", "volunteer",
        "rats", "mice", "rabbits", "pigs", "monkeys", "dogs", "cats", "hamsters", "worms"
    }

    @classmethod
    def find_plants(cls, text: str) -> List[Dict[str, Any]]:
        """Extracts plant entities from text."""
        plants = []
        found_names = set()

        # 1. Search common names lexicon first
        text_lower = text.lower()
        for common_name, sci_name in COMMON_MEDICINAL_PLANTS.items():
            pattern = r'\b' + re.escape(common_name) + r'\b'
            for match in re.finditer(pattern, text_lower):
                if sci_name not in found_names:
                    found_names.add(sci_name)
                    plants.append({
                        "scientific_name": sci_name,
                        "matched_term": common_name,
                        "is_vernacular": True,
                        "start": match.start(),
                        "end": match.end(),
                        "confidence": 0.95
                    })

        # 2. Search scientific binomials
        for match in cls.BINOMIAL_PATTERN.finditer(text):
            genus = match.group(1)
            species = match.group(2)
            
            # Filter English nouns, prepositions, and grammatical suffixes
            g_lower = genus.lower()
            s_lower = species.lower()

            if (genus in cls.FALSE_POSITIVE_GENERA or 
                s_lower in cls.FALSE_POSITIVE_SPECIES or
                g_lower.endswith(('ical', 'ological', 'scopic', 'metric', 'graphic', 'tory', 'tion', 'sion', 'ment', 'ity', 'ance', 'ence', 'ing', 'able', 'ible')) or
                s_lower.endswith(('ing', 'tion', 'sion', 'ment', 'ity', 'ance', 'ence', 'able', 'ible'))):
                continue
            if len(genus) < 3 or len(species) < 3:
                continue

            full_binomial = f"{genus} {species}"
            if full_binomial not in found_names:
                found_names.add(full_binomial)
                plants.append({
                    "scientific_name": full_binomial,
                    "matched_term": match.group(0).strip(),
                    "is_vernacular": False,
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.92
                })

        return plants


class PhytochemicalNER:
    """Identifies chemical compounds, bioactives, and secondary metabolites."""

    # Chemical suffix patterns
    SUFFIX_PATTERN = re.compile(
        r'\b([a-z0-9\-\(\)]+('
        r'oside|oside[s]?|in|in[s]?|ine|ine[s]?|ol|ol[s]?|one|one[s]?|oid|oid[s]?|'
        r'terpene|terpenoid[s]?|flavone[s]?|flavonol[s]?|tannin[s]?|alkaloid[s]?|'
        r'lactone[s]?|catechin[s]?|cannabinoid[s]?|saponin[s]?|curcuminoid[s]?'
        r'))\b',
        re.IGNORECASE
    )

    COMMON_NON_COMPOUNDS = {
        "within", "main", "brain", "protein", "origin", "skin", "pain", "gain", "drain",
        "strain", "train", "chain", "remain", "contain", "certain", "mountain", "fountain",
        "curtain", "captain", "villain", "routine", "discipline", "doctrine", "engine",
        "examine", "determine", "combine", "define", "decline", "line", "fine", "mine",
        "wine", "shine", "online", "outline", "guideline", "timeline", "baseline",
        "pipeline", "discipline", "feminine", "masculine", "control", "protocol",
        "alcohol", "cholesterol", "phenol", "glycerol", "done", "alone", "stone",
        "bone", "zone", "tone", "cone", "phone", "clone", "none", "shone", "prone"
    }

    @classmethod
    def find_compounds(cls, text: str) -> List[Dict[str, Any]]:
        """Extracts chemical compounds from text."""
        compounds = []
        found_compounds = set()
        text_lower = text.lower()

        # 1. Exact match against curated phytochemical dictionary
        for comp_name, comp_info in KNOWN_COMPOUNDS.items():
            pattern = r'\b' + re.escape(comp_name) + r'\b'
            for match in re.finditer(pattern, text_lower):
                capitalized_name = comp_name.title()
                if capitalized_name not in found_compounds:
                    found_compounds.add(capitalized_name)
                    compounds.append({
                        "name": capitalized_name,
                        "matched_term": comp_name,
                        "chemical_class": comp_info["class"],
                        "pubchem_cid": comp_info["cid"],
                        "start": match.start(),
                        "end": match.end(),
                        "confidence": 0.98
                    })

        # 2. Match regular chemical patterns if not already found
        for match in cls.SUFFIX_PATTERN.finditer(text):
            word = match.group(1).lower().strip()
            if word in cls.COMMON_NON_COMPOUNDS or len(word) < 5:
                continue

            cap_word = word.title()
            if cap_word not in found_compounds:
                # Infer rough chemical class from suffix
                chem_class = "Secondary Metabolite"
                if word.endswith(("ol", "ols")):
                    chem_class = "Phenolic / Alcohol"
                elif word.endswith(("ine", "ines")):
                    chem_class = "Alkaloid / Amine"
                elif word.endswith(("oside", "osides")):
                    chem_class = "Glycoside"
                elif word.endswith(("one", "ones")):
                    chem_class = "Ketone / Flavonoid"
                elif word.endswith(("in", "ins")):
                    chem_class = "Bioactive Constituent"

                found_compounds.add(cap_word)
                compounds.append({
                    "name": cap_word,
                    "matched_term": match.group(0),
                    "chemical_class": chem_class,
                    "pubchem_cid": None,
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.82
                })

        return compounds


class EvidenceClassifier:
    """Classifies scientific sentences into standardized evidence tiers.
    Separates extraction confidence from scientific evidence strength.
    """

    CLINICAL_KEYWORDS = [
        "clinical trial", "human trial", "human subjects", "randomized controlled trial",
        "double-blind", "placebo-controlled", "rct", "patients", "human volunteers",
        "clinical efficacy", "phase i", "phase ii", "phase iii", "phase iv", "in humans",
        "tolerability in humans", "clinical study", "participants", "serum levels in patients"
    ]

    IN_VIVO_KEYWORDS = [
        "in vivo", "in-vivo", "mice", "mouse model", "rats", "wistar", "sprague-dawley",
        "guinea pig", "rabbits", "animal model", "oral gavage", "intraperitoneal",
        "mg/kg", "paw edema", "carrageenan", "streptozotocin-induced", "rodent"
    ]

    IN_VITRO_KEYWORDS = [
        "in vitro", "in-vitro", "cell culture", "cell line", "assay", "inhibition",
        "ic50", "mic", "ec50", "dpph", "mcf-7", "hepg2", "raw 264.7", "hct-116",
        "enzyme assay", "free radical scavenging", "agar dilution", "well diffusion",
        "microplate", "spectrophotometric", "receptor binding", "elisa", "western blot"
    ]

    TRADITIONAL_KEYWORDS = [
        "traditional", "traditionally", "ethnobotanical", "indigenous", "folk medicine",
        "folkloric", "ayurveda", "ayurvedic", "charaka", "sushruta", "unani", "siddha",
        "traditional chinese medicine", "tcm", "decoction", "infusion", "poultice",
        "healer", "tribal", "ancestral", "herbal preparation", "ancient prescription",
        "qinghao", "rasayana"
    ]

    REVIEW_KEYWORDS = [
        "systematic review", "meta-analysis", "meta analysis", "literature review",
        "cochrane", "prisma", "pooled analysis"
    ]

    @classmethod
    def classify(cls, sentence: str, section: str = "") -> Tuple[str, float]:
        """Classifies sentence into evidence tier and returns (tier_code, confidence)."""
        s_lower = sentence.lower()
        sec_lower = section.lower()

        scores = {
            "CLINICAL": 0.0,
            "IN_VIVO": 0.0,
            "IN_VIVO": 0.0,
            "IN_VITRO": 0.0,
            "TRADITIONAL": 0.0,
            "REVIEW_META": 0.0,
        }

        # Check keywords
        for kw in cls.CLINICAL_KEYWORDS:
            if kw in s_lower:
                scores["CLINICAL"] += 2.0

        for kw in cls.IN_VIVO_KEYWORDS:
            if kw in s_lower:
                scores["IN_VIVO"] += 2.0

        for kw in cls.IN_VITRO_KEYWORDS:
            if kw in s_lower:
                scores["IN_VITRO"] += 2.0

        for kw in cls.TRADITIONAL_KEYWORDS:
            if kw in s_lower:
                scores["TRADITIONAL"] += 2.0

        for kw in cls.REVIEW_KEYWORDS:
            if kw in s_lower:
                scores["REVIEW_META"] += 2.5

        # Section boosts
        if "clinical" in sec_lower or "human" in sec_lower:
            scores["CLINICAL"] += 1.5
        elif "in vivo" in sec_lower or "animal" in sec_lower:
            scores["IN_VIVO"] += 1.5
        elif "in vitro" in sec_lower or "assay" in sec_lower or "cell" in sec_lower:
            scores["IN_VITRO"] += 1.5
        elif "ethno" in sec_lower or "traditional" in sec_lower or "folk" in sec_lower:
            scores["TRADITIONAL"] += 1.5

        # Pick highest scoring tier
        best_tier, best_score = max(scores.items(), key=lambda x: x[1])

        if best_score == 0:
            # Default fallback: If mentions ethnobotanical roots, TRADITIONAL; otherwise IN_VITRO
            return "TRADITIONAL" if any(w in s_lower for w in ["used", "remedy", "plant", "herb"]) else "IN_VITRO", 0.65

        # Calculate confidence based on evidence signals
        confidence = min(0.98, 0.70 + (best_score * 0.06))
        return best_tier, confidence


class KnowledgeExtractor:
    """End-to-End Extraction Engine:
    Processes full PDF or text, extracts entities, finds claim triples,
    preserves exact source sentences, and structures the output.
    """

    CLAIM_TRIGGERS = [
        r'\b(?:is|was|were|has been)\s+(?:traditionally\s+)?(?:used|administered|prescribed|employed)\s+(?:for|to treat|in the treatment of|against)\b',
        r'\b(?:exhibited|demonstrated|showed|displayed|possessed)\s+(?:potent|significant|notable|strong|marked)?\s*(?:activity|effects?|properties|efficacy)\s+(?:against|in|for)\b',
        r'\b(?:inhibited|suppressed|reduced|attenuated|blocked|alleviated|ameliorated|relieved)\b',
        r'\b(?:treatment|therapy|prevention|management)\s+of\b',
        r'\b(?:potential\s+therapeutic\s+agent\s+for|promising\s+candidate\s+for)\b',
        r'\b(?:induced\s+apoptosis|cytotoxic\s+against|scavenged|reduced\s+pain)\b',
    ]

    @staticmethod
    def split_into_sentences(text: str) -> List[Dict[str, Any]]:
        """Splits text into sentences while tracking offsets."""
        # Clean excessive whitespace
        raw_sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9])', text)
        sentences = []
        current_offset = 0

        for s in raw_sentences:
            s_clean = s.strip()
            if len(s_clean) > 20:  # Skip trivial fragments
                sentences.append({
                    "sentence": s_clean,
                    "start": current_offset,
                    "end": current_offset + len(s_clean),
                    "length": len(s_clean)
                })
            current_offset += len(s) + 1

        return sentences

    @classmethod
    def detect_section(cls, text_before: str) -> str:
        """Determines current section heading based on preceding text."""
        for pattern, section_name in reversed(SECTION_PATTERNS):
            if re.search(pattern, text_before[-500:], re.IGNORECASE):
                return section_name
        return "Literature"

    @classmethod
    def extract_claims_from_text(cls, text: str, default_page: int = 1, context_plant: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Analyzes text and returns structured medicinal-use claim records.
        Supports document-level context plant propagation across sentences.
        """
        claims = []
        sentences = cls.split_into_sentences(text)
        current_plant_context = context_plant

        for sent_info in sentences:
            sentence = sent_info["sentence"]
            
            # 1. Identify plant entities in this sentence
            plants = BotanicalNER.find_plants(sentence)
            if plants:
                current_plant_context = plants[0]
            elif current_plant_context:
                # Inherit document/section plant context if none in current sentence
                plants = [current_plant_context]

            if not plants:
                continue

            # 2. Identify chemical compounds
            compounds = PhytochemicalNER.find_compounds(sentence)

            # 3. Identify therapeutic indications / conditions
            s_lower = sentence.lower()
            matched_indications = []
            for action in THERAPEUTIC_ACTIONS:
                if action in s_lower:
                    matched_indications.append(action)

            # 4. Check for claim action triggers or presence of indication
            has_trigger = any(re.search(trig, sentence, re.IGNORECASE) for trig in cls.CLAIM_TRIGGERS)
            
            if matched_indications or has_trigger:
                # Classify evidence tier
                evidence_tier, tier_conf = EvidenceClassifier.classify(sentence)

                # Format primary condition or use
                if matched_indications:
                    # Clean up condition string
                    condition_str = ", ".join(sorted(list(set(matched_indications))[:3])).title()
                else:
                    condition_str = "Medicinal / Bioactive Property"

                for plant in plants:
                    linked_compound = compounds[0]["name"] if compounds else None
                    compound_cid = compounds[0]["pubchem_cid"] if compounds else None
                    compound_class = compounds[0]["chemical_class"] if compounds else None

                    # Calculate NLP extraction confidence (distinct from evidence strength)
                    extraction_conf = 0.80
                    if has_trigger:
                        extraction_conf += 0.08
                    if compounds:
                        extraction_conf += 0.07
                    if plant.get("confidence", 0) > 0.90:
                        extraction_conf += 0.04
                    extraction_conf = min(0.99, extraction_conf)

                    claims.append({
                        "plant_name": plant["scientific_name"],
                        "plant_common": plant.get("matched_term") if plant.get("is_vernacular") else None,
                        "compound_name": linked_compound,
                        "compound_cid": compound_cid,
                        "compound_class": compound_class,
                        "condition_or_use": condition_str,
                        "evidence_tier": evidence_tier,
                        "source_sentence": sentence,
                        "section": cls.detect_section(text[:sent_info["start"]]),
                        "page_number": default_page,
                        "extraction_confidence": round(extraction_conf, 2),
                        "verification_status": "Unverified",  # Default per scientific constraint!
                        "is_demo": 0
                    })

        return claims

    @classmethod
    def extract_from_pdf_data(cls, pdf_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Runs full end-to-end extraction pipeline on a PDF with context tracking."""
        extracted_doc = PDFExtractor.extract_from_bytes(pdf_bytes, filename)
        all_claims = []
        unique_plants = {}
        unique_compounds = {}

        # First pass: find global primary plant for the paper from Title or Page 1
        initial_plants = BotanicalNER.find_plants(extracted_doc["full_text"][:2000])
        primary_plant_context = initial_plants[0] if initial_plants else None

        for page in extracted_doc["pages"]:
            page_claims = cls.extract_claims_from_text(
                page["text"], 
                default_page=page["page_number"],
                context_plant=primary_plant_context
            )
            all_claims.extend(page_claims)

            for claim in page_claims:
                p_name = claim["plant_name"]
                if p_name not in unique_plants:
                    unique_plants[p_name] = {
                        "scientific_name": p_name,
                        "common_names": claim.get("plant_common") or "",
                        "occurrences": 1
                    }
                else:
                    unique_plants[p_name]["occurrences"] += 1

                c_name = claim["compound_name"]
                if c_name and c_name not in unique_compounds:
                    unique_compounds[c_name] = {
                        "name": c_name,
                        "pubchem_cid": claim.get("compound_cid"),
                        "chemical_class": claim.get("compound_class"),
                        "occurrences": 1
                    }
                elif c_name:
                    unique_compounds[c_name]["occurrences"] += 1

        return {
            "document_info": extracted_doc["metadata"],
            "filename": filename,
            "page_count": extracted_doc["page_count"],
            "claims": all_claims,
            "plants": list(unique_plants.values()),
            "compounds": list(unique_compounds.values()),
            "full_text": extracted_doc["full_text"]
        }
