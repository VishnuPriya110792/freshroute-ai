from __future__ import annotations

from collections import defaultdict
from typing import Literal

import numpy as np
from scipy.optimize import linprog

from .models import (
    Allocation,
    InventoryBatch,
    PlanDiagnostics,
    PlanInput,
    StrategyPlan,
    UnallocatedBatch,
)
from .evaluation import evaluate_allocations

_EPS = 1e-7


def _is_eligible(batch: InventoryBatch, destination_id: str) -> bool:
    return not batch.eligible_destinations or destination_id in batch.eligible_destinations


def _edge_candidates(inputs: PlanInput) -> tuple[list[tuple[int, int]], dict[str, list[str]]]:
    edges: list[tuple[int, int]] = []
    excluded: dict[str, list[str]] = defaultdict(list)
    for bi, batch in enumerate(inputs.inventory):
        for di, destination in enumerate(inputs.destinations):
            demand = destination.demand_by_commodity.get(batch.commodity, 0.0)
            has_price = batch.commodity in destination.price_by_commodity
            if demand <= _EPS or not has_price:
                continue
            if not _is_eligible(batch, destination.destination_id):
                excluded[batch.batch_id].append(f"Not eligible for {destination.destination_id}")
                continue
            arrival = destination.travel_hours + destination.handling_hours
            if arrival - batch.shelf_life_hours > _EPS:
                excluded[batch.batch_id].append(
                    f"{destination.destination_id} needs {arrival:g} h; batch has {batch.shelf_life_hours:g} h"
                )
                continue
            edges.append((bi, di))
    return edges, excluded


def _make_allocation(
    batch: InventoryBatch,
    destination,
    quantity: float,
    strategy: str,
) -> Allocation:
    arrival = destination.travel_hours + destination.handling_hours
    remaining = max(0.0, batch.shelf_life_hours - arrival)
    price = destination.price_by_commodity[batch.commodity]
    cost = destination.transport_cost_inr_per_kg
    contribution = (price - cost) * quantity
    if strategy == "optimized":
        explanation = (
            f"Chosen by maximum net contribution: ₹{price:g}/kg selling price less "
            f"₹{cost:g}/kg transport. Eligible route; arrival in {arrival:g} h leaves "
            f"{remaining:g} estimated usable hours."
        )
    else:
        explanation = (
            f"FEFO priority: {batch.shelf_life_hours:g} estimated usable hours, then "
            f"route contribution and destination ID for tie-breaking. Arrival in {arrival:g} h "
            f"leaves {remaining:g} h; the route has demand and remaining capacity."
        )
    return Allocation(
        batch_id=batch.batch_id,
        commodity=batch.commodity,
        destination_id=destination.destination_id,
        destination_name=destination.name,
        quantity_kg=quantity,
        travel_hours=destination.travel_hours,
        handling_hours=destination.handling_hours,
        arrival_hours=arrival,
        shelf_life_remaining_on_arrival_hours=remaining,
        selling_price_inr_per_kg=price,
        transport_cost_inr_per_kg=cost,
        transport_cost_inr=cost * quantity,
        net_contribution_inr=contribution,
        explanation=explanation,
    )


