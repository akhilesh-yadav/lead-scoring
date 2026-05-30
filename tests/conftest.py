"""
Shared test fixtures for the lead scoring pipeline.
Consolidates common test data to avoid duplication across test modules.
"""

import os
import sys
from datetime import datetime

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


REFERENCE_DATE = datetime(2025, 5, 15)


@pytest.fixture
def reference_date():
    return REFERENCE_DATE


@pytest.fixture
def sample_accounts():
    """Minimal account fixture covering named, ICP, and DNC variants."""
    return pd.DataFrame(
        [
            {
                "account_id": "ACC-001",
                "account_name": "TargetCorp",
                "industry": "Technology",
                "employee_count": 5000,
                "annual_revenue": 500e6,
                "is_icp_qualified": True,
                "is_named_account": True,
                "intent_score": 80,
                "do_not_contact": False,
                "country": "US",
            },
            {
                "account_id": "ACC-002",
                "account_name": "SmallBiz",
                "industry": "Retail",
                "employee_count": 50,
                "annual_revenue": 1e6,
                "is_icp_qualified": False,
                "is_named_account": False,
                "intent_score": 10,
                "do_not_contact": False,
                "country": "US",
            },
            {
                "account_id": "ACC-003",
                "account_name": "BlockedInc",
                "industry": "Finance",
                "employee_count": 1000,
                "annual_revenue": 100e6,
                "is_icp_qualified": True,
                "is_named_account": False,
                "intent_score": 50,
                "do_not_contact": True,
                "country": "UK",
            },
        ]
    )


@pytest.fixture
def sample_leads():
    """Minimal leads fixture with diverse scenarios."""
    return pd.DataFrame(
        [
            {
                "lead_id": "L1",
                "email": "vp@target.com",
                "first_name": "Sarah",
                "last_name": "Chen",
                "title": "VP of Security",
                "company": "TargetCorp",
                "lead_status": "MQL",
                "lead_source": "Web",
                "job_persona": "CISO",
                "job_level": "VP",
                "created_date": "2025-04-01",
                "mql_date": "2025-05-10",
                "is_converted": False,
                "converted_contact_id": None,
                "mkto_lead_score": 85,
                "is_disqualified": False,
                "dq_reason": None,
                "dq_date": None,
                "has_opted_out": False,
                "email_bounced": False,
            },
            {
                "lead_id": "L2",
                "email": "spy@crowdstrike.com",
                "first_name": "James",
                "last_name": "Bond",
                "title": "Solutions Engineer",
                "company": "CrowdStrike",
                "lead_status": "New",
                "lead_source": "Event",
                "job_persona": "Non-Prospect",
                "job_level": "Individual Contributor",
                "created_date": "2025-03-15",
                "mql_date": None,
                "is_converted": False,
                "converted_contact_id": None,
                "mkto_lead_score": 70,
                "is_disqualified": False,
                "dq_reason": None,
                "dq_date": None,
                "has_opted_out": False,
                "email_bounced": False,
            },
            {
                "lead_id": "L3",
                "email": "bounced@gone.com",
                "first_name": "Ghost",
                "last_name": "User",
                "title": None,
                "company": "UnknownCo",
                "lead_status": "Attempted",
                "lead_source": "Purchased List",
                "job_persona": None,
                "job_level": None,
                "created_date": "2025-01-15",
                "mql_date": None,
                "is_converted": True,
                "converted_contact_id": None,
                "mkto_lead_score": 30,
                "is_disqualified": False,
                "dq_reason": None,
                "dq_date": None,
                "has_opted_out": True,
                "email_bounced": True,
            },
        ]
    )


@pytest.fixture
def sample_contacts():
    """Minimal contacts fixture with diverse scenarios."""
    return pd.DataFrame(
        [
            {
                "contact_id": "C1",
                "account_id": "ACC-001",
                "email": "director@target.com",
                "first_name": "Mike",
                "last_name": "Johnson",
                "title": "Director of IT",
                "contact_status": "Active",
                "job_persona": "Technical Buyer",
                "job_level": "Director",
                "created_date": "2024-06-01",
                "mql_date": "2025-05-12",
                "mkto_contact_score": 75,
                "is_mql": True,
                "has_lead_origin": False,
                "primary_lead_id": None,
                "no_longer_with_company": False,
                "has_opted_out": False,
            },
            {
                "contact_id": "C2",
                "account_id": "ACC-003",
                "email": "left@blocked.com",
                "first_name": "Former",
                "last_name": "Employee",
                "title": "Manager",
                "contact_status": "Nurture",
                "job_persona": "IT Operations",
                "job_level": "Manager",
                "created_date": "2023-01-01",
                "mql_date": None,
                "mkto_contact_score": 20,
                "is_mql": False,
                "has_lead_origin": True,
                "primary_lead_id": "L3",
                "no_longer_with_company": True,
                "has_opted_out": False,
            },
        ]
    )


@pytest.fixture
def sample_campaign_members():
    """Campaign members with mix of real and automated engagement."""
    return pd.DataFrame(
        [
            {
                "cm_id": "cm-001",
                "entity_id": "L1",
                "entity_type": "lead",
                "campaign_name": "Webinar_CloudSec_2025",
                "campaign_type": "Webinar",
                "member_status": "Attended",
                "is_responded": True,
                "response_date": "2025-05-10",
                "is_active": True,
            },
            {
                "cm_id": "cm-002",
                "entity_id": "L1",
                "entity_type": "lead",
                "campaign_name": "Webinar_ZeroTrust_2025",
                "campaign_type": "Webinar",
                "member_status": "Attended",
                "is_responded": True,
                "response_date": "2025-05-05",
                "is_active": False,
            },
            {
                "cm_id": "cm-003",
                "entity_id": "L1",
                "entity_type": "lead",
                "campaign_name": "Event_RSA_2025",
                "campaign_type": "Event",
                "member_status": "Attended",
                "is_responded": True,
                "response_date": "2025-04-28",
                "is_active": False,
            },
            {
                "cm_id": "cm-004",
                "entity_id": "L2",
                "entity_type": "lead",
                "campaign_name": "Webinar_Competitor_Intel",
                "campaign_type": "Webinar",
                "member_status": "Attended",
                "is_responded": True,
                "response_date": "2025-05-12",
                "is_active": True,
            },
            {
                "cm_id": "cm-005",
                "entity_id": "C1",
                "entity_type": "contact",
                "campaign_name": "Content_Whitepaper_2025",
                "campaign_type": "Content Syndication",
                "member_status": "Downloaded",
                "is_responded": True,
                "response_date": "2025-05-14",
                "is_active": True,
            },
            {
                "cm_id": "cm-006",
                "entity_id": "C1",
                "entity_type": "contact",
                "campaign_name": "Email_Drip_Q2",
                "campaign_type": "Email",
                "member_status": "Sent",
                "is_responded": False,
                "response_date": "2025-05-01",
                "is_active": False,
            },
            {
                "cm_id": "cm-007",
                "entity_id": "C1",
                "entity_type": "contact",
                "campaign_name": "Email_Drip_Q2_2",
                "campaign_type": "Email",
                "member_status": "Sent",
                "is_responded": False,
                "response_date": "2025-04-15",
                "is_active": False,
            },
        ]
    )
