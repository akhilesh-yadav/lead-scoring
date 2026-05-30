"""
ScoringPipeline — Composite pipeline orchestrator (Pipeline + Builder pattern).

Composes PipelineStages into a configurable, reusable pipeline object.
Supports adding/removing stages and swapping scorer strategies at runtime.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List

import pandas as pd

from src.pipeline.base import PipelineStage, StageResult
from src.pipeline.logging_config import logger
from src.pipeline.scorers import (
    AccountScorer,
    EngagementScorer,
    EngagementScoringConfig,
    MomentumScorer,
    ProfileScorer,
    ScorerStrategy,
)
from src.pipeline.stages.clean import CleaningResult, clean_data
from src.pipeline.stages.features import engineer_features
from src.pipeline.stages.rank import TierConfig, assign_tiers, merge_record_details


@dataclass(frozen=True)
class ScoringWeights:
    """Configurable weights for the composite score. Must sum to 1.0."""
    engagement: float = 0.40
    profile: float = 0.25
    account: float = 0.20
    momentum: float = 0.15

    def validate(self):
        total = self.engagement + self.profile + self.account + self.momentum
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Weights must sum to 1.0, got {total}")

    def as_dict(self) -> dict:
        return {
            "score_engagement": self.engagement,
            "score_profile": self.profile,
            "score_account": self.account,
            "score_momentum": self.momentum,
        }


# ─── Concrete Pipeline Stages ────────────────────────────────────────────────


class CleaningStage(PipelineStage):
    """Layer 1: Data loading, exclusion flags, DQ detection, entity resolution."""

    def __init__(self, data_dir: str):
        self._data_dir = data_dir

    @property
    def stage_name(self) -> str:
        return "Layer 1: Cleaning"

    def _validate_input(self, input_data) -> None:
        if not os.path.isdir(self._data_dir):
            raise ValueError(f"Data directory not found: {self._data_dir}")

    def _execute(self, input_data) -> StageResult:
        result = clean_data(self._data_dir)
        return StageResult(
            data=result,
            metrics=result.resolution_stats,
            stage_name=self.stage_name,
        )


class FeatureEngineeringStage(PipelineStage):
    """Layer 2: Transforms raw CRM data into scoring-ready feature vectors."""

    @property
    def stage_name(self) -> str:
        return "Layer 2: Feature Engineering"

    def _validate_input(self, input_data: CleaningResult) -> None:
        if not isinstance(input_data, CleaningResult):
            raise ValueError("FeatureEngineeringStage requires CleaningResult input")

    def _execute(self, input_data: CleaningResult) -> StageResult:
        features_df = engineer_features(
            input_data.accounts,
            input_data.leads,
            input_data.contacts,
            input_data.campaign_members,
        )
        return StageResult(
            data=features_df,
            metrics={"records": len(features_df), "features": len(features_df.columns)},
            stage_name=self.stage_name,
        )


class ScoringStage(PipelineStage):
    """Layer 3: Applies scorer strategies and computes weighted composite score."""

    def __init__(
        self,
        scorers: List[ScorerStrategy] | None = None,
        weights: ScoringWeights | None = None,
    ):
        self._weights = weights or ScoringWeights()
        self._weights.validate()
        self._scorers = scorers or [
            EngagementScorer(),
            ProfileScorer(),
            AccountScorer(),
            MomentumScorer(),
        ]

    @property
    def stage_name(self) -> str:
        return "Layer 3: Scoring"

    @property
    def scorers(self) -> List[ScorerStrategy]:
        return self._scorers

    def add_scorer(self, scorer: ScorerStrategy) -> None:
        self._scorers.append(scorer)

    def replace_scorer(self, name: str, scorer: ScorerStrategy) -> None:
        """Replace an existing scorer by name."""
        self._scorers = [s if s.name != name else scorer for s in self._scorers]

    def _validate_input(self, input_data: pd.DataFrame) -> None:
        if not isinstance(input_data, pd.DataFrame):
            raise ValueError("ScoringStage requires a DataFrame input")

    def _execute(self, input_data: pd.DataFrame) -> StageResult:
        df = input_data.copy()
        weight_map = self._weights.as_dict()

        for scorer in self._scorers:
            df[scorer.name] = df.apply(scorer.score, axis=1)

        df["readiness_score"] = sum(
            df[scorer.name] * weight_map.get(scorer.name, 0)
            for scorer in self._scorers
        ).round(1)

        return StageResult(
            data=df,
            metrics={
                "mean_score": round(df["readiness_score"].mean(), 1),
                "median_score": round(df["readiness_score"].median(), 1),
            },
            stage_name=self.stage_name,
        )


class RankingStage(PipelineStage):
    """Layer 4: Assigns tiers, merges record details, produces final ranked output."""

    def __init__(self, tier_config: TierConfig | None = None):
        self._tier_config = tier_config or TierConfig()

    @property
    def stage_name(self) -> str:
        return "Layer 4: Ranking"

    def _validate_input(self, input_data: dict) -> None:
        required = {"scored_df", "leads", "contacts", "accounts"}
        if not required.issubset(input_data.keys()):
            raise ValueError(f"RankingStage requires keys: {required}")

    def _execute(self, input_data: dict) -> StageResult:
        scored_df = assign_tiers(input_data["scored_df"], self._tier_config)
        result = merge_record_details(
            scored_df, input_data["leads"], input_data["contacts"], input_data["accounts"]
        )
        result = result.sort_values("readiness_score", ascending=False).reset_index(drop=True)
        result["rank"] = range(1, len(result) + 1)

        tier_counts = dict(result["tier"].value_counts())
        return StageResult(
            data=result,
            metrics={"tiers": tier_counts, "total": len(result)},
            stage_name=self.stage_name,
        )


# ─── Pipeline Orchestrator ────────────────────────────────────────────────────


@dataclass
class PipelineConfig:
    """All configuration for a scoring pipeline run."""
    data_dir: str = ""
    output_dir: str = ""
    weights: ScoringWeights = field(default_factory=ScoringWeights)
    tier_config: TierConfig = field(default_factory=TierConfig)
    engagement_config: EngagementScoringConfig = field(default_factory=EngagementScoringConfig)


class ScoringPipeline:
    """Configurable pipeline that chains stages together (Composite pattern).

    Usage:
        pipeline = ScoringPipeline.build(PipelineConfig(data_dir="./data/raw"))
        result = pipeline.execute()

    Or customize individual stages:
        pipeline = ScoringPipeline.build(config)
        pipeline.scoring_stage.replace_scorer("score_engagement", CustomEngagementScorer())
        result = pipeline.execute()
    """

    def __init__(
        self,
        cleaning: CleaningStage,
        features: FeatureEngineeringStage,
        scoring: ScoringStage,
        ranking: RankingStage,
        output_dir: str = "",
    ):
        self._cleaning = cleaning
        self._features = features
        self._scoring = scoring
        self._ranking = ranking
        self._output_dir = output_dir

    @property
    def scoring_stage(self) -> ScoringStage:
        """Access scoring stage to swap strategies at runtime."""
        return self._scoring

    @classmethod
    def build(cls, config: PipelineConfig) -> ScoringPipeline:
        """Factory method: construct a pipeline from configuration."""
        scorers = [
            EngagementScorer(config.engagement_config),
            ProfileScorer(),
            AccountScorer(),
            MomentumScorer(),
        ]
        return cls(
            cleaning=CleaningStage(config.data_dir),
            features=FeatureEngineeringStage(),
            scoring=ScoringStage(scorers=scorers, weights=config.weights),
            ranking=RankingStage(config.tier_config),
            output_dir=config.output_dir,
        )

    def execute(self) -> pd.DataFrame:
        """Run the full pipeline: Clean → Features → Score → Rank → Output."""
        logger.info("Pipeline started")

        clean_result = self._cleaning.run(None)
        cleaning_data: CleaningResult = clean_result.data

        features_result = self._features.run(cleaning_data)
        features_df: pd.DataFrame = features_result.data

        scoring_result = self._scoring.run(features_df)
        scored_df: pd.DataFrame = scoring_result.data

        ranking_input = {
            "scored_df": scored_df,
            "leads": cleaning_data.leads,
            "contacts": cleaning_data.contacts,
            "accounts": cleaning_data.accounts,
        }
        ranking_result = self._ranking.run(ranking_input)
        final_df: pd.DataFrame = ranking_result.data

        if self._output_dir:
            os.makedirs(self._output_dir, exist_ok=True)
            output_path = os.path.join(self._output_dir, "scored_records.csv")
            final_df.to_csv(output_path, index=False)
            logger.info(f"Pipeline complete: {len(final_df)} records → {output_path}")

        return final_df
