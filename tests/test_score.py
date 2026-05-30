"""Tests for Layer 3: Component Scoring."""

import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.pipeline.stages.score import (
    EngagementScoringConfig,
    ScoringWeights,
    compute_scores,
    score_account,
    score_engagement,
    score_momentum,
    score_profile,
)


def make_row(**kwargs):
    """Helper to create a row with defaults for all required fields."""
    defaults = {
        "days_since_last_engagement": 999,
        "engagement_last_30d": 0,
        "engagement_last_90d": 0,
        "automation_ratio": 0.0,
        "campaign_type_diversity": 0,
        "webinar_attendances": 0,
        "event_attendances": 0,
        "content_responses": 0,
        "level_score": 0.2,
        "persona_score": 0.2,
        "has_title": 0,
        "has_persona": 0,
        "has_account": 0,
        "account_is_named": 0,
        "account_is_icp": 0,
        "account_intent": 0.0,
        "account_employee_score": 0.0,
        "account_revenue_score": 0.0,
        "momentum_score": 0.0,
        "is_accelerating": False,
    }
    defaults.update(kwargs)
    return pd.Series(defaults)


class TestEngagementScoring:
    def test_no_engagement_scores_zero(self):
        row = make_row(days_since_last_engagement=999)
        assert score_engagement(row) == 0.0

    def test_fresh_engagement_scores_high(self):
        row = make_row(
            days_since_last_engagement=1,
            engagement_last_30d=3,
            engagement_last_90d=5,
            campaign_type_diversity=3,
            webinar_attendances=1,
        )
        assert score_engagement(row) > 50.0

    def test_stale_engagement_scores_low(self):
        row = make_row(
            days_since_last_engagement=180,
            engagement_last_30d=0,
            engagement_last_90d=0,
            engagement_last_180d=5,
        )
        assert score_engagement(row) < 20.0

    def test_automation_penalized(self):
        base_row = make_row(
            days_since_last_engagement=10,
            engagement_last_30d=2,
            campaign_type_diversity=2,
        )
        high_auto_row = make_row(
            days_since_last_engagement=10,
            engagement_last_30d=2,
            campaign_type_diversity=2,
            automation_ratio=0.9,
        )
        assert score_engagement(base_row) > score_engagement(high_auto_row)

    def test_time_decay_halflife(self):
        row_0 = make_row(days_since_last_engagement=0, engagement_last_30d=1)
        row_45 = make_row(
            days_since_last_engagement=45, engagement_last_30d=0, engagement_last_90d=1
        )
        # At half-life, recency component should be ~half
        score_0 = score_engagement(row_0)
        score_45 = score_engagement(row_45)
        assert score_0 > score_45

    def test_output_bounded(self):
        row = make_row(
            days_since_last_engagement=0,
            engagement_last_30d=50,
            engagement_last_90d=100,
            campaign_type_diversity=7,
            webinar_attendances=10,
            event_attendances=10,
            content_responses=10,
        )
        assert 0 <= score_engagement(row) <= 100

    def test_custom_config(self):
        config = EngagementScoringConfig(half_life_days=10)
        row = make_row(days_since_last_engagement=30, engagement_last_30d=1)
        score_fast = score_engagement(row, config)
        score_default = score_engagement(row)
        # Faster decay → lower score at 30 days
        assert score_fast < score_default


class TestProfileScoring:
    def test_ciso_vp_maxes(self):
        row = make_row(level_score=0.85, persona_score=1.0, has_title=1, has_persona=1)
        assert score_profile(row) == pytest.approx(100.0, abs=5)

    def test_unknown_profile(self):
        row = make_row(level_score=0.2, persona_score=0.2, has_title=0, has_persona=0)
        assert score_profile(row) == 20.0

    def test_bounded(self):
        row = make_row(level_score=1.0, persona_score=1.0, has_title=1, has_persona=1)
        assert 0 <= score_profile(row) <= 100


class TestAccountScoring:
    def test_no_account_baseline(self):
        row = make_row(has_account=0)
        assert score_account(row) == 15.0

    def test_custom_baseline(self):
        row = make_row(has_account=0)
        assert score_account(row, lead_baseline=25.0) == 25.0

    def test_named_icp_high_intent(self):
        row = make_row(
            has_account=1,
            account_is_named=1,
            account_is_icp=1,
            account_intent=0.8,
            account_employee_score=0.5,
            account_revenue_score=0.5,
        )
        score = score_account(row)
        assert score > 70.0

    def test_weak_account(self):
        row = make_row(
            has_account=1,
            account_is_named=0,
            account_is_icp=0,
            account_intent=0.1,
            account_employee_score=0.1,
            account_revenue_score=0.01,
        )
        assert score_account(row) < 20.0


class TestMomentumScoring:
    def test_no_recent_engagement(self):
        row = make_row(engagement_last_30d=0, momentum_score=0.5, is_accelerating=True)
        assert score_momentum(row) == 0.0

    def test_accelerating(self):
        row = make_row(engagement_last_30d=3, momentum_score=1.5, is_accelerating=True)
        score = score_momentum(row)
        assert score > 50.0

    def test_not_accelerating(self):
        row = make_row(engagement_last_30d=2, momentum_score=0.5, is_accelerating=False)
        score = score_momentum(row)
        assert score < 30.0


class TestScoringWeights:
    def test_default_weights_valid(self):
        w = ScoringWeights()
        w.validate()  # Should not raise

    def test_invalid_weights_raise(self):
        w = ScoringWeights(engagement=0.5, profile=0.5, account=0.5, momentum=0.5)
        with pytest.raises(AssertionError):
            w.validate()


class TestComputeScores:
    def test_produces_readiness_score(self):
        features = pd.DataFrame(
            [
                make_row(
                    days_since_last_engagement=5,
                    engagement_last_30d=2,
                    campaign_type_diversity=2,
                    level_score=0.7,
                    persona_score=0.9,
                    has_title=1,
                    has_persona=1,
                    has_account=1,
                    account_is_named=1,
                    account_is_icp=1,
                    account_intent=0.7,
                    momentum_score=1.0,
                    is_accelerating=True,
                    engagement_last_90d=3,
                ).to_dict()
            ]
        )
        result = compute_scores(features)
        assert "readiness_score" in result.columns
        assert "score_engagement" in result.columns
        assert result.iloc[0]["readiness_score"] > 0

    def test_score_bounded(self):
        features = pd.DataFrame([make_row().to_dict()] * 10)
        result = compute_scores(features)
        assert result["readiness_score"].min() >= 0
        assert result["readiness_score"].max() <= 100
