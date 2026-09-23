"""
Bonus extensions for the FastBox Delivery Simulator:
1. Route / entity visualization in ASCII grid.
2. CSV export of agent performance and top performer.
3. Realistic random delivery delays.
4. Dynamic mid-day agent arrival handler.
"""

from __future__ import annotations
import csv
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from .models import Agent, Warehouse, Package, Location, SimulationResult
from .distance import calculate_distance


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


def simulate_with_delays(
    agents: Dict[str, Agent],
    warehouses: Dict[str, Warehouse],
    assignments: Dict[str, List[Package]],
    seed: Optional[int] = 42,
    min_delay_mins: float = 2.0,
    max_delay_mins: float = 15.0,
) -> Dict[str, Dict[str, float]]:
    """
    Bonus: Simulates delivery operations with random traffic / handling delays.
    Returns per-agent travel time and delay breakdowns in minutes.
    Assumes an average travel speed of 40 distance-units per hour (0.67 units/min).
    """
    rng = random.Random(seed)
    speed_units_per_min = 40.0 / 60.0
    results: Dict[str, Dict[str, float]] = {}

    for agent_id, assigned in assignments.items():
        agent = agents[agent_id]
        curr_loc = agent.initial_location
        total_dist = 0.0
        total_delay = 0.0

        for pkg in assigned:
            wh = warehouses[pkg.warehouse_id]
            d1 = calculate_distance(curr_loc, wh.location)
            d2 = calculate_distance(wh.location, pkg.destination)
            total_dist += (d1 + d2)
            curr_loc = pkg.destination

            delay = rng.uniform(min_delay_mins, max_delay_mins)
            total_delay += delay

        travel_time_mins = total_dist / speed_units_per_min if speed_units_per_min > 0 else 0.0
        total_time_mins = travel_time_mins + total_delay

        results[agent_id] = {
            "packages_delivered": float(len(assigned)),
            "distance": round(total_dist, 2),
            "travel_time_minutes": round(travel_time_mins, 2),
            "delay_minutes": round(total_delay, 2),
            "total_time_minutes": round(total_time_mins, 2),
        }

    return results


def handle_midday_agent_arrival(
    existing_agents: Dict[str, Agent],
    new_agent_id: str,
    new_agent_loc: Location,
    remaining_packages: List[Package],
    warehouses: Dict[str, Warehouse],
) -> Dict[str, Agent]:
    """
    Bonus: Incorporates a newly joined delivery agent mid-day into the active fleet.
    """
    updated_agents = dict(existing_agents)
    new_agent = Agent(id=new_agent_id, initial_location=new_agent_loc)
    updated_agents[new_agent_id] = new_agent
    return updated_agents
