"""
Pipeline Orchestrator
Backward-compatible entry point that delegates to the OOP ScoringPipeline.
"""

from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.pipeline.pipeline import PipelineConfig, ScoringPipeline, ScoringWeights
from src.pipeline.stages.rank import TierConfig

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")


def run_pipeline(
    data_dir: str = RAW_DIR,
    output_dir: str = PROCESSED_DIR,
    weights: ScoringWeights = ScoringWeights(),
    tier_config: TierConfig = TierConfig(),
) -> pd.DataFrame:
    """Run the full 4-layer scoring pipeline: Clean → Features → Score → Rank."""
    config = PipelineConfig(
        data_dir=data_dir,
        output_dir=output_dir,
        weights=weights,
        tier_config=tier_config,
    )
    pipeline = ScoringPipeline.build(config)
    return pipeline.execute()


if __name__ == "__main__":
    run_pipeline()
