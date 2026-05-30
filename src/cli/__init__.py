"""
CLI entry point for the Lead Scoring pipeline.
Usage:
    python -m lead_scorer generate [--records N]
    python -m lead_scorer score [--weights 0.4,0.25,0.2,0.15] [--half-life 45]
    python -m lead_scorer demo [--port 8501]
    python -m lead_scorer validate
"""
import argparse
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, PROJECT_ROOT)

RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")


def cmd_generate(args):
    """Generate synthetic CRM data."""
    sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts"))
    from generate_data import (
        generate_accounts,
        generate_campaign_members,
        generate_contacts,
        generate_leads,
        inject_personas,
    )

    output_dir = args.output
    os.makedirs(output_dir, exist_ok=True)

    print(f"Generating synthetic CRM data ({args.leads} leads, {args.contacts} contacts)...")
    accounts = generate_accounts()
    leads = generate_leads(accounts)
    contacts = generate_contacts(accounts, leads)
    campaign_members = generate_campaign_members(leads, contacts)
    leads, contacts = inject_personas(leads, contacts, accounts, campaign_members)

    accounts.to_csv(os.path.join(output_dir, "accounts.csv"), index=False)
    leads.to_csv(os.path.join(output_dir, "leads.csv"), index=False)
    contacts.to_csv(os.path.join(output_dir, "contacts.csv"), index=False)
    campaign_members.to_csv(os.path.join(output_dir, "campaign_members.csv"), index=False)

    print(f"Generated: {len(accounts)} accounts, {len(leads)} leads, "
          f"{len(contacts)} contacts, {len(campaign_members)} campaign members")
    print(f"Output: {output_dir}")


def cmd_score(args):
    """Run the scoring pipeline."""
    from src.pipeline.pipeline import ScoringWeights
    from src.pipeline.run_pipeline import run_pipeline
    from src.pipeline.stages.rank import TierConfig

    weights = ScoringWeights(
        engagement=args.weights[0],
        profile=args.weights[1],
        account=args.weights[2],
        momentum=args.weights[3],
    )
    tiers = TierConfig(
        hot_threshold=args.hot,
        warm_threshold=args.warm,
        nurture_threshold=args.nurture,
    )
    run_pipeline(data_dir=args.data_dir, output_dir=args.output_dir, weights=weights, tier_config=tiers)


def cmd_demo(args):
    """Launch the Streamlit demo application."""
    import subprocess
    app_path = os.path.join(PROJECT_ROOT, "src", "app", "main.py")
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", app_path,
        "--server.port", str(args.port),
        "--server.headless", "true",
    ])


def cmd_validate(args):
    """Run tests and validation."""
    import subprocess
    subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
                   cwd=PROJECT_ROOT)


def parse_weights(s):
    """Parse comma-separated weights string into list of floats."""
    parts = [float(x) for x in s.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("Weights must be 4 comma-separated floats (e.g., 0.4,0.25,0.2,0.15)")
    if abs(sum(parts) - 1.0) > 0.01:
        raise argparse.ArgumentTypeError(f"Weights must sum to 1.0, got {sum(parts)}")
    return parts


def main():
    parser = argparse.ArgumentParser(
        prog="lead-scorer",
        description="Lead/Contact Readiness Scoring Pipeline",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # generate
    gen_parser = subparsers.add_parser("generate", help="Generate synthetic CRM data")
    gen_parser.add_argument("--leads", type=int, default=600, help="Number of leads (default: 600)")
    gen_parser.add_argument("--contacts", type=int, default=400, help="Number of contacts (default: 400)")
    gen_parser.add_argument("--output", default=RAW_DIR, help="Output directory")

    # score
    score_parser = subparsers.add_parser("score", help="Run scoring pipeline")
    score_parser.add_argument("--weights", type=parse_weights, default=[0.4, 0.25, 0.2, 0.15],
                              help="Component weights: engagement,profile,account,momentum (default: 0.4,0.25,0.2,0.15)")
    score_parser.add_argument("--half-life", type=float, default=45.0, help="Decay half-life in days (default: 45)")
    score_parser.add_argument("--hot", type=float, default=70.0, help="Hot tier threshold (default: 70)")
    score_parser.add_argument("--warm", type=float, default=45.0, help="Warm tier threshold (default: 45)")
    score_parser.add_argument("--nurture", type=float, default=20.0, help="Nurture tier threshold (default: 20)")
    score_parser.add_argument("--data-dir", default=RAW_DIR, help="Raw data directory")
    score_parser.add_argument("--output-dir", default=PROCESSED_DIR, help="Output directory")

    # demo
    demo_parser = subparsers.add_parser("demo", help="Launch Streamlit demo app")
    demo_parser.add_argument("--port", type=int, default=8501, help="Port (default: 8501)")

    # validate
    subparsers.add_parser("validate", help="Run tests and validation")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    commands = {
        "generate": cmd_generate,
        "score": cmd_score,
        "demo": cmd_demo,
        "validate": cmd_validate,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
