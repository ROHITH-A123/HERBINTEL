"""HERBINTEL Biodiversity & Taxonomy Explorer Page.
Provides live queries to Kew POWO, GBIF, PubChem, and Europe PMC for cross-validating
botanical nomenclature, global biodiversity distributions, phytochemical structures, and peer-reviewed literature.
"""

import streamlit as st
import plotly.graph_objects as go
from ..components import render_header, render_disclaimer
from ...integrations.powo import POWOClient
from ...integrations.pubchem import PubChemClient
from ...integrations.europe_pmc import EuropePMCClient
from ...integrations.gbif import GBIFClient


def render_validator_page():
    render_header("Biodiversity Explorer", "Cross-Validation via Kew POWO, GBIF, PubChem & Europe PMC")
    render_disclaimer()

    st.markdown("""
    Use this utility to cross-validate ethnobotanical taxa, map global occurrences from GBIF, inspect chemical structures,
    and discover open-access research papers in real time.
    """)

    sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs([
        "🌿 Kew POWO Botanical Validator",
        "🌍 GBIF Biodiversity & Occurrences",
        "🧪 PubChem Chemical Inspector",
        "📚 Europe PMC Literature Search"
    ])

    with sub_tab1:
        st.subheader("Kew Plants of the World Online (POWO) Taxonomy Validation")
        plant_query = st.text_input("Enter Plant Scientific Name or Vernacular:", value="Curcuma longa")
        
        if st.button("Validate Botanical Taxon", type="primary", key="btn_powo_val"):
            with st.spinner(f"Resolving '{plant_query}' via Kew POWO API..."):
                powo_client = POWOClient()
                res = powo_client.search_taxon(plant_query)

            if res:
                st.success(f"Taxon Resolved: **{res.get('name', plant_query)}**")
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**Family:** `{res.get('family', 'N/A')}`")
                    st.markdown(f"**Taxonomic Status:** `{res.get('taxonomic_status', 'N/A')}`")
                    st.markdown(f"**Accepted Name:** *{res.get('accepted_name', res.get('name'))}*")
                with c2:
                    if res.get("powo_id"):
                        st.markdown(f"**POWO / IPNI Identifier:** `{res['powo_id']}`")
                        st.markdown(f"🔗 [View Official Kew POWO Profile]({res.get('url', '#')})")
            else:
                st.warning("No taxon records found for this query.")

    with sub_tab2:
        st.subheader("Global Biodiversity Information Facility (GBIF) Species & Occurrence Map")
        gbif_query = st.text_input("Enter Plant Scientific Name for GBIF Distribution:", value="Withania somnifera")

        if st.button("Search GBIF Occurrences", type="primary", key="btn_gbif_val"):
            with st.spinner(f"Querying GBIF for '{gbif_query}' taxonomy and specimen records..."):
                gbif_client = GBIFClient()
                tax = gbif_client.match_species(gbif_query)
                coords = gbif_client.get_occurrences(
                    species_key=tax.get("usageKey") if tax else None,
                    scientific_name=gbif_query,
                    limit=50
                )

            if tax:
                st.success(f"GBIF Match: **{tax.get('scientificName', gbif_query)}** (Status: `{tax.get('status', 'ACCEPTED')}`)")
                g1, g2, g3 = st.columns(3)
                with g1:
                    st.markdown(f"**Kingdom:** {tax.get('kingdom', 'Plantae')}")
                    st.markdown(f"**Family:** `{tax.get('family', 'N/A')}`")
                with g2:
                    st.markdown(f"**Genus:** *{tax.get('genus', 'N/A')}*")
                    st.markdown(f"**GBIF Usage Key:** `{tax.get('usageKey', 'N/A')}`")
                with g3:
                    st.markdown(f"**Specimens Mapped:** `{len(coords)}`")

            if coords:
                lats = [c["latitude"] for c in coords]
                lons = [c["longitude"] for c in coords]
                text_pts = [f"{c.get('country', '')} ({c.get('year', '')})" for c in coords]

                fig_map = go.Figure(data=go.Scattergeo(
                    lon=lons,
                    lat=lats,
                    text=text_pts,
                    mode="markers",
                    marker=dict(size=8, color="#2E7D32", opacity=0.85, line=dict(width=1, color="#FFFFFF"))
                ))
                fig_map.update_layout(
                    title=f"GBIF Occurrence Records for {gbif_query}",
                    geo=dict(projection_type="natural earth", showland=True, landcolor="#F4F6F4", countrycolor="#CCCCCC"),
                    margin=dict(l=0, r=0, t=35, b=0),
                    height=420
                )
                st.plotly_chart(fig_map, use_container_width=True)
                source = coords[0].get("data_source", "Live GBIF occurrence record")
                if source.startswith("Illustrative"):
                    st.warning("Illustrative fallback coordinates only — these are not live GBIF specimen records.")
            else:
                st.info("No georeferenced specimen points available.")

    with sub_tab3:
        st.subheader("NCBI PubChem Phytochemical Structure Inspector")
        comp_query = st.text_input("Enter Chemical Compound Name:", value="Artemisinin")

        if st.button("Inspect Chemical Structure", type="primary", key="btn_pubchem_val"):
            with st.spinner(f"Fetching chemical properties for '{comp_query}' from PubChem..."):
                pubchem_client = PubChemClient()
                res = pubchem_client.get_compound_by_name(comp_query)

            if res:
                st.success(f"Compound Resolved: **{res.get('name', comp_query)}**")
                cp1, cp2 = st.columns([3, 2])
                with cp1:
                    st.markdown(f"**PubChem CID:** `{res.get('pubchem_cid')}`")
                    st.markdown(f"**Molecular Formula:** `{res.get('molecular_formula', 'N/A')}`")
                    st.markdown(f"**Molecular Weight:** `{res.get('molecular_weight', 'N/A')} g/mol`")
                    st.markdown(f"**InChIKey:** `{res.get('inchi_key', 'N/A')}`")
                    if res.get("canonical_smiles"):
                        st.markdown("**Canonical SMILES:**")
                        st.code(res["canonical_smiles"], language="text")
                with cp2:
                    img_url = res.get("structure_image_url")
                    if img_url:
                        st.image(img_url, caption=f"2D Structure: {res.get('name')}", width=260)
            else:
                st.warning("No PubChem record found for this compound.")

    with sub_tab4:
        st.subheader("Europe PMC Open-Access Research Search")
        lit_query = st.text_input("Enter Literature Query (Plant, Compound, or Indication):", value="Curcuma longa osteoarthritis")

        if st.button("Search Literature", type="primary", key="btn_epmc_val"):
            with st.spinner(f"Querying Europe PMC for '{lit_query}'..."):
                pmc_client = EuropePMCClient()
                papers = pmc_client.search_literature(lit_query, page_size=6)

            if papers:
                st.success(f"Found {len(papers)} publications from Europe PMC:")
                for p in papers:
                    with st.expander(f"📄 {p['title']} ({p.get('year', 'N/A')})"):
                        st.markdown(f"**Authors:** {p.get('authors', 'N/A')}")
                        st.markdown(f"**Journal:** *{p.get('journal', 'N/A')}* ({p.get('year', '')})")
                        if p.get("doi"):
                            st.markdown(f"**DOI:** [{p['doi']}](https://doi.org/{p['doi']})")
                        if p.get("pmid"):
                            st.markdown(f"**PMID:** [{p['pmid']}](https://pubmed.ncbi.nlm.nih.gov/{p['pmid']}/)")
                        st.markdown(f"**License:** `{p.get('license', 'Standard')}`")
                        st.markdown("**Abstract:**")
                        st.write(p.get("abstract", "No abstract available."))
            else:
                st.warning("No literature records returned for this query.")

