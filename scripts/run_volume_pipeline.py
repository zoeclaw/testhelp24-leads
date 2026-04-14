#!/usr/bin/env python3
"""
Single-command volume-first pipeline runner.

Official run order:
1. Collect sources
2. Validate + deduplicate
3. Enrich contacts
4. Discover decision-makers
5. Score + tier for outreach
"""

import argparse
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"


def run_step(label: str, command: list[str]):
    print("\n" + "=" * 78)
    print(f"▶ {label}")
    print("=" * 78)
    print("$", " ".join(command))
    subprocess.run(command, cwd=BASE_DIR, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the volume-first lead pipeline")
    parser.add_argument("--cities", nargs="*", default=[], help="Cities to collect")
    parser.add_argument("--with-google-maps", action="store_true")
    parser.add_argument("--with-kompass", action="store_true")
    parser.add_argument("--kompass-pages", type=int, default=2)
    parser.add_argument("--skip-collect", action="store_true")
    parser.add_argument("--skip-enrich", action="store_true")
    parser.add_argument("--skip-decision-makers", action="store_true")
    parser.add_argument("--decision-maker-limit", type=int, default=0)
    return parser.parse_args()


def main():
    args = parse_args()
    python = sys.executable

    if not args.skip_collect:
        collect_cmd = [python, str(SCRIPTS_DIR / "collect_volume_sources.py")]
        if args.cities:
            collect_cmd += ["--cities", *args.cities]
        if args.with_google_maps:
            collect_cmd.append("--with-google-maps")
        if args.with_kompass:
            collect_cmd.append("--with-kompass")
            collect_cmd += ["--kompass-pages", str(args.kompass_pages)]
        run_step("Collect leads", collect_cmd)

    run_step("Validate and deduplicate raw leads", [python, str(SCRIPTS_DIR / "pipeline.py")])

    if not args.skip_enrich:
        run_step("Enrich contacts", [python, str(SCRIPTS_DIR / "enrich_leads.py")])

    if not args.skip_decision_makers:
        decision_cmd = [python, str(SCRIPTS_DIR / "discover_decision_makers.py")]
        if args.decision_maker_limit > 0:
            decision_cmd += ["--limit", str(args.decision_maker_limit)]
        run_step("Discover decision-makers", decision_cmd)

    run_step("Score and tier leads", [python, str(SCRIPTS_DIR / "generate_pipeline.py")])

    print("\n" + "=" * 78)
    print("✅ Volume-first pipeline complete")
    print("=" * 78)


if __name__ == "__main__":
    main()
