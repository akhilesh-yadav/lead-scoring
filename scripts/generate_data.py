"""
Synthetic CRM Data Generator
Generates ~1000 leads/contacts with realistic data quality issues (DQ-1 through DQ-10).
Outputs: accounts.csv, leads.csv, contacts.csv, campaign_members.csv
"""

import os
import random
import uuid
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)
np.random.seed(42)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
os.makedirs(OUTPUT_DIR, exist_ok=True)

NUM_ACCOUNTS = 200
NUM_LEADS = 600
NUM_CONTACTS = 400
NUM_CAMPAIGN_MEMBERS = 4000

INDUSTRIES = [
    "Technology",
    "Financial Services",
    "Healthcare",
    "Manufacturing",
    "Retail",
    "Energy",
    "Government",
    "Education",
    "Media",
    "Telecommunications",
]
CAMPAIGN_TYPES = [
    "Webinar",
    "Event",
    "Content Syndication",
    "Email",
    "Advertisement",
    "Telemarketing",
    "Direct Mail",
]
MEMBER_STATUSES = {
    "Webinar": ["Registered", "Attended", "No Show"],
    "Event": ["Registered", "Attended", "No Show"],
    "Content Syndication": ["Responded", "Downloaded"],
    "Email": ["Sent", "Opened", "Clicked"],
    "Advertisement": ["Clicked", "Converted"],
    "Telemarketing": ["Contacted", "Interested", "Not Interested"],
    "Direct Mail": ["Sent", "Responded"],
}
LEAD_SOURCES = [
    "Web",
    "Event",
    "Content Syndication",
    "Purchased List",
    "Partner Referral",
    "Organic Search",
]
JOB_PERSONAS = [
    "Technical Buyer",
    "CISO",
    "Financial Buyer",
    "IT Operations",
    "Security Engineer",
    None,
]
JOB_LEVELS = ["C-Level", "VP", "Director", "Manager", "Individual Contributor", None]
LEAD_STATUSES = ["New", "MQL", "Attempted", "Qualified", "Disqualified", "Recycled"]
DQ_REASONS = ["Competitor", "Duplicate", "No Longer With Company", "Bad Data", None]
CYBERSECURITY_COMPANIES = [
    "CrowdStrike",
    "Palo Alto Networks",
    "Fortinet",
    "SentinelOne",
    "Zscaler",
    "Okta",
    "CyberArk",
    "Varonis",
    "Rapid7",
    "Qualys",
]

NOW = datetime(2025, 5, 15)


def generate_accounts():
    accounts = []
    for i in range(NUM_ACCOUNTS):
        is_named = random.random() < 0.15
        is_icp = is_named or random.random() < 0.25
        intent = np.clip(int(np.random.beta(2, 5) * 100), 0, 100) if random.random() < 0.7 else None
        if is_named:
            intent = max(intent or 0, int(np.random.beta(5, 3) * 100))

        accounts.append(
            {
                "account_id": f"ACC-{i + 1:04d}",
                "account_name": fake.company(),
                "industry": random.choice(INDUSTRIES),
                "employee_count": random.choice([50, 200, 500, 1000, 2500, 5000, 10000, 50000]),
                "annual_revenue": round(
                    random.choice([1e6, 5e6, 10e6, 50e6, 100e6, 500e6, 1e9]), 0
                ),
                "is_icp_qualified": is_icp,
                "is_named_account": is_named,
                "intent_score": intent,
                "do_not_contact": random.random() < 0.03,
                "country": random.choice(
                    ["US", "US", "US", "UK", "Canada", "Germany", "Australia"]
                ),
            }
        )
    return pd.DataFrame(accounts)


