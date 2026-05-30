"""
Layer 4: Final Ranking & Tiering
Assigns priority tiers and produces the final ranked output.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.pipeline.logging_config import logger


@dataclass(frozen=True)
class TierConfig:
    """Configurable tier thresholds (score ranges)."""

    hot_threshold: float = 70.0
    warm_threshold: float = 45.0
    nurture_threshold: float = 20.0

    def get_tier(self, score: float) -> str:
        if score >= self.hot_threshold:
            return "Hot"
        elif score >= self.warm_threshold:
            return "Warm"
        elif score >= self.nurture_threshold:
            return "Nurture"
        return "Cold"


DEFAULT_TIER_CONFIG = TierConfig()


def assign_tiers(scored_df: pd.DataFrame, config: TierConfig = DEFAULT_TIER_CONFIG) -> pd.DataFrame:
    """Assign priority tiers based on readiness score."""
    df = scored_df.copy()
    conditions = [
        df["readiness_score"] >= config.hot_threshold,
        df["readiness_score"] >= config.warm_threshold,
        df["readiness_score"] >= config.nurture_threshold,
    ]
    choices = ["Hot", "Warm", "Nurture"]
    df["tier"] = np.select(conditions, choices, default="Cold")
    return df


def merge_record_details(
    scored_df: pd.DataFrame,
    leads: pd.DataFrame,
    contacts: pd.DataFrame,
    accounts: pd.DataFrame,
) -> pd.DataFrame:
    """Merge back original record details for the demo UI."""
    lead_cols = [
        c
        for c in [
            "lead_id",
            "email",
            "first_name",
            "last_name",
            "title",
            "company",
            "lead_status",
            "lead_source",
            "job_persona",
            "job_level",
            "created_date",
            "mql_date",
            "is_converted",
            "mkto_lead_score",
            "is_excluded",
            "dq_issue_count",
            "exclude_competitor",
            "exclude_opted_out",
            "exclude_bounced",
            "exclude_non_prospect",
            "dq_broken_conversion",
            "dq_duplicate_email",
            "dq_mql_overwritten",
            "dq_etl_timestamp",
            "dq_incomplete",
        ]
        if c in leads.columns
    ]

    contact_cols = [
        c
        for c in [
            "contact_id",
            "account_id",
            "email",
            "first_name",
            "last_name",
            "title",
            "contact_status",
            "job_persona",
            "job_level",
            "created_date",
            "mql_date",
            "mkto_contact_score",
            "is_mql",
            "has_lead_origin",
            "no_longer_with_company",
            "is_excluded",
            "dq_issue_count",
            "exclude_opted_out",
            "exclude_no_longer",
            "exclude_non_prospect",
            "dq_duplicate_email",
            "dq_mql_overwritten",
            "dq_etl_timestamp",
            "dq_incomplete",
        ]
        if c in contacts.columns
    ]

    lead_records = leads[lead_cols].copy()
    lead_records["entity_id"] = lead_records["lead_id"]
    lead_records["entity_type"] = "lead"

    contact_records = contacts[contact_cols].copy()
    contact_records["entity_id"] = contact_records["contact_id"]
    contact_records["entity_type"] = "contact"

    if "account_id" in contact_records.columns:
        contact_records = contact_records.merge(
            accounts[
                ["account_id", "account_name", "industry", "is_named_account", "intent_score"]
            ],
            on="account_id",
            how="left",
        )

    all_records = pd.concat([lead_records, contact_records], ignore_index=True)
    result = scored_df.merge(all_records, on=["entity_id", "entity_type"], how="left")
    return result


def rank_and_tier(
    scored_df: pd.DataFrame,
    leads: pd.DataFrame,
    contacts: pd.DataFrame,
    accounts: pd.DataFrame,
    tier_config: TierConfig = DEFAULT_TIER_CONFIG,
) -> pd.DataFrame:
    """Main ranking orchestrator.

    Args:
        scored_df: Output from Layer 3 (scoring).
        leads: Cleaned leads from Layer 1.
        contacts: Cleaned contacts from Layer 1.
        accounts: Raw accounts table.
        tier_config: Configurable tier thresholds.

    Returns:
        Final ranked DataFrame with all details merged.
    """
    logger.info("Layer 4: Ranking & tiering...")

    scored_df = assign_tiers(scored_df, tier_config)
    result = merge_record_details(scored_df, leads, contacts, accounts)
    result = result.sort_values("readiness_score", ascending=False).reset_index(drop=True)
    result["rank"] = range(1, len(result) + 1)

    tier_counts = result["tier"].value_counts()
    logger.info(f"Tier distribution: {dict(tier_counts)}")
    logger.info(f"Excluded records: {result['is_excluded'].sum()}")

    return result
