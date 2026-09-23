"""
Input parsing and validation module for the Delivery System.
Normalizes heterogeneous JSON structures into strongly-typed domain models.
"""

from __future__ import annotations
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

from .models import Location, Warehouse, Agent, Package, ParserError, ValidationError


def parse_location(raw_coords: Any, context: str = "Location") -> Location:
    """
    Parses and validates a 2D coordinate array or tuple [x, y].
    """
    if not isinstance(raw_coords, (list, tuple)):
        raise ValidationError(f"{context}: expected list or tuple of 2 coordinates, got {type(raw_coords).__name__}")
    if len(raw_coords) != 2:
        raise ValidationError(f"{context}: expected exactly 2 coordinates [x, y], got {len(raw_coords)}")

    x, y = raw_coords
    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
        raise ValidationError(f"{context}: coordinates must be numeric, got ({type(x).__name__}, {type(y).__name__})")

    if math.isnan(x) or math.isnan(y) or math.isinf(x) or math.isinf(y):
        raise ValidationError(f"{context}: coordinates cannot be NaN or infinite")

    return Location(x=float(x), y=float(y))


def parse_warehouses(raw_warehouses: Any) -> Dict[str, Warehouse]:
    """
    Parses warehouses supporting both:
    1. Dict format: {"W1": [0, 0], "W2": [50, 75]}
    2. List format: [{"id": "W1", "location": [0, 0]}, ...]
    """
    if raw_warehouses is None:
        raise ValidationError("Missing 'warehouses' field in input data")

    warehouses: Dict[str, Warehouse] = {}

    if isinstance(raw_warehouses, dict):
        for wh_id, loc_data in raw_warehouses.items():
            if not isinstance(wh_id, str) or not wh_id.strip():
                raise ValidationError(f"Invalid warehouse id: {wh_id!r}")
            loc = parse_location(loc_data, context=f"Warehouse '{wh_id}' location")
            warehouses[wh_id] = Warehouse(id=wh_id, location=loc)

    elif isinstance(raw_warehouses, list):
        for idx, item in enumerate(raw_warehouses):
            if not isinstance(item, dict):
                raise ValidationError(f"Warehouse entry at index {idx} must be a dictionary")
            wh_id = item.get("id")
            if not wh_id or not isinstance(wh_id, str):
                raise ValidationError(f"Warehouse entry at index {idx} missing valid 'id'")
            if wh_id in warehouses:
                raise ValidationError(f"Duplicate warehouse id detected: '{wh_id}'")
            loc_data = item.get("location")
            if loc_data is None:
                raise ValidationError(f"Warehouse '{wh_id}' missing 'location'")
            loc = parse_location(loc_data, context=f"Warehouse '{wh_id}' location")
            warehouses[wh_id] = Warehouse(id=wh_id, location=loc)

    else:
        raise ValidationError(f"'warehouses' must be a dict or list, got {type(raw_warehouses).__name__}")

    return warehouses


def parse_agents(raw_agents: Any) -> Dict[str, Agent]:
    """
    Parses agents supporting both:
    1. Dict format: {"A1": [5, 5], "A2": [60, 60]}
    2. List format: [{"id": "A1", "location": [5, 5]}, ...]
    """
    if raw_agents is None:
        raise ValidationError("Missing 'agents' field in input data")

    agents: Dict[str, Agent] = {}

    if isinstance(raw_agents, dict):
        for ag_id, loc_data in raw_agents.items():
            if not isinstance(ag_id, str) or not ag_id.strip():
                raise ValidationError(f"Invalid agent id: {ag_id!r}")
            loc = parse_location(loc_data, context=f"Agent '{ag_id}' location")
            agents[ag_id] = Agent(id=ag_id, initial_location=loc)

    elif isinstance(raw_agents, list):
        for idx, item in enumerate(raw_agents):
            if not isinstance(item, dict):
                raise ValidationError(f"Agent entry at index {idx} must be a dictionary")
            ag_id = item.get("id")
            if not ag_id or not isinstance(ag_id, str):
                raise ValidationError(f"Agent entry at index {idx} missing valid 'id'")
            if ag_id in agents:
                raise ValidationError(f"Duplicate agent id detected: '{ag_id}'")
            loc_data = item.get("location")
            if loc_data is None:
                raise ValidationError(f"Agent '{ag_id}' missing 'location'")
            loc = parse_location(loc_data, context=f"Agent '{ag_id}' location")
            agents[ag_id] = Agent(id=ag_id, initial_location=loc)

    else:
        raise ValidationError(f"'agents' must be a dict or list, got {type(raw_agents).__name__}")

    return agents