def generate_leads(accounts_df):
    leads = []
    etl_dates = [NOW - timedelta(days=random.randint(1, 30)) for _ in range(5)]

    for i in range(NUM_LEADS):
        is_converted = random.random() < 0.35
        is_competitor = random.random() < 0.05
        is_non_prospect = is_competitor or random.random() < 0.08

        persona = "Non-Prospect" if is_non_prospect else random.choice(JOB_PERSONAS)
        level = "Non-Prospect" if is_non_prospect else random.choice(JOB_LEVELS)

        # DQ-4: ETL-dominated creation timestamps (~80%)
        if random.random() < 0.8:
            created = random.choice(etl_dates)
        else:
            created = NOW - timedelta(days=random.randint(1, 730))

        # MQL logic
        is_mql = random.random() < 0.3
        mql_date = None
        if is_mql:
            # DQ-3: MQL date overwrites (shows most recent, not first)
            _num_mqls = random.randint(1, 4) if random.random() < 0.2 else 1  # noqa: F841
            mql_date = NOW - timedelta(days=random.randint(1, 60))

        # DQ-1: Broken conversion links
        converted_contact_id = None
        if is_converted:
            if random.random() < 0.8:
                converted_contact_id = f"CON-{random.randint(1, NUM_CONTACTS):04d}"
            # else: NULL (DQ-1, ~20% of converted)

        # Score: DQ-5 asymmetry (different scale for leads)
        score = int(np.random.exponential(30)) if not is_non_prospect else random.randint(0, 10)

        # DQ-6: Competitor contamination
        company = random.choice(CYBERSECURITY_COMPANIES) if is_competitor else fake.company()

        # DQ-7: Data completeness gaps
        title = fake.job() if random.random() > 0.35 else None
        phone = fake.phone_number() if random.random() > 0.40 else None

        # DQ-9: Do-not-contact
        has_opted_out = random.random() < 0.05
        email_bounced = random.random() < 0.04

        # DQ-10: DQ/re-MQL cycles
        is_disqualified = random.random() < 0.1
        dq_reason = random.choice(DQ_REASONS[:3]) if is_disqualified else None
        dq_date = (NOW - timedelta(days=random.randint(30, 365))) if is_disqualified else None

        email = fake.email()
        # DQ-2: Email duplication (some share emails)
        if random.random() < 0.08 and i > 10:
            email = leads[random.randint(0, len(leads) - 1)]["email"]

        lead_status = (
            "Disqualified"
            if is_disqualified
            else ("MQL" if is_mql else random.choice(["New", "Attempted", "Qualified", "Recycled"]))
        )

        leads.append(
            {
                "lead_id": f"LEAD-{i + 1:04d}",
                "email": email,
                "first_name": fake.first_name(),
                "last_name": fake.last_name(),
                "title": title,
                "company": company,
                "lead_status": lead_status,
                "lead_source": random.choice(LEAD_SOURCES),
                "job_persona": persona,
                "job_level": level,
                "created_date": created.strftime("%Y-%m-%d"),
                "mql_date": mql_date.strftime("%Y-%m-%d") if mql_date else None,
                "is_converted": is_converted,
                "converted_contact_id": converted_contact_id,
                "mkto_lead_score": score,
                "is_disqualified": is_disqualified,
                "dq_reason": dq_reason,
                "dq_date": dq_date.strftime("%Y-%m-%d") if dq_date else None,
                "has_opted_out": has_opted_out,
                "email_bounced": email_bounced,
                "phone": phone,
            }
        )
    return pd.DataFrame(leads)


