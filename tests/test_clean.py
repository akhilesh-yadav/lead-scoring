"""Tests for Layer 1: Cleaning & Entity Resolution."""

import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.pipeline.stages.clean import (
    detect_etl_dates,
    find_duplicate_emails,
    flag_contact_exclusions,
    flag_lead_dq,
    flag_lead_exclusions,
    get_dnc_accounts,
    resolve_broken_conversions,
)


@pytest.fixture
def sample_leads():
    return pd.DataFrame(
        [
            {
                "lead_id": "L1",
                "email": "a@test.com",
                "company": "Acme",
                "has_opted_out": False,
                "email_bounced": False,
                "job_persona": "CISO",
                "is_disqualified": False,
                "is_converted": False,
                "converted_contact_id": None,
                "mql_date": None,
                "lead_status": "New",
                "created_date": "2025-01-15",
                "title": "VP Security",
            },
            {
                "lead_id": "L2",
                "email": "b@test.com",
                "company": "CrowdStrike",
                "has_opted_out": False,
                "email_bounced": False,
                "job_persona": "Non-Prospect",
                "is_disqualified": False,
                "is_converted": False,
                "converted_contact_id": None,
                "mql_date": None,
                "lead_status": "New",
                "created_date": "2025-01-15",
                "title": None,
            },
            {
                "lead_id": "L3",
                "email": "c@test.com",
                "company": "BigCo",
                "has_opted_out": True,
                "email_bounced": False,
                "job_persona": "Technical Buyer",
                "is_disqualified": False,
                "is_converted": True,
                "converted_contact_id": None,
                "mql_date": "2024-12-01",
                "lead_status": "Recycled",
                "created_date": "2025-01-15",
                "title": "Director",
            },
            {
                "lead_id": "L4",
                "email": "a@test.com",
                "company": "AnotherCo",
                "has_opted_out": False,
                "email_bounced": True,
                "job_persona": None,
                "is_disqualified": True,
                "is_converted": False,
                "converted_contact_id": None,
                "mql_date": None,
                "lead_status": "Disqualified",
                "created_date": "2025-03-01",
                "title": None,
            },
        ]
    )


@pytest.fixture
def sample_contacts():
    return pd.DataFrame(
        [
            {
                "contact_id": "C1",
                "email": "x@test.com",
                "account_id": "ACC-001",
                "has_opted_out": False,
                "no_longer_with_company": False,
                "job_persona": "CISO",
                "created_date": "2024-06-01",
                "title": "CISO",
            },
            {
                "contact_id": "C2",
                "email": "a@test.com",
                "account_id": "ACC-002",
                "has_opted_out": False,
                "no_longer_with_company": True,
                "job_persona": "Technical Buyer",
                "created_date": "2024-06-01",
                "title": None,
            },
        ]
    )


@pytest.fixture
def sample_accounts():
    return pd.DataFrame(
        [
            {"account_id": "ACC-001", "do_not_contact": False},
            {"account_id": "ACC-002", "do_not_contact": True},
        ]
    )


class TestLeadExclusions:
    def test_competitor_flagged(self, sample_leads):
        result = flag_lead_exclusions(sample_leads)
        assert result.loc[1, "exclude_competitor"]
        assert not result.loc[0, "exclude_competitor"]

    def test_opted_out_flagged(self, sample_leads):
        result = flag_lead_exclusions(sample_leads)
        assert result.loc[2, "exclude_opted_out"]
        assert not result.loc[0, "exclude_opted_out"]

    def test_bounced_flagged(self, sample_leads):
        result = flag_lead_exclusions(sample_leads)
        assert result.loc[3, "exclude_bounced"]

    def test_non_prospect_flagged(self, sample_leads):
        result = flag_lead_exclusions(sample_leads)
        assert result.loc[1, "exclude_non_prospect"]
        assert not result.loc[0, "exclude_non_prospect"]

    def test_is_excluded_composite(self, sample_leads):
        result = flag_lead_exclusions(sample_leads)
        assert not result.loc[0, "is_excluded"]
        assert result.loc[1, "is_excluded"]  # competitor + non-prospect
        assert result.loc[2, "is_excluded"]  # opted out
        assert result.loc[3, "is_excluded"]  # bounced + disqualified

    def test_does_not_mutate_input(self, sample_leads):
        original_cols = set(sample_leads.columns)
        flag_lead_exclusions(sample_leads)
        assert set(sample_leads.columns) == original_cols


