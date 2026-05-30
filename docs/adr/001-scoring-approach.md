# ADR-001: Weighted Heuristic Formula Over ML Classifier

## Status
Accepted

## Context
We need a scoring model to rank CRM records by "call readiness." Options considered:
1. Machine learning classifier (logistic regression, gradient boosting)
2. Weighted heuristic formula (multi-component composite)
3. Single-dimension ranking (engagement only)
4. Rule-based decision tree

## Decision
Use a **weighted heuristic formula** with 4 independently computed components.

## Rationale
- **No labeled training data**: There is no reliable "converted" outcome signal to train against. The MQL flag is what we're replacing, so it can't serve as ground truth.
- **Explainability required**: The VP of Demand Gen needs to understand *why* each record scored the way it did. A random forest doesn't satisfy this.
- **Auditability**: Each component score is independently inspectable. Stakeholders can ask "why did engagement score 85?" and get a formula-level answer.
- **Tunability**: Weights and thresholds are configurable without retraining. Business priorities shift (e.g., "focus on named accounts this quarter") and the model adapts via config, not code.

## Consequences
- The model cannot learn non-obvious patterns from data.
- Component weights are based on domain judgment, not empirical optimization.
- Future improvement path: once outcome data exists, use it to calibrate weights rather than replace the approach entirely.
