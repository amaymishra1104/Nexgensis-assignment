# Nexgensis Delivery System

A clean, modular Python logistics simulation system implementing the Nexgensis Technologies Python Developer Assignment (FastBox Delivery Simulator).

---

## Overview

The **Nexgensis Delivery System** models operations for a delivery company (**FastBox**). Given a set of fulfillment warehouses, delivery agents with initial positions, and packages to be dispatched, the system:
1. Normalizes and validates diverse input JSON formats.
2. Optimally maps each package to the nearest delivery agent based on Euclidean distance to its pickup warehouse.
3. Simulates realistic sequential agent routing where each agent starts at their initial position, travels to the warehouse for package pickup, delivers to the destination, and initiates subsequent assigned deliveries directly from that dropoff location without artificial resets.
4. Computes exact Euclidean travel distances, delivery counts, and efficiency scores.
5. Generates the required JSON report identifying per-agent metrics and the overall top-performing agent.

---

## Features

- **Heterogeneous JSON Schema Normalization**: Seamlessly ingests both dictionary-based and list-based schemas for warehouses and agents, as well as aliased keys (`warehouse` vs `warehouse_id`, `destination` vs `location`).
- **Strict Validation Layer**: Validates coordinate types (rejects non-numeric values and booleans), dimensions, duplicate IDs, non-existent warehouse links, NaN/Infinity values, and non-empty agent fleets.
- **Deterministic Assignment Engine**: Employs Euclidean distance nearest-neighbor assignment with deterministic lexicographical tie-breaking by agent ID (`A1` before `A2`).
- **Continuous Agent Routing Model**: Accurate physical simulation where an agent's location updates to the destination of each delivered package before proceeding to the next assigned pickup.
- **Zero-Delivery Safety**: Agents receiving 0 packages are handled gracefully with `packages_delivered = 0`, `total_distance = 0.0`, and `efficiency = 0.0` (protected against zero-division errors and excluded from `best_agent` selection).
- **Exact Output Schema**: Conforms to the required output format specified in the assignment specification, with distance and efficiency rounded to 2 decimal places.
- **Bonus Capabilities**:
  - **ASCII Map Visualization**: 2D ASCII grid rendering of warehouses, agents, and package destinations (`--visualize`).
  - **CSV Export**: Performance metrics exported to CSV for reporting (`--export-csv`).
- **Zero External Runtime Dependencies**: Core system runs solely on the Python standard library; only `pytest` is used for automated testing.

---

## Architecture

The project is structured with modular separation of concerns:

```text
nexgensis-delivery-system/
│
├── main.py                     # Command-line interface and entry point
├── delivery_system/            # Core package
│   ├── __init__.py             # Public API exports
│   ├── models.py               # Domain models, dataclasses, and custom exceptions
│   ├── distance.py             # Pure Euclidean distance calculation
│   ├── parser.py               # Input loading, normalization, and validation
│   ├── assignment.py           # Nearest-agent assignment & tie-breaking logic
│   ├── simulation.py           # Physical route simulation and metrics collection
│   ├── report.py               # Output JSON formatting, summary, and serialization
│   └── bonus.py                # ASCII map rendering and CSV performance export
│
├── tests/
│   ├── __init__.py
│   └── test_delivery_system.py # Comprehensive pytest test suite (28 tests)
│
├── data/                       # Canonical test datasets
│   ├── base_case.json
│   └── test_cases/
│       ├── test_case_1.json ... test_case_10.json
│
├── Python Assignment(Delivery System).pdf # Assignment specification
├── report.json                 # Generated sample report
├── requirements.txt            # Test dependency specification (pytest)
├── .gitignore                  # Git ignore specification
└── README.md                   # System documentation
```

### Module Responsibilities

