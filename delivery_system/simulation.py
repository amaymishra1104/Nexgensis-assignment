"""
Delivery simulation engine.
Executes physical movement of agents fulfilling assigned packages,
tracks metrics, and verifies integrity.
"""

from __future__ import annotations
from typing import Dict, List, Optional

from .models import (
    Agent,
    Warehouse,
    Package,
    AgentDeliverySummary,
    SimulationResult,
    SimulationError,
)
from .distance import calculate_distance


def simulate_deliveries(
    agents: Dict[str, Agent],
    warehouses: Dict[str, Warehouse],
    assignments: Dict[str, List[Package]],
) -> SimulationResult:
    """
    Simulates package deliveries for all agents.

    Movement rules for each agent:
    - Agent starts at its initial location.
    - For package 1:
        Agent initial location -> package warehouse -> package destination
        Agent's current location becomes package destination.
    - For package 2+:
        Agent current location -> package warehouse -> package destination
        Agent's current location updates to package destination.
    - Agent does NOT reset to original position between packages.

    Calculates:
    - total_distance: Sum of all legs traveled.
    - packages_delivered: Count of packages completed.
    - efficiency: total_distance / packages_delivered (or 0.0 if 0 deliveries).
    - best_agent: Agent with the minimum efficiency score among active agents.
    """
    agent_reports: Dict[str, AgentDeliverySummary] = {}
    delivered_package_ids: set[str] = set()

    for agent_id in sorted(agents.keys()):
        agent = agents[agent_id]
        agent.reset_to_initial()

        assigned = assignments.get(agent_id, [])
        total_distance = 0.0
        current_loc = agent.initial_location

        for pkg in assigned:
            warehouse = warehouses[pkg.warehouse_id]

            # Leg 1: current location to pickup warehouse
            leg1 = calculate_distance(current_loc, warehouse.location)

            # Leg 2: warehouse to dropoff destination
            leg2 = calculate_distance(warehouse.location, pkg.destination)

            total_distance += (leg1 + leg2)
            current_loc = pkg.destination
            agent.current_location = current_loc

            if pkg.id in delivered_package_ids:
                raise SimulationError(f"Duplicate delivery detected for package '{pkg.id}'")
            delivered_package_ids.add(pkg.id)

        pkg_count = len(assigned)
        if pkg_count > 0:
            efficiency = total_distance / pkg_count
        else:
            efficiency = 0.0

        agent_reports[agent_id] = AgentDeliverySummary(
            agent_id=agent_id,
            packages_delivered=pkg_count,
            total_distance=total_distance,
            efficiency=efficiency,
            assigned_packages=[p.id for p in assigned],
        )

    # Determine best agent (most efficient = lowest distance per delivered package)
    # Only agents that delivered >= 1 package are candidates
    active_candidates = [
        rep for rep in agent_reports.values() if rep.packages_delivered > 0
    ]

    best_agent: Optional[str] = None
    if active_candidates:
        best_rep = min(
            active_candidates,
            key=lambda rep: (rep.efficiency, rep.agent_id),
        )
        best_agent = best_rep.agent_id

    # Post-condition verification
    expected_total_packages = sum(len(pkgs) for pkgs in assignments.values())
    if len(delivered_package_ids) != expected_total_packages:
        raise SimulationError(
            f"Delivery count mismatch: expected {expected_total_packages}, delivered {len(delivered_package_ids)}"
        )

    return SimulationResult(
        agent_reports=agent_reports,
        best_agent=best_agent,
        total_packages_delivered=len(delivered_package_ids),
    )
