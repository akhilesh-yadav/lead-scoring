"""
Integration test: runs the full pipeline end-to-end on a small dataset.
Verifies that all layers compose correctly and produce valid output.
"""

import os
import sys
import tempfile

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture
def mini_pipeline_dir(sample_accounts, sample_leads, sample_contacts, sample_campaign_members):
    """Create a temporary directory with mini CSVs for pipeline testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sample_accounts.to_csv(os.path.join(tmpdir, "accounts.csv"), index=False)
        sample_leads.to_csv(os.path.join(tmpdir, "leads.csv"), index=False)
        sample_contacts.to_csv(os.path.join(tmpdir, "contacts.csv"), index=False)
        sample_campaign_members.to_csv(os.path.join(tmpdir, "campaign_members.csv"), index=False)
        yield tmpdir


class TestFullPipeline:
    def test_pipeline_produces_scored_output(self, mini_pipeline_dir):
        from src.pipeline.run_pipeline import run_pipeline

        result = run_pipeline(data_dir=mini_pipeline_dir, output_dir=mini_pipeline_dir)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 5  # 3 leads + 2 contacts
        assert "readiness_score" in result.columns
        assert "tier" in result.columns
        assert "rank" in result.columns

    def test_scores_are_bounded(self, mini_pipeline_dir):
        from src.pipeline.run_pipeline import run_pipeline

        result = run_pipeline(data_dir=mini_pipeline_dir, output_dir=mini_pipeline_dir)

        assert result["readiness_score"].min() >= 0
        assert result["readiness_score"].max() <= 100

    def test_all_tiers_valid(self, mini_pipeline_dir):
        from src.pipeline.run_pipeline import run_pipeline

        result = run_pipeline(data_dir=mini_pipeline_dir, output_dir=mini_pipeline_dir)
        valid_tiers = {"Hot", "Warm", "Nurture", "Cold"}

        assert set(result["tier"].unique()).issubset(valid_tiers)

    def test_exclusions_flagged(self, mini_pipeline_dir):
        from src.pipeline.run_pipeline import run_pipeline

        result = run_pipeline(data_dir=mini_pipeline_dir, output_dir=mini_pipeline_dir)

        excluded = result[result["is_excluded"]]
        assert len(excluded) >= 2

    def test_ranking_is_monotonic(self, mini_pipeline_dir):
        from src.pipeline.run_pipeline import run_pipeline

        result = run_pipeline(data_dir=mini_pipeline_dir, output_dir=mini_pipeline_dir)

        scores = result["readiness_score"].tolist()
        assert scores == sorted(scores, reverse=True)

    def test_custom_weights(self, mini_pipeline_dir):
        from src.pipeline.pipeline import ScoringWeights
        from src.pipeline.run_pipeline import run_pipeline

        weights = ScoringWeights(engagement=0.6, profile=0.15, account=0.15, momentum=0.1)
        result = run_pipeline(
            data_dir=mini_pipeline_dir, output_dir=mini_pipeline_dir, weights=weights
        )

        assert len(result) == 5
        assert result["readiness_score"].notna().all()

    def test_custom_tier_config(self, mini_pipeline_dir):
        from src.pipeline.run_pipeline import run_pipeline
        from src.pipeline.stages.rank import TierConfig

        config = TierConfig(hot_threshold=90, warm_threshold=60, nurture_threshold=30)
        result = run_pipeline(
            data_dir=mini_pipeline_dir, output_dir=mini_pipeline_dir, tier_config=config
        )

        assert len(result) == 5

    def test_output_csv_written(self, mini_pipeline_dir):
        from src.pipeline.run_pipeline import run_pipeline

        run_pipeline(data_dir=mini_pipeline_dir, output_dir=mini_pipeline_dir)

        assert os.path.exists(os.path.join(mini_pipeline_dir, "scored_records.csv"))