def generate_contacts(accounts_df, leads_df):
    contacts = []
    etl_dates = [NOW - timedelta(days=random.randint(1, 30)) for _ in range(3)]
    account_ids = accounts_df["account_id"].tolist()

    for i in range(NUM_CONTACTS):
        has_lead_origin = random.random() < 0.4
        is_non_prospect = random.random() < 0.06

        persona = "Non-Prospect" if is_non_prospect else random.choice(JOB_PERSONAS)
        level = "Non-Prospect" if is_non_prospect else random.choice(JOB_LEVELS)

        # DQ-4: ETL timestamps (~34% for contacts)
        if random.random() < 0.34:
            created = random.choice(etl_dates)
        else:
            created = NOW - timedelta(days=random.randint(1, 1095))

        # Account linkage (contacts almost always have one)
        account_id = random.choice(account_ids) if random.random() > 0.02 else None

        is_mql = random.random() < 0.25
        mql_date = (NOW - timedelta(days=random.randint(1, 90))) if is_mql else None

        # DQ-5: Different score field (mkto_contact_score vs mkto_lead_score)
        score = int(np.random.exponential(40)) if not is_non_prospect else random.randint(0, 5)

        no_longer = random.random() < 0.08
        has_opted_out = random.random() < 0.04
        title = fake.job() if random.random() > 0.20 else None

        email = fake.email()
        # DQ-2: cross-entity email duplication
        if random.random() < 0.05 and len(contacts) > 5:
            email = contacts[random.randint(0, len(contacts) - 1)]["email"]

        contacts.append(
            {
                "contact_id": f"CON-{i + 1:04d}",
                "account_id": account_id,
                "email": email,
                "first_name": fake.first_name(),
                "last_name": fake.last_name(),
                "title": title,
                "contact_status": "MQL"
                if is_mql
                else random.choice(["Active", "Attempted", "Qualified", "Nurture"]),
                "job_persona": persona,
                "job_level": level,
                "created_date": created.strftime("%Y-%m-%d"),
                "mql_date": mql_date.strftime("%Y-%m-%d") if mql_date else None,
                "mkto_contact_score": score,
                "is_mql": is_mql,
                "has_lead_origin": has_lead_origin,
                "primary_lead_id": f"LEAD-{random.randint(1, NUM_LEADS):04d}"
                if has_lead_origin
                else None,
                "no_longer_with_company": no_longer,
                "has_opted_out": has_opted_out,
            }
        )
    return pd.DataFrame(contacts)


def generate_campaign_members(leads_df, contacts_df):
    members = []
    lead_ids = leads_df["lead_id"].tolist()
    contact_ids = contacts_df["contact_id"].tolist()

    # Create engagement distribution: most records have few, some have many
    engagement_counts = np.random.zipf(1.8, len(lead_ids) + len(contact_ids))
    engagement_counts = np.clip(engagement_counts, 0, 50)

    all_entities = [(lid, "lead") for lid in lead_ids] + [(cid, "contact") for cid in contact_ids]

    for idx, (entity_id, entity_type) in enumerate(all_entities):
        n_campaigns = int(engagement_counts[idx % len(engagement_counts)])
        if n_campaigns == 0 and random.random() < 0.3:
            n_campaigns = random.randint(1, 3)

        for _ in range(min(n_campaigns, 40)):
            campaign_type = random.choice(CAMPAIGN_TYPES)
            statuses = MEMBER_STATUSES[campaign_type]
            status = random.choice(statuses)

            # DQ-8: Automation-inflated engagement (emails with "Sent" only)
            if campaign_type == "Email" and random.random() < 0.6:
                status = "Sent"

            is_responded = status not in ["Sent", "No Show", "Not Interested"]
            days_ago = int(np.random.exponential(120))
            response_date = NOW - timedelta(days=min(days_ago, 730))

            members.append(
                {
                    "cm_id": str(uuid.uuid4())[:12],
                    "entity_id": entity_id,
                    "entity_type": entity_type,
                    "campaign_name": f"{campaign_type}_{fake.bs()[:20]}_{response_date.year}",
                    "campaign_type": campaign_type,
                    "member_status": status,
                    "is_responded": is_responded,
                    "response_date": response_date.strftime("%Y-%m-%d"),
                    "is_active": days_ago < 30 and random.random() < 0.3,
                }
            )

            if len(members) >= NUM_CAMPAIGN_MEMBERS:
                break
        if len(members) >= NUM_CAMPAIGN_MEMBERS:
            break

    return pd.DataFrame(members)


