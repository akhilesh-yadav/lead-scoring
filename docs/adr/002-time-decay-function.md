# ADR-002: Exponential Time-Decay Function

## Status
Accepted

## Context
Engagement recency is the strongest predictor of "call-worthiness right now." We need a decay function to weight recent engagement more heavily than historical.

Options considered:
1. Linear decay (score decreases uniformly over time)
2. Step function (full credit within 30 days, zero after)
3. Exponential decay with configurable half-life

## Decision
Use **exponential decay with a 45-day half-life**.

Formula: `recency_score = 100 × exp(-0.693 × days / 45)`

## Rationale
- **Exponential matches real-world intent decay**: A prospect who engaged yesterday is dramatically more likely to take a call than one who engaged 30 days ago. Linear decay doesn't capture this non-linearity.
- **45-day half-life matches B2B cybersecurity sales cycles**: Average deal cycle is 60-90 days. At 45 days (one half-life), a record is worth 50% — still visible but deprioritized. At 90 days (two half-lives), it's at 25%.
- **No cliff effects**: Unlike step functions, exponential decay provides a smooth gradient. There's no arbitrary "30-day cutoff" where records suddenly drop from 100% to 0%.
- **Configurable**: The half-life parameter can be adjusted per segment (e.g., 14 days for event follow-ups, 90 days for enterprise accounts).

## Consequences
- Records with no engagement score 0 on the recency component (days_since = 999 → ~0).
- Very old engagement (>180 days) contributes negligibly, which is intentional.
- The half-life may need tuning per segment once outcome data is available.
