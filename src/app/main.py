"""
Lead/Contact Readiness Scoring Demo
A self-hosted Streamlit application for exploring prioritized CRM records.
"""

import os
import subprocess
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, PROJECT_ROOT)

DATA_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
KB_DIR = os.path.join(PROJECT_ROOT, "docs", "knowledge-base")
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")


if not os.path.exists(os.path.join(DATA_DIR, "scored_records.csv")):
    subprocess.run(
        [sys.executable, "-m", "lead_scorer", "generate"],
        cwd=PROJECT_ROOT,
        check=True,
    )
    subprocess.run(
        [sys.executable, "-m", "lead_scorer", "score"],
        cwd=PROJECT_ROOT,
        check=True,
    )

st.set_page_config(
    page_title="Lead Readiness Scoring",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data
def load_scored_data():
    return pd.read_csv(os.path.join(DATA_DIR, "scored_records.csv"))


@st.cache_data
def load_campaign_members():
    return pd.read_csv(os.path.join(RAW_DIR, "campaign_members.csv"))


def load_knowledge_base():
    docs = {}
    for f in sorted(os.listdir(KB_DIR)):
        if f.endswith(".md"):
            with open(os.path.join(KB_DIR, f)) as fh:
                docs[f.replace(".md", "").replace("-", " ").title()] = fh.read()
    # Include the DQ Issue Catalogue from docs/
    dq_path = os.path.join(DOCS_DIR, "dq-issue-catalogue.md")
    if os.path.exists(dq_path):
        with open(dq_path) as fh:
            docs["DQ Issue Catalogue"] = fh.read()
    return docs


def _on_exec_change():
    if st.session_state.get("exec_nav") is not None:
        st.session_state["deep_nav"] = None


def _on_deep_change():
    if st.session_state.get("deep_nav") is not None:
        st.session_state["exec_nav"] = None


def render_sidebar(df):
    st.sidebar.title("🎯 Readiness Scorer")
    st.sidebar.markdown("---")

    if "exec_nav" not in st.session_state and "deep_nav" not in st.session_state:
        st.session_state["exec_nav"] = "🎬 The Story"

    st.sidebar.subheader("Executive View", divider="red")
    exec_page = st.sidebar.radio(
        "Executive",
        ["🎬 The Story", "📊 Ranked List", "📈 Score Distribution"],
        index=None,
        label_visibility="collapsed",
        key="exec_nav",
        on_change=_on_exec_change,
    )

    st.sidebar.subheader("Deep Dive", divider="blue")
    deep_page = st.sidebar.radio(
        "Deep Dive",
        [
            "🧪 Persona Tester",
            "🎚️ Weight Explorer",
            "🔍 Record Inspector",
            "📚 Methodology",
            "📖 Knowledge Base",
        ],
        index=None,
        label_visibility="collapsed",
        key="deep_nav",
        on_change=_on_deep_change,
    )

    page = exec_page or deep_page or "🎬 The Story"

    st.sidebar.markdown("---")
    st.sidebar.metric("Total Records", len(df))
    st.sidebar.metric("Excluded", int(df["is_excluded"].sum()))
    st.sidebar.metric("Scorable", int((~df["is_excluded"]).sum()))

    return page


def render_ranked_list(df):
    st.title("📊 Prioritized Record List")
    st.markdown("*Top records to call this week, ranked by readiness score.*")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        tier_filter = st.multiselect(
            "Tier", ["Hot", "Warm", "Nurture", "Cold"], default=["Hot", "Warm"]
        )
    with col2:
        type_filter = st.multiselect(
            "Entity Type", ["lead", "contact"], default=["lead", "contact"]
        )
    with col3:
        show_excluded = st.checkbox("Show Excluded", value=False)
    with col4:
        max_rows = st.slider("Max rows", 25, 500, 100)

    filtered = df[df["tier"].isin(tier_filter) & df["entity_type"].isin(type_filter)]
    if not show_excluded:
        filtered = filtered[~filtered["is_excluded"]]

    # Build visual badge column for DQ/exclusion flags
    def build_flags(row):
        flags = []
        if row.get("is_excluded"):
            excl_cols = [c for c in row.index if c.startswith("exclude_")]
            for c in excl_cols:
                if row.get(c) is True:
                    flags.append("🚫 " + c.replace("exclude_", "").replace("_", " ").title())
        dq_count = row.get("dq_issue_count", 0)
        if dq_count and int(dq_count) > 0:
            flags.append(f"⚠️ {int(dq_count)} DQ")
        return " | ".join(flags) if flags else ""

    filtered = filtered.copy()
    filtered["flags"] = filtered.apply(build_flags, axis=1)

    display_cols = [
        "rank",
        "entity_id",
        "entity_type",
        "tier",
        "readiness_score",
        "first_name",
        "last_name",
        "title",
        "flags",
        "score_engagement",
        "score_profile",
        "score_account",
        "score_momentum",
    ]
    display_cols = [c for c in display_cols if c in filtered.columns]

    st.dataframe(
        filtered[display_cols].head(max_rows),
        use_container_width=True,
        height=600,
        column_config={
            "readiness_score": st.column_config.ProgressColumn(
                "Readiness", min_value=0, max_value=100, format="%.1f"
            ),
            "score_engagement": st.column_config.NumberColumn("Engagement", format="%.1f"),
            "score_profile": st.column_config.NumberColumn("Profile", format="%.1f"),
            "score_account": st.column_config.NumberColumn("Account", format="%.1f"),
            "score_momentum": st.column_config.NumberColumn("Momentum", format="%.1f"),
        },
    )

    st.caption(f"Showing {min(max_rows, len(filtered))} of {len(filtered)} records")


def render_record_inspector(df, cm_df):
    st.title("🔍 Record Inspector")
    st.markdown(
        "*Inspect individual records: profile, engagement history, score breakdown, DQ flags.*"
    )

    scorable = df[~df["is_excluded"]].sort_values("readiness_score", ascending=False)
    options = [
        f"#{r['rank']} | {r['entity_id']} | {r.get('first_name', '')} {r.get('last_name', '')} | Score: {r['readiness_score']}"
        for _, r in scorable.head(200).iterrows()
    ]

    if not options:
        st.warning("No scorable records found.")
        return

    selected = st.selectbox("Select a record", options)
    entity_id = selected.split("|")[1].strip()
    record = df[df["entity_id"] == entity_id].iloc[0]

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Profile")
        profile_data = {
            "Entity ID": record["entity_id"],
            "Type": record["entity_type"],
            "Name": f"{record.get('first_name', '')} {record.get('last_name', '')}",
            "Title": record.get("title", "N/A"),
            "Email": record.get("email", "N/A"),
            "Persona": record.get("job_persona", "N/A"),
            "Level": record.get("job_level", "N/A"),
        }
        if record["entity_type"] == "lead":
            profile_data["Company"] = record.get("company", "N/A")
            profile_data["Lead Status"] = record.get("lead_status", "N/A")
            profile_data["Lead Source"] = record.get("lead_source", "N/A")
        else:
            profile_data["Account"] = record.get("account_name", "N/A")
            profile_data["Contact Status"] = record.get("contact_status", "N/A")

        for k, v in profile_data.items():
            st.text(f"{k}: {v}")

    with col2:
        st.subheader("Score Breakdown")
        fig = go.Figure(
            go.Bar(
                x=[
                    record["score_engagement"],
                    record["score_profile"],
                    record["score_account"],
                    record["score_momentum"],
                ],
                y=["Engagement (40%)", "Profile (25%)", "Account (20%)", "Momentum (15%)"],
                orientation="h",
                marker_color=["#FF6B6B", "#4ECDC4", "#45B7D1", "#96E6A1"],
                text=[
                    f"{v:.1f}"
                    for v in [
                        record["score_engagement"],
                        record["score_profile"],
                        record["score_account"],
                        record["score_momentum"],
                    ]
                ],
                textposition="inside",
            )
        )
        fig.update_layout(
            title=f"Readiness Score: {record['readiness_score']:.1f} / 100 ({record['tier']})",
            xaxis_title="Component Score (0-100)",
            height=250,
            margin=dict(l=0, r=0, t=40, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)

        st.metric("Final Readiness Score", f"{record['readiness_score']:.1f} / 100")
        st.metric("Priority Tier", record["tier"])

    # Data Quality Flags
    st.subheader("Data Quality Flags")
    dq_cols = [c for c in record.index if c.startswith("dq_") and c != "dq_issue_count"]
    active_flags = [
        c.replace("dq_", "").replace("_", " ").title() for c in dq_cols if record.get(c) is True
    ]
    if active_flags:
        st.warning(f"⚠️ DQ Issues ({len(active_flags)}): {', '.join(active_flags)}")
    else:
        st.success("✅ No data quality issues detected")

    # Exclusion flags
    excl_cols = [c for c in record.index if c.startswith("exclude_")]
    active_excl = [
        c.replace("exclude_", "").replace("_", " ").title()
        for c in excl_cols
        if record.get(c) is True
    ]
    if active_excl:
        st.error(f"🚫 Exclusion Flags: {', '.join(active_excl)}")

    # Engagement History
    st.subheader("Engagement History")
    entity_cm = cm_df[cm_df["entity_id"] == entity_id].sort_values("response_date", ascending=False)
    if len(entity_cm) > 0:
        st.dataframe(
            entity_cm[
                ["campaign_type", "campaign_name", "member_status", "is_responded", "response_date"]
            ].head(20),
            use_container_width=True,
        )
        st.caption(f"Showing {min(20, len(entity_cm))} of {len(entity_cm)} campaign memberships")
    else:
        st.info("No campaign engagement history found")


def render_distribution(df):
    st.title("📈 Score Distribution Analysis")

    scorable = df[~df["is_excluded"]]

    col1, col2 = st.columns(2)
    with col1:
        fig = px.histogram(
            scorable,
            x="readiness_score",
            color="tier",
            nbins=30,
            title="Readiness Score Distribution by Tier",
            color_discrete_map={
                "Hot": "#FF6B6B",
                "Warm": "#FFA94D",
                "Nurture": "#74C0FC",
                "Cold": "#ADB5BD",
            },
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.histogram(
            scorable,
            x="readiness_score",
            color="entity_type",
            nbins=30,
            title="Score Distribution by Entity Type",
            color_discrete_map={"lead": "#4ECDC4", "contact": "#FF6B6B"},
        )
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        scatter_df = scorable.dropna(
            subset=["score_engagement", "score_profile", "readiness_score"]
        )
        fig = px.scatter(
            scatter_df,
            x="score_engagement",
            y="score_profile",
            color="tier",
            size="readiness_score",
            title="Engagement vs Profile (size = readiness)",
            color_discrete_map={
                "Hot": "#FF6B6B",
                "Warm": "#FFA94D",
                "Nurture": "#74C0FC",
                "Cold": "#ADB5BD",
            },
        )
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        tier_stats = (
            scorable.groupby("tier")
            .agg(
                count=("readiness_score", "count"),
                avg_score=("readiness_score", "mean"),
                avg_engagement=("score_engagement", "mean"),
                avg_profile=("score_profile", "mean"),
            )
            .round(1)
        )
        st.dataframe(tier_stats, use_container_width=True)

    # Entity type fairness check
    st.subheader("Entity Type Fairness")
    fairness = (
        scorable.groupby("entity_type")
        .agg(
            count=("readiness_score", "count"),
            mean_score=("readiness_score", "mean"),
            median_score=("readiness_score", "median"),
            pct_hot=("tier", lambda x: (x == "Hot").mean() * 100),
        )
        .round(1)
    )
    fairness.columns = ["Count", "Mean Score", "Median Score", "% Hot Tier"]
    st.dataframe(fairness, use_container_width=True)


def render_methodology():
    st.title("📚 Scoring Methodology")

    st.markdown("""
    ## Overview

    The Readiness Scoring Model ranks every lead and contact on a **0-100 scale** to answer
    one question: *"Is this person worth a phone call right now?"*

    It replaces the legacy MQL flag (a binary threshold on behavioral score) with a
    **multi-dimensional, time-aware, explainable composite score**.

    ---

    ## Architecture: 4-Layer Pipeline

    ```
    Raw CRM Data
         │
         ▼
    ┌─────────────────────┐
    │  Layer 1: CLEAN     │  Entity resolution, DQ flagging, exclusion overlays
    └─────────────────────┘
         │
         ▼
    ┌─────────────────────┐
    │  Layer 2: FEATURES  │  Engagement recency, profile fit, account strength, momentum
    └─────────────────────┘
         │
         ▼
    ┌─────────────────────┐
    │  Layer 3: SCORE     │  Component scoring (0-100 per dimension)
    └─────────────────────┘
         │
         ▼
    ┌─────────────────────┐
    │  Layer 4: RANK      │  Weighted composite → tiers → final ranked list
    └─────────────────────┘
    ```

    ---

    ## Scoring Components

    | Component | Weight | What It Measures | Key Signal |
    |-----------|--------|-----------------|------------|
    | **Engagement Recency** | 40% | Recent real engagement | Exponential decay (45-day half-life) |
    | **Profile Fit** | 25% | ICP alignment | Title seniority + persona match |
    | **Account Strength** | 20% | Company-level signals | Named account, intent score, firmographics |
    | **Behavioral Momentum** | 15% | Engagement acceleration | Is activity increasing? |

    ---

    ## Time-Decay Function

    Engagement recency uses exponential decay with a **45-day half-life**:

    `score = 100 × e^(-0.693 × days_since_last / 45)`

    | Days Since Last Engagement | Recency Score |
    |---------------------------|---------------|
    | 0 (today) | 100 |
    | 15 days | 79 |
    | 30 days | 63 |
    | 45 days | 50 |
    | 90 days | 25 |
    | 180 days | 6 |
    | 365 days | ~0 |

    ---

    ## Exclusion Overlays (Not Score Penalties)

    These are **orthogonal flags** — a record can score 90/100 on readiness and still be excluded:

    - **Opted out**: Legal/compliance block on email outreach
    - **Email bounced**: No deliverable email address
    - **Competitor**: Employee of known competitor company
    - **Non-prospect**: Partner, vendor, or other non-buyer persona
    - **Do-not-contact (account-level)**: Compliance block at the account level
    - **No longer with company**: Contact has left the account

    ---

    ## Data Quality Handling

    DQ issues are **flagged but don't directly penalize scores**. Instead:
    - **DQ-8 (automation inflation)**: Filtered out before engagement scoring
    - **DQ-7 (missing data)**: Profile score doesn't assume absence = bad
    - **DQ-1 (broken links)**: Attempted resolution via email matching
    - **DQ-5 (score asymmetry)**: Legacy Marketo scores are not used as inputs

    ---

    ## Tier Definitions

    | Tier | Score Range | Action |
    |------|-------------|--------|
    | 🔥 **Hot** | 70-100 | Call this week |
    | 🌡️ **Warm** | 45-69 | Prioritize outreach |
    | 🌱 **Nurture** | 20-44 | Marketing nurture programs |
    | ❄️ **Cold** | 0-19 | Deprioritize / monitor |

    ---

    ## What This Model Does NOT Do

    - ❌ Predict conversion probability (no labeled data)
    - ❌ Use existing MQL status as an input (avoids circular dependency)
    - ❌ Penalize records for data quality issues (flags, not penalties)
    - ❌ Replace human judgment (augments BDR decision-making)
    """)


def render_weight_explorer(df):
    """Interactive weight tuner — re-scores all records live with slider-adjusted parameters."""
    st.title("🎚️ Weight Explorer — Tune the Model Live")
    st.markdown("""
    *Adjust the scoring formula in real-time. Move the sliders and watch how the Top 10, tier
    distribution, and individual records change. This proves the pipeline is modular and parameterized —
    no hardcoded magic numbers.*
    """)

    scorable = df[~df["is_excluded"]].copy()

    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ Model Parameters")

    # Weight sliders (normalized automatically)
    st.subheader("Component Weights")
    st.caption("Weights are auto-normalized to sum to 1.0")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        w_eng = st.slider("Engagement", 0.0, 1.0, 0.40, 0.05, key="w_eng")
    with col2:
        w_prof = st.slider("Profile", 0.0, 1.0, 0.25, 0.05, key="w_prof")
    with col3:
        w_acc = st.slider("Account", 0.0, 1.0, 0.20, 0.05, key="w_acc")
    with col4:
        w_mom = st.slider("Momentum", 0.0, 1.0, 0.15, 0.05, key="w_mom")

    total = w_eng + w_prof + w_acc + w_mom
    if total == 0:
        st.error("Weights cannot all be zero.")
        return

    # Normalize
    w_eng_n, w_prof_n, w_acc_n, w_mom_n = (
        w_eng / total,
        w_prof / total,
        w_acc / total,
        w_mom / total,
    )

    st.markdown(
        f"**Normalized:** Engagement={w_eng_n:.2f} | Profile={w_prof_n:.2f} | "
        f"Account={w_acc_n:.2f} | Momentum={w_mom_n:.2f}"
    )

    # Tier thresholds
    st.subheader("Tier Thresholds")
    tc1, tc2, tc3 = st.columns(3)
    with tc1:
        hot_t = st.slider("Hot ≥", 30.0, 90.0, 70.0, 5.0, key="hot_t")
    with tc2:
        warm_t = st.slider("Warm ≥", 15.0, 70.0, 45.0, 5.0, key="warm_t")
    with tc3:
        nurture_t = st.slider("Nurture ≥", 5.0, 45.0, 20.0, 5.0, key="nurture_t")

    # Re-score with new weights

    scorable["new_score"] = (
        scorable["score_engagement"] * w_eng_n
        + scorable["score_profile"] * w_prof_n
        + scorable["score_account"] * w_acc_n
        + scorable["score_momentum"] * w_mom_n
    ).round(2)

    def assign_tier(score):
        if score >= hot_t:
            return "Hot"
        elif score >= warm_t:
            return "Warm"
        elif score >= nurture_t:
            return "Nurture"
        return "Cold"

    scorable["new_tier"] = scorable["new_score"].apply(assign_tier)
    scorable = scorable.sort_values("new_score", ascending=False).reset_index(drop=True)
    scorable["new_rank"] = range(1, len(scorable) + 1)

    st.markdown("---")

    # Comparison metrics
    st.subheader("Impact Analysis")
    comp1, comp2, comp3, comp4 = st.columns(4)
    old_hot = (scorable["tier"] == "Hot").sum()
    new_hot = (scorable["new_tier"] == "Hot").sum()
    comp1.metric("Hot Tier", new_hot, delta=int(new_hot - old_hot))

    old_warm = (scorable["tier"] == "Warm").sum()
    new_warm = (scorable["new_tier"] == "Warm").sum()
    comp2.metric("Warm Tier", new_warm, delta=int(new_warm - old_warm))

    old_mean = scorable["readiness_score"].mean()
    new_mean = scorable["new_score"].mean()
    comp3.metric("Avg Score", f"{new_mean:.1f}", delta=f"{new_mean - old_mean:+.1f}")

    # Rank displacement
    scorable["rank_change"] = scorable["rank"] - scorable["new_rank"]
    max_jump = scorable["rank_change"].abs().mean()
    comp4.metric("Avg Rank Δ", f"{max_jump:.1f} positions")

    # Top 10 comparison
    st.subheader("New Top 10 (with your weights)")
    top10 = scorable.head(10)
    display_cols = [
        "new_rank",
        "entity_type",
        "first_name",
        "last_name",
        "title",
        "new_score",
        "new_tier",
        "score_engagement",
        "score_profile",
        "score_account",
        "score_momentum",
    ]
    display_cols = [c for c in display_cols if c in top10.columns]
    st.dataframe(
        top10[display_cols],
        use_container_width=True,
        column_config={
            "new_score": st.column_config.ProgressColumn(
                "New Score", min_value=0, max_value=100, format="%.1f"
            ),
        },
    )

    # Before/After comparison
    st.subheader("Tier Distribution: Default vs Your Weights")
    tier_order = ["Hot", "Warm", "Nurture", "Cold"]
    old_dist = scorable["tier"].value_counts().reindex(tier_order, fill_value=0)
    new_dist = scorable["new_tier"].value_counts().reindex(tier_order, fill_value=0)

    compare_df = pd.DataFrame({"Default Weights": old_dist, "Your Weights": new_dist})
    fig = go.Figure(
        data=[
            go.Bar(
                name="Default (0.4/0.25/0.2/0.15)",
                x=tier_order,
                y=compare_df["Default Weights"],
                marker_color=["#FF6B6B", "#FFA94D", "#74C0FC", "#ADB5BD"],
            ),
            go.Bar(
                name="Your Weights",
                x=tier_order,
                y=compare_df["Your Weights"],
                marker_color=["#FF3333", "#FF8800", "#3399FF", "#888888"],
            ),
        ]
    )
    fig.update_layout(barmode="group", height=350, title="Tier Counts: Before vs After")
    st.plotly_chart(fig, use_container_width=True)

    # Biggest movers
    st.subheader("Biggest Rank Movers (who benefited most?)")
    movers = scorable.nlargest(10, "rank_change")[
        [
            "entity_id",
            "first_name",
            "last_name",
            "title",
            "rank",
            "new_rank",
            "rank_change",
            "score_engagement",
            "score_profile",
            "score_account",
            "score_momentum",
        ]
    ]
    movers_display = [c for c in movers.columns if c in scorable.columns]
    st.dataframe(movers[movers_display], use_container_width=True, hide_index=True)

    st.markdown("""
    ---
    **Why this matters**: The scoring formula is fully parameterized. No hardcoded numbers in the math —
    weights are passed as a `ScoringWeights` dataclass. This means the model can be tuned for different
    business priorities (e.g., "engagement-heavy" for pipeline acceleration vs "profile-heavy" for
    ABM campaigns) without changing any code.
    """)


PERSONA_DEFINITIONS = [
    {
        "id": "P1",
        "name": "Hot Prospect — VP Security, Named ICP, Active MQL",
        "description": "VP of Security at a named ICP account with 3 webinars attended this month. Recently MQL'd.",
        "expected_tier": "Hot",
        "expected_behavior": "Score 70+. Strong across all 4 dimensions — this is your #1 call.",
        "entity_type": "lead",
        "index": 0,
    },
    {
        "id": "P2",
        "name": "Stale VP — Same Profile, 6-Month-Old Engagement",
        "description": "VP-level CISO profile, but MQL'd 200 days ago. No recent activity. Status: Recycled.",
        "expected_tier": "Nurture or Cold",
        "expected_behavior": "Profile score high, engagement near zero (time-decay crushes it). Proves recency matters.",
        "entity_type": "lead",
        "index": 1,
    },
    {
        "id": "P3",
        "name": "Junior Hyperactive — IC with 15 Responses in 30 Days",
        "description": "Security Analyst at a tiny startup. Very high engagement but weak profile and weak account.",
        "expected_tier": "Warm (high engagement, low everything else)",
        "expected_behavior": "Engagement dominates but profile/account drag it down. Not a Hot — proves multi-dimensional matters.",
        "entity_type": "lead",
        "index": 2,
    },
    {
        "id": "P4",
        "name": "Ghost CISO — Fortune 500, Zero Engagement",
        "description": "CISO at a large enterprise. Purchased list import. Never opened an email or attended anything.",
        "expected_tier": "Cold",
        "expected_behavior": "Amazing profile (C-Level, CISO persona) but 0 engagement = Cold. Old MQL system would never surface them anyway.",
        "entity_type": "lead",
        "index": 3,
    },
    {
        "id": "P5",
        "name": "Competitor Spy — CrowdStrike Engineer, High Webinar Attendance",
        "description": "Solutions Engineer at CrowdStrike. Attends all webinars and downloads whitepapers.",
        "expected_tier": "EXCLUDED",
        "expected_behavior": "Would score high on engagement, but orthogonal exclusion removes them entirely. Not penalized — removed.",
        "entity_type": "lead",
        "index": 4,
    },
    {
        "id": "P6",
        "name": "Bounced & Opted Out — Hard Exclusion",
        "description": "Email bounced AND opted out. Had a physical event attendance recently.",
        "expected_tier": "EXCLUDED",
        "expected_behavior": "Even real engagement can't override hard exclusion flags (bounced + opted out).",
        "entity_type": "lead",
        "index": 5,
    },
    {
        "id": "P7",
        "name": "Broken Conversion — DQ-1 Entity Resolution Failure",
        "description": "Lead marked is_converted=True but converted_contact_id is NULL. Data integrity issue.",
        "expected_tier": "Varies (scored after resolution)",
        "expected_behavior": "DQ flag raised. Entity resolution attempts to find matching contact. Record still scored.",
        "entity_type": "lead",
        "index": 6,
    },
    {
        "id": "P8",
        "name": "The Bot — 40 Campaign Memberships, 38 Auto-Sends",
        "description": "IT Manager in an email drip. 40 campaign memberships but 38 are automated sends (is_responded=False).",
        "expected_tier": "Nurture or Cold",
        "expected_behavior": "Automation discounting: only 2 real responses count. Looks engaged on paper, actually isn't.",
        "entity_type": "lead",
        "index": 7,
    },
    {
        "id": "P9",
        "name": "Re-MQL Carousel — MQL'd 4 Times, Never Converted",
        "description": "Lead that has cycled through MQL status multiple times. Currently MQL again.",
        "expected_tier": "Warm (recent MQL) or Nurture",
        "expected_behavior": "Recent MQL gives some momentum, but the cycling pattern doesn't boost engagement. Moderate score.",
        "entity_type": "lead",
        "index": 8,
    },
    {
        "id": "P10",
        "name": "Contact Champion — High-Intent Named Account, Form Fills",
        "description": "Director of IT at a named ICP account with high intent. 2 recent content downloads.",
        "expected_tier": "Hot or Warm",
        "expected_behavior": "Strong account signal + director-level profile + recent engagement. Benefits from entity-type fairness (contact has account data).",
        "entity_type": "contact",
        "index": 1,
    },
]


def render_persona_tester(df, cm_df):
    st.title("🧪 Persona Tester — Appendix B Archetypes")
    st.markdown("""
    *Select any of the 10 pre-defined edge-case personas to verify the model handles them correctly.
    Each persona was injected into the synthetic data at generation time with specific characteristics.*
    """)

    persona_names = [f"{p['id']}: {p['name']}" for p in PERSONA_DEFINITIONS]
    selected_name = st.selectbox("Select a persona", persona_names)
    selected_idx = persona_names.index(selected_name)
    persona = PERSONA_DEFINITIONS[selected_idx]

    st.markdown("---")

    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("Expected Behavior")
        st.info(f"**Persona:** {persona['description']}")
        st.markdown(f"**Expected Tier:** `{persona['expected_tier']}`")
        st.markdown(f"**Why:** {persona['expected_behavior']}")

    # Find the actual record
    entity_type = persona["entity_type"]
    idx = persona["index"]

    if entity_type == "lead":
        entity_id = f"L-{idx:04d}"
    else:
        entity_id = f"C-{idx:04d}"

    record_match = df[df["entity_id"] == entity_id]

    with col2:
        st.subheader("Actual Result")
        if len(record_match) == 0:
            # Try matching by index position within type
            type_records = df[df["entity_type"] == entity_type].reset_index(drop=True)
            if idx < len(type_records):
                record_match = type_records.iloc[[idx]]

        if len(record_match) > 0:
            record = record_match.iloc[0]
            is_excluded = record.get("is_excluded", False)

            if is_excluded:
                st.error("🚫 **EXCLUDED** — removed from callable pool")
                excl_cols = [c for c in record.index if c.startswith("exclude_")]
                reasons = [
                    c.replace("exclude_", "").replace("_", " ").title()
                    for c in excl_cols
                    if record.get(c) is True
                ]
                if reasons:
                    st.markdown(f"Exclusion reasons: {', '.join(reasons)}")
            else:
                tier = record.get("tier", "Unknown")
                tier_colors = {"Hot": "🔥", "Warm": "🟠", "Nurture": "🔵", "Cold": "❄️"}
                st.success(
                    f"{tier_colors.get(tier, '')} **Tier: {tier}** — Score: {record['readiness_score']:.1f}/100"
                )

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Engagement", f"{record.get('score_engagement', 0):.0f}")
            c2.metric("Profile", f"{record.get('score_profile', 0):.0f}")
            c3.metric("Account", f"{record.get('score_account', 0):.0f}")
            c4.metric("Momentum", f"{record.get('score_momentum', 0):.0f}")

            # DQ Flags
            dq_cols = [c for c in record.index if c.startswith("dq_") and c != "dq_issue_count"]
            active_dq = [
                c.replace("dq_", "").replace("_", " ").title()
                for c in dq_cols
                if record.get(c) is True
            ]
            if active_dq:
                st.warning(f"⚠️ DQ Flags: {', '.join(active_dq)}")
        else:
            st.warning("Record not found — regenerate data with `make data && make score`")

    # Engagement history
    if len(record_match) > 0:
        st.markdown("---")
        st.subheader("Engagement History")
        entity_id_val = record_match.iloc[0].get("entity_id", entity_id)
        entity_cm = cm_df[cm_df["entity_id"] == entity_id_val].sort_values(
            "response_date", ascending=False
        )
        if len(entity_cm) > 0:
            responded = entity_cm[entity_cm["is_responded"]]
            auto = entity_cm[~entity_cm["is_responded"]]
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Memberships", len(entity_cm))
            c2.metric("Real Responses", len(responded))
            c3.metric("Auto/Sent Only", len(auto))
            st.dataframe(
                entity_cm[
                    [
                        "campaign_type",
                        "campaign_name",
                        "member_status",
                        "is_responded",
                        "response_date",
                    ]
                ].head(15),
                use_container_width=True,
            )
        else:
            st.info("No campaign memberships found for this record.")

    # Summary table of all personas
    st.markdown("---")
    st.subheader("All 10 Personas — Summary Grid")
    summary_rows = []
    for p in PERSONA_DEFINITIONS:
        etype = p["entity_type"]
        pidx = p["index"]
        eid = f"L-{pidx:04d}" if etype == "lead" else f"C-{pidx:04d}"
        match = df[df["entity_id"] == eid]
        if len(match) == 0:
            type_recs = df[df["entity_type"] == etype].reset_index(drop=True)
            if pidx < len(type_recs):
                match = type_recs.iloc[[pidx]]
        if len(match) > 0:
            r = match.iloc[0]
            summary_rows.append(
                {
                    "Persona": p["id"],
                    "Name": p["name"].split("—")[0].strip() if "—" in p["name"] else p["name"][:25],
                    "Score": f"{r.get('readiness_score', 0):.0f}",
                    "Tier": "EXCLUDED" if r.get("is_excluded", False) else r.get("tier", "?"),
                    "Expected": p["expected_tier"],
                    "Match": "✅"
                    if (
                        (r.get("is_excluded", False) and "EXCLUDED" in p["expected_tier"])
                        or (
                            not r.get("is_excluded", False)
                            and r.get("tier", "") in p["expected_tier"]
                        )
                    )
                    else "⚠️",
                }
            )
    if summary_rows:
        import pandas as pd_local

        st.dataframe(pd_local.DataFrame(summary_rows), use_container_width=True, hide_index=True)


def render_narrative(df, cm_df):
    st.title("🎬 The Story: Why MQL Is Broken")
    st.markdown("""
    *A 2-minute walkthrough showing why the legacy MQL system fails and how readiness scoring fixes it.*

    ---

    ### The Problem

    The BDR team gets a daily list of "MQLs" — records that crossed a 50-point behavioral threshold
    in Marketo. They work the list top-to-bottom. **But half the list is garbage.**
    """)

    col1, col2 = st.columns(2)
    with col1:
        st.error("**What BDRs see today (MQL list)**")
        st.markdown("""
        - People who left the company
        - Competitors attending our webinars
        - Records with zero engagement in 90+ days
        - Duplicates they've already called
        - Automated email sends inflating scores
        """)
    with col2:
        st.success("**What they need**")
        st.markdown("""
        - Ranked by *call-worthiness right now*
        - Profile + engagement + account signals combined
        - Recent activity weighted heavily
        - Non-prospects automatically excluded
        - Explainable: *why* is this person #1?
        """)

    st.markdown("---")
    st.subheader("Meet the Personas")
    st.markdown("*Let's walk through 4 contrasting records to see how the new scoring works:*")

    scorable = df[~df["is_excluded"]].sort_values("readiness_score", ascending=False)
    excluded = df[df["is_excluded"]].sort_values("readiness_score", ascending=False)

    # Persona cards
    personas = [
        {
            "title": "Sarah — VP of Security at a Named Account",
            "description": "3 webinars attended this month, active MQL, ICP-qualified account with high intent.",
            "expectation": "**Should be: #1 on the call list**",
            "icon": "🔥",
            "filter": lambda d: d[(d["job_level"] == "VP") & (d["score_engagement"] > 60)],
        },
        {
            "title": "The Ghost — CISO, Fortune 500, Zero Engagement",
            "description": "Amazing profile. Purchased list entry. Never opened an email, never clicked, never attended anything.",
            "expectation": "**Should be: Nurture tier — great profile but no intent signal right now**",
            "icon": "❄️",
            "filter": lambda d: d[(d["score_engagement"] < 10) & (d["score_profile"] > 60)],
        },
        {
            "title": "The Bot — 40 Campaign Memberships, 38 Auto-Sends",
            "description": "Looks highly engaged on paper. In reality, they're just enrolled in an email drip. Only 2 real interactions.",
            "expectation": "**Should be: Low score — automation discounting reveals the truth**",
            "icon": "🤖",
            "filter": lambda d: d[d["automation_ratio"] > 0.7],
        },
        {
            "title": "The Spy — Competitor Employee with High Engagement",
            "description": "Attends every webinar, downloads every whitepaper. Works at CrowdStrike.",
            "expectation": "**Should be: EXCLUDED — not scored low, completely removed from the callable pool**",
            "icon": "🚫",
            "filter": lambda d: excluded[
                excluded.get("exclude_competitor", pd.Series(dtype=bool)).fillna(False)
            ],
        },
    ]

    for p in personas:
        with st.expander(f"{p['icon']} {p['title']}", expanded=True):
            st.markdown(p["description"])
            st.markdown(p["expectation"])
            try:
                matches = p["filter"](df)
                if len(matches) > 0:
                    record = matches.iloc[0]
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Readiness Score", f"{record['readiness_score']:.0f}/100")
                    c2.metric("Engagement", f"{record['score_engagement']:.0f}")
                    c3.metric("Profile", f"{record['score_profile']:.0f}")
                    c4.metric("Tier", record.get("tier", "N/A"))
            except Exception:
                pass

    st.markdown("---")
    st.subheader("The Result: Top 10 This Week")
    st.markdown("*The VP's ask: 'Give me the top people to call this week. Show me why.'*")

    top10 = scorable.head(10)
    display_cols = [
        "rank",
        "entity_type",
        "first_name",
        "last_name",
        "title",
        "readiness_score",
        "tier",
        "score_engagement",
        "score_profile",
        "score_account",
    ]
    display_cols = [c for c in display_cols if c in top10.columns]
    st.dataframe(top10[display_cols], use_container_width=True, height=400)

    st.markdown("""
    ---
    **Key insight**: The old system would have ranked The Bot and The Spy above Sarah
    (they have more raw "engagement"). The readiness score correctly identifies that
    *recent real engagement + strong profile + strong account = call now*.
    """)


def render_knowledge_base():
    st.title("📖 Knowledge Base")
    st.markdown(
        "*Discovery notes, design decisions, and lessons learned from building this system.*"
    )

    docs = load_knowledge_base()
    tabs = st.tabs(list(docs.keys()))
    for tab, (title, content) in zip(tabs, docs.items()):
        with tab:
            st.markdown(content)


def main():
    df = load_scored_data()
    cm_df = load_campaign_members()

    page = render_sidebar(df)

    if page == "🎬 The Story":
        render_narrative(df, cm_df)
    elif page == "🧪 Persona Tester":
        render_persona_tester(df, cm_df)
    elif page == "🎚️ Weight Explorer":
        render_weight_explorer(df)
    elif page == "📊 Ranked List":
        render_ranked_list(df)
    elif page == "🔍 Record Inspector":
        render_record_inspector(df, cm_df)
    elif page == "📈 Score Distribution":
        render_distribution(df)
    elif page == "📚 Methodology":
        render_methodology()
    elif page == "📖 Knowledge Base":
        render_knowledge_base()


if __name__ == "__main__":
    main()
