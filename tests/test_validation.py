"""Tests for the validation logic (QualityValidator)."""

import pytest
from app.validation import QualityValidator


@pytest.fixture
def validator():
    return QualityValidator()


class TestJobDescriptionValidation:
    def test_valid_job_description(self, validator):
        desc = "I want to improve my team's deployment process because it takes too long"
        result = validator.validate_job_description(desc)
        assert result["valid"] is True
        assert result["score"] > 50

    def test_too_short(self, validator):
        result = validator.validate_job_description("short")
        assert result["valid"] is False
        assert result["score"] < 100

    def test_missing_action_words(self, validator):
        desc = "This is a long enough description about work processes in the department."
        result = validator.validate_job_description(desc)
        assert "action" in str(result.get("feedback", []) + result.get("suggestions", [])).lower() or result["score"] < 100

    def test_generic_terms_reduce_score(self, validator):
        desc = "I need to do things and something related to stuff at work because of everything"
        result = validator.validate_job_description(desc)
        assert result["valid"] is False


class TestItemQuality:
    def test_valid_item(self, validator):
        result = validator.validate_item_quality(
            "Spending 3+ hours manually entering data into spreadsheets every week"
        )
        assert result["valid"] is True
        assert result["score"] > 50

    def test_too_short(self, validator):
        result = validator.validate_item_quality("bad stuff")
        assert result["valid"] is False

    def test_vague_item(self, validator):
        result = validator.validate_item_quality("bad good nice problem issue thing stuff more words")
        assert result["score"] < 100


class TestIndependence:
    def test_independent_items(self, validator):
        items = [
            "Spending 3+ hours on manual data entry every week",
            "Frequent miscommunication between design and engineering teams",
            "No automated testing leads to bugs in production",
        ]
        independent, issues = validator.check_independence(items)
        assert independent is True
        assert len(issues) == 0

    def test_similar_items(self, validator):
        # Use identical items to reliably trigger similarity detection
        items = [
            "Spending too much time on manual data entry into spreadsheets each week",
            "Spending too much time on manual data entry into spreadsheets every week",
        ]
        independent, issues = validator.check_independence(items)
        # These should be flagged as similar (high TF-IDF overlap)
        assert independent is False
        assert len(issues) >= 1

    def test_single_item(self, validator):
        independent, issues = validator.check_independence(["Just one item here"])
        assert independent is True

    def test_empty_list(self, validator):
        independent, issues = validator.check_independence([])
        assert independent is True


class TestCollectionValidation:
    def test_pain_points_below_minimum(self, validator):
        items = ["Pain point one with enough detail here", "Pain point two with enough detail here"]
        result = validator.validate_pain_points(items)
        assert result["enough_points"] is False
        assert result["valid"] is False

    def test_gain_points_below_minimum(self, validator):
        items = ["Gain one detail"]
        result = validator.validate_gain_points(items)
        assert result["enough_points"] is False


class TestCompleteCanvas:
    def test_valid_canvas(self, validator):
        job = "I want to streamline our deployment process because it currently takes too long"
        pains = [
            "Manual testing takes hours before each release cycle",
            "Frequent merge conflicts slow down the entire development team",
            "No automated rollback mechanism when production bugs are found",
            "Environment configuration differs between staging and production systems",
            "Documentation becomes stale quickly and misleads developers",
            "On-call rotations are exhausting due to frequent night alerts",
            "Third-party API rate limits cause cascading failures downstream",
        ]
        gains = [
            "Automated CI/CD pipeline cutting deployment time by seventy percent",
            "Real-time monitoring dashboards with actionable alerting thresholds",
            "Self-healing infrastructure that recovers from common failure modes",
            "Comprehensive integration test suite catching regression bugs early",
            "Standardized development environment using container technology",
            "Clear runbooks reducing incident response time significantly overall",
            "Improved developer satisfaction through reduced toil and automation",
            "Better customer experience through faster feature delivery cycles",
        ]
        result = validator.validate_complete_canvas(job, pains, gains)
        assert result["valid"] is True
        assert result["ready_for_export"] is True

    def test_invalid_canvas_no_job(self, validator):
        result = validator.validate_complete_canvas("x", [], [])
        assert result["valid"] is False


class TestPriorityLevel:
    """Tests for compute_priority_level() progressive disclosure."""

    def test_count_priority_when_not_enough_points(self, validator):
        result = validator.validate_pain_points(["One item here with enough detail"])
        priority = validator.compute_priority_level(result)
        assert priority == "count"

    def test_quality_priority_when_items_have_issues(self, validator):
        # Enough items (7) but some have quality issues (too short)
        items = [
            "Detailed pain point about manual data entry processes",
            "Complex workflow issues with deployment pipeline",
            "bad",  # too short, quality issue
            "Communication problems between team members daily",
            "Testing takes too long before each release cycle",
            "Documentation becomes outdated very quickly now",
            "Third party API failures cause downstream issues",
        ]
        result = validator.validate_pain_points(items)
        priority = validator.compute_priority_level(result)
        assert priority == "quality"

    def test_independence_priority_when_similar_items(self, validator):
        items = [
            "Spending too much time on manual data entry into spreadsheets each week",
            "Spending too much time on manual data entry into spreadsheets every week",
            "Frequent miscommunication between design and engineering teams",
            "No automated testing leads to bugs in production releases",
            "Environment configuration differs between staging and production",
            "Documentation becomes stale quickly and misleads developers",
            "On-call rotations are exhausting due to frequent alerts",
        ]
        result = validator.validate_pain_points(items)
        priority = validator.compute_priority_level(result)
        assert priority == "independence"

    def test_complete_priority_when_all_good(self, validator):
        items = [
            "Manual testing takes several hours before each release",
            "Frequent merge conflicts slow down the development team",
            "No automated rollback mechanism for production bugs",
            "Environment configuration differs between staging and prod",
            "Documentation becomes stale quickly and misleads devs",
            "On-call rotations exhausting due to frequent night alerts",
            "Third-party API rate limits cause cascading failures",
        ]
        result = validator.validate_pain_points(items)
        priority = validator.compute_priority_level(result)
        assert priority == "complete"


