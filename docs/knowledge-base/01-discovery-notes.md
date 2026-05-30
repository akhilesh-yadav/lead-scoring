# Discovery Notes

## Initial Exploration (Data Quality Landscape)

### What We Found

Exploring the Salesforce CRM data model for a B2B cybersecurity company revealed a classic pattern: **data accumulated over years with minimal governance**, leading to systematic quality degradation that undermines any scoring system built on top of it.

### Key Findings

1. **Entity Fragmentation**: The Lead-to-Contact conversion model creates a fundamental entity resolution problem. ~35% of leads are marked as converted, but ~20% of those have broken `converted_contact_id` links (DQ-1). This means engagement history is split across two records with no reliable join key.

2. **Temporal Unreliability**: Two independent timestamp issues compound each other:
   - `created_date` is dominated by ETL load times (80% of leads, 34% of contacts share bulk-load timestamps)
   - `mql_date` is overwritten on re-qualification, destroying first-touch attribution

3. **Engagement Inflation**: The CampaignMember table is ~60% noise for scoring purposes. Automated email sends ("Sent" status) outnumber real engagements by 3:1 in some cohorts. Without filtering, a drip campaign enrollee looks identical to a conference attendee.

4. **Non-Prospect Contamination**: ~8-13% of the database consists of competitors, partners, vendors, and other non-prospect personas. Only ~60% of records have the `job_persona` field populated, making automated identification incomplete.

5. **Score Field Asymmetry** (DQ-5): Leads use `mkto_lead_score` (0-300+ range, exponential distribution) while contacts use `mkto_contact_score` (different calibration). Naively comparing these values across entity types is invalid.

### Implications for Scoring

- Any model that uses `created_date` as a feature will be misled by ETL artifacts
- Raw engagement counts are meaningless without automation filtering
- The existing MQL flag cannot be used as a training signal (circular dependency risk)
- Entity-type fairness requires explicit handling: leads lack account context, contacts lack conversion history

## Data Quality Issue Catalogue

| ID | Issue | Prevalence | Impact on Scoring | Handling |
|----|-------|-----------|-------------------|----------|
| DQ-1 | Broken conversion links | ~20% of converted | Engagement split across entities | Attempt email-based resolution; flag unresolvable |
| DQ-2 | Email duplication | ~5-8% of records | Fragmented history | Flag for manual review; don't merge automatically |
| DQ-3 | MQL date overwrite | All re-MQLd records | Lost first-touch timing | Use campaign membership dates instead |
| DQ-4 | ETL creation timestamps | 80% leads, 34% contacts | Unreliable cohort analysis | Flag; use earliest campaign response as proxy |
| DQ-5 | Score field asymmetry | All records | Invalid cross-entity comparison | Normalize separately; don't use as input |
| DQ-6 | Non-prospect contamination | ~13% of records | Noise in ranked list | Orthogonal exclusion flag |
| DQ-7 | Data completeness gaps | 35-50% missing key fields | Profile scoring disadvantages newer records | Explicit completeness handling in model |
| DQ-8 | Automation inflation | ~60% of email CMs | Inflated engagement counts | Filter to `is_responded=True` for scoring |
| DQ-9 | Do-not-contact flags | ~5% of records | Legally uncontactable | Hard exclusion overlay |
| DQ-10 | DQ/re-MQL cycles | ~10% of records | Ambiguous intent signal | Track as "resilience" pattern, not penalty |

## Surprises

- **The MQL flag is nearly useless for prioritization.** Records that are MQL'd include stale re-fires (DQ-3), automation-inflated scores (DQ-8), and competitors (DQ-6). The VP of Demand Gen's instinct is correct: the signal-to-noise ratio is terrible.
- **Recency dominates everything.** When we plot conversion probability against engagement recency, the curve drops off a cliff after 30 days. A single webinar attendance this week is worth more than 50 historical touchpoints from last year.
- **Account-level signals are underutilized.** Named accounts with high intent scores have 3x higher conversion rates regardless of individual engagement. The current MQL system ignores this entirely.
