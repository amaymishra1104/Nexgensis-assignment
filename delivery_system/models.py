"""
Domain models and exception hierarchy for the Nexgensis Delivery System.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional


class DeliverySystemError(Exception):
    """Base exception class for all delivery system errors."""
    pass


class ParserError(DeliverySystemError):
    """Raised when JSON file reading or syntax parsing fails."""
    pass


class ValidationError(DeliverySystemError):
    """Raised when input data schema or business rules are violated."""
    pass


class SimulationError(DeliverySystemError):
    """Raised when an error occurs during delivery simulation."""
    pass


@dataclass(frozen=True)
class Location:
    """Represents a 2D Cartesian coordinate point (x, y)."""
    x: float
    y: float

    def __post_init__(self) -> None:
        if not isinstance(self.x, (int, float)) or not isinstance(self.y, (int, float)):
            raise ValidationError(f"Coordinates must be numbers, got x={type(self.x).__name__}, y={type(self.y).__name__}")
        if self.x != self.x or self.y != self.y:  # NaN check
            raise ValidationError("Coordinates cannot be NaN")

    def as_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)

    def __str__(self) -> str:
        return f"({self.x}, {self.y})"


@dataclass(frozen=True)
class Warehouse:
    """Represents a fulfillment warehouse."""
    id: str
    location: Location

    def __post_init__(self) -> None:
        if not self.id or not isinstance(self.id, str):
            raise ValidationError("Warehouse id must be a non-empty string")


@dataclass
class Agent:
    """Represents a delivery agent."""
    id: str
    initial_location: Location
    current_location: Location = field(init=False)

    def __post_init__(self) -> None:
        if not self.id or not isinstance(self.id, str):
            raise ValidationError("Agent id must be a non-empty string")
        self.current_location = self.initial_location

    def reset_to_initial(self) -> None:
        """Resets the agent's current position back to its start location."""
        self.current_location = self.initial_location


@dataclass(frozen=True)
class Package:
    """Represents a package to be picked up from a warehouse and delivered to a destination."""
    id: str
    warehouse_id: str
    destination: Location

    def __post_init__(self) -> None:
        if not self.id or not isinstance(self.id, str):
            raise ValidationError("Package id must be a non-empty string")
        if not self.warehouse_id or not isinstance(self.warehouse_id, str):
            raise ValidationError("Package warehouse_id must be a non-empty string")


@dataclass
class AgentDeliverySummary:
    """Delivery and performance metrics for a single agent."""
    agent_id: str
    packages_delivered: int
    total_distance: float
    efficiency: float
    assigned_packages: List[str] = field(default_factory=list)


@dataclass
class SimulationResult:
    """Aggregated output metrics from the delivery simulation run."""
    agent_reports: Dict[str, AgentDeliverySummary]
    best_agent: Optional[str]
    total_packages_delivered: int