class TestPositiveFeedback:
    """Tests for compute_positive_feedback()."""

    def test_positive_feedback_when_enough_items(self, validator):
        items = [
            "Manual testing takes several hours before each release",
            "Frequent merge conflicts slow down the development team",
            "No automated rollback mechanism for production bugs",
            "Environment configuration differs between staging and prod",
            "Documentation becomes stale quickly and misleads devs",
            "On-call rotations exhausting due to frequent night alerts",
            "Third-party API rate limits cause cascading failures",
        ]
        result = validator.validate_pain_points(items)
        feedback = validator.compute_positive_feedback(result, "pain point")
        assert any("meeting the minimum" in f for f in feedback)

    def test_no_positive_feedback_when_insufficient(self, validator):
        items = ["One item only with enough detail here"]
        result = validator.validate_pain_points(items)
        feedback = validator.compute_positive_feedback(result, "pain point")
        assert not any("meeting the minimum" in f for f in feedback)


class TestClassifyDimension:
    """Tests for classify_dimension()."""

    def test_functional_default(self, validator):
        assert validator.classify_dimension("Spending too much time on manual data entry") == "functional"

    def test_emotional_classification(self, validator):
        assert validator.classify_dimension("Feeling stressed and frustrated by tight deadlines") == "emotional"

    def test_social_classification(self, validator):
        assert validator.classify_dimension("Poor collaboration and communication between team members") == "social"


class TestRelevance:
    """Tests for check_relevance()."""

    def test_relevant_items(self, validator):
        job = "I want to improve our software deployment process because it takes too long"
        items = [
            "Manual testing takes hours before each release",
            "Deployment scripts are fragile and often fail",
        ]
        result = validator.check_relevance(items, job)
        assert result["relevant"] is True
        assert len(result["item_scores"]) == 2
        assert all(s["relevant"] for s in result["item_scores"])

    def test_irrelevant_item_detected(self, validator):
        job = "I want to improve our software deployment process because it takes too long"
        items = [
            "Manual testing takes hours before each release",
            "My favorite recipe is chocolate cake with vanilla frosting",
        ]
        result = validator.check_relevance(items, job)
        # The cake item should be flagged as irrelevant
        cake_score = result["item_scores"][1]
        assert cake_score["relevant"] is False
        assert "feedback" in cake_score

    def test_dimension_distribution(self, validator):
        job = "I want to improve team productivity"
        items = [
            "Manual processes waste time every day",
            "Feeling stressed by constant interruptions",
            "Poor communication between team members",
        ]
        result = validator.check_relevance(items, job)
        dist = result["dimension_distribution"]
        assert dist["functional"] >= 1
        assert dist["emotional"] >= 1
        assert dist["social"] >= 1

    def test_empty_items(self, validator):
        result = validator.check_relevance([], "some job")
        assert result["relevant"] is True
        assert result["item_scores"] == []

    def test_empty_job_description(self, validator):
        result = validator.check_relevance(["some item"], "")
        assert result["relevant"] is True


class TestHybridRelevance:
    """Tests for hybrid relevance scoring (synonym clusters + Jaccard + TF-IDF)."""

    def test_semantically_related_items_pass(self, validator):
        """Items using different vocabulary but related to the job should pass."""
        job = "I want to improve our software deployment process because it takes too long"
        items = [
            "Real-time monitoring dashboards with actionable alerting thresholds",
            "Self-healing infrastructure that recovers from common failure modes",
            "Clear runbooks reducing incident response time significantly overall",
        ]
        result = validator.check_relevance(items, job)
        for s in result["item_scores"]:
            assert s["relevant"] is True, f"'{s['item']}' scored {s['relevance_score']}% — expected relevant"

    def test_hybrid_threshold_separates_relevant_from_irrelevant(self, validator):
        """CI/CD items pass, chocolate cake fails."""
        job = "I want to improve our software deployment process because it takes too long"
        items = [
            "Automated CI/CD pipeline cutting deployment time by seventy percent",
            "My favorite recipe is chocolate cake with vanilla frosting",
        ]
        result = validator.check_relevance(items, job)
        assert result["item_scores"][0]["relevant"] is True
        assert result["item_scores"][1]["relevant"] is False

    def test_keyword_overlap_score(self, validator):
        """Synonym cluster expansion should create non-zero overlap."""
        score = validator._keyword_overlap_score(
            "deployment process",
            "infrastructure environment"
        )
        assert score > 0, "deploy and infrastructure share a synonym cluster"

    def test_jaccard_stem_score(self, validator):
        """Truncated stems should find overlap between related words."""
        score = validator._jaccard_stem_score(
            "deployment automated",
            "deploying automation"
        )
        assert score > 0, "deploy* and automa* stems should overlap"


class TestSimilarityThreshold:
    """Test that the threshold was raised to 0.8."""

    def test_threshold_is_08(self, validator):
        assert validator.SIMILARITY_THRESHOLD == 0.8
