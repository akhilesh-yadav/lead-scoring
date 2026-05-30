---
name: scoring-pipeline
description: Configurable 4-layer readiness scoring pipeline for B2B CRM records. Transforms raw lead/contact data into ranked prioritization lists with explainable scores. Supports custom weights, tier thresholds, and decay parameters. Use when user says "run scoring", "configure scoring model", "change scoring weights", "adjust tier thresholds", or needs to understand/modify the prioritization logic.
---

# Scoring Pipeline

## Quick Start

```bash
python pipeline/run_pipeline.py
# Reads: output/*.csv → Produces: output/scored_records.csv
```

## Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  L1: CLEAN  │───→│ L2: FEATURES│───→│  L3: SCORE  │───→│  L4: RANK   │
│             │    │             │    │             │    │             │
│ Exclusions  │    │ Engagement  │    │ 4 component │    │ Tier assign │
│ DQ flags    │    │ Profile     │    │ scores 0-100│    │ Merge detail│
│ Resolution  │    │ Account     │    │ Weighted    │    │ Sort & rank │
│             │    │ Momentum    │    │ composite   │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

## Configuration

### Scoring Weights

```python
from src.pipeline.stages.score import ScoringWeights, compute_scores

# Default: engagement-dominant for "call readiness"
weights = ScoringWeights(
    engagement=0.40,  # Time-decayed engagement recency
    profile=0.25,     # ICP fit (title, seniority, persona)
    account=0.20,     # Company-level signals
    momentum=0.15,    # Engagement acceleration
)

scored = compute_scores(features_df, weights)
```

### Engagement Decay

```python
from src.pipeline.stages.score import EngagementScoringConfig

config = EngagementScoringConfig(
    half_life_days=45.0,           # Days until engagement worth 50%
    volume_weight_30d=20.0,        # Points per engagement in last 30d
    volume_weight_90d=5.0,         # Points per engagement in last 90d
    automation_penalty_factor=30.0, # Penalty multiplied by automation_ratio
    webinar_value=15.0,            # Bonus per webinar attendance
    event_value=20.0,              # Bonus per event attendance
    content_value=10.0,            # Bonus per content download
)
```

### Tier Thresholds

```python
from src.pipeline.stages.rank import TierConfig, rank_and_tier

tiers = TierConfig(
    hot_threshold=70.0,     # 70+ = call this week
    warm_threshold=45.0,    # 45-69 = prioritize outreach
    nurture_threshold=20.0, # 20-44 = marketing nurture
    # Below 20 = Cold
)

final = rank_and_tier(scored_df, leads, contacts, accounts, tiers)
```

## Component Scoring Functions

Each function takes a pandas Series (row) and returns a float 0-100:

### `score_engagement(row)` — 40% weight
- Exponential time-decay: `100 × e^(-ln2 × days / half_life)`
- Volume bonus (capped at 100)
- Campaign diversity bonus (capped at 30)
- High-value engagement bonus (webinars, events, content)
- Automation penalty (DQ-8 discount)

### `score_profile(row)` — 25% weight
- Level score (C-Level=1.0, VP=0.85, Director=0.7, Manager=0.5, IC=0.3)
- Persona score (CISO=1.0, Technical Buyer=0.9, Financial=0.7)
- Completeness bonus (+10 for title, +10 for persona)

### `score_account(row)` — 20% weight
- Named account: +30
- ICP qualified: +25
- Intent score: up to +30
- Company size: up to +15
- Lead baseline (no account): 15 (entity-type fairness)

### `score_momentum(row)` — 15% weight
- Compares last-30d vs prior-30d engagement volume
- Acceleration bonus: +20 if increasing
- Zero if no recent engagement

## Design Principles

1. **No circular dependency**: MQL status is never an input to scoring
2. **Recency > volume**: A single fresh engagement beats 50 old ones
3. **Orthogonal exclusions**: Exclusions are flags, not score penalties
4. **Entity-type fairness**: Leads get baseline account score (don't penalize missing data)
5. **Automation discounting**: Only real human actions count as engagement
6. **Configurable everything**: Weights, thresholds, decay curves are all parameters

## Testing

```bash
python -m pytest tests/test_score.py tests/test_features.py tests/test_rank.py -v
```

Key test categories:
- Boundary conditions (score always 0-100)
- Time-decay correctness (half-life verification)
- Entity-type fairness (leads vs contacts)
- Weight validation (must sum to 1.0)
- Immutability (input DataFrames not mutated)

## Programmatic Usage

```python
from src.pipeline.stages.clean import clean_data
from src.pipeline.stages.features import engineer_features
from src.pipeline.stages.score import compute_scores, ScoringWeights
from src.pipeline.stages.rank import rank_and_tier, TierConfig

# Run layer by layer (inspect intermediate results)
result = clean_data("./data/raw")
features = engineer_features(result.accounts, result.leads, result.contacts, result.campaign_members)
scored = compute_scores(features, ScoringWeights(engagement=0.5, profile=0.2, account=0.2, momentum=0.1))
final = rank_and_tier(scored, result.leads, result.contacts, result.accounts)
```
