"""Transparent manual-evaluation dashboard for extraction validation."""

import io
import pandas as pd
import streamlit as st
from ..components import render_header, render_disclaimer


REQUIRED_COLUMNS = {"task", "gold", "predicted"}


def _metrics(frame: pd.DataFrame):
    rows = []
    for task, subset in frame.groupby("task"):
        gold = subset["gold"].astype(str).str.lower().isin(["1", "true", "yes", "present"])
        predicted = subset["predicted"].astype(str).str.lower().isin(["1", "true", "yes", "present"])
        tp = int((gold & predicted).sum())
        fp = int((~gold & predicted).sum())
        fn = int((gold & ~predicted).sum())
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        rows.append({"Task": task, "Sentences": len(subset), "Precision": precision, "Recall": recall, "F1": f1, "TP": tp, "FP": fp, "FN": fn})
    return pd.DataFrame(rows)


def render_validation_page():
    render_header("Validation & Audit", "Publish measured extraction quality—not guarantees")
    render_disclaimer()
    st.markdown("Upload a manually adjudicated CSV from real open-access papers. Required columns: `task`, `gold`, `predicted`. Use one row per sentence or entity decision; tasks may be `plant_ner`, `compound_ner`, or `evidence_tier`.")
    st.warning("No performance score is shown until an adjudicated dataset is supplied. This prevents demo data from being presented as scientific validation.")

    template = pd.DataFrame([
        {"task": "plant_ner", "gold": 1, "predicted": 1, "source": "PMCID / DOI", "reviewer": "initials"},
        {"task": "compound_ner", "gold": 1, "predicted": 0, "source": "PMCID / DOI", "reviewer": "initials"},
        {"task": "evidence_tier", "gold": 1, "predicted": 1, "source": "PMCID / DOI", "reviewer": "initials"},
    ])
    st.download_button("Download annotation template", template.to_csv(index=False).encode("utf-8"), "herbintel_annotation_template.csv", "text/csv")

    upload = st.file_uploader("Upload adjudicated evaluation CSV", type=["csv"])
    if upload is None:
        st.info("Recommended protocol: independently annotate 30–50 sentences from each of three open-access papers, resolve disagreements, then upload the final adjudication file.")
        return
    try:
        frame = pd.read_csv(upload)
    except Exception as exc:
        st.error(f"Could not read CSV: {exc}")
        return
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        st.error(f"Missing required columns: {', '.join(sorted(missing))}")
        return
    result = _metrics(frame)
    st.subheader("Measured extraction performance")
    st.dataframe(result.style.format({"Precision": "{:.1%}", "Recall": "{:.1%}", "F1": "{:.1%}"}), use_container_width=True, hide_index=True)
    st.caption(f"Audit dataset: {len(frame)} adjudicated decisions. Keep the source and reviewer columns with the exported evaluation file for reproducibility.")
