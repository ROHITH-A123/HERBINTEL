"""HERBINTEL Plant Explorer Page.
Provides in-depth botanical profiles, Kew POWO taxonomy, GBIF occurrence mapping,
verified phytochemical composition, and associated scientific evidence claims.
"""

import streamlit as st
import plotly.graph_objects as go
from ..components import render_header, render_disclaimer, render_trust_panel
from ..theme import render_evidence_badge, render_status_badge
from ...core.database import get_all_plants, get_plant_details
from ...integrations.gbif import GBIFClient
from ...integrations.powo import POWOClient
from ...integrations.pubchem import PubChemClient


def render_plant_explorer_page():
    render_header("Plant Explorer", "Taxonomy, Phytochemistry & Evidence Profiles")
    render_disclaimer()

    plants = get_all_plants()
    if not plants:
        st.warning("No plant records found in the database. Please initialize the database.")
        return

    plant_options = {f"{p['scientific_name']} ({p.get('common_names') or 'No common name'})": p["id"] for p in plants}
    selected_label = st.selectbox("Select Medicinal Plant:", list(plant_options.keys()))
    plant_id = plant_options[selected_label]

    plant = get_plant_details(plant_id)
    if not plant:
        st.error("Plant profile could not be loaded.")
        return

    # Plant Header Details
    st.markdown(f"## *{plant['scientific_name']}*")
    if plant.get("is_demo"):
        st.markdown('<span class="badge badge-demo">BENCHMARK ETHNOBOTANICAL RECORD</span>', unsafe_allow_html=True)

    col_meta1, col_meta2, col_meta3 = st.columns(3)
    with col_meta1:
        st.markdown(f"**Common Names:** {plant.get('common_names') or 'N/A'}")
        st.markdown(f"**Family:** `{plant.get('family') or 'N/A'}`")
        st.markdown(f"**Genus:** *{plant.get('genus') or 'N/A'}*")

    with col_meta2:
        st.markdown(f"**Native Region:** {plant.get('native_region') or 'N/A'}")
        st.markdown(f"**Conservation Status:** `{plant.get('conservation_status') or 'Not Evaluated'}`")
        if plant.get("powo_id"):
            st.markdown(f"**Kew POWO:** [{plant['powo_id']}](https://powo.science.kew.org/taxon/{plant['powo_id']})")

    with col_meta3:
        if plant.get("gbif_id"):
            st.markdown(f"**GBIF Species ID:** [{plant['gbif_id']}](https://www.gbif.org/species/{plant['gbif_id']})")
        st.markdown(f"**Active Phytocompounds:** {len(plant.get('compounds', []))}")
        st.markdown(f"**Documented Claims:** {len(plant.get('claims', []))}")

    if plant.get("notes"):
        st.info(f"**Botanical & Ethnobotanical Context:** {plant['notes']}")

    # Tabs: Distribution Map, Phytochemistry, Evidence Claims
    tab_geo, tab_phyto, tab_claims = st.tabs(["🌍 Geographic Distribution (GBIF)", "🧪 Phytochemical Profile (PubChem)", "📚 Evidence & Claims Matrix"])

    with tab_geo:
        st.subheader("Georeferenced Occurrence Distribution")
        gbif_client = GBIFClient()
        coords = gbif_client.get_occurrences(species_key=plant.get("gbif_id"), scientific_name=plant["scientific_name"])

        if coords:
            lats = [c["latitude"] for c in coords]
            lons = [c["longitude"] for c in coords]
            hover_text = [f"{c.get('country', '')} ({c.get('year', '')})" for c in coords]

            fig_map = go.Figure(data=go.Scattergeo(
                lon=lons,
                lat=lats,
                text=hover_text,
                mode="markers",
                marker=dict(
                    size=9,
                    color="#2E7D32",
                    opacity=0.85,
                    line=dict(width=1, color="#FFFFFF")
                )
            ))
            fig_map.update_layout(
                title=f"Specimen Occurrences for {plant['scientific_name']}",
                geo=dict(
                    projection_type="natural earth",
                    showland=True,
                    landcolor="#F0F4F1",
                    countrycolor="#CCCCCC",
                    coastlinecolor="#CCCCCC",
                    showcountries=True,
                ),
                margin=dict(l=0, r=0, t=40, b=0),
                height=450
            )
            st.plotly_chart(fig_map, use_container_width=True)
            source = coords[0].get("data_source", "Live GBIF occurrence record")
            if source.startswith("Illustrative"):
                st.warning("Illustrative fallback coordinates are displayed because live GBIF records were unavailable. They are not specimen occurrences.")
            else:
                st.caption(f"Showing {len(coords)} georeferenced specimen coordinate points from GBIF.")
        else:
            st.info("No georeferenced specimen coordinates available for this taxon.")

    with tab_phyto:
        st.subheader("Isolated Bioactive Secondary Metabolites")
        compounds = plant.get("compounds", [])
        if compounds:
            for comp in compounds:
                with st.expander(f"🧪 {comp['name']} ({comp.get('chemical_class', 'Bioactive')})", expanded=True):
                    cp1, cp2 = st.columns([2, 1])
                    with cp1:
                        st.markdown(f"**Chemical Class:** {comp.get('chemical_class', 'N/A')}")
                        st.markdown(f"**Plant Part Located:** {comp.get('plant_part', 'Whole plant')}")
                        if comp.get("concentration_notes"):
                            st.markdown(f"**Yield / Concentration:** {comp.get('concentration_notes')}")
                        if comp.get("molecular_formula"):
                            st.markdown(f"**Molecular Formula:** `{comp.get('molecular_formula')}`")
                        if comp.get("molecular_weight"):
                            st.markdown(f"**Molecular Weight:** {comp.get('molecular_weight')} g/mol")
                        if comp.get("pubchem_cid"):
                            st.markdown(f"**PubChem CID:** [{comp['pubchem_cid']}](https://pubchem.ncbi.nlm.nih.gov/compound/{comp['pubchem_cid']})")
                        if comp.get("canonical_smiles"):
                            st.code(comp["canonical_smiles"], language="text")
                    with cp2:
                        cid = comp.get("pubchem_cid")
                        if cid:
                            img_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/PNG"
                            st.image(img_url, caption=f"2D Structure: {comp['name']}", width=220)
        else:
            st.info("No chemical constituents currently indexed for this plant.")

    with tab_claims:
        st.subheader("Documented Medicinal Claims & Evidence Hierarchy")
        claims = plant.get("claims", [])
        if claims:
            for idx, c in enumerate(claims, 1):
                st.markdown(f"#### #{idx} {c['condition_or_use']}")
                st.markdown(
                    f"{render_evidence_badge(c['evidence_tier'])} {render_status_badge(c['verification_status'])}",
                    unsafe_allow_html=True
                )
                if c.get("compound_name"):
                    st.markdown(f"**Bioactive Component:** `{c['compound_name']}`")
                
                st.markdown(f"""
                <div class="citation-box">
                    "{c['source_sentence']}"
                </div>
                """, unsafe_allow_html=True)

                st.caption(
                    f"Section: {c.get('section', 'N/A')} | "
                    f"Page: {c.get('page_number', 1)} | "
                    f"Extraction Confidence: {round(c.get('extraction_confidence', 0.85)*100, 1)}% | "
                    f"Paper: {c.get('paper_title', 'Literature')}"
                )
                if c.get("paper_doi"):
                    st.markdown(f"🔗 DOI: [{c['paper_doi']}](https://doi.org/{c['paper_doi']})")
                render_trust_panel(c)
                st.markdown("---")
        else:
            st.info("No claims currently associated with this plant.")

