# ADR-004: Entity-Type Fairness (Lead Baseline Score)

## Status
Accepted

## Context
Leads and contacts have structural differences:
- Contacts always have an `account_id` → can receive account-level scoring (named, ICP, intent)
- Leads typically lack account associations → would score 0 on the account component (20% of total)

This creates systematic bias: contacts have a 20-point head start regardless of engagement.

Options considered:
1. Zero for missing accounts (strict meritocracy)
2. Impute account scores based on company name matching
3. Fixed baseline score for leads without accounts
4. Different weight distributions per entity type

## Decision
Give leads without account associations a **fixed baseline account score of 15/100** (instead of 0).

## Rationale
- **Fairness over accuracy**: A brand-new lead who filled out a form 5 minutes ago shouldn't be systematically disadvantaged because their company hasn't been matched to an account yet. That's a data engineering gap, not a prospect quality signal.
- **15 represents "unknown" not "poor"**: The baseline acknowledges that account quality is unknown, not that the account is bad. This is semantically correct — absence of data ≠ negative signal.
- **Simple and transparent**: A fixed baseline is easy to explain ("leads get a 15-point head start because we don't know their account yet") versus complex imputation logic.
- **Conservative**: 15/100 means leads still score lower on the account component than any contact at a named ICP account (which would score 55-100). The baseline doesn't overcompensate.

## Consequences
- Leads with genuine poor accounts (if we knew them) might be slightly overscored.
- The 15-point value is a judgment call — should be revisited with outcome data.
- Contacts at weak accounts (score < 15) are slightly disadvantaged vs leads — acceptable tradeoff.
