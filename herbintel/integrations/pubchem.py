"""PubChem Integration for HERBINTEL.
Fetches chemical structures, molecular formulas, molecular weights,
Canonical SMILES, InChIKeys, and 2D structure depictions from NCBI PubChem.
"""

import requests
from typing import Dict, Any, Optional
import logging
from ..core.config import PUBCHEM_REST_URL

logger = logging.getLogger(__name__)


class PubChemClient:
    """Client for NCBI PubChem PUG REST API."""

    def __init__(self, timeout: int = 8):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "HERBINTEL-Bioinformatics-Platform/1.0 (EthnoHack 2026; mailto:research@herbintel.org)"
        })

    def get_compound_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Queries PubChem by compound name to retrieve chemical properties and structure."""
        url = f"{PUBCHEM_REST_URL}/compound/name/{name}/property/CanonicalSMILES,InChIKey,MolecularFormula,MolecularWeight,IUPACName/JSON"
        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                props = data.get("PropertyTable", {}).get("Properties", [{}])[0]
                cid = props.get("CID")
                return {
                    "name": name,
                    "pubchem_cid": cid,
                    "canonical_smiles": props.get("CanonicalSMILES"),
                    "inchi_key": props.get("InChIKey"),
                    "molecular_formula": props.get("MolecularFormula"),
                    "molecular_weight": float(props.get("MolecularWeight", 0.0)),
                    "iupac_name": props.get("IUPACName"),
                    "structure_image_url": f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/PNG" if cid else None,
                }
            else:
                logger.warning("PubChem returned %s for compound %s", resp.status_code, name)
                return self._fallback_compound(name)
        except Exception as e:
            logger.info("PubChem offline or unreachable (%s). Using fallback properties for %s.", e, name)
            return self._fallback_compound(name)

    def get_compound_by_cid(self, cid: int) -> Optional[Dict[str, Any]]:
        """Queries PubChem by CID."""
        url = f"{PUBCHEM_REST_URL}/compound/cid/{cid}/property/CanonicalSMILES,InChIKey,MolecularFormula,MolecularWeight,IUPACName,Title/JSON"
        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                props = data.get("PropertyTable", {}).get("Properties", [{}])[0]
                return {
                    "pubchem_cid": cid,
                    "name": props.get("Title", f"CID-{cid}"),
                    "canonical_smiles": props.get("CanonicalSMILES"),
                    "inchi_key": props.get("InChIKey"),
                    "molecular_formula": props.get("MolecularFormula"),
                    "molecular_weight": float(props.get("MolecularWeight", 0.0)),
                    "iupac_name": props.get("IUPACName"),
                    "structure_image_url": f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/PNG",
                }
        except Exception as e:
            logger.info("PubChem CID lookup error (%s).", e)
        return None

    def _fallback_compound(self, name: str) -> Optional[Dict[str, Any]]:
        """Fallback dictionary for prominent ethnobotanical chemical compounds."""
        curated = {
            "curcumin": {
                "name": "Curcumin",
                "pubchem_cid": 969516,
                "canonical_smiles": "COC1=C(C=CC(=C1)/C=C/C(=O)CC(=O)/C=C/C2=CC(=C(C=C2)O)OC)O",
                "inchi_key": "VWDWKYGDQIYTJZ-QHCPKHFHSA-N",
                "molecular_formula": "C21H20O6",
                "molecular_weight": 368.38,
                "structure_image_url": "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/969516/PNG",
            },
            "azadirachtin": {
                "name": "Azadirachtin",
                "pubchem_cid": 5281303,
                "canonical_smiles": "CC1=CC2C(C(=O)O1)C(C3(C(C4C5(C(C(=O)O5)C(C6(O4)C(C(=O)OC6)C(C2(O3)C)OC(=O)C)O)C)OC(=O)C)O)O",
                "inchi_key": "UPHSQYWCCXAZBM-UHFFFAOYSA-N",
                "molecular_formula": "C35H44O16",
                "molecular_weight": 720.7,
                "structure_image_url": "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/5281303/PNG",
            },
            "withaferin a": {
                "name": "Withaferin A",
                "pubchem_cid": 265237,
                "canonical_smiles": "CC1C2C(CC3(C2(CC4C(O3)CC(=O)C=C4C)C)O)C5(C1(CCC5C(C)C6CC(C(=O)O6)C(=C)CO)C)O",
                "inchi_key": "JHPWVIWZMDODDY-UHFFFAOYSA-N",
                "molecular_formula": "C28H38O6",
                "molecular_weight": 470.6,
                "structure_image_url": "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/265237/PNG",
            },
            "artemisinin": {
                "name": "Artemisinin",
                "pubchem_cid": 68827,
                "canonical_smiles": "CC1CCC2C(C(=O)OC3C24C1CCC(O3)(OO4)C)C",
                "inchi_key": "BLUAFEHZUYTIPD-UHFFFAOYSA-N",
                "molecular_formula": "C15H22O5",
                "molecular_weight": 282.33,
                "structure_image_url": "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/68827/PNG",
            },
            "6-gingerol": {
                "name": "6-Gingerol",
                "pubchem_cid": 442793,
                "canonical_smiles": "CCCCCC(CC(=O)CCC1=CC(=C(C=C1)O)OC)O",
                "inchi_key": "XEZLXZDWHGSPTP-UHFFFAOYSA-N",
                "molecular_formula": "C17H26O4",
                "molecular_weight": 294.39,
                "structure_image_url": "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/442793/PNG",
            },
            "eugenol": {
                "name": "Eugenol",
                "pubchem_cid": 3314,
                "canonical_smiles": "COC1=C(C=CC(=C1)CC=C)O",
                "inchi_key": "RRAFCDWUMFUJTC-UHFFFAOYSA-N",
                "molecular_formula": "C10H12O2",
                "molecular_weight": 164.20,
                "structure_image_url": "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/3314/PNG",
            },
            "quercetin": {
                "name": "Quercetin",
                "pubchem_cid": 5280343,
                "canonical_smiles": "C1=CC(=C(C=C1C2=C(C(=O)C3=C(C=C(C=C3O2)O)O)O)O)O",
                "inchi_key": "REFJWTPEDVJJIY-UHFFFAOYSA-N",
                "molecular_formula": "C15H10O7",
                "molecular_weight": 302.24,
                "structure_image_url": "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/5280343/PNG",
            },
            "berberine": {
                "name": "Berberine",
                "pubchem_cid": 2353,
                "canonical_smiles": "COC1=C(C2=C[N+]3=C(C=C2C=C1)C4=CC5=C(C=C4CC3)OCO5)OC",
                "inchi_key": "UBKPKBDUEAFBAP-UHFFFAOYSA-N",
                "molecular_formula": "C20H18NO4+",
                "molecular_weight": 336.4,
                "structure_image_url": "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/2353/PNG",
            }
        }
        return curated.get(name.lower())

