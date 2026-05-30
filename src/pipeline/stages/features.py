"""
Layer 2: Feature Engineering
Transforms raw CRM data into scoring-ready features.
Key dimensions: engagement recency, profile fit, account strength, behavioral momentum.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

import pandas as pd

from src.pipeline.logging_config import logger

DEFAULT_REFERENCE_DATE = datetime(2025, 5, 15)

LEVEL_SCORES = {
    "C-Level": 1.0, "VP": 0.85, "Director": 0.7,
    "Manager": 0.5, "Individual Contributor": 0.3, None: 0.2,
}
PERSONA_SCORES = {
    "CISO": 1.0, "Technical Buyer": 0.9, "Financial Buyer": 0.7,
    "IT Operations": 0.6, "Security Engineer": 0.5, None: 0.2, "Non-Prospect": 0.0,
}


@dataclass
class EngagementFeatures:
    total_engagements: int = 0
    real_engagements: int = 0
    engagement_last_30d: int = 0
    engagement_last_90d: int = 0
    engagement_last_180d: int = 0
    days_since_last_engagement: int = 999
    automation_ratio: float = 0.0
    campaign_type_diversity: int = 0
    webinar_attendances: int = 0
    event_attendances: int = 0
    content_responses: int = 0

    def to_dict(self) -> Dict:
        return self.__dict__


@dataclass
class ProfileFeatures:
    level_score: float = 0.2
    persona_score: float = 0.2
    has_title: int = 0
    has_persona: int = 0

    def to_dict(self) -> Dict:
        return self.__dict__


@dataclass
class AccountFeatures:
    account_is_icp: int = 0
    account_is_named: int = 0
    account_intent: float = 0.0
    account_employee_score: float = 0.0
    account_revenue_score: float = 0.0
    has_account: int = 0

    def to_dict(self) -> Dict:
        return self.__dict__


@dataclass
class MomentumFeatures:
    momentum_score: float = 0.0
    is_accelerating: bool = False

    def to_dict(self) -> Dict:
        return self.__dict__


def compute_engagement_features(
    entity_id: str,
    entity_type: str,
    campaign_members: pd.DataFrame,
    reference_date: datetime = DEFAULT_REFERENCE_DATE,
) -> EngagementFeatures:
    """Compute engagement features for a single entity from campaign member records."""
    cm = campaign_members[
        (campaign_members["entity_id"] == entity_id) &
        (campaign_members["entity_type"] == entity_type)
    ].copy()

    if len(cm) == 0:
        return EngagementFeatures()

    cm["response_date"] = pd.to_datetime(cm["response_date"])
    cm["days_ago"] = (reference_date - cm["response_date"]).dt.days

    real_cm = cm[cm["is_responded"]]
    auto_cm = cm[(cm["campaign_type"] == "Email") & (cm["member_status"] == "Sent")]

    days_since = int(real_cm["days_ago"].min()) if len(real_cm) > 0 else 999

    return EngagementFeatures(
        total_engagements=len(cm),
        real_engagements=len(real_cm),
        engagement_last_30d=int((real_cm["days_ago"] <= 30).sum()),
        engagement_last_90d=int((real_cm["days_ago"] <= 90).sum()),
        engagement_last_180d=int((real_cm["days_ago"] <= 180).sum()),
        days_since_last_engagement=days_since,
        automation_ratio=len(auto_cm) / max(len(cm), 1),
        campaign_type_diversity=cm["campaign_type"].nunique(),
        webinar_attendances=int(((cm["campaign_type"] == "Webinar") & (cm["member_status"] == "Attended")).sum()),
        event_attendances=int(((cm["campaign_type"] == "Event") & (cm["member_status"] == "Attended")).sum()),
        content_responses=int(((cm["campaign_type"] == "Content Syndication") & (cm["is_responded"])).sum()),
    )


def compute_profile_features(
    job_level: Optional[str],
    job_persona: Optional[str],
    title: Optional[str],
) -> ProfileFeatures:
    """Compute profile/ICP fit features from demographic fields."""
    return ProfileFeatures(
        level_score=LEVEL_SCORES.get(job_level, 0.2),
        persona_score=PERSONA_SCORES.get(job_persona, 0.2),
        has_title=1 if pd.notna(title) else 0,
        has_persona=1 if pd.notna(job_persona) and job_persona != "Non-Prospect" else 0,
    )


def compute_account_features(
    account_id: Optional[str],
    accounts_df: pd.DataFrame,
) -> AccountFeatures:
    """Compute account-level features. Returns defaults when account is absent."""
    if not account_id or pd.isna(account_id):
        return AccountFeatures()

    acct = accounts_df[accounts_df["account_id"] == account_id]
    if len(acct) == 0:
        return AccountFeatures()

    acct = acct.iloc[0]
    emp = acct.get("employee_count", 0) or 0
    rev = acct.get("annual_revenue", 0) or 0

    return AccountFeatures(
        account_is_icp=1 if acct.get("is_icp_qualified") else 0,
        account_is_named=1 if acct.get("is_named_account") else 0,
        account_intent=(acct.get("intent_score") or 0) / 100.0,
        account_employee_score=min(emp / 10000, 1.0),
        account_revenue_score=min(rev / 1e9, 1.0),
        has_account=1,
    )


def compute_momentum_features(
    entity_id: str,
    entity_type: str,
    campaign_members: pd.DataFrame,
    reference_date: datetime = DEFAULT_REFERENCE_DATE,
) -> MomentumFeatures:
    """Is engagement accelerating? Compares last-30-day vs prior-30-day volume."""
    cm = campaign_members[
        (campaign_members["entity_id"] == entity_id) &
        (campaign_members["entity_type"] == entity_type)
    ].copy()

    real_cm = cm[cm["is_responded"]].copy()
    if len(real_cm) < 2:
        return MomentumFeatures()

    real_cm["response_date"] = pd.to_datetime(real_cm["response_date"])
    real_cm["days_ago"] = (reference_date - real_cm["response_date"]).dt.days

    last_30 = int((real_cm["days_ago"] <= 30).sum())
    prev_30 = int(((real_cm["days_ago"] > 30) & (real_cm["days_ago"] <= 60)).sum())

    if prev_30 == 0:
        momentum = 1.0 if last_30 > 0 else 0.0
    else:
        momentum = min((last_30 - prev_30) / max(prev_30, 1), 2.0)

    return MomentumFeatures(
        momentum_score=max(momentum, 0),
        is_accelerating=last_30 > prev_30,
    )


def engineer_features(
    accounts: pd.DataFrame,
    leads: pd.DataFrame,
    contacts: pd.DataFrame,
    campaign_members: pd.DataFrame,
    reference_date: datetime = DEFAULT_REFERENCE_DATE,
) -> pd.DataFrame:
    """Compute feature vectors for all leads and contacts."""
    logger.info("Layer 2: Feature engineering...")

    all_features = []

    for _, lead in leads.iterrows():
        eng = compute_engagement_features(lead["lead_id"], "lead", campaign_members, reference_date)
        prof = compute_profile_features(lead.get("job_level"), lead.get("job_persona"), lead.get("title"))
        acct = AccountFeatures()
        mom = compute_momentum_features(lead["lead_id"], "lead", campaign_members, reference_date)
        all_features.append({
            **eng.to_dict(), **prof.to_dict(), **acct.to_dict(), **mom.to_dict(),
            "entity_id": lead["lead_id"], "entity_type": "lead",
        })

    for _, contact in contacts.iterrows():
        eng = compute_engagement_features(contact["contact_id"], "contact", campaign_members, reference_date)
        prof = compute_profile_features(contact.get("job_level"), contact.get("job_persona"), contact.get("title"))
        acct = compute_account_features(contact.get("account_id"), accounts)
        mom = compute_momentum_features(contact["contact_id"], "contact", campaign_members, reference_date)
        all_features.append({
            **eng.to_dict(), **prof.to_dict(), **acct.to_dict(), **mom.to_dict(),
            "entity_id": contact["contact_id"], "entity_type": "contact",
        })

    features_df = pd.DataFrame(all_features)
    logger.info(f"Engineered features for {len(features_df)} records")
    return features_df
