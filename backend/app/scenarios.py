from __future__ import annotations

from .evaluation import compare_plans
from .models import PlanInput, ScenarioRequest
from .planner import fefo_baseline, optimize


def apply_scenario(inputs: PlanInput, request: ScenarioRequest) -> PlanInput:
    """Return a validated, independent copy; the caller's active input is never mutated."""
    updated = inputs.model_dump()
    for destination in updated["destinations"]:
        destination["travel_hours"] *= request.travel_time_multiplier
        destination["capacity_kg"] *= request.capacity_multiplier
        destination["demand_by_commodity"] = {
            commodity: amount * request.demand_multiplier
            for commodity, amount in destination["demand_by_commodity"].items()
        }
    return PlanInput.model_validate(updated)


def simulate(request: ScenarioRequest) -> dict:
    original = compare_plans(request.inputs, fefo_baseline(request.inputs), optimize(request.inputs))
    scenario_inputs = apply_scenario(request.inputs, request)
    scenario = compare_plans(scenario_inputs, fefo_baseline(scenario_inputs), optimize(scenario_inputs))

    before = original.optimized.metrics
    after = scenario.optimized.metrics
    metric_changes = {
        "quantity_delivered_kg": after.quantity_delivered_kg - before.quantity_delivered_kg,
        "demand_fulfillment_pct": after.demand_fulfillment_pct - before.demand_fulfillment_pct,
        "unallocated_kg": after.unallocated_kg - before.unallocated_kg,
        "at_risk_kg": after.at_risk_kg - before.at_risk_kg,
        "transport_cost_inr": after.transport_cost_inr - before.transport_cost_inr,
        "net_revenue_inr": after.net_revenue_inr - before.net_revenue_inr,
    }
    before_alloc = {(row.batch_id, row.destination_id): row.quantity_kg for row in original.optimized.allocations}
    after_alloc = {(row.batch_id, row.destination_id): row.quantity_kg for row in scenario.optimized.allocations}
    allocation_changes = []
    for batch_id, destination_id in sorted(set(before_alloc) | set(after_alloc)):
        delta = after_alloc.get((batch_id, destination_id), 0.0) - before_alloc.get((batch_id, destination_id), 0.0)
        if abs(delta) > 1e-6:
            allocation_changes.append({"batch_id": batch_id, "destination_id": destination_id, "quantity_change_kg": delta})

    explanations: list[str] = []
    if request.travel_time_multiplier != 1:
        explanations.append(f"Travel hours changed by {(request.travel_time_multiplier - 1) * 100:+g}%; this changes arrival feasibility and remaining shelf life.")
    if request.demand_multiplier != 1:
        explanations.append(f"Demand changed by {(request.demand_multiplier - 1) * 100:+g}%; this changes market demand ceilings.")
    if request.capacity_multiplier != 1:
        explanations.append(f"Shared route capacity changed by {(request.capacity_multiplier - 1) * 100:+g}%; this changes the kilograms available across the planning horizon.")
    if not explanations:
        explanations.append("All scenario multipliers are 1.0, so the scenario uses the original inputs.")
    return {
        "scenario_inputs": scenario_inputs,
        "multipliers": {
            "travel_time_multiplier": request.travel_time_multiplier,
            "demand_multiplier": request.demand_multiplier,
            "capacity_multiplier": request.capacity_multiplier,
        },
        "original": original,
        "scenario": scenario,
        "metric_changes": metric_changes,
        "allocation_changes": allocation_changes,
        "explanations": explanations,
    }
