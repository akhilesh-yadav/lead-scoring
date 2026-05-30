# Lessons Learned

## What Worked

1. **Layered pipeline architecture**: Breaking the scoring into 4 explicit layers (clean → features → score → rank) made debugging dramatically easier. When the tier distribution looked wrong, we could inspect feature distributions at Layer 2 without re-running the full pipeline.

2. **Orthogonal exclusion from the start**: Separating "is this record contactable?" from "is this record ready?" avoided the most common scoring trap where competitors and opted-out records pollute the model calibration.

3. **Exponential time-decay**: The 45-day half-life creates a natural "urgency gradient" that matches BDR workflow — records actively engaging this week float to the top without needing manual priority overrides.

4. **Automation filtering (DQ-8)**: Filtering to `is_responded=True` before computing engagement features removed the single largest source of score inflation. Without this, the median engagement count drops from 12 to 3 — exposing how much CRM "engagement" is just email automation running in the background.

## What Didn't Work (Dead Ends)

1. **Using `created_date` for anything**: Initially tried to use record age as a feature ("newer records might be hotter"). Abandoned immediately when we discovered 80% of leads share bulk ETL timestamps. The field is operationally meaningless for individual records.

2. **Attempting ML classification**: Spent 30 minutes exploring whether we could use lead conversion as a training signal. Problems: (a) conversion is a process outcome, not a quality signal, (b) converted leads are frozen, so any features derived from them reflect post-conversion state, (c) 35% conversion rate is too noisy for meaningful separation.

3. **Email-based entity resolution**: Attempted to link broken DQ-1 records via email matching. Resolution rate was 0% in our synthetic data because the broken links don't share emails with any contact (they were generated independently). In production, this would likely yield ~30-50% resolution. Worth implementing but shouldn't be trusted blindly.

4. **Equal weighting across all dimensions**: Initial prototype used 25/25/25/25 weighting. Result: too many CISO-at-Fortune-500 records with zero engagement ranked highly. The VP's requirement is clear: "worth a phone call **right now**" — which demands engagement recency dominance.

## Tradeoffs Accepted

| Tradeoff | Chose | Over | Because |
|----------|-------|------|---------|
| Simplicity vs. sophistication | Weighted formula | ML model | No training data, explainability required |
| Speed vs. accuracy | Batch scoring | Real-time | 1000 records; batch is fine for weekly list |
| Coverage vs. precision | Score everyone | Only score engaged records | VP wants to see the full population ranked |
| Automation discount vs. full exclusion | 30% penalty | Complete removal | Some automated touches indicate enrollment in a relevant program |
| Lead fairness vs. strict meritocracy | 15pt baseline account score | 0 for missing accounts | Prevents systematic lead disadvantage |

## What I'd Do Differently With More Time

1. **Build a proper entity resolution graph**: Use email + name + company fuzzy matching to link fragmented records before scoring. This would recover significant engagement signal currently lost to DQ-1 and DQ-2.

2. **Implement decay curves per engagement type**: A webinar attendance should decay slower than an email click. Currently using uniform decay regardless of engagement quality.

3. **Add temporal engagement patterns**: "3 touchpoints spread over 6 months" means something different than "3 touchpoints in 3 days." Burst detection would improve the momentum component.

4. **Validate against historical outcomes**: If we had access to "records that actually converted to opportunity", we could calibrate the component weights empirically rather than using domain judgment.

5. **A/B test the BDR workflow**: The real test isn't model accuracy — it's whether BDRs using this ranked list book more meetings than BDRs using the old MQL queue.
