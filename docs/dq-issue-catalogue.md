# Data Quality Issue Catalogue

> **Purpose**: This document explicitly lists each DQ issue simulated in the synthetic data, how it manifests in the raw CSVs, and exactly how the scoring pipeline handles it. This is a core deliverable demonstrating that the model handles real-world CRM data failures gracefully.

---

## DQ-1: Broken Conversion Links

| Attribute | Detail |
|-----------|--------|
| **What it is** | A Lead is marked `is_converted=True` but `converted_contact_id` is NULL or points to a non-existent Contact. |
| **How it manifests** | In `leads.csv`: record has `is_converted=True` AND `converted_contact_id` is empty. The system "forgot" the link during the SFDC migration. |
| **Prevalence** | ~20% of converted leads (~7% of all leads) |
| **Impact if unhandled** | Engagement history is fragmented: the Lead has pre-conversion touches, the Contact has post-conversion touches, but they can't be joined. The BDR would see an incomplete picture of either record. |
| **How the model handles it** | `resolve_broken_conversions()` in `src/pipeline/clean.py` attempts email-based resolution: it tries to match the Lead's email to a Contact's email. Successful matches get the link repaired. Unresolvable cases are flagged with `dq_broken_conversion=True` so the BDR is aware. The record is still scored (not excluded). |
| **Code location** | `src/pipeline/clean.py:resolve_broken_conversions()` |

---

## DQ-2: Email Duplication (Spam Clusters)

| Attribute | Detail |
|-----------|--------|
| **What it is** | Multiple Lead/Contact records share the exact same email address — creating "high-cardinality spam clusters" that fragment a single person's history. |
| **How it manifests** | In `leads.csv` + `contacts.csv`: 2+ records with identical `email` values. |
| **Prevalence** | ~5-8% of the database |
| **Impact if unhandled** | Engagement is split across duplicates. A person might appear as 3 separate low-engagement records instead of 1 highly-engaged record. Alternatively, all duplicates get the same call — wasting BDR time. |
| **How the model handles it** | `find_duplicate_emails()` detects all shared emails across both entity tables. Records with duplicates are flagged `dq_duplicate_email=True`. We deliberately do NOT auto-merge (incorrect merges are worse than missed merges). The flag tells BDRs "verify this is really a new person before calling." |
| **Code location** | `src/pipeline/clean.py:find_duplicate_emails()`, `flag_lead_dq()`, `flag_contact_dq()` |

---

## DQ-3: MQL Date Overwrite

| Attribute | Detail |
|-----------|--------|
| **What it is** | When a Lead re-qualifies as MQL for the 2nd/3rd/4th time, the system overwrites `mql_date` with the latest qualification. The original first-touch MQL date is permanently lost. |
| **How it manifests** | In `leads.csv`: `mql_date` may reflect the most recent re-MQL, not the original. Records with status "Recycled" → "MQL" have lost their history. |
| **Prevalence** | All re-MQL'd records (~10% of leads) |
| **Impact if unhandled** | First-touch attribution is impossible. If you use `mql_date` as a recency signal, re-MQL'd records look artificially fresh. |
| **How the model handles it** | The scoring pipeline ignores `mql_date` entirely for recency calculation. Instead, it uses `campaign_members.response_date` — the actual date of real engagement events. This is immune to MQL date overwrites because each campaign membership is an independent record. |
| **Code location** | `src/pipeline/features.py:compute_engagement_features()` uses campaign response dates, not MQL dates |

---

## DQ-4: ETL Creation Timestamps

| Attribute | Detail |
|-----------|--------|
| **What it is** | The `created_date` field is dominated by ETL bulk-load timestamps rather than actual creation dates. When records were migrated to Salesforce, they all received the migration date. |
| **How it manifests** | In `leads.csv`: 80% of leads share one of a handful of `created_date` values (bulk load days). In `contacts.csv`: 34% share ETL dates. |
| **Prevalence** | 80% of leads, 34% of contacts |
| **Impact if unhandled** | Any analysis using `created_date` as a signal (e.g., "new record = higher potential") is completely misleading. Cohort analysis is impossible. |
| **How the model handles it** | `detect_etl_dates()` identifies dates that appear more than a threshold number of times (default: 20). These are flagged `dq_etl_created_date=True`. The scoring model never uses `created_date` as a feature — it uses campaign response dates for all temporal calculations. |
| **Code location** | `src/pipeline/clean.py:detect_etl_dates()`, `flag_lead_dq()`, `flag_contact_dq()` |

