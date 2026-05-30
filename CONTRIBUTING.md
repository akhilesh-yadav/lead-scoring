# Contributing Guide

## Development Setup

```bash
git clone <repo-url>
cd lead-scoring-poc
pip install -e ".[dev,notebook]"
pre-commit install
```

## Running the Project

```bash
make data      # Generate synthetic CRM data
make score     # Run scoring pipeline
make app       # Launch Streamlit at localhost:8501
make test      # Run all tests (73 tests)
make validate  # Tests + lint + type check
```

## How to Add a New Data Quality Check

1. **Add detection function** in `src/pipeline/stages/clean.py`:
   ```python
   def detect_my_issue(leads: pd.DataFrame) -> pd.DataFrame:
       leads = leads.copy()
       leads["dq_my_issue"] = <detection logic>
       return leads
   ```

2. **Call it from the orchestrator** in `clean_data()`:
   ```python
   leads = detect_my_issue(leads)
   ```

3. **Add tests** in `tests/test_clean.py`:
   ```python
   class TestMyIssue:
       def test_detects_positive_case(self, sample_leads):
           ...
       def test_negative_case(self, sample_leads):
           ...
   ```

4. **Document** in `knowledge-base/01-discovery-notes.md`

5. **Update** `skills/data-quality-auditor/SKILL.md`

## How to Add a New Scoring Component

1. **Create a scorer strategy** in `src/pipeline/scorers.py`:
   - Subclass `ScorerStrategy` with a `name` property and `score()` method
   - Return a float 0-100

   ```python
   class NewComponentScorer(ScorerStrategy):
       @property
       def name(self) -> str:
           return "score_new_component"

       def score(self, row: pd.Series) -> float:
           return float(np.clip(<logic>, 0, 100))
   ```

2. **Add feature computation** in `src/pipeline/stages/features.py`:
   - Create a dataclass (e.g., `NewFeatures`) with `.to_dict()` method
   - Add a `compute_new_features()` function that returns the dataclass
   - Call it from `engineer_features()` and include in the output row

3. **Register the scorer** in `src/pipeline/pipeline.py`:
   - Add to `ScoringPipeline.build()` scorers list
   - Update `ScoringWeights` to include the new dimension
   - **All weights must sum to 1.0** (validated at runtime)

4. **Add tests**:
   - `tests/test_features.py` — test the feature computation
   - `tests/test_score.py` — test the scoring function
   - Verify bounds (always 0-100), edge cases (empty/null inputs)

5. **Update the Streamlit app** (`src/app/main.py`):
   - Add to score breakdown chart in Record Inspector
   - Update Methodology page text

## How to Modify Tier Thresholds

Edit `.env` or pass CLI args:
```bash
python -m lead_scorer score --hot 80 --warm 55 --nurture 25
```

Or modify `config.py` defaults.

## Code Style

- Python 3.9+ compatible
- Type hints on all public functions
- Dataclasses for structured return values
- Functions should not mutate input DataFrames (use `.copy()`)
- All scores bounded 0-100 (use `np.clip()`)
- No circular imports between pipeline modules

## Testing Conventions

- Test files mirror source: `src/pipeline/stages/clean.py` → `tests/test_clean.py`
- Shared fixtures in `tests/conftest.py`
- Integration tests in `tests/test_integration.py`
- Tests must not depend on `data/raw/*.csv` (use fixtures)
- Run with: `python -m pytest tests/ -v`

## Commit Convention

```
feat: add momentum scoring component
fix: correct automation ratio calculation
docs: update methodology for new weights
test: add edge case for empty campaign members
refactor: extract time-decay into separate function
```

## Architecture Decision Records

Major design decisions are documented in `docs/adr/`. When making a significant architectural choice, add a new ADR following the template:

```markdown
# ADR-NNN: Title

## Status
Proposed | Accepted | Deprecated | Superseded

## Context
What is the issue?

## Decision
What did we decide?

## Rationale
Why this over alternatives?

## Consequences
What are the tradeoffs?
```
