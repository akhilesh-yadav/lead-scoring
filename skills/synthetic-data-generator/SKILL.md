---
name: synthetic-data-generator
description: Generates realistic synthetic CRM data (Salesforce object model) with configurable data quality issues, engagement distributions, and persona archetypes. Produces leads, contacts, accounts, and campaign members CSVs. Use when user says "generate synthetic data", "create test CRM data", "simulate Salesforce records", or needs realistic B2B marketing data for testing.
---

# Synthetic CRM Data Generator

## Quick Start

```bash
cd lead-scoring-poc
python scripts/generate_data.py
# Output: data/raw/accounts.csv, leads.csv, contacts.csv, campaign_members.csv
```

## Configuration

Edit constants at the top of `scripts/generate_data.py`:

```python
NUM_ACCOUNTS = 200      # Target companies
NUM_LEADS = 600         # Top-of-funnel records
NUM_CONTACTS = 400      # Converted/orphan contacts
NUM_CAMPAIGN_MEMBERS = 4000  # Engagement records
```

## Salesforce Object Model

The generator produces data conforming to the standard SFDC schema:

```
Account (1) ←── (N) Contact
                       ↑
Lead ──── converts to ─┘
                       
Campaign (1) ←── (N) CampaignMember ──→ Lead OR Contact
```

### Entity Sub-Populations

| Type | Description | % of Total |
|------|-------------|-----------|
| Orphan Leads | Never converted, no contact link | ~65% of leads |
| Connected Pairs | Lead → Contact via conversion | ~35% of leads |
| Orphan Contacts | Created directly on account, no lead origin | ~60% of contacts |

## Data Quality Issue Injection

The generator deliberately injects these DQ patterns:

### DQ-1: Broken Conversion Links (~20% of converted)
```python
# 20% of is_converted=True leads get NULL converted_contact_id
if is_converted and random.random() < 0.8:
    converted_contact_id = f"CON-{id}"
# else: NULL (broken link)
```

### DQ-2: Email Duplication (~8% of leads)
```python
# Some records reuse emails from earlier records
if random.random() < 0.08:
    email = leads[random.randint(0, len(leads)-1)]["email"]
```

### DQ-4: ETL Timestamps (~80% of leads)
```python
etl_dates = [NOW - timedelta(days=random.randint(1, 30)) for _ in range(5)]
if random.random() < 0.8:
    created = random.choice(etl_dates)  # Cluster on bulk-load dates
```

### DQ-6: Non-Prospect Contamination (~13%)
```python
is_competitor = random.random() < 0.05
is_non_prospect = is_competitor or random.random() < 0.08
```

### DQ-8: Automation-Inflated Engagement (~60% of emails)
```python
if campaign_type == "Email" and random.random() < 0.6:
    status = "Sent"  # Auto-send, no real engagement
```

## Engagement Distribution

Campaign members follow a **Zipf distribution** (power law):
- Most entities have 1-3 campaign memberships
- Some have 10-20 (active engagers)
- A few outliers have 30-50 (automation-inflated)

```python
engagement_counts = np.random.zipf(1.8, total_entities)
engagement_counts = np.clip(engagement_counts, 0, 50)
```

## Required Persona Archetypes

The generator ensures these 10 test personas exist (Appendix B):

| # | Persona | Expected Behavior |
|---|---------|-------------------|
| 1 | VP Security, named account, 3 recent webinars | Should score Hot |
| 2 | Same profile, all engagement >6mo old | Should score Mid/Low |
| 3 | Junior analyst, 15 responses in 30 days | Should score Mid/High |
| 4 | CISO Fortune 500, zero engagement | Should score Low |
| 5 | Competitor employee, high engagement | Should be Excluded |
| 6 | Bounced + opted out + recent physical event | Edge case |
| 7 | Broken conversion link, split engagement | Edge case |
| 8 | 40 campaigns, 38 automated email sends | Should score Mid/Low |
| 9 | Re-MQL'd 4 times over 2 years | Ambiguous |
| 10 | CC contact, high-intent account, 2 form fills | Should score High |

## Extending the Generator

To add new DQ issues or entity types:

1. Add the injection logic in `generate_leads()` or `generate_contacts()`
2. Add the persona to `inject_personas()` if it's a test archetype
3. Update `pipeline/clean.py` with the corresponding detection function
4. Add a test in `tests/test_clean.py`

## Reproducibility

All random seeds are fixed:
```python
Faker.seed(42)
random.seed(42)
np.random.seed(42)
```

Re-running produces identical output every time.