---

## DQ-5: Score Field Asymmetry

| Attribute | Detail |
|-----------|--------|
| **What it is** | Leads have `mkto_lead_score` (range 0-300+, exponential distribution). Contacts have `mkto_contact_score` (different calibration, different range). These are not comparable. |
| **How it manifests** | In `leads.csv`: `mkto_lead_score` with values 0-300+. In `contacts.csv`: `mkto_contact_score` with a different scale. |
| **Prevalence** | All records |
| **Impact if unhandled** | Naively comparing or combining these scores across entity types would create systematic bias. A Contact with score 50 might be more engaged than a Lead with score 150. |
| **How the model handles it** | The readiness scoring pipeline **completely ignores** existing Marketo scores. It computes its own engagement score from raw campaign membership data using consistent logic for both Leads and Contacts. The `mkto_lead_score`/`mkto_contact_score` fields are preserved for reference but never used as model inputs. The model flags the asymmetry: `dq_score_asymmetry=True`. |
| **Code location** | `src/pipeline/features.py` — engagement features computed from campaign_members, not from Marketo scores |

---

## DQ-6: Non-Prospect Contamination

| Attribute | Detail |
|-----------|--------|
| **What it is** | The database contains competitors, partners, vendors, students, and other non-prospect personas mixed in with real prospects. |
| **How it manifests** | In `leads.csv`: `company` matches known competitors (CrowdStrike, Palo Alto Networks, etc.) OR `job_persona = "Non-Prospect"`. |
| **Prevalence** | ~8-13% of the database |
| **Impact if unhandled** | Competitors who attend every webinar would appear at the top of the call list. BDRs waste time calling people who will never buy. |
| **How the model handles it** | **Orthogonal exclusion flag** — NOT a score penalty. `flag_lead_exclusions()` sets `exclude_competitor=True` for records matching known competitor companies. These records ARE scored (their score is analytically valid for competitive intelligence) but are removed from the callable pool via the exclusion overlay. The BDR never sees them in the "Top 500" list. |
| **Code location** | `src/pipeline/clean.py:flag_lead_exclusions()`, `COMPETITOR_COMPANIES` constant |

---

## DQ-7: Data Completeness Gaps

