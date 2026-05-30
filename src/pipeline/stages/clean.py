"""
Layer 1: Data Cleaning & Entity Resolution
Handles DQ-1 (broken links), DQ-2 (email dupes), DQ-4 (ETL timestamps),
DQ-6 (non-prospects), DQ-9 (do-not-contact).
"""
from dataclasses import dataclass
from typing import Set, Tuple

import pandas as pd

from src.pipeline.logging_config import logger

COMPETITOR_COMPANIES = frozenset([
    "CrowdStrike", "Palo Alto Networks", "Fortinet", "SentinelOne",
    "Zscaler", "Okta", "CyberArk", "Varonis", "Rapid7", "Qualys",
])


@dataclass
class CleaningResult:
    """Output container for the cleaning layer."""
    accounts: pd.DataFrame
    leads: pd.DataFrame
    contacts: pd.DataFrame
    campaign_members: pd.DataFrame
    resolution_stats: dict


def load_data(output_dir: str) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load raw CSV data from output directory."""
    accounts = pd.read_csv(f"{output_dir}/accounts.csv")
    leads = pd.read_csv(f"{output_dir}/leads.csv")
    contacts = pd.read_csv(f"{output_dir}/contacts.csv")
    campaign_members = pd.read_csv(f"{output_dir}/campaign_members.csv")
    return accounts, leads, contacts, campaign_members


def get_dnc_accounts(accounts: pd.DataFrame) -> Set[str]:
    """Extract set of account_ids with do_not_contact flag."""
    return set(accounts[accounts["do_not_contact"]]["account_id"])


def flag_lead_exclusions(leads: pd.DataFrame, competitors: frozenset = COMPETITOR_COMPANIES) -> pd.DataFrame:
    """Flag leads that are structurally unprioritizable (orthogonal to score)."""
    leads = leads.copy()
    leads["exclude_opted_out"] = leads["has_opted_out"].fillna(False).astype(bool)
    leads["exclude_bounced"] = leads["email_bounced"].fillna(False).astype(bool)
    leads["exclude_competitor"] = leads["company"].isin(competitors)
    leads["exclude_non_prospect"] = leads["job_persona"] == "Non-Prospect"
    leads["exclude_disqualified"] = leads["is_disqualified"].fillna(False).astype(bool)
    leads["is_excluded"] = (
        leads["exclude_opted_out"] | leads["exclude_bounced"] |
        leads["exclude_competitor"] | leads["exclude_non_prospect"] |
        leads["exclude_disqualified"]
    )
    return leads


def flag_contact_exclusions(contacts: pd.DataFrame, dnc_accounts: Set[str]) -> pd.DataFrame:
    """Flag contacts that are structurally unprioritizable."""
    contacts = contacts.copy()
    contacts["exclude_opted_out"] = contacts["has_opted_out"].fillna(False).astype(bool)
    contacts["exclude_no_longer"] = contacts["no_longer_with_company"].fillna(False).astype(bool)
    contacts["exclude_non_prospect"] = contacts["job_persona"] == "Non-Prospect"
    contacts["exclude_dnc_account"] = contacts["account_id"].isin(dnc_accounts) if "account_id" in contacts.columns else False
    contacts["is_excluded"] = (
        contacts["exclude_opted_out"] | contacts["exclude_no_longer"] |
        contacts["exclude_non_prospect"] | contacts["exclude_dnc_account"]
    )
    return contacts


def find_duplicate_emails(leads: pd.DataFrame, contacts: pd.DataFrame) -> Set[str]:
    """Identify email addresses that appear on multiple records (DQ-2)."""
    all_emails = pd.concat([leads[["email"]], contacts[["email"]]])
    return set(all_emails[all_emails.duplicated(subset="email", keep=False)]["email"])


def detect_etl_dates(dates: pd.Series, threshold: int = 20) -> Set[str]:
    """Detect dates that are likely ETL bulk-load timestamps (DQ-4)."""
    counts = dates.value_counts()
    return set(counts[counts > threshold].index)


def flag_lead_dq(leads: pd.DataFrame, dup_emails: Set[str], etl_dates: Set[str]) -> pd.DataFrame:
    """Flag data quality issues on leads."""
    leads = leads.copy()
    leads["dq_broken_conversion"] = leads["is_converted"].astype(bool) & leads["converted_contact_id"].isna()
    leads["dq_duplicate_email"] = leads["email"].isin(dup_emails)
    leads["dq_mql_overwritten"] = leads["mql_date"].notna() & leads["lead_status"].isin(["Recycled", "Disqualified"])
    leads["dq_etl_timestamp"] = leads["created_date"].isin(etl_dates)
    leads["dq_incomplete"] = leads["title"].isna() | leads["job_persona"].isna()

    dq_cols = [c for c in leads.columns if c.startswith("dq_")]
    leads["dq_issue_count"] = leads[dq_cols].astype(bool).sum(axis=1)
    return leads


def flag_contact_dq(contacts: pd.DataFrame, dup_emails: Set[str], etl_dates: Set[str]) -> pd.DataFrame:
    """Flag data quality issues on contacts."""
    contacts = contacts.copy()
    contacts["dq_duplicate_email"] = contacts["email"].isin(dup_emails)
    contacts["dq_mql_overwritten"] = False
    contacts["dq_etl_timestamp"] = contacts["created_date"].isin(etl_dates)
    contacts["dq_incomplete"] = contacts["title"].isna() | contacts["job_persona"].isna()

    dq_cols = [c for c in contacts.columns if c.startswith("dq_")]
    contacts["dq_issue_count"] = contacts[dq_cols].astype(bool).sum(axis=1)
    return contacts


def resolve_broken_conversions(leads: pd.DataFrame, contacts: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    """Attempt to link broken conversion pairs via email matching (DQ-1)."""
    leads = leads.copy()
    leads["resolved_contact_id"] = None

    broken = leads[leads.get("dq_broken_conversion", pd.Series(dtype=bool)).fillna(False)]
    resolved = 0

    contact_email_map = contacts.drop_duplicates(subset="email").set_index("email")["contact_id"]

    for idx, lead in broken.iterrows():
        if lead["email"] in contact_email_map.index:
            leads.at[idx, "resolved_contact_id"] = contact_email_map[lead["email"]]
            resolved += 1

    return leads, resolved


def clean_data(output_dir: str) -> CleaningResult:
    """Run all cleaning steps: exclusion flags, DQ flags, and entity resolution."""
    logger.info("Layer 1: Cleaning & entity resolution...")
    accounts, leads, contacts, campaign_members = load_data(output_dir)

    dnc_accounts = get_dnc_accounts(accounts)
    leads = flag_lead_exclusions(leads)
    contacts = flag_contact_exclusions(contacts, dnc_accounts)

    dup_emails = find_duplicate_emails(leads, contacts)
    lead_etl_dates = detect_etl_dates(leads["created_date"], threshold=20)
    contact_etl_dates = detect_etl_dates(contacts["created_date"], threshold=10)
    leads = flag_lead_dq(leads, dup_emails, lead_etl_dates)
    contacts = flag_contact_dq(contacts, dup_emails, contact_etl_dates)

    leads, resolved_count = resolve_broken_conversions(leads, contacts)
    broken_count = leads["dq_broken_conversion"].sum() if "dq_broken_conversion" in leads.columns else 0

    stats = {
        "total_leads": len(leads),
        "total_contacts": len(contacts),
        "excluded_leads": int(leads["is_excluded"].sum()),
        "excluded_contacts": int(contacts["is_excluded"].sum()),
        "duplicate_emails": len(dup_emails),
        "broken_conversions": int(broken_count),
        "resolved_conversions": resolved_count,
    }
    logger.info(f"Layer 1 complete: {len(leads)} leads, {len(contacts)} contacts, "
                f"{resolved_count}/{broken_count} conversions resolved")

    return CleaningResult(
        accounts=accounts,
        leads=leads,
        contacts=contacts,
        campaign_members=campaign_members,
        resolution_stats=stats,
    )
