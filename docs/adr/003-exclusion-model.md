# ADR-003: Orthogonal Exclusion Model

## Status
Accepted

## Context
Some records are structurally unprioritizable: competitors, opted-out contacts, bounced emails, DNC accounts. How should these be handled in the scoring model?

Options considered:
1. Score penalties (subtract points for exclusion flags)
2. Score multiplication (multiply by 0 if excluded)
3. Orthogonal flags (exclusions are independent of score)

## Decision
Use **orthogonal exclusion flags** that exist independently of the readiness score.

## Rationale
- **Separation of concerns**: "Is this person ready?" and "Can we legally/practically contact them?" are different questions. Mixing them creates ambiguity: is a score of 30 a weak prospect or a strong competitor?
- **Analytical value**: A competitor who attends all our webinars *should* score 90 on engagement — that's correct and useful information. The insight is that they're highly engaged with our content (competitive intelligence). The fix is removing them from the callable pool, not pretending they're unengaged.
- **Reversibility**: Exclusion flags can be lifted (e.g., a person leaves a competitor and joins a prospect company). When the flag is removed, their score is immediately accurate — no need to recalculate or wait for decay.
- **Transparency**: BDRs can see *why* a record was excluded (opted out? competitor? DNC?) rather than just seeing a low score and wondering why.

## Consequences
- Excluded records still consume scoring compute (they get scored, then filtered).
- UI must show exclusion flags clearly to prevent confusion.
- Reports on "Top 500" must filter exclusions, not just sort by score.