| Attribute | Detail |
|-----------|--------|
| **What it is** | 35% of records are missing `title`, ~40% are missing phone numbers, ~40% have no `job_persona`. Newer, top-of-funnel records are disproportionately incomplete. |
| **How it manifests** | In `leads.csv` / `contacts.csv`: NULL/empty values in `title`, `job_persona`, `job_level` fields. |
| **Prevalence** | 35-50% of records for various fields |
| **Impact if unhandled** | Profile scoring would systematically disadvantage newer records (who haven't been enriched yet) compared to older, fully-populated records. This creates anti-recency bias — the opposite of what BDRs need. |
| **How the model handles it** | Profile scoring uses a completeness-aware approach: `score_profile()` gives a moderate bonus for having title/persona data (`has_title`, `has_persona`) rather than penalizing absence. Missing fields contribute 0 to the profile dimension (neutral, not negative). Additionally, the 15-point lead baseline for account scoring (ADR-004) ensures new leads aren't systematically disadvantaged by missing account associations. Flag: `dq_missing_title=True`. |
| **Code location** | `src/pipeline/features.py:compute_profile_features()`, `src/pipeline/score.py:score_profile()` |

---

## DQ-8: Automation Inflation (Drip Campaign Noise)

| Attribute | Detail |
|-----------|--------|
| **What it is** | Automated marketing workflows (email drips, nurture sequences) generate 20-40 campaign memberships per person — but with `is_responded=False` and `member_status="Sent"`. These aren't real engagement. |
| **How it manifests** | In `campaign_members.csv`: records with `is_responded=False` and status "Sent" or similar automated statuses. Some entities have 40+ memberships but only 2 real responses. |
| **Prevalence** | ~60% of all campaign membership records are automated |
| **Impact if unhandled** | A person enrolled in a drip campaign appears identical to a conference attendee with 40 real touchpoints. Raw counts would rank drip enrollees above genuinely engaged prospects. |
| **How the model handles it** | Two-pronged: (1) Only `is_responded=True` campaign memberships count for engagement feature calculation. (2) An explicit `automation_ratio` feature measures what fraction of memberships are automated. High ratios (>0.7) apply a scoring penalty via `automation_penalty_factor` in the engagement scoring formula. This is the "Bot" persona (P8) test case. |
| **Code location** | `src/pipeline/features.py:compute_engagement_features()` (filters to responded), `src/pipeline/score.py:score_engagement()` (applies automation penalty) |

---

## DQ-9: Do-Not-Contact Flags

| Attribute | Detail |
|-----------|--------|
| **What it is** | Records or accounts are legally/contractually uncontactable: `has_opted_out=True`, `email_bounced=True`, or the parent account has `do_not_contact=True`. |
| **How it manifests** | In `leads.csv`: `has_opted_out=True` or `email_bounced=True`. In `accounts.csv`: `do_not_contact=True` (cascades to all associated contacts). |
| **Prevalence** | ~5% of records |
| **Impact if unhandled** | BDRs call people who cannot legally be contacted. Compliance risk + wasted effort. |
| **How the model handles it** | **Hard exclusion overlay**: `flag_lead_exclusions()` and `flag_contact_exclusions()` set `exclude_opted_out=True`, `exclude_bounced=True`, or `exclude_dnc_account=True`. These are absolute exclusions — no score can override them. Like DQ-6, the record is scored (useful for analytics) but removed from the callable pool. |
| **Code location** | `src/pipeline/clean.py:flag_lead_exclusions()`, `flag_contact_exclusions()`, `get_dnc_accounts()` |

---

## DQ-10: Disqualification/Re-MQL Cycles

| Attribute | Detail |
|-----------|--------|
| **What it is** | Records cycle through MQL → DQ → MQL → DQ repeatedly. They've been "qualified" 3-4 times but never converted. Each re-qualification overwrites the MQL date (see DQ-3). |
| **How it manifests** | In `leads.csv`: `lead_status="MQL"` with a recent `mql_date`, but the record has been through this cycle before. `is_disqualified` may have been True previously. |
| **Prevalence** | ~10% of leads |
| **Impact if unhandled** | These records look fresh (recent MQL date) but have a track record of not converting. Without context, BDRs re-work the same unresponsive records every quarter. |
| **How the model handles it** | The model treats re-MQL as a weak positive signal — recent MQL gives some momentum score, but the cycling pattern doesn't boost engagement because engagement scoring uses actual campaign response dates (not MQL dates). The record will only score high if it has genuine recent engagement. Flag: `dq_re_mql_cycle=True`. This is Persona P9 in the test suite. |
| **Code location** | `src/pipeline/features.py:compute_momentum_features()`, `src/pipeline/score.py:score_momentum()` |

---

## Summary: Handling Philosophy

| Principle | Implementation |
|-----------|---------------|
| **Overlay flags, not math penalties** | Structural exclusions (DQ-6, DQ-9) use orthogonal boolean flags — never score deductions |
| **Cross-dimensional independence** | DQ flags and readiness score are independent axes; a record can be high-quality AND low-readiness, or vice versa |
| **Explicit > implicit** | Every DQ issue is surfaced as a named flag column; nothing is silently buried |
| **Completeness-neutral** | Missing data contributes 0 (neutral), never negative. New/sparse records aren't penalized |
| **Real signals only** | Automation noise (DQ-8) is filtered at the data layer, not masked at the scoring layer |
| **Document everything** | This catalogue exists as both a developer reference and an in-app Knowledge Base tab |

---

## Cross-Reference: Personas That Test DQ Handling

| Persona | DQ Issues Tested | Expected Outcome |
|---------|-----------------|------------------|
| P5: Competitor Spy | DQ-6 | EXCLUDED (not scored low — removed) |
| P6: Bounced & Opted Out | DQ-9 | EXCLUDED (hard exclusion flags) |
| P7: Broken Conversion | DQ-1 | Flagged, entity resolution attempted |
| P8: The Bot | DQ-8 | Low engagement score (automation discounting) |
| P9: Re-MQL Carousel | DQ-10, DQ-3 | Moderate score (recent MQL, but no real engagement boost) |
| P4: Ghost CISO | DQ-7 | Cold tier (great profile, zero engagement — completeness doesn't help without action) |
