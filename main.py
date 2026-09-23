#!/usr/bin/env python3
"""
Nexgensis Delivery System CLI
Main entry point for running delivery simulation and generating reports.
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path

from delivery_system.parser import load_input_data
from delivery_system.assignment import assign_packages
from delivery_system.simulation import simulate_deliveries
from delivery_system.report import format_report, save_report, generate_summary_text
from delivery_system.models import DeliverySystemError
from delivery_system.bonus import render_ascii_map, export_performance_to_csv


def find_default_input() -> str:
    """Finds sensible default input file path."""
    candidate_paths = [
        Path("data/base_case.json"),
        Path("base_case.json"),
    ]
    for path in candidate_paths:
        if path.is_file():
            return str(path)
    return "data/base_case.json"


def parse_arguments() -> argparse.Namespace:
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(
        description="FastBox Delivery System - Package assignment and routing simulator.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input",
        "-i",
        dest="input_file",
        default=find_default_input(),
        help="Path to the input JSON file containing warehouses, agents, and packages.",
    )
    parser.add_argument(
        "--output",
        "-o",
        dest="output_file",
        default="report.json",
        help="Path where the output report JSON will be saved.",
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Include detailed package assignment lists in the report JSON.",
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Render a 2D ASCII map of warehouses, agents, and delivery destinations.",
    )
    parser.add_argument(
        "--export-csv",
        dest="csv_file",
        default=None,
        help="Optional path to export agent performance metrics to a CSV file.",
    )

    return parser.parse_args()


def run_pipeline(
    input_file: str,
    output_file: str,
    detailed: bool = False,
    visualize: bool = False,
    csv_file: str | None = None,
) -> int:
    """
    Executes the complete delivery simulation pipeline.
    Returns 0 on success, non-zero integer on error.
    """
    try:
        # 1. Load and validate input
        warehouses, agents, packages = load_input_data(input_file)

        # 2. Assign packages to nearest agents
        assignments = assign_packages(agents, warehouses, packages)

        # 3. Simulate deliveries
        simulation_result = simulate_deliveries(agents, warehouses, assignments)

        # 4. Generate and save report JSON
        report_data = format_report(simulation_result, detailed=detailed)
        save_report(report_data, output_file)

        # 5. Print summary table to console
        summary_text = generate_summary_text(simulation_result)
        print(summary_text)
        print(f"\nReport successfully generated and saved to: {output_file}")

        # Optional ASCII visualization
        if visualize:
            print("\n" + render_ascii_map(warehouses, agents, packages))

        # Optional CSV export
        if csv_file:
            export_performance_to_csv(simulation_result, csv_file)
            print(f"Performance metrics exported to CSV: {csv_file}")

        return 0

    except DeliverySystemError as exc:
        print(f"\n[ERROR] Delivery System Failure: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"\n[ERROR] File Not Found: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"\n[ERROR] Unexpected error: {exc}", file=sys.stderr)
        return 1


def main() -> None:
    """CLI entry point."""
    args = parse_arguments()
    exit_code = run_pipeline(
        input_file=args.input_file,
        output_file=args.output_file,
        detailed=args.detailed,
        visualize=args.visualize,
        csv_file=args.csv_file,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
