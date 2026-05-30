---
name: data-quality-auditor
description: Audits CRM/Salesforce data for quality issues across 10 standard DQ categories (broken links, duplication, temporal anomalies, contamination, completeness gaps, automation inflation). Produces a structured findings report with prevalence, impact, and recommended handling. Use when user says "audit data quality", "check DQ issues", "find data problems", or needs CRM data profiling.
---

# Data Quality Auditor

## Quick Start

Run against any dataset with CRM-like structure (leads, contacts, accounts, campaign members):

```python
from src.pipeline.stages.clean import clean_data, CleaningResult

result = clean_data("./data/raw")
print(result.resolution_stats)
```

## DQ Issue Taxonomy

This skill checks for 10 categories of data quality issues commonly found in B2B CRM systems:

| ID | Category | Detection Method | Severity |
|----|----------|-----------------|----------|
| DQ-1 | Broken entity links | `is_converted=True` AND `converted_contact_id IS NULL` | High |
| DQ-2 | Email duplication | Cross-entity email frequency analysis | Medium |
| DQ-3 | Temporal field overwrites | MQL date present on Recycled/Disqualified records | Low |
| DQ-4 | ETL-dominated timestamps | Date frequency > threshold (bulk-load detection) | Medium |
| DQ-5 | Score field asymmetry | Different score scales across entity types | Medium |
| DQ-6 | Non-prospect contamination | `job_persona = 'Non-Prospect'` + competitor company match | High |
| DQ-7 | Data completeness gaps | NULL rates on critical fields (title, persona, phone) | Medium |
| DQ-8 | Automation-inflated engagement | `campaign_type='Email' AND member_status='Sent'` ratio | High |
| DQ-9 | Structural contact blocks | Opted-out, bounced, DNC flags | Critical |
| DQ-10 | Qualification cycling | DQ→re-MQL pattern detection | Low |

## Audit Workflow

### Step 1: Profile the Dataset

```python
from src.pipeline.stages.clean import load_data, find_duplicate_emails, detect_etl_dates

accounts, leads, contacts, cm = load_data("./data/raw")

# Basic profiling
print(f"Records: {len(leads)} leads, {len(contacts)} contacts")
print(f"NULL rates:")
for col in ['title', 'job_persona', 'job_level', 'email']:
    null_rate = leads[col].isna().mean() * 100
    print(f"  {col}: {null_rate:.1f}%")
```

### Step 2: Run DQ Detection

Each detection function is independently callable:

```python
from src.pipeline.stages.clean import (
    flag_lead_exclusions,
    flag_contact_exclusions,
    find_duplicate_emails,
    detect_etl_dates,
    flag_lead_dq,
    flag_contact_dq,
    get_dnc_accounts,
)

# Exclusions
leads = flag_lead_exclusions(leads)
dnc = get_dnc_accounts(accounts)
contacts = flag_contact_exclusions(contacts, dnc)

# DQ flags
dup_emails = find_duplicate_emails(leads, contacts)
etl_dates = detect_etl_dates(leads["created_date"], threshold=20)
leads = flag_lead_dq(leads, dup_emails, etl_dates)
```

### Step 3: Generate Findings Report

Structure findings as:

```
## Finding: [DQ-ID] [Issue Name]

**Prevalence**: X records affected (Y% of population)
**Impact on scoring**: [How this biases or breaks the model]
**Detection confidence**: [High/Medium/Low]
**Recommended handling**: [Flag / Filter / Resolve / Exclude]
**Evidence**: [Query or metric that proves the issue]
```

### Step 4: Classify Impact

For each finding, classify along two axes:

1. **Scoring impact**: Does this bias the readiness score? (Distorts / Inflates / Deflates / Neutral)
2. **Operational impact**: Does this affect BDR workflow? (Wastes calls / Misses prospects / Legal risk / None)

## Key Principles

- **Flags over penalties**: DQ issues are overlays, not score deductions
- **Exclusions are orthogonal**: A record can be high-quality AND excluded (competitor with clean data)
- **Threshold awareness**: What's a "problem" depends on threshold — 5% duplication is noise, 30% is systemic
- **Entity-type sensitivity**: Leads and contacts have different expected completeness levels
- **Automation is not engagement**: Email sends without opens/clicks are not real human behavior

## Testing

```bash
python -m pytest tests/test_clean.py -v
```

All DQ detection functions have unit tests covering edge cases, empty inputs, and boundary conditions.
