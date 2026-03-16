"""Tests for proactive AI nudges."""

import pytest
from app.validation import QualityValidator


@pytest.fixture
def validator():
    return QualityValidator()


class TestComputeNudges:
    """Tests for QualityValidator.compute_nudges()."""

    def test_dimension_imbalance_detected(self, validator):
        """When >70% of items are one dimension, a nudge is generated."""
        # All functional pain points
        pains = [
            "Manual deployment takes 45 minutes each time",
            "Build pipeline fails silently without alerting the team",
            "Server provisioning requires 12 manual configuration steps",
            "Database migrations must be run manually on each environment",
        ]
        nudges = validator.compute_nudges("Deploy software", pains, [])
        imbalance = [n for n in nudges if n["type"] == "dimension_imbalance"]
        assert len(imbalance) > 0
        assert imbalance[0]["section"] == "pains"
        assert "functional" in imbalance[0]["message"]

    def test_no_nudges_when_balanced(self, validator):
        """Balanced canvas produces fewer or no nudges."""
        pains = [
            "Manual deployment takes 45 minutes each time",
            "Team feels frustrated when releases fail",
            "Stakeholders lose trust when deadlines slip",
            "Build pipeline fails silently without alerting the team",
            "Server provisioning requires 12 manual configuration steps",
            "Engineers feel anxious about deploying on Fridays",
            "Client satisfaction drops when features are delayed",
        ]
        gains = [
            "Reduce deployment time to under 5 minutes per release",
            "Engineers feel confident pushing code any day of the week",
            "Stakeholders trust the team to deliver on schedule",
            "Automated rollback reduces recovery time to seconds",
            "Team collaboration improves with shared deployment dashboards",
            "Zero-downtime deploys eliminate customer-facing outages",
            "New engineers onboard to the deploy process in one day",
        ]
        job = "When deploying software updates, I want to automate the release pipeline so that deployments are fast, reliable, and stress-free"
        nudges = validator.compute_nudges(job, pains, gains)
        # Should have no dimension imbalance nudges (mixed functional/emotional/social)
        imbalance = [n for n in nudges if n["type"] == "dimension_imbalance"]
        assert len(imbalance) == 0

    def test_coverage_gap_no_pains(self, validator):
        """Nudge when gains exist but no pains."""
        gains = ["Faster deployments save 2 hours per week"]
        nudges = validator.compute_nudges("Deploy software", [], gains)
        coverage = [n for n in nudges if n["type"] == "coverage_gap"]
        assert len(coverage) == 1
        assert coverage[0]["section"] == "pains"

    def test_coverage_gap_no_gains(self, validator):
        """Nudge when pains exist but no gains."""
        pains = ["Manual deployment takes 45 minutes each time"]
        nudges = validator.compute_nudges("Deploy software", pains, [])
        coverage = [n for n in nudges if n["type"] == "coverage_gap"]
        assert len(coverage) == 1
        assert coverage[0]["section"] == "gains"

    def test_near_threshold(self, validator):
        """Nudge when item count is close to minimum."""
        pains = [
            f"Specific pain point number {i} that describes a real problem in detail"
            for i in range(5, 5 + validator.MIN_PAIN_POINTS - 2)
        ]
        nudges = validator.compute_nudges("Deploy software", pains, [])
        near = [n for n in nudges if n["type"] == "near_threshold"]
        assert len(near) >= 1
        assert near[0]["section"] == "pains"

    def test_max_five_nudges(self, validator):
        """Never return more than 5 nudges."""
        # Deliberately create many issues
        nudges = validator.compute_nudges("bad", ["x"] * 5, ["y"] * 5)
        assert len(nudges) <= 5

    def test_empty_canvas_no_crash(self, validator):
        """Empty inputs don't crash."""
        nudges = validator.compute_nudges("", [], [])
        assert isinstance(nudges, list)

    def test_low_specificity_nudge(self, validator):
        """Low quality items trigger specificity nudge."""
        pains = ["bad thing", "problem stuff", "issue here"]
        nudges = validator.compute_nudges("Deploy software", pains, [])
        spec = [n for n in nudges if n["type"] == "low_specificity"]
        assert len(spec) >= 1

    def test_nudge_structure(self, validator):
        """Each nudge has required fields."""
        pains = ["Manual deployment takes 45 minutes each time"]
        nudges = validator.compute_nudges("Deploy software", pains, [])
        for nudge in nudges:
            assert "id" in nudge
            assert "type" in nudge
            assert "section" in nudge
            assert "message" in nudge
            assert "severity" in nudge
            assert nudge["severity"] in ("info", "suggestion")