def parse_packages(raw_packages: Any, valid_warehouse_ids: set[str]) -> List[Package]:
    """
    Parses package records, validating warehouse linkages and destination coordinates.
    Normalizes key aliases: 'warehouse' vs 'warehouse_id', 'destination' vs 'location'.
    """
    if raw_packages is None:
        raise ValidationError("Missing 'packages' field in input data")

    if not isinstance(raw_packages, list):
        raise ValidationError(f"'packages' must be a list, got {type(raw_packages).__name__}")

    packages: List[Package] = []
    seen_package_ids: set[str] = set()

    for idx, item in enumerate(raw_packages):
        if not isinstance(item, dict):
            raise ValidationError(f"Package entry at index {idx} must be a dictionary")

        pkg_id = item.get("id")
        if not pkg_id or not isinstance(pkg_id, str):
            raise ValidationError(f"Package entry at index {idx} missing valid 'id'")
        if pkg_id in seen_package_ids:
            raise ValidationError(f"Duplicate package id detected: '{pkg_id}'")
        seen_package_ids.add(pkg_id)

        # Normalize warehouse key alias
        wh_id = item.get("warehouse") or item.get("warehouse_id")
        if not wh_id or not isinstance(wh_id, str):
            raise ValidationError(f"Package '{pkg_id}' missing valid warehouse reference ('warehouse' or 'warehouse_id')")
        if wh_id not in valid_warehouse_ids:
            raise ValidationError(f"Package '{pkg_id}' references unknown warehouse '{wh_id}'")

        # Destination coordinates
        dest_data = item.get("destination") or item.get("location")
        if dest_data is None:
            raise ValidationError(f"Package '{pkg_id}' missing 'destination'")
        dest_loc = parse_location(dest_data, context=f"Package '{pkg_id}' destination")

        packages.append(Package(id=pkg_id, warehouse_id=wh_id, destination=dest_loc))

    return packages


def parse_input_data(data: Any) -> Tuple[Dict[str, Warehouse], Dict[str, Agent], List[Package]]:
    """
    Validates and parses loaded JSON object into normalized domain objects.
    Enforces business validation rules.
    """
    if not isinstance(data, dict):
        raise ValidationError(f"Root JSON input must be an object/dict, got {type(data).__name__}")

    warehouses = parse_warehouses(data.get("warehouses"))
    agents = parse_agents(data.get("agents"))
    packages = parse_packages(data.get("packages"), set(warehouses.keys()))

    # Validate business invariants
    if packages and not agents:
        raise ValidationError("Packages exist to deliver, but no delivery agents are available.")

    if packages and not warehouses:
        raise ValidationError("Packages exist to deliver, but no fulfillment warehouses are available.")

    return warehouses, agents, packages


def load_input_data(file_path: Union[str, Path]) -> Tuple[Dict[str, Warehouse], Dict[str, Agent], List[Package]]:
    """
    Reads a JSON file from disk and parses it into domain entities.
    """
    path = Path(file_path)
    if not path.is_file():
        raise ParserError(f"Input file not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ParserError(f"Invalid JSON syntax in {path}: {exc}") from exc
    except Exception as exc:
        raise ParserError(f"Failed to read file {path}: {exc}") from exc

    return parse_input_data(raw_data)
