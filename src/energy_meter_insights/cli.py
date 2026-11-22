"""Command-line entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

from .pipeline import run
from .synthetic import generate


def main() -> int:
    parser = argparse.ArgumentParser(prog="energy-insights", description="Analyze interval meter readings from CSV.")
    sub = parser.add_subparsers(dest="command")
    analyze = sub.add_parser("analyze", help="validate and analyze an input CSV")
    analyze.add_argument("--input", type=Path, required=True)
    analyze.add_argument("--output-dir", type=Path, default=Path("output"))
    analyze.add_argument("--anomaly-multiplier", type=float, default=3.0)
    demo = sub.add_parser("demo", help="generate and analyze the synthetic example")
    demo.add_argument("--output-dir", type=Path, default=Path("output"))
    make_demo = sub.add_parser("make-demo", help="write synthetic interval readings")
    make_demo.add_argument("--output", type=Path, default=Path("data/demo_readings.csv"))
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "make-demo":
        print(f"Wrote {generate(args.output)} synthetic readings to {args.output}")
        return 0
    if args.command == "demo":
        sample = Path("data/demo_readings.csv")
        if not sample.exists():
            generate(sample)
        result = run(sample, args.output_dir)
    else:
        result = run(args.input, args.output_dir, args.anomaly_multiplier)
    print(f"Accepted {result['accepted_readings']} readings; wrote reports to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
