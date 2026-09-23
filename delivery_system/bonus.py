"""
Bonus extensions for the FastBox Delivery Simulator:
1. Route and entity visualization in an ASCII grid (--visualize).
2. CSV export of agent performance and metrics (--export-csv).
"""

from __future__ import annotations
import csv
from pathlib import Path
from typing import Dict, List, Tuple, Union

from .models import Agent, Warehouse, Package, SimulationResult


def export_performance_to_csv(
    simulation_result: SimulationResult,
    csv_path: Union[str, Path],
    only_top_performer: bool = False,
) -> None:
    """
    Exports agent simulation metrics to a CSV file.
    Optionally filters to only the top-performing agent.
    """
    path = Path(csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["agent_id", "packages_delivered", "total_distance", "efficiency", "is_best_agent", "assigned_packages"])

        for agent_id in sorted(simulation_result.agent_reports.keys()):
            rep = simulation_result.agent_reports[agent_id]
            is_best = (agent_id == simulation_result.best_agent)
            if only_top_performer and not is_best:
                continue
            writer.writerow([
                rep.agent_id,
                rep.packages_delivered,
                f"{rep.total_distance:.2f}",
                f"{rep.efficiency:.2f}",
                "YES" if is_best else "NO",
                ";".join(rep.assigned_packages),
            ])


def render_ascii_map(
    warehouses: Dict[str, Warehouse],
    agents: Dict[str, Agent],
    packages: List[Package],
    grid_width: int = 40,
    grid_height: int = 20,
) -> str:
    """
    Visualizes entities (Warehouses 'W', Agents 'A', Destinations 'D') in an ASCII grid.
    Scales coordinates dynamically into the grid dimensions.
    """
    all_points: List[Tuple[float, float]] = []
    for w in warehouses.values():
        all_points.append(w.location.as_tuple())
    for a in agents.values():
        all_points.append(a.initial_location.as_tuple())
    for p in packages:
        all_points.append(p.destination.as_tuple())

    if not all_points:
        return "[Empty Map: No entities to display]"

    min_x = min(p[0] for p in all_points)
    max_x = max(p[0] for p in all_points)
    min_y = min(p[1] for p in all_points)
    max_y = max(p[1] for p in all_points)

    range_x = max(max_x - min_x, 1.0)
    range_y = max(max_y - min_y, 1.0)

    # 2D character canvas
    canvas = [["." for _ in range(grid_width)] for _ in range(grid_height)]

    def to_grid(x: float, y: float) -> Tuple[int, int]:
        gx = int(((x - min_x) / range_x) * (grid_width - 1))
        # Invert Y so highest coordinate is at top of grid
        gy = int((1.0 - ((y - min_y) / range_y)) * (grid_height - 1))
        return max(0, min(grid_width - 1, gx)), max(0, min(grid_height - 1, gy))

    # Mark destinations 'D'
    for p in packages:
        gx, gy = to_grid(p.destination.x, p.destination.y)
        canvas[gy][gx] = "D"

    # Mark warehouses 'W'
    for w in warehouses.values():
        gx, gy = to_grid(w.location.x, w.location.y)
        canvas[gy][gx] = "W"

    # Mark agents 'A'
    for a in agents.values():
        gx, gy = to_grid(a.initial_location.x, a.initial_location.y)
        canvas[gy][gx] = "A"

    lines = [
        f"--- ASCII Map ({grid_width}x{grid_height}) [X: {min_x:.0f}..{max_x:.0f}, Y: {min_y:.0f}..{max_y:.0f}] ---",
        "Legend: 'W' = Warehouse, 'A' = Agent Start, 'D' = Package Destination, '.' = Open Space",
        "+" + "-" * grid_width + "+",
    ]
    for row in canvas:
        lines.append("|" + "".join(row) + "|")
    lines.append("+" + "-" * grid_width + "+")

    return "\n".join(lines)



