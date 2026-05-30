# Agent Instructions

This project is a B2B lead/contact scoring proof-of-concept. It implements a configurable 4-layer pipeline that transforms raw CRM data into ranked prioritization lists.

## Project Structure

```
lead-scoring-poc/
├── src/pipeline/stages/     # Core pipeline: clean → features → score → rank
├── src/app/main.py          # Streamlit dashboard
├── scripts/generate_data.py # Synthetic CRM data generator
├── data/raw/                # Input CSVs (Salesforce object model)
├── data/processed/          # Scored output
├── tests/                   # pytest suite
├── notebooks/               # Exploration and walkthrough
└── skills/                  # Detailed skill documentation (see below)
```

## Available Skills

Each skill below has a full SKILL.md with usage, API, and design principles.

### scoring-pipeline

Configurable 4-layer readiness scoring pipeline for B2B CRM records. Transforms raw lead/contact data into ranked prioritization lists with explainable scores. Supports custom weights, tier thresholds, and decay parameters.

**Triggers**: "run scoring", "configure scoring model", "change scoring weights", "adjust tier thresholds"

**Reference**: [skills/scoring-pipeline/SKILL.md](skills/scoring-pipeline/SKILL.md)

### data-quality-auditor

Audits CRM/Salesforce data for quality issues across 10 standard DQ categories (broken links, duplication, temporal anomalies, contamination, completeness gaps, automation inflation). Produces structured findings reports with prevalence, impact, and recommended handling.

**Triggers**: "audit data quality", "check DQ issues", "find data problems", "CRM data profiling"

**Reference**: [skills/data-quality-auditor/SKILL.md](skills/data-quality-auditor/SKILL.md)

### synthetic-data-generator

Generates realistic synthetic CRM data (Salesforce object model) with configurable data quality issues, engagement distributions, and persona archetypes. Produces leads, contacts, accounts, and campaign members CSVs.

**Triggers**: "generate synthetic data", "create test CRM data", "simulate Salesforce records"

**Reference**: [skills/synthetic-data-generator/SKILL.md](skills/synthetic-data-generator/SKILL.md)

### clean-code

Mandatory working rules for this repository based on Clean Code by Robert C. Martin. Covers naming, function design, error handling, testing, refactoring, and code review standards.

**Triggers**: Always active for code changes. "review code quality", "apply clean code"

**Reference**: [skills/clean-code/SKILL.md](skills/clean-code/SKILL.md)

## Key Design Principles

1. **No circular dependency** — MQL status is never an input to scoring
2. **Recency > volume** — A single fresh engagement beats 50 old ones
3. **Orthogonal exclusions** — Exclusions are flags, not score penalties
4. **Entity-type fairness** — Leads get baseline account score (don't penalize missing data)
5. **Automation discounting** — Only real human actions count as engagement
6. **Configurable everything** — Weights, thresholds, decay curves are all parameters

## Running the Project

```bash
# Generate synthetic data
python scripts/generate_data.py

# Run the scoring pipeline
python pipeline/run_pipeline.py

# Run the Streamlit dashboard
streamlit run src/app/main.py

# Run tests
python -m pytest tests/ -v
```
