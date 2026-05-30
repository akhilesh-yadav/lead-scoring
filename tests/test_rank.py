"""Tests for Layer 4: Ranking & Tiering."""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.pipeline.stages.rank import TierConfig, assign_tiers


class TestTierConfig:
    def test_hot_tier(self):
        config = TierConfig()
        assert config.get_tier(85.0) == "Hot"
        assert config.get_tier(70.0) == "Hot"

    def test_warm_tier(self):
        config = TierConfig()
        assert config.get_tier(60.0) == "Warm"
        assert config.get_tier(45.0) == "Warm"

    def test_nurture_tier(self):
        config = TierConfig()
        assert config.get_tier(30.0) == "Nurture"
        assert config.get_tier(20.0) == "Nurture"

    def test_cold_tier(self):
        config = TierConfig()
        assert config.get_tier(10.0) == "Cold"
        assert config.get_tier(0.0) == "Cold"

    def test_custom_thresholds(self):
        config = TierConfig(hot_threshold=90, warm_threshold=60, nurture_threshold=30)
        assert config.get_tier(80.0) == "Warm"
        assert config.get_tier(25.0) == "Cold"


class TestAssignTiers:
    def test_assigns_correct_tiers(self):
        df = pd.DataFrame({"readiness_score": [95, 75, 50, 30, 10]})
        result = assign_tiers(df)
        assert list(result["tier"]) == ["Hot", "Hot", "Warm", "Nurture", "Cold"]

    def test_does_not_mutate_input(self):
        df = pd.DataFrame({"readiness_score": [50, 30]})
        original_cols = set(df.columns)
        assign_tiers(df)
        assert set(df.columns) == original_cols

    def test_boundary_values(self):
        config = TierConfig(hot_threshold=70, warm_threshold=45, nurture_threshold=20)
        df = pd.DataFrame({"readiness_score": [70.0, 69.9, 45.0, 44.9, 20.0, 19.9]})
        result = assign_tiers(df, config)
        expected = ["Hot", "Warm", "Warm", "Nurture", "Nurture", "Cold"]
        assert list(result["tier"]) == expected