1. **`delivery_system.models`**: Defines immutable value objects (`Location`), entities (`Warehouse`, `Agent`, `Package`), result structures (`AgentDeliverySummary`, `SimulationResult`), and a structured exception hierarchy (`DeliverySystemError`, `ParserError`, `ValidationError`, `SimulationError`).
2. **`delivery_system.distance`**: Pure function computing standard Euclidean distance between 2D coordinates.
3. **`delivery_system.parser`**: Normalizes divergent JSON representations (lists vs dicts, key aliases) into domain objects while performing data validation.
4. **`delivery_system.assignment`**: Matches packages to agents based on distance from the agent's initial coordinates to the package's pickup warehouse.
5. **`delivery_system.simulation`**: Executes the physical travel loop, tracks package deliveries, enforces single-delivery constraints, and evaluates efficiency.
6. **`delivery_system.report`**: Formats simulation metrics into the final JSON specification and renders console summaries.
7. **`delivery_system.bonus`**: Provides ASCII route rendering and CSV performance export.

---

## Algorithm

### 1. Distance Calculation
For two coordinates $(x_1, y_1)$ and $(x_2, y_2)$, the distance is calculated using standard Euclidean distance:
$$\text{distance} = \sqrt{(x_2 - x_1)^2 + (y_2 - y_1)^2}$$
All intermediate calculations preserve full IEEE 754 floating-point precision without premature rounding.

### 2. Agent Assignment
- For each package $P_i$ originating at warehouse $W(P_i)$, compute the Euclidean distance from the initial position of every agent $A_j$ to $W(P_i)$.
- Select the agent minimizing $(d(A_j^{\text{init}}, W(P_i)), \text{ID}(A_j))$.
- This guarantees deterministic assignment even if multiple agents are equidistant from the warehouse.
- Packages are queued for each agent in the order they appear in the input file.

### 3. Delivery Simulation
For each agent with an assigned list of packages:
- The agent begins at their `initial_location`.
- For the first package:
  - Leg 1: Agent moves from initial location to pickup warehouse ($d_1 = \text{dist}(\text{current\_loc}, \text{warehouse})$).
  - Leg 2: Agent moves from warehouse to dropoff destination ($d_2 = \text{dist}(\text{warehouse}, \text{dest})$).
  - Agent's physical position is updated: $\text{current\_loc} = \text{dest}$.
- For subsequent packages:
  - Leg 1: Agent moves from their current dropoff location to the next pickup warehouse.
  - Leg 2: Agent moves from warehouse to destination.
  - Position updates to the new destination.
- **The agent never resets to their start location between deliveries.**
- Total distance is the exact sum of all legs: $\sum (d_1 + d_2)$.

### 4. Efficiency Calculation
$$\text{efficiency} = \frac{\text{total\_distance}}{\text{packages\_delivered}}$$
- A lower efficiency score indicates superior performance (fewer distance units consumed per delivery).
- If an agent delivered $0$ packages, efficiency is defined as $0.0$ to avoid zero-division errors.
- **`best_agent` selection**: Evaluated among active agents with $\text{packages\_delivered} \ge 1$. The agent with the minimum efficiency score is chosen (with lexicographical agent ID tie-breaking). If no packages were delivered by any agent, `best_agent` is `null`.

### 5. Reporting
Generates a JSON document matching the exact specification:
```json
{
  "A1": {
    "packages_delivered": 2,
    "total_distance": 121.21,
    "efficiency": 60.61
  },
  "A2": {
    "packages_delivered": 2,
    "total_distance": 79.21,
    "efficiency": 39.60
  },
  "A3": {
    "packages_delivered": 1,
    "total_distance": 14.14,
    "efficiency": 14.14
  },
  "best_agent": "A3"
}
```
`total_distance` and `efficiency` are rounded to 2 decimal places in the final report.

---

## Assumptions

