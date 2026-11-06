"""HERBINTEL UI Theme and Styling.
Provides clean bioinformatics typography, evidence badge styling,
status badges, and medical disclaimer formatting.
"""

CUSTOM_CSS = """
<style>
    /* Global Container Adjustments */
    .block-container {
        padding-top: 1.8rem;
        padding-bottom: 2.5rem;
    }

    /* Main Brand Header */
    .brand-title {
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
        font-size: 2.2rem;
        font-weight: 800;
        color: #1b5e20;
        margin-bottom: 0.2rem;
        display: flex;
        align-items: center;
        gap: 0.6rem;
    }
    .brand-subtitle {
        font-size: 1.05rem;
        color: #555555;
        margin-bottom: 1.2rem;
    }

    /* Disclaimer Box */
    .disclaimer-card {
        background-color: #fff8e1;
        border-left: 5px solid #f57f17;
        padding: 0.85rem 1.2rem;
        border-radius: 4px;
        margin-bottom: 1.4rem;
        font-size: 0.88rem;
        color: #5d4037;
        line-height: 1.45;
    }
    .disclaimer-title {
        font-weight: 700;
        color: #e65100;
        margin-bottom: 0.3rem;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }

    /* Metric Cards */
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1.1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        text-align: center;
    }
    .metric-value {
        font-size: 2.1rem;
        font-weight: 800;
        color: #2e7d32;
        line-height: 1.1;
    }
    .metric-label {
        font-size: 0.85rem;
        font-weight: 600;
        color: #616161;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 0.3rem;
    }

    /* Badges */
    .badge {
        display: inline-block;
        padding: 0.22rem 0.55rem;
        border-radius: 12px;
        font-size: 0.78rem;
        font-weight: 600;
        margin-right: 0.35rem;
    }
    .badge-traditional {
        background-color: #ffe0b2;
        color: #e65100;
        border: 1px solid #ffb74d;
    }
    .badge-invitro {
        background-color: #e1f5fe;
        color: #0288d1;
        border: 1px solid #81d4fa;
    }
    .badge-invivo {
        background-color: #e8eaf6;
        color: #303f9f;
        border: 1px solid #9fa8da;
    }
    .badge-clinical {
        background-color: #e8f5e9;
        color: #2e7d32;
        border: 1px solid #81c784;
    }
    .badge-review {
        background-color: #f3e5f5;
        color: #6a1b9a;
        border: 1px solid #ce93d8;
    }
    .badge-verified {
        background-color: #e8f5e9;
        color: #1b5e20;
        border: 1px solid #a5d6a7;
    }
    .badge-unverified {
        background-color: #fff3e0;
        color: #e65100;
        border: 1px solid #ffcc80;
    }
    .badge-disputed {
        background-color: #ffebee;
        color: #c62828;
        border: 1px solid #ef9a9a;
    }
    .badge-demo {
        background-color: #f5f5f5;
        color: #757575;
        border: 1px dashed #bdbdbd;
        font-size: 0.72rem;
    }

    /* Sentence Citation Block */
    .citation-box {
        background-color: #fafafa;
        border-left: 4px solid #43a047;
        padding: 0.75rem 1rem;
        border-radius: 4px;
        margin-top: 0.4rem;
        margin-bottom: 0.6rem;
        font-style: italic;
        font-size: 0.9rem;
        color: #263238;
    }
</style>
"""


def render_evidence_badge(tier_code: str) -> str:
    """Returns HTML for evidence tier badge."""
    tier_map = {
        "TRADITIONAL": ("Traditional / Ethnobotanical", "badge-traditional"),
        "IN_VITRO": ("In Vitro / Lab Assay", "badge-invitro"),
        "IN_VIVO": ("In Vivo / Animal Model", "badge-invivo"),
        "CLINICAL": ("Clinical Trial / Human", "badge-clinical"),
        "REVIEW_META": ("Systematic Review", "badge-review"),
    }
    label, css_class = tier_map.get(tier_code, (tier_code, "badge-traditional"))
    return f'<span class="badge {css_class}">{label}</span>'


def render_status_badge(status: str) -> str:
    """Returns HTML for verification status badge."""
    status_map = {
        "Verified": ("Verified", "badge-verified"),
        "Unverified": ("Unverified (AI)", "badge-unverified"),
        "Disputed": ("Disputed", "badge-disputed"),
    }
    label, css_class = status_map.get(status, (status, "badge-unverified"))
    return f'<span class="badge {css_class}">{label}</span>'

