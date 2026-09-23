"""
Report generation and serialization module.
Outputs report matching the exact schema specified in the assignment specification.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, Union

from .models import SimulationResult


def format_report(simulation_result: SimulationResult, detailed: bool = False) -> Dict[str, Any]:
    """
    Constructs the report dictionary according to the specification.

    Default format matches the exact schema specified in the assignment PDF:
    {
      "A1": {"packages_delivered": 2, "total_distance": 121.21, "efficiency": 60.61},
      ...
      "best_agent": "A3"
    }

    Values are rounded to 2 decimal places in the final report.
    """
    report: Dict[str, Any] = {}

    for agent_id in sorted(simulation_result.agent_reports.keys()):
        summary = simulation_result.agent_reports[agent_id]
        agent_data: Dict[str, Any] = {
            "packages_delivered": summary.packages_delivered,
            "total_distance": round(summary.total_distance, 2),
            "efficiency": round(summary.efficiency, 2),
        }
        if detailed:
            agent_data["assigned_packages"] = list(summary.assigned_packages)

        report[agent_id] = agent_data

    report["best_agent"] = simulation_result.best_agent
    return report


def save_report(report_data: Dict[str, Any], output_path: Union[str, Path]) -> None:
    """
    Serializes report dictionary to disk as indented JSON.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)
        f.write("\n")


def generate_summary_text(simulation_result: SimulationResult) -> str:
    """
    Generates a concise, formatted console summary table of the simulation results.
    """
    lines = [
        "=" * 68,
        "             FASTBOX DELIVERY SIMULATION SUMMARY",
        "=" * 68,
        f"{'Agent':<8} {'Packages':<10} {'Distance':<16} {'Efficiency':<14} {'Assigned IDs'}",
        "-" * 68,
    ]

    for agent_id in sorted(simulation_result.agent_reports.keys()):
        rep = simulation_result.agent_reports[agent_id]
        pkg_list = ", ".join(rep.assigned_packages) if rep.assigned_packages else "None"
        if len(pkg_list) > 20:
            pkg_list = pkg_list[:17] + "..."
        lines.append(
            f"{agent_id:<8} {rep.packages_delivered:<10} {rep.total_distance:<16.2f} {rep.efficiency:<14.2f} {pkg_list}"
        )

    lines.append("-" * 68)
    lines.append(f"Total Packages Delivered: {simulation_result.total_packages_delivered}")
    lines.append(f"Best Agent (Most Efficient): {simulation_result.best_agent or 'None'}")
    lines.append("=" * 68)

    return "\n".join(lines)
