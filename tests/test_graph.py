"""Automated Tests for NetworkX Knowledge Graph and Plotly generation."""

import pytest
from herbintel.core.database import init_db, seed_benchmark_data
from herbintel.graph.knowledge_graph import HerbKnowledgeGraph
from pathlib import Path

TEST_DB_PATH = Path("data/test_herbintel.db")


@pytest.fixture(scope="module", autouse=True)
def setup_test_data():
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass
    init_db(TEST_DB_PATH)
    seed_benchmark_data(TEST_DB_PATH)
    yield
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass


def test_knowledge_graph_construction():
    kg = HerbKnowledgeGraph()
    G = kg.build_graph(db_path=TEST_DB_PATH)
    assert len(G) > 0
    assert G.number_of_nodes() >= 20
    assert G.number_of_edges() >= 15


def test_graph_metrics():
    kg = HerbKnowledgeGraph()
    kg.build_graph(db_path=TEST_DB_PATH)
    metrics = kg.get_metrics()
    assert metrics["node_count"] > 0
    assert metrics["edge_count"] > 0
    assert len(metrics["top_plants"]) > 0


def test_graph_filtering_and_plotly():
    kg = HerbKnowledgeGraph()
    kg.build_graph(db_path=TEST_DB_PATH)
    
    # Subgraph by plant
    sub_g = kg.filter_subgraph(plant_name="Curcuma")
    assert len(sub_g) > 0
    assert len(sub_g) <= len(kg.graph)

    # Plotly figure generation
    fig = kg.create_plotly_figure(sub_g)
    assert fig is not None
    assert len(fig.data) > 0

