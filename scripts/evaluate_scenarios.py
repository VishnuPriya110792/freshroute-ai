from __future__ import annotations

import json
from copy import deepcopy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.data import SAMPLE_DATA
from backend.app.evaluation import compare_plans
from backend.app.models import PlanInput
from backend.app.planner import fefo_baseline, optimize


def build_scenarios() -> dict[str, dict]:
    source = deepcopy(SAMPLE_DATA)
    scenarios: dict[str, dict] = {"normal_operations": deepcopy(source)}

    short = deepcopy(source)
    for row in short["inventory"]:
        row["shelf_life_hours"] = max(2, row["shelf_life_hours"] * 0.20)
    scenarios["short_remaining_shelf_life"] = short

    spike = deepcopy(source)
    for destination in spike["destinations"]:
        destination["demand_by_commodity"] = {name: value * 1.5 for name, value in destination["demand_by_commodity"].items()}
    scenarios["demand_spike"] = spike

    delay = deepcopy(source)
    for destination in delay["destinations"]:
        destination["travel_hours"] += 14
    scenarios["transport_delay"] = delay

    reduced = deepcopy(source)
    for destination in reduced["destinations"]:
        destination["capacity_kg"] *= 0.5
    scenarios["reduced_vehicle_capacity"] = reduced

    low_margin = deepcopy(source)
    for destination in low_margin["destinations"]:
        destination["transport_cost_inr_per_kg"] += 45
    scenarios["low_margin_fefo_delivers_more"] = low_margin
    return scenarios


def main() -> None:
    report = {}
    for name, raw in build_scenarios().items():
        inputs = PlanInput.model_validate(raw)
        comparison = compare_plans(inputs, fefo_baseline(inputs), optimize(inputs))
        base, optimized = comparison.baseline.metrics, comparison.optimized.metrics
        report[name] = {
            "baseline": {
                "delivered_kg": round(base.quantity_delivered_kg, 3),
                "unallocated_kg": round(base.unallocated_kg, 3),
                "transport_cost_inr": round(base.transport_cost_inr, 2),
                "net_revenue_inr": round(base.net_revenue_inr, 2),
            },
            "optimized": {
                "delivered_kg": round(optimized.quantity_delivered_kg, 3),
                "unallocated_kg": round(optimized.unallocated_kg, 3),
                "transport_cost_inr": round(optimized.transport_cost_inr, 2),
                "net_revenue_inr": round(optimized.net_revenue_inr, 2),
            },
            "optimized_minus_baseline": {
                "delivered_kg": round(optimized.quantity_delivered_kg - base.quantity_delivered_kg, 3),
                "transport_cost_inr": round(optimized.transport_cost_inr - base.transport_cost_inr, 2),
                "net_revenue_inr": round(optimized.net_revenue_inr - base.net_revenue_inr, 2),
            },
        }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
