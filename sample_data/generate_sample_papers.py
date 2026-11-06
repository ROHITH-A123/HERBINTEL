"""Generates sample research PDFs for testing HERBINTEL extraction pipeline."""

import fitz
from pathlib import Path


def create_turmeric_pdf(output_path: Path):
    doc = fitz.open()
    
    # Page 1: Title, Abstract, Ethnopharmacology, In Vitro Assays
    page1 = doc.new_page()
    text_page1 = """JOURNAL OF ETHNOPHARMACOLOGY AND PHYTOCHEMISTRY (2024)

Evaluation of Curcuma longa and Curcumin in Experimental Osteoarthritis and Synovial Inflammation
Authors: Daily JW, Park S, Hewlings SJ, Kalman DS

ABSTRACT
Curcuma longa (turmeric), an ancient perennial herb belonging to the family Zingiberaceae, is extensively documented across traditional Ayurvedic medicine. The rhizome contains active bioactive polyphenols known as curcuminoids, predominantly curcumin. This investigation evaluates traditional ethnobotanical claims against modern in vitro assays, rodent models, and human clinical trial cohorts.

ETHNOPHARMACOLOGY AND TRADITIONAL USES
In Ayurvedic and Traditional Chinese Medicine, Curcuma longa has been traditionally used for centuries for the treatment of inflammatory disorders, joint rheumatism, biliary colic, and abdominal pain. Traditional preparations involved boiling the dried rhizome with milk or topically applying fresh rhizome paste onto septic lesions and sprains.

IN VITRO MECHANISTIC ASSAYS
In vitro macrophage cell culture assays revealed that curcumin inhibited the activation of NF-kappaB and downregulated COX-2 expression with an IC50 of 5.8 micromolar. Furthermore, curcumin exhibited marked free radical scavenging activity in DPPH antioxidant assays, neutralizing reactive oxygen species in synovial fibroblasts."""
    
    page1.insert_textbox(fitz.Rect(50, 50, 550, 750), text_page1, fontsize=10, fontname="helv")

    # Page 2: In Vivo Animal Studies, Human Clinical Trials, Discussion
    page2 = doc.new_page()
    text_page2 = """PAGE 2 - EXPERIMENTAL FINDINGS AND CLINICAL VALIDATION

IN VIVO ANIMAL MODELS
In male Wistar rats subjected to carrageenan-induced paw edema, oral administration of standardized Curcuma longa extract (250 mg/kg) produced a 62% reduction in paw swelling over 6 hours. Histopathological analysis confirmed significant suppression of neutrophil infiltration and preservation of articular cartilage integrity without noticeable gastric ulceration.

RANDOMIZED CONTROLLED CLINICAL TRIALS
In a randomized, double-blind, placebo-controlled clinical trial involving 120 patients with symptomatic knee osteoarthritis, oral supplementation with 1000 mg/day of standardized curcumin extract for 12 weeks demonstrated statistically significant pain reduction in Western Ontario and McMaster Universities Osteoarthritis Index (WOMAC) scores. Serum C-reactive protein (CRP) levels decreased by 34% compared to baseline in the active treatment cohort.

DISCUSSION AND CONCLUSIONS
These multi-tiered findings support the traditional ethnopharmacological status of Curcuma longa while identifying specific molecular targets of curcumin. Further multi-center human trials are recommended to validate long-term bioavailability."""
    
    page2.insert_textbox(fitz.Rect(50, 50, 550, 750), text_page2, fontsize=10, fontname="helv")

    doc.save(str(output_path))
    doc.close()
    print(f"Generated {output_path}")


def create_ashwagandha_pdf(output_path: Path):
    doc = fitz.open()

    page1 = doc.new_page()
    text_page1 = """INTERNATIONAL JOURNAL OF AYURVEDIC BIOSCIENCES (2025)

Withania somnifera and Withaferin A: Biomarkers, Cortisol Dynamics, and Neuroprotection
Authors: Chandrasekhar K, Kapoor J, Mishra LC, Singh BB

ABSTRACT
Withania somnifera, popularly designated as Ashwagandha or Indian Ginseng, holds central status as a premier Rasayana in traditional Ayurvedic jurisprudence. This research clarifies the clinical and molecular basis of its adaptogenic and neuroprotective properties.

AYURVEDIC TRADITION AND ETHNOBOTANY
Withania somnifera has been traditionally used for over 3,000 years in Ayurveda as a rejuvenating rasayana to promote longevity, enhance cognitive vigor, and relieve nervous exhaustion. Indigenous practitioners prepare fine root powder mixed with clarified butter (ghee) or warm milk for restorative convalescence.

IN VITRO CELLULAR MODELS
Phytochemical fractions containing withaferin A demonstrated significant neuroprotection against beta-amyloid-induced toxicity in human neuroblastoma SH-SY5Y cell lines. In vitro assays demonstrated that withaferin A suppressed microglial nitric oxide synthase and reduced pro-inflammatory cytokines."""
    
    page1.insert_textbox(fitz.Rect(50, 50, 550, 750), text_page1, fontsize=10, fontname="helv")

    page2 = doc.new_page()
    text_page2 = """PAGE 2 - CLINICAL INVESTIGATION AND ADAPTOGENIC PROFILING

HUMAN CLINICAL TRIAL FINDINGS
In a prospective, randomized, double-blind, placebo-controlled clinical trial evaluating 64 healthy adult subjects with a history of chronic mental stress, administration of 300 mg of high-concentration Withania somnifera root extract twice daily for 60 days resulted in a 27.9% reduction in serum cortisol levels compared to the placebo group. Participants reported substantial improvements on standardized stress-assessment scales.

IN VIVO STRESS ASSAYS
In Sprague-Dawley rodents subjected to chronic restraint stress, Withania somnifera administration attenuated lipid peroxidation in the hippocampus and prevented stress-induced adrenal hypertrophy.

CONCLUSION
The integration of traditional Ayurvedic claims with verified randomized human clinical evidence substantiates Withania somnifera as an authentic adaptogen driven by steroidal withanolides."""
    
    page2.insert_textbox(fitz.Rect(50, 50, 550, 750), text_page2, fontsize=10, fontname="helv")

    doc.save(str(output_path))
    doc.close()
    print(f"Generated {output_path}")


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent
    create_turmeric_pdf(out_dir / "sample_turmeric_curcumin_study.pdf")
    create_ashwagandha_pdf(out_dir / "sample_ashwagandha_neuroprotection.pdf")
