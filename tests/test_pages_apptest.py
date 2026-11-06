"""Automated UI Integration Tests using Streamlit AppTest.
Tests that all 7 navigation pages compile, render, and execute with 0 unhandled exceptions.
"""

import pytest
from streamlit.testing.v1 import AppTest


@pytest.fixture
def app():
    at = AppTest.from_file("app.py", default_timeout=15)
    at.run()
    return at


def test_dashboard_page(app):
    assert len(app.exception) == 0
    assert "HERBINTEL" in app.sidebar.markdown[0].value


def test_plant_explorer_page(app):
    app.sidebar.radio[0].set_value("🌿 Plant Explorer")
    app.run()
    assert len(app.exception) == 0
    assert len(app.selectbox) > 0


def test_ai_knowledge_extractor_page(app):
    app.sidebar.radio[0].set_value("🔬 AI Knowledge Extractor")
    app.run()
    assert len(app.exception) == 0
    assert len(app.radio) > 0


def test_ai_research_discovery_page(app):
    app.sidebar.radio[0].set_value("🔎 AI Research Discovery")
    app.run()
    assert len(app.exception) == 0


def test_knowledge_graph_page(app):
    app.sidebar.radio[0].set_value("🕸️ Knowledge Graph")
    app.run()
    assert len(app.exception) == 0


def test_evidence_explorer_page(app):
    app.sidebar.radio[0].set_value("📑 Evidence Explorer")
    app.run()
    assert len(app.exception) == 0


def test_biodiversity_explorer_page(app):
    app.sidebar.radio[0].set_value("🌍 Biodiversity Explorer")
    app.run()
    assert len(app.exception) == 0


def test_methodology_page(app):
    app.sidebar.radio[0].set_value("ℹ️ Methodology & Constraints")
    app.run()
    assert len(app.exception) == 0

