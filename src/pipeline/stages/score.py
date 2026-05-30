"""
Layer 3: Component Scoring
Computes four independent score components and combines into a single readiness score.

Each scoring function takes a row (Series) and returns a float 0-100.
The final readiness_score is a weighted sum.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.pipeline.logging_config import logger


@dataclass(frozen=True)
class ScoringWeights:
    """Configurable weights for the composite score."""

    engagement: float = 0.40
    profile: float = 0.25
    account: float = 0.20
    momentum: float = 0.15

    def validate(self):
        total = self.engagement + self.profile + self.account + self.momentum
        assert abs(total - 1.0) < 0.001, f"Weights must sum to 1.0, got {total}"


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


DEFAULT_WEIGHTS = ScoringWeights()
DEFAULT_ENGAGEMENT_CONFIG = EngagementScoringConfig()


def score_engagement(
    row: pd.Series, config: EngagementScoringConfig = DEFAULT_ENGAGEMENT_CONFIG
) -> float:
    """Engagement recency score (0-100). Rewards recent real engagement, penalizes staleness.

    Uses exponential decay: score = 100 * exp(-ln2 * days / half_life)
    """
    days_since = row["days_since_last_engagement"]
    eng_30d = row["engagement_last_30d"]
    eng_90d = row["engagement_last_90d"]
    auto_ratio = row["automation_ratio"]
    diversity = row["campaign_type_diversity"]

    # Time-decay component
    if days_since >= 999:
        recency_score = 0.0
    else:
        recency_score = 100.0 * np.exp(-0.693 * days_since / config.half_life_days)

    # Volume component (diminishing returns via cap)
    volume_score = min(
        eng_30d * config.volume_weight_30d + eng_90d * config.volume_weight_90d, 100.0
    )

    # Diversity bonus
    diversity_bonus = min(diversity * config.diversity_bonus_per_type, config.diversity_cap)

    # Automation discount (DQ-8 handling)
    automation_penalty = auto_ratio * config.automation_penalty_factor

    # High-value engagement bonus
    high_value = (
        row["webinar_attendances"] * config.webinar_value
        + row["event_attendances"] * config.event_value
        + row["content_responses"] * config.content_value
    )
    high_value_bonus = min(high_value, config.high_value_cap)

    raw = (
        recency_score * config.recency_weight
        + volume_score * config.volume_weight
        + diversity_bonus
        + high_value_bonus
        - automation_penalty
    )
    return float(np.clip(raw, 0, 100))


def score_profile(row: pd.Series) -> float:
    """Profile fit score (0-100). ICP alignment based on seniority and persona."""
    level = row["level_score"]
    persona = row["persona_score"]
    has_title = row["has_title"]
    has_persona = row["has_persona"]

    base = level * 50 + persona * 50
    completeness_bonus = (has_title + has_persona) * 10
    return float(np.clip(base + completeness_bonus, 0, 100))


def score_account(row: pd.Series, lead_baseline: float = 15.0) -> float:
    """Account strength score (0-100). Named accounts and intent signals.

    Leads without account association get a baseline score (entity-type fairness).
    """
    if row["has_account"] == 0:
        return lead_baseline

    named = row["account_is_named"] * 30
    icp = row["account_is_icp"] * 25
    intent = row["account_intent"] * 30
    size = (row["account_employee_score"] + row["account_revenue_score"]) * 7.5
    return float(np.clip(named + icp + intent + size, 0, 100))


def score_momentum(row: pd.Series) -> float:
    """Behavioral momentum score (0-100). Is engagement accelerating?"""
    momentum = row["momentum_score"]
    is_accel = row["is_accelerating"]
    eng_30d = row["engagement_last_30d"]

    if eng_30d == 0:
        return 0.0

    base = min(momentum * 40, 80)
    accel_bonus = 20 if is_accel else 0
    return float(np.clip(base + accel_bonus, 0, 100))


def compute_scores(
    features_df: pd.DataFrame, weights: ScoringWeights = DEFAULT_WEIGHTS
) -> pd.DataFrame:
    """Compute all component scores and the weighted composite readiness score."""
    weights.validate()
    logger.info("Layer 3: Component scoring...")

    df = features_df.copy()
    df["score_engagement"] = df.apply(score_engagement, axis=1)
    df["score_profile"] = df.apply(score_profile, axis=1)
    df["score_account"] = df.apply(score_account, axis=1)
    df["score_momentum"] = df.apply(score_momentum, axis=1)

    df["readiness_score"] = (
        df["score_engagement"] * weights.engagement
        + df["score_profile"] * weights.profile
        + df["score_account"] * weights.account
        + df["score_momentum"] * weights.momentum
    ).round(1)

    logger.info(
        f"Score distribution: mean={df['readiness_score'].mean():.1f}, "
        f"median={df['readiness_score'].median():.1f}, "
        f"std={df['readiness_score'].std():.1f}"
    )
    return df