class TestContactExclusions:
    def test_no_longer_flagged(self, sample_contacts, sample_accounts):
        dnc = get_dnc_accounts(sample_accounts)
        result = flag_contact_exclusions(sample_contacts, dnc)
        assert result.loc[1, "exclude_no_longer"]
        assert not result.loc[0, "exclude_no_longer"]

    def test_dnc_account_flagged(self, sample_contacts, sample_accounts):
        dnc = get_dnc_accounts(sample_accounts)
        result = flag_contact_exclusions(sample_contacts, dnc)
        assert result.loc[1, "exclude_dnc_account"]
        assert not result.loc[0, "exclude_dnc_account"]


class TestDuplicateEmails:
    def test_finds_cross_entity_dupes(self, sample_leads, sample_contacts):
        dupes = find_duplicate_emails(sample_leads, sample_contacts)
        assert "a@test.com" in dupes  # appears in both leads and contacts

    def test_finds_intra_entity_dupes(self, sample_leads, sample_contacts):
        dupes = find_duplicate_emails(sample_leads, sample_contacts)
        assert "a@test.com" in dupes  # L1 and L4 share this email

    def test_unique_emails_not_flagged(self, sample_leads, sample_contacts):
        dupes = find_duplicate_emails(sample_leads, sample_contacts)
        assert "x@test.com" not in dupes


class TestETLDetection:
    def test_detects_bulk_dates(self):
        dates = pd.Series(["2025-01-15"] * 25 + ["2025-02-01", "2025-03-01"])
        etl = detect_etl_dates(dates, threshold=20)
        assert "2025-01-15" in etl
        assert "2025-02-01" not in etl

    def test_empty_series(self):
        dates = pd.Series([], dtype=str)
        etl = detect_etl_dates(dates)
        assert len(etl) == 0


class TestLeadDQ:
    def test_broken_conversion_flagged(self, sample_leads):
        leads = flag_lead_exclusions(sample_leads)
        result = flag_lead_dq(leads, set(), set())
        assert result.loc[2, "dq_broken_conversion"]  # converted but no contact_id
        assert not result.loc[0, "dq_broken_conversion"]

    def test_mql_overwritten_flagged(self, sample_leads):
        leads = flag_lead_exclusions(sample_leads)
        result = flag_lead_dq(leads, set(), set())
        assert result.loc[2, "dq_mql_overwritten"]  # has mql_date + Recycled status

    def test_incomplete_flagged(self, sample_leads):
        leads = flag_lead_exclusions(sample_leads)
        result = flag_lead_dq(leads, set(), set())
        assert result.loc[3, "dq_incomplete"]  # no title + no persona
        assert not result.loc[0, "dq_incomplete"]

    def test_dq_count_accumulates(self, sample_leads):
        leads = flag_lead_exclusions(sample_leads)
        result = flag_lead_dq(leads, {"a@test.com"}, {"2025-01-15"})
        # L1: dup_email + etl = 2
        assert result.loc[0, "dq_issue_count"] >= 2


class TestEntityResolution:
    def test_resolves_via_email(self, sample_leads, sample_contacts):
        leads = sample_leads.copy()
        leads["dq_broken_conversion"] = [False, False, True, False]
        resolved_leads, count = resolve_broken_conversions(leads, sample_contacts)
        # L3 has email c@test.com which doesn't match any contact
        # But if we fix L3's email to match C2...
        assert count == 0  # no match in this fixture

    def test_resolves_matching_email(self):
        leads = pd.DataFrame(
            [
                {
                    "lead_id": "L1",
                    "email": "match@test.com",
                    "is_converted": True,
                    "converted_contact_id": None,
                }
            ]
        )
        leads["dq_broken_conversion"] = True
        contacts = pd.DataFrame([{"contact_id": "C99", "email": "match@test.com"}])
        resolved, count = resolve_broken_conversions(leads, contacts)
        assert count == 1
        assert resolved.loc[0, "resolved_contact_id"] == "C99"
