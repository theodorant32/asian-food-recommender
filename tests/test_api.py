"""API endpoint tests."""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_list_dishes(client):
    resp = client.get("/api/v1/dishes")
    assert resp.status_code == 200
    data = resp.json()
    assert "count" in data
    assert len(data["dishes"]) > 0


def test_get_dish(client):
    resp = client.get("/api/v1/dishes/mapo_tofu")
    assert resp.status_code == 200
    assert resp.json()["id"] == "mapo_tofu"


def test_get_dish_not_found(client):
    resp = client.get("/api/v1/dishes/nonexistent")
    assert resp.status_code == 404


def test_cuisines(client):
    resp = client.get("/api/v1/cuisines")
    assert resp.status_code == 200
    assert len(resp.json()["cuisines"]) > 0


def test_taste_map(client):
    resp = client.get("/api/v1/taste-map")
    assert resp.status_code == 200
    data = resp.json()
    assert "dishes" in data
    assert "x" in data["dishes"][0]
    assert "y" in data["dishes"][0]


def test_similar_dishes(client):
    resp = client.get("/api/v1/similar/mapo_tofu?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "similar_dishes" in data


def test_recommend_with_query(client):
    resp = client.post("/api/v1/recommend", json={"query": "spicy", "max_results": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert "recommendations" in data


def test_recommend_with_filters(client):
    resp = client.post(
        "/api/v1/recommend",
        json={"max_results": 10, "cuisine_filter": "Japanese", "vegetarian_only": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    for rec in data["recommendations"]:
        assert rec["dish"]["cuisine"] == "Japanese"


def test_search(client):
    resp = client.get("/api/v1/search?q=spicy&limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data


def test_search_no_query(client):
    resp = client.get("/api/v1/search")
    assert resp.status_code == 422