def _diagnostics(inputs: PlanInput, allocations: list[Allocation], solver_status: Literal["optimal", "feasible", "infeasible"], objective: float, excluded: dict[str, list[str]]) -> PlanDiagnostics:
    allocated_by_batch: dict[str, float] = defaultdict(float)
    demand_used: dict[tuple[str, str], float] = defaultdict(float)
    capacity_used: dict[str, float] = defaultdict(float)
    for row in allocations:
        allocated_by_batch[row.batch_id] += row.quantity_kg
        demand_used[(row.destination_id, row.commodity)] += row.quantity_kg
        capacity_used[row.destination_id] += row.quantity_kg

    destination_by_id = {d.destination_id: d for d in inputs.destinations}
    unallocated: list[UnallocatedBatch] = []
    shelf_rejected = eligibility_rejected = capacity_limited = 0.0
    messages: list[str] = []
    for batch in sorted(inputs.inventory, key=lambda item: item.batch_id):
        remaining = max(0.0, batch.quantity_kg - allocated_by_batch[batch.batch_id])
        if remaining <= _EPS:
            continue
        demand_routes = [
            d for d in inputs.destinations
            if d.demand_by_commodity.get(batch.commodity, 0.0) > _EPS
            and batch.commodity in d.price_by_commodity
        ]
        eligible = [d for d in demand_routes if _is_eligible(batch, d.destination_id)]
        feasible = [
            d for d in eligible
            if d.travel_hours + d.handling_hours <= batch.shelf_life_hours + _EPS
        ]
        open_demand = [
            d for d in feasible
            if d.demand_by_commodity.get(batch.commodity, 0.0) - demand_used[(d.destination_id, batch.commodity)] > _EPS
        ]
        open_capacity = [
            d for d in open_demand
            if d.capacity_kg - capacity_used[d.destination_id] > _EPS
        ]
        if not demand_routes:
            reason = "No modeled destination demand and selling price for this commodity."
        elif not eligible:
            reason = "Destination restrictions exclude all markets with modeled demand."
            eligibility_rejected += remaining
        elif not feasible:
            reason = "All eligible destinations require more travel plus handling time than this batch's estimated shelf life."
            shelf_rejected += remaining
        elif not open_demand:
            reason = "Eligible feasible destination demand is already fulfilled."
        elif not open_capacity:
            reason = "Eligible feasible routes still have demand, but their shared planning-horizon capacity is exhausted."
            capacity_limited += remaining
        else:
            reason = "Feasible capacity remains, but this strategy leaves the stock unallocated under its decision rule."
        unallocated.append(UnallocatedBatch(
            batch_id=batch.batch_id,
            commodity=batch.commodity,
            remaining_kg=remaining,
            shelf_life_hours=batch.shelf_life_hours,
            reason=reason,
        ))

    capacity_destinations = sorted(
        d.destination_id for d in inputs.destinations
        if d.capacity_kg - capacity_used[d.destination_id] <= _EPS
    )
    if shelf_rejected > _EPS:
        messages.append(f"{shelf_rejected:g} kg remain without a shelf-life-feasible eligible destination.")
    if eligibility_rejected > _EPS:
        messages.append(f"{eligibility_rejected:g} kg remain because destination eligibility excludes all modeled demand markets.")
    if capacity_limited > _EPS:
        messages.append(f"Up to {capacity_limited:g} kg are blocked by exhausted route capacity while demand remains.")
    if capacity_destinations:
        messages.append("Capacity is binding at: " + ", ".join(capacity_destinations) + ".")
    if not messages:
        messages.append("No binding infeasibility was found; remaining stock is explained by fulfilled demand or the strategy rule.")
    return PlanDiagnostics(
        solver_status=solver_status,
        objective_net_contribution_inr=objective,
        rejected_by_shelf_life_kg=shelf_rejected,
        rejected_by_eligibility_kg=eligibility_rejected,
        capacity_limited_kg=capacity_limited,
        capacity_limited_destinations=capacity_destinations,
        unallocated_batches=unallocated,
        messages=messages,
    )


def _finish(inputs: PlanInput, allocations: list[Allocation], strategy: Literal["optimized", "fefo_baseline"], solver_status: Literal["optimal", "feasible", "infeasible"], objective: float, excluded: dict[str, list[str]]) -> StrategyPlan:
    metrics = evaluate_allocations(inputs, allocations)
    diagnostics = _diagnostics(inputs, allocations, solver_status, objective, excluded)
    return StrategyPlan(
        strategy=strategy,
        status="feasible" if solver_status != "infeasible" else "infeasible",
        allocations=allocations,
        metrics=metrics,
        diagnostics=diagnostics,
    )


