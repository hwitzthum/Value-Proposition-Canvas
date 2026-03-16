"""Tests for UX enhancement API endpoints (improve, merge, relevance)."""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestImproveItemEndpoint:
    def test_improve_item_returns_result(self, client):
        response = client.post("/api/improve-item", json={
            "item": "bad stuff happens",
            "item_type": "pain",
        })
        assert response.status_code == 200
        data = response.json()
        assert "original" in data
        assert "improved" in data
        assert "source" in data

    def test_improve_item_with_context(self, client):
        response = client.post("/api/improve-item", json={
            "item": "Testing is slow",
            "item_type": "pain",
            "job_description": "Improve deployment speed",
            "context_items": ["Manual deploys", "No CI/CD"],
        })
        assert response.status_code == 200
        data = response.json()
        assert data["source"] in ("ai", "rules")

    def test_improve_item_invalid_type(self, client):
        response = client.post("/api/improve-item", json={
            "item": "something",
            "item_type": "invalid",
        })
        assert response.status_code == 422


class TestMergeItemsEndpoint:
    def test_merge_items_returns_result(self, client):
        response = client.post("/api/merge-items", json={
            "item1": "Manual data entry takes too long",
            "item2": "Spending hours on data entry every week",
            "item_type": "pain",
        })
        assert response.status_code == 200
        data = response.json()
        assert "merged" in data
        assert "source" in data

    def test_merge_items_invalid_type(self, client):
        response = client.post("/api/merge-items", json={
            "item1": "a",
            "item2": "b",
            "item_type": "invalid",
        })
        assert response.status_code == 422


class TestRelevanceEndpoint:
    def test_relevance_check_basic(self, client):
        response = client.post("/api/validate/relevance", json={
            "items": [
                "Manual testing takes hours before each release",
                "Deployment scripts often fail",
            ],
            "job_description": "Improve our software deployment process",
            "item_type": "pain",
        })
        assert response.status_code == 200
        data = response.json()
        assert "relevant" in data
        assert "item_scores" in data
        assert "dimension_distribution" in data
        assert len(data["item_scores"]) == 2

    def test_relevance_check_dimension_distribution(self, client):
        response = client.post("/api/validate/relevance", json={
            "items": ["Slow builds"],
            "job_description": "Improve CI/CD",
            "item_type": "pain",
        })
        assert response.status_code == 200
        dist = response.json()["dimension_distribution"]
        assert "functional" in dist
        assert "emotional" in dist
        assert "social" in dist


class TestImproveItemRuleBased:
    """Tests for improved rule-based improve_item fallback."""

    def test_short_item_gets_expanded(self, client):
        response = client.post("/api/improve-item", json={
            "item": "Slow builds",
            "item_type": "pain",
        })
        data = response.json()
        assert data["source"] == "rules"
        assert len(data["improved"]) > len("Slow builds")
        assert "progress" in data["improved"].lower() or "effort" in data["improved"].lower()

    def test_vague_words_get_replaced(self, client):
        response = client.post("/api/improve-item", json={
            "item": "There is a bad problem with the thing we use at work every single day",
            "item_type": "pain",
        })
        data = response.json()
        assert data["source"] == "rules"
        assert "bad" not in data["improved"].lower().split()
        assert "problem" not in data["improved"].lower().split()
        assert "thing" not in data["improved"].lower().split()

    def test_gain_short_item_expanded_differently(self, client):
        response = client.post("/api/improve-item", json={
            "item": "Better tools",
            "item_type": "gain",
        })
        data = response.json()
        assert "improvement" in data["improved"].lower() or "outcomes" in data["improved"].lower()


class TestMergeItemsRuleBased:
    """Tests for improved rule-based merge_items fallback."""

    def test_shared_concepts_extracted(self, client):
        response = client.post("/api/merge-items", json={
            "item1": "Manual data entry takes too long every week",
            "item2": "Spending hours on data entry into spreadsheets weekly",
            "item_type": "pain",
        })
        data = response.json()
        assert data["source"] == "rules"
        # Should mention the shared concept (data/entry) rather than just concatenating
        assert "data" in data["merged"].lower() or "entry" in data["merged"].lower()
        assert "; additionally," not in data["merged"]

    def test_no_overlap_keeps_longer(self, client):
        response = client.post("/api/merge-items", json={
            "item1": "Server latency is extremely high during peak hours",
            "item2": "Team morale low",
            "item_type": "pain",
        })
        data = response.json()
        assert data["source"] == "rules"
        # Should keep the longer/more detailed item
        assert "latency" in data["merged"].lower() or "morale" in data["merged"].lower()


class TestSuggestionsListRuleBased:
    """Tests that rule-based suggestions include suggestions_list."""

    def test_pain_suggestions_have_list(self, client):
        response = client.post("/api/suggestions", json={
            "step": "pains",
            "job_description": "Improve our deployment process because it is slow",
            "existing_items": ["Manual testing takes hours"],
            "count_needed": 3,
        })
        data = response.json()
        assert "suggestions_list" in data
        assert len(data["suggestions_list"]) == 3
        assert "text" in data["suggestions_list"][0]
        assert "category" in data["suggestions_list"][0]

    def test_gain_suggestions_have_list(self, client):
        response = client.post("/api/suggestions", json={
            "step": "gains",
            "job_description": "Improve our deployment process because it is slow",
            "existing_items": ["Faster builds"],
            "count_needed": 4,
        })
        data = response.json()
        assert "suggestions_list" in data
        assert len(data["suggestions_list"]) == 4
        assert "text" in data["suggestions_list"][0]
        assert "category" in data["suggestions_list"][0]

    def test_suggestions_list_respects_count(self, client):
        response = client.post("/api/suggestions", json={
            "step": "pains",
            "job_description": "Improve our deployment process because it is slow",
            "existing_items": [],
            "count_needed": 2,
        })
        data = response.json()
        assert len(data["suggestions_list"]) == 2


class TestEnrichedValidation:
    def test_pain_points_include_priority_and_feedback(self, client):
        response = client.post("/api/validate/pain-points", json={
            "pain_points": ["One pain point with enough detail here"],
        })
        assert response.status_code == 200
        data = response.json()
        assert "priority_level" in data
        assert "positive_feedback" in data
        assert data["priority_level"] == "count"

    def test_gain_points_include_priority_and_feedback(self, client):
        response = client.post("/api/validate/gain-points", json={
            "gain_points": ["One gain point with enough detail here"],
        })
        assert response.status_code == 200
        data = response.json()
        assert "priority_level" in data
        assert "positive_feedback" in data
