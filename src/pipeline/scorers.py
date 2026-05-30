"""
Scorer strategies implementing the Strategy Pattern.

Each scorer is a pluggable algorithm that computes one dimension of readiness.
The composite score is assembled by the ScoringEngine using weights.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import pandas as pd


class ScorerStrategy(ABC):
    """Interface for a single scoring dimension (Strategy Pattern)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Column name for this score component (e.g., 'score_engagement')."""
        ...

    @abstractmethod
    def score(self, row: pd.Series) -> float:
        """Compute a 0-100 score for a single record."""
        ...


@dataclass(frozen=True)
class EngagementScoringConfig:
    """Tunable parameters for engagement scoring."""
    half_life_days: float = 45.0
    volume_weight_30d: float = 20.0
    volume_weight_90d: float = 5.0
    diversity_bonus_per_type: float = 10.0
    diversity_cap: float = 30.0
    automation_penalty_factor: float = 30.0
    webinar_value: float = 15.0
    event_value: float = 20.0
    content_value: float = 10.0
    high_value_cap: float = 40.0
    recency_weight: float = 0.4
    volume_weight: float = 0.3


class EngagementScorer(ScorerStrategy):
    """Scores engagement recency using exponential decay + volume + diversity."""

    def __init__(self, config: EngagementScoringConfig | None = None):
        self._config = config or EngagementScoringConfig()

    @property
    def name(self) -> str:
        return "score_engagement"

    def score(self, row: pd.Series) -> float:
        cfg = self._config
        days_since = row["days_since_last_engagement"]

        if days_since >= 999:
            recency_score = 0.0
        else:
            recency_score = 100.0 * np.exp(-0.693 * days_since / cfg.half_life_days)

        volume_score = min(
            row["engagement_last_30d"] * cfg.volume_weight_30d +
            row["engagement_last_90d"] * cfg.volume_weight_90d,
            100.0,
        )

        diversity_bonus = min(
            row["campaign_type_diversity"] * cfg.diversity_bonus_per_type,
            cfg.diversity_cap,
        )

        automation_penalty = row["automation_ratio"] * cfg.automation_penalty_factor

        high_value = (
            row["webinar_attendances"] * cfg.webinar_value +
            row["event_attendances"] * cfg.event_value +
            row["content_responses"] * cfg.content_value
        )
        high_value_bonus = min(high_value, cfg.high_value_cap)

        raw = (
            recency_score * cfg.recency_weight +
            volume_score * cfg.volume_weight +
            diversity_bonus + high_value_bonus - automation_penalty
        )
        return float(np.clip(raw, 0, 100))


class ProfileScorer(ScorerStrategy):
    """Scores ICP profile fit based on job level and persona alignment."""

    @property
    def name(self) -> str:
        return "score_profile"

    def score(self, row: pd.Series) -> float:
        base = row["level_score"] * 50 + row["persona_score"] * 50
        completeness_bonus = (row["has_title"] + row["has_persona"]) * 10
        return float(np.clip(base + completeness_bonus, 0, 100))


class AccountScorer(ScorerStrategy):
    """Scores account strength: named accounts, ICP qualification, intent signals."""

    def __init__(self, lead_baseline: float = 15.0):
        self._lead_baseline = lead_baseline

    @property
    def name(self) -> str:
        return "score_account"

    def score(self, row: pd.Series) -> float:
        if row["has_account"] == 0:
            return self._lead_baseline

        named = row["account_is_named"] * 30
        icp = row["account_is_icp"] * 25
        intent = row["account_intent"] * 30
        size = (row["account_employee_score"] + row["account_revenue_score"]) * 7.5
        return float(np.clip(named + icp + intent + size, 0, 100))


class MomentumScorer(ScorerStrategy):
    """Scores behavioral momentum: is engagement accelerating?"""

    @property
    def name(self) -> str:
        return "score_momentum"

    def score(self, row: pd.Series) -> float:
        if row["engagement_last_30d"] == 0:
            return 0.0

        base = min(row["momentum_score"] * 40, 80)
        accel_bonus = 20 if row["is_accelerating"] else 0
        return float(np.clip(base + accel_bonus, 0, 100))
