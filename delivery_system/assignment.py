"""
Package assignment module.
Maps packages to agents based on nearest initial distance to the package warehouse.
"""

from __future__ import annotations
from typing import Dict, List

from .models import Agent, Warehouse, Package, ValidationError
from .distance import calculate_distance


def assign_packages(
    agents: Dict[str, Agent],
    warehouses: Dict[str, Warehouse],
    packages: List[Package],
) -> Dict[str, List[Package]]:
    """
    Assigns each package to the nearest agent based on Euclidean distance
    from the agent's initial location to the package's pickup warehouse.

    Tie-breaking:
    When distances are identical, agents are chosen based on lexicographical
    order of agent ID (e.g., 'A1' before 'A2').

    Preserves package input order within each agent's assigned queue.
    Ensures every package is assigned to exactly one agent.
    """
    # Initialize assignment mapping for all agents (including those with 0 packages)
    assignments: Dict[str, List[Package]] = {agent_id: [] for agent_id in sorted(agents.keys())}

    if not packages:
        return assignments

    if not agents:
        raise ValidationError("Cannot assign packages: no delivery agents available.")

    assigned_pkg_ids: set[str] = set()

    for package in packages:
        warehouse = warehouses.get(package.warehouse_id)
        if not warehouse:
            raise ValidationError(
                f"Package '{package.id}' references warehouse '{package.warehouse_id}', which does not exist."
            )

        # Find the nearest agent to the warehouse
        # Tie-breaker key is (distance, agent_id)
        best_agent_id = min(
            agents.keys(),
            key=lambda ag_id: (
                calculate_distance(agents[ag_id].initial_location, warehouse.location),
                ag_id,
            ),
        )

        assignments[best_agent_id].append(package)
        assigned_pkg_ids.add(package.id)

    # Sanity checks
    if len(assigned_pkg_ids) != len(packages):
        raise ValidationError(
            f"Assignment mismatch: expected {len(packages)} assignments, got {len(assigned_pkg_ids)}"
        )

    return assignments
