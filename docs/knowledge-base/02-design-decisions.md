# Design Decisions

## Scoring Architecture

### Decision: Four-Component Weighted Model

**Chosen approach**: Weighted composite of four independent scoring dimensions:
1. Engagement Recency (40%) — time-decayed engagement signals
2. Profile Fit (25%) — ICP alignment via title/seniority/persona
3. Account Strength (20%) — named account, intent data, firmographics
4. Behavioral Momentum (15%) — acceleration in recent engagement

**Alternatives considered**:
- **ML classifier (logistic regression / gradient boosting)**: Rejected because (a) no labeled outcome data (no "converted" signal to train against), (b) would create a black box that contradicts the explainability requirement, (c) limited data makes overfitting likely.
- **Single-dimension ranking (engagement only)**: Too simplistic. A junior analyst with many webinar views shouldn't outrank a CISO at a target account with 2 recent touches.
- **Rule-based heuristic**: Too brittle. Hard thresholds create cliff effects and don't scale.
- **Equal weighting**: Engagement recency is empirically the strongest predictor of "call-worthiness right now." Profile and account are modifiers, not primary signals.

### Decision: Orthogonal Exclusion Flags

**Chosen approach**: Structural exclusions (competitor, opted-out, bounced, DNC) are overlay flags that exist independently of the readiness score.

**Rationale**: A competitor who attends all our webinars might score 90/100 on engagement — and that's *correct*. The problem isn't the score; it's that the record shouldn't be in the callable pool. Mixing exclusions into the score creates ambiguity: is a 30/100 a weak prospect or a strong competitor?

### Decision: Time-Decay Function

**Chosen approach**: Exponential decay with 45-day half-life.

`recency_score = 100 * exp(-0.693 * days_since_last / 45)`

This means:
- Last engagement today: 100
- 45 days ago: 50
- 90 days ago: 25
- 180 days ago: ~6

**Why 45 days**: B2B sales cycles in cybersecurity average 60-90 days. A 45-day half-life means a record that hasn't engaged in one full sales cycle is worth 25% of a fresh one — still visible but deprioritized.

### Decision: Automation Discounting (DQ-8)

**Chosen approach**: Filter to `is_responded=True` for all engagement scoring. Apply an explicit penalty proportional to the automation ratio.

**Rationale**: A record with 40 campaign memberships where 38 are automated email sends (status="Sent") is not highly engaged — they're on a drip list. Only real human actions (attended, clicked, downloaded, responded) count as engagement signals.

### Decision: Entity-Type Fairness

**Chosen approach**: Leads receive a baseline account score of 15/100 (instead of 0) because they structurally lack account associations.

**Rationale**: Leads are newer and sparser by nature. Scoring account strength as 0 for all leads would systematically push them to the bottom regardless of engagement. The 15-point baseline represents "unknown account quality" rather than "no account quality."

## Technology Choices

| Choice | Why |
|--------|-----|
| Streamlit for demo | Fast to build, interactive, supports both data exploration and narrative. The VP of Demand Gen can use it without training. |
| Python pipeline (no ML framework) | The scoring model is fundamentally a weighted formula, not a trained model. pandas + numpy is the right level of complexity. |
| Layered pipeline architecture | Each layer is independently testable and inspectable. You can examine the output of Layer 2 (features) without running Layer 3 (scoring). |
| CSV outputs between stages | Simple, debuggable, portable. No database required for 1000 records. |

## Scope Decisions

### What we cut:
- **NLP on job titles**: Title normalization is a real problem but adds complexity without changing the top-500 ranking significantly.
- **Cross-entity engagement merging**: When DQ-1 entities are resolved, we could merge engagement histories. Cut because the resolution rate is low and incorrect merges are worse than missed merges.
- **Predictive modeling**: No outcome variable to train against. The scoring model is descriptive/heuristic, not predictive.
- **Real-time scoring**: This is a batch system. Real-time would require infrastructure that doesn't serve the POC.

### What we kept despite complexity:
- **Momentum scoring**: Acceleration is the strongest "call them NOW" signal. Worth the additional computation.
- **Full DQ flagging**: Every data quality issue is surfaced, even when we can't fix it. Transparency > convenience.
