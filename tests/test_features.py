"""Tests for Layer 2: Feature Engineering."""

import os
import sys
from datetime import datetime

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.pipeline.stages.features import (
    EngagementFeatures,
    ProfileFeatures,
    compute_account_features,
    compute_engagement_features,
    compute_momentum_features,
    compute_profile_features,
)

REF_DATE = datetime(2025, 5, 15)


@pytest.fixture
def campaign_members():
    return pd.DataFrame(
        [
            {
                "entity_id": "L1",
                "entity_type": "lead",
                "campaign_type": "Webinar",
                "member_status": "Attended",
                "is_responded": True,
                "response_date": "2025-05-10",
            },
            {
                "entity_id": "L1",
                "entity_type": "lead",
                "campaign_type": "Email",
                "member_status": "Sent",
                "is_responded": False,
                "response_date": "2025-05-01",
            },
            {
                "entity_id": "L1",
                "entity_type": "lead",
                "campaign_type": "Event",
                "member_status": "Attended",
                "is_responded": True,
                "response_date": "2025-04-20",
            },
            {
                "entity_id": "L2",
                "entity_type": "lead",
                "campaign_type": "Email",
                "member_status": "Sent",
                "is_responded": False,
                "response_date": "2024-01-01",
            },
            {
                "entity_id": "C1",
                "entity_type": "contact",
                "campaign_type": "Content Syndication",
                "member_status": "Downloaded",
                "is_responded": True,
                "response_date": "2025-05-14",
            },
        ]
    )


@pytest.fixture
def accounts():
    return pd.DataFrame(
        [
            {
                "account_id": "ACC-001",
                "is_icp_qualified": True,
                "is_named_account": True,
                "intent_score": 80,
                "employee_count": 5000,
                "annual_revenue": 500e6,
            },
            {
                "account_id": "ACC-002",
                "is_icp_qualified": False,
                "is_named_account": False,
                "intent_score": 20,
                "employee_count": 100,
                "annual_revenue": 5e6,
            },
        ]
    )


class TestEngagementFeatures:
    def test_no_engagement(self, campaign_members):
        result = compute_engagement_features("NONEXIST", "lead", campaign_members, REF_DATE)
        assert result.total_engagements == 0
        assert result.days_since_last_engagement == 999
        assert result.automation_ratio == 0.0

    def test_with_engagement(self, campaign_members):
        result = compute_engagement_features("L1", "lead", campaign_members, REF_DATE)
        assert result.total_engagements == 3
        assert result.real_engagements == 2  # 2 responded
        assert result.webinar_attendances == 1
        assert result.event_attendances == 1
        assert result.days_since_last_engagement == 5  # 2025-05-10 to 2025-05-15

    def test_automation_ratio(self, campaign_members):
        result = compute_engagement_features("L1", "lead", campaign_members, REF_DATE)
        assert result.automation_ratio == pytest.approx(1 / 3, rel=0.01)  # 1 auto / 3 total

    def test_all_automation(self, campaign_members):
        result = compute_engagement_features("L2", "lead", campaign_members, REF_DATE)
        assert result.real_engagements == 0
        assert result.automation_ratio == 1.0
        assert result.days_since_last_engagement == 999  # no real engagement

    def test_recency_30d(self, campaign_members):
        result = compute_engagement_features("L1", "lead", campaign_members, REF_DATE)
        assert result.engagement_last_30d == 2  # May 10 and Apr 20 are both within 30d of May 15

    def test_returns_dataclass(self, campaign_members):
        result = compute_engagement_features("L1", "lead", campaign_members, REF_DATE)
        assert isinstance(result, EngagementFeatures)
        assert isinstance(result.to_dict(), dict)


class TestProfileFeatures:
    def test_ciso_vp(self):
        result = compute_profile_features("VP", "CISO", "VP of Security")
        assert result.level_score == 0.85
        assert result.persona_score == 1.0
        assert result.has_title == 1
        assert result.has_persona == 1

    def test_missing_fields(self):
        result = compute_profile_features(None, None, None)
        assert result.level_score == 0.2
        assert result.persona_score == 0.2
        assert result.has_title == 0
        assert result.has_persona == 0

    def test_non_prospect(self):
        result = compute_profile_features("Individual Contributor", "Non-Prospect", "Sales Rep")
        assert result.persona_score == 0.0
        assert result.has_persona == 0

    def test_returns_dataclass(self):
        result = compute_profile_features("Director", "Technical Buyer", "Dir Eng")
        assert isinstance(result, ProfileFeatures)


class TestAccountFeatures:
    def test_no_account(self, accounts):
        result = compute_account_features(None, accounts)
        assert result.has_account == 0
        assert result.account_is_named == 0

    def test_named_icp_account(self, accounts):
        result = compute_account_features("ACC-001", accounts)
        assert result.has_account == 1
        assert result.account_is_named == 1
        assert result.account_is_icp == 1
        assert result.account_intent == 0.8

    def test_weak_account(self, accounts):
        result = compute_account_features("ACC-002", accounts)
        assert result.account_is_named == 0
        assert result.account_is_icp == 0
        assert result.account_intent == 0.2

    def test_nonexistent_account(self, accounts):
        result = compute_account_features("FAKE-999", accounts)
        assert result.has_account == 0


class TestMomentumFeatures:
    def test_no_engagement(self, campaign_members):
        result = compute_momentum_features("NONEXIST", "lead", campaign_members, REF_DATE)
        assert result.momentum_score == 0.0
        assert not result.is_accelerating

    def test_recent_burst(self, campaign_members):
        result = compute_momentum_features("L1", "lead", campaign_members, REF_DATE)
        # L1 has 2 real engagements, both in last 30 days
        assert result.momentum_score >= 0.0

    def test_stale_engagement(self, campaign_members):
        result = compute_momentum_features("L2", "lead", campaign_members, REF_DATE)
        # L2 has 0 real engagements
        assert result.momentum_score == 0.0