| Dimension | Engineering Decision & Rationale |
| :--- | :--- |
| **Agent Movement** | Agents start at their initial location. After delivering package $k$, the agent remains at destination $k$. The subsequent package pickup originates from destination $k$. Agents are **not** reset to start between deliveries. |
| **Package Ordering** | When no routing priority is specified, packages assigned to an agent are serviced strictly in their original input order. |
| **Tie-Breaking** | If two or more agents have identical distance to a warehouse, deterministic tie-breaking chooses the agent with the smallest lexicographical ID (`A1` < `A2` < `A3`). |
| **Efficiency Metric** | Defined as $\frac{\text{total\_distance}}{\text{packages\_delivered}}$. Lower values represent better performance. |
| **Zero-Delivery Agents** | Inactive agents are reported with `packages_delivered: 0`, `total_distance: 0.0`, `efficiency: 0.0`. They are excluded from `best_agent` consideration so an idle agent is never crowned the best performer over an active delivery agent. |
| **Input Normalization** | Handled transparently by `delivery_system/parser.py`: supports both dict mappings (`{"W1": [x, y]}`) and list objects (`[{"id": "W1", "location": [x, y]}]`), as well as key aliases (`warehouse` vs `warehouse_id`, `destination` vs `location`). |
| **Delivery Uniqueness** | The simulation strictly asserts that every package is delivered exactly once. Duplicate deliveries or omitted packages trigger explicit errors. |
| **Floating Point Precision**| All distance summations and divisions are computed at full 64-bit IEEE 754 precision. Only the final output values are rounded to 2 decimal places. |

---

## How to Run

### Basic Run (Base Case)
```bash
python main.py --input data/base_case.json --output report.json
```

Or using default arguments:
```bash
python main.py
```

### Running Test Cases
Run against any of the 10 provided test cases:
```bash
python main.py --input data/test_cases/test_case_1.json --output report_1.json
```

### Running with Bonus Flags
```bash
# Render ASCII map in console
python main.py --input data/base_case.json --visualize

# Export performance metrics to CSV
python main.py --input data/base_case.json --export-csv performance.csv

# Detailed report (includes assigned package IDs)
python main.py --input data/base_case.json --detailed
```

---

## How to Test

Run the full test suite using `pytest`:

```bash
pytest -q
```

All 28 tests pass:
```text
............................                                             [100%]
28 passed in 0.35s
```

### Test Coverage Highlights

The automated test suite verifies:
1. **Euclidean distance**: 3-4-5 right triangles, 5-12-13 triangles, zero distance, negative coordinates, precision without intermediate rounding.
2. **Nearest-agent assignment**: Proximity matching from agent start location to warehouse.
3. **Tie-breaking**: Equidistant agents resolved by alphabetical/lexicographical order.
4. **Multiple package handling**: Queuing multiple packages per agent in input order.
5. **Continuous agent movement**: Accurate coordinate transitions across sequential delivery legs.
6. **Zero-delivery agents**: Zero division safety, correct metric output, exclusion from best agent.
7. **Validation & error detection**: Duplicate package IDs, non-existent warehouses, malformed/non-numeric coordinates (including strict boolean coordinate rejection), empty agents.
8. **Schema variants**: Both dictionary and list representations for warehouses and agents.
9. **Full pipeline execution on Base Case**: Exact verification of outputs for `base_case.json`.
10. **All 10 supplied test cases**: Parametrized automated test running against `test_case_1.json` through `test_case_10.json`.
11. **CLI end-to-end integration**: Exit code 0 on valid inputs, non-zero exit on errors.
12. **Bonus feature verification**: CSV exporter and ASCII map generator.

---

## Design Decisions

1. **Standard Library Runtime**: The core delivery system utilizes only Python 3 standard library modules (`math`, `json`, `pathlib`, `dataclasses`, `typing`, `argparse`, `csv`). This ensures 100% portability without external dependency conflicts.
2. **Immutable Value Objects**: `Location`, `Warehouse`, and `Package` are defined as frozen dataclasses to guarantee immutability throughout the pipeline.
3. **Explicit Error Hierarchy**: A custom exception hierarchy rooted at `DeliverySystemError` differentiates parser issues, schema validation errors, and simulation invariants.
4. **Canonical Datasets**: Canonical test scenarios are organized cleanly under `data/` and `data/test_cases/`.