def optimize(inputs: PlanInput) -> StrategyPlan:
    """Maximize total sales contribution less variable route cost with a continuous LP."""
    all_edges, excluded = _edge_candidates(inputs)
    edges = [
        (bi, di) for bi, di in all_edges
        if inputs.destinations[di].price_by_commodity[inputs.inventory[bi].commodity]
        - inputs.destinations[di].transport_cost_inr_per_kg > _EPS
    ]
    if not edges:
        return _finish(inputs, [], "optimized", "optimal", 0.0, excluded)

    batch_n, destination_n = len(inputs.inventory), len(inputs.destinations)
    demand_keys = sorted({
        (d.destination_id, commodity)
        for d in inputs.destinations for commodity, amount in d.demand_by_commodity.items()
        if amount > _EPS
    })
    demand_index = {key: i for i, key in enumerate(demand_keys)}
    route_index = {d.destination_id: i for i, d in enumerate(inputs.destinations)}
    row_count = batch_n + len(demand_keys) + destination_n
    matrix = np.zeros((row_count, len(edges)), dtype=float)
    bounds = np.zeros(row_count, dtype=float)
    for i, batch in enumerate(inputs.inventory):
        bounds[i] = batch.quantity_kg
    for key, i in demand_index.items():
        dest = next(d for d in inputs.destinations if d.destination_id == key[0])
        bounds[batch_n + i] = dest.demand_by_commodity[key[1]]
    for i, dest in enumerate(inputs.destinations):
        bounds[batch_n + len(demand_keys) + i] = dest.capacity_kg

    objective: list[float] = []
    for col, (bi, di) in enumerate(edges):
        batch, dest = inputs.inventory[bi], inputs.destinations[di]
        matrix[bi, col] = 1.0
        matrix[batch_n + demand_index[(dest.destination_id, batch.commodity)], col] = 1.0
        matrix[batch_n + len(demand_keys) + route_index[dest.destination_id], col] = 1.0
        margin = dest.price_by_commodity[batch.commodity] - dest.transport_cost_inr_per_kg
        objective.append(-margin)

    result = linprog(
        c=np.asarray(objective),
        A_ub=matrix,
        b_ub=bounds,
        bounds=(0, None),
        method="highs",
    )
    if not result.success or result.x is None:
        return _finish(inputs, [], "optimized", "infeasible", 0.0, excluded)

    rows: list[Allocation] = []
    for quantity, (bi, di) in zip(result.x, edges):
        if quantity > _EPS:
            rows.append(_make_allocation(inputs.inventory[bi], inputs.destinations[di], float(quantity), "optimized"))
    rows.sort(key=lambda row: (row.batch_id, row.destination_id))
    net = sum(row.net_contribution_inr for row in rows)
    return _finish(inputs, rows, "optimized", "optimal", net, excluded)


def fefo_baseline(inputs: PlanInput) -> StrategyPlan:
    """Greedy earliest-expiry-first dispatch with deterministic route tie-breaking."""
    _, excluded = _edge_candidates(inputs)
    demand_left = {
        (d.destination_id, commodity): amount
        for d in inputs.destinations for commodity, amount in d.demand_by_commodity.items()
    }
    capacity_left = {d.destination_id: d.capacity_kg for d in inputs.destinations}
    rows: list[Allocation] = []
    for batch in sorted(inputs.inventory, key=lambda item: (item.shelf_life_hours, item.batch_id)):
        candidates = [
            d for d in inputs.destinations
            if d.demand_by_commodity.get(batch.commodity, 0.0) > _EPS
            and batch.commodity in d.price_by_commodity
            and _is_eligible(batch, d.destination_id)
            and d.travel_hours + d.handling_hours <= batch.shelf_life_hours + _EPS
        ]
        candidates.sort(key=lambda d: (
            -(d.price_by_commodity[batch.commodity] - d.transport_cost_inr_per_kg),
            d.destination_id,
        ))
        remaining = batch.quantity_kg
        for dest in candidates:
            key = (dest.destination_id, batch.commodity)
            quantity = min(remaining, demand_left.get(key, 0.0), capacity_left[dest.destination_id])
            if quantity <= _EPS:
                continue
            rows.append(_make_allocation(batch, dest, quantity, "fefo_baseline"))
            remaining -= quantity
            demand_left[key] -= quantity
            capacity_left[dest.destination_id] -= quantity
            if remaining <= _EPS:
                break
    rows.sort(key=lambda row: (row.batch_id, row.destination_id))
    net = sum(row.net_contribution_inr for row in rows)
    return _finish(inputs, rows, "fefo_baseline", "feasible", net, excluded)