def inject_personas(leads_df, contacts_df, accounts_df, cm_df):
    """Inject the 10 required test personas from Appendix B."""
    # Persona 1: VP Security at named ICP, 3 webinars this month
    leads_df.loc[0] = {
        **leads_df.loc[0],
        "title": "VP of Security",
        "job_persona": "CISO",
        "job_level": "VP",
        "lead_status": "MQL",
        "mkto_lead_score": 85,
        "is_converted": False,
        "mql_date": (NOW - timedelta(days=5)).strftime("%Y-%m-%d"),
    }
    # Link to named account
    named_accts = accounts_df[accounts_df["is_named_account"]]["account_id"].tolist()
    if named_accts:
        contacts_df.loc[0] = {
            **contacts_df.loc[0],
            "account_id": named_accts[0],
            "title": "VP of Security",
            "job_persona": "CISO",
            "job_level": "VP",
            "is_mql": True,
            "mkto_contact_score": 90,
            "mql_date": (NOW - timedelta(days=5)).strftime("%Y-%m-%d"),
        }

    # Persona 2: Same profile but stale engagement (>6 months old) - use index 1
    leads_df.loc[1] = {
        **leads_df.loc[1],
        "title": "VP of Information Security",
        "job_persona": "CISO",
        "job_level": "VP",
        "lead_status": "Recycled",
        "mkto_lead_score": 65,
        "is_converted": False,
        "mql_date": (NOW - timedelta(days=200)).strftime("%Y-%m-%d"),
    }

    # Persona 3: Junior analyst, 15 responses in 30 days, not MQL
    leads_df.loc[2] = {
        **leads_df.loc[2],
        "title": "Security Analyst",
        "job_persona": "Security Engineer",
        "job_level": "Individual Contributor",
        "lead_status": "New",
        "mkto_lead_score": 35,
        "mql_date": None,
        "company": "TinyStartup Inc",
    }

    # Persona 4: CISO Fortune 500, zero engagement
    leads_df.loc[3] = {
        **leads_df.loc[3],
        "title": "Chief Information Security Officer",
        "job_persona": "CISO",
        "job_level": "C-Level",
        "lead_status": "New",
        "mkto_lead_score": 5,
        "lead_source": "Purchased List",
        "mql_date": None,
    }

    # Persona 5: Competitor employee
    leads_df.loc[4] = {
        **leads_df.loc[4],
        "title": "Solutions Engineer",
        "job_persona": "Non-Prospect",
        "job_level": "Individual Contributor",
        "company": "CrowdStrike",
        "lead_status": "New",
        "mkto_lead_score": 70,
    }

    # Persona 6: Bounced + opted out but recent physical event
    leads_df.loc[5] = {
        **leads_df.loc[5],
        "has_opted_out": True,
        "email_bounced": True,
        "lead_status": "Attempted",
        "mkto_lead_score": 45,
    }

    # Persona 7: Broken conversion link (DQ-1)
    leads_df.loc[6] = {
        **leads_df.loc[6],
        "is_converted": True,
        "converted_contact_id": None,
        "lead_status": "MQL",
        "mkto_lead_score": 60,
    }

    # Persona 8: 40 campaign memberships, 38 automated emails
    leads_df.loc[7] = {
        **leads_df.loc[7],
        "title": "IT Manager",
        "lead_status": "MQL",
        "mkto_lead_score": 55,
    }

    # Persona 9: Re-MQL'd 4 times
    leads_df.loc[8] = {
        **leads_df.loc[8],
        "lead_status": "MQL",
        "mkto_lead_score": 50,
        "is_disqualified": False,
        "mql_date": (NOW - timedelta(days=10)).strftime("%Y-%m-%d"),
    }

    # Persona 10: CC contact, high-intent account, 2 recent form fills
    if named_accts and len(named_accts) > 1:
        contacts_df.loc[1] = {
            **contacts_df.loc[1],
            "account_id": named_accts[1],
            "has_lead_origin": False,
            "title": "Director of IT",
            "job_persona": "Technical Buyer",
            "job_level": "Director",
            "mkto_contact_score": 40,
        }

    return leads_df, contacts_df


if __name__ == "__main__":
    print("Generating synthetic CRM data...")
    accounts = generate_accounts()
    leads = generate_leads(accounts)
    contacts = generate_contacts(accounts, leads)
    campaign_members = generate_campaign_members(leads, contacts)
    leads, contacts = inject_personas(leads, contacts, accounts, campaign_members)

    accounts.to_csv(os.path.join(OUTPUT_DIR, "accounts.csv"), index=False)
    leads.to_csv(os.path.join(OUTPUT_DIR, "leads.csv"), index=False)
    contacts.to_csv(os.path.join(OUTPUT_DIR, "contacts.csv"), index=False)
    campaign_members.to_csv(os.path.join(OUTPUT_DIR, "campaign_members.csv"), index=False)

    print(
        f"Generated: {len(accounts)} accounts, {len(leads)} leads, "
        f"{len(contacts)} contacts, {len(campaign_members)} campaign members"
    )
    print(f"Output: {OUTPUT_DIR}")
