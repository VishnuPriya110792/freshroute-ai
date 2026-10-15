from __future__ import annotations

from collections import defaultdict

from .models import Allocation, ComparisonResult, DestinationSummary, MetricDifference, MetricSet, PlanInput, StrategyPlan


def evaluate_allocations(inputs: PlanInput, allocations: list[Allocation]) -> MetricSet:
    """Shared evaluator; unallocated is projected unsold at cutoff, not physical spoilage."""
    total_stock = sum(batch.quantity_kg for batch in inputs.inventory)
    delivered = sum(row.quantity_kg for row in allocations)
    unallocated_by_batch: dict[str, float] = {batch.batch_id: batch.quantity_kg for batch in inputs.inventory}
    for row in allocations:
        unallocated_by_batch[row.batch_id] = max(0.0, unallocated_by_batch[row.batch_id] - row.quantity_kg)
    total_demand = sum(sum(destination.demand_by_commodity.values()) for destination in inputs.destinations)
    gross_sales = sum(row.quantity_kg * row.selling_price_inr_per_kg for row in allocations)
    transport_cost = sum(row.transport_cost_inr for row in allocations)
    unallocated = max(0.0, total_stock - delivered)
    at_risk = sum(
        unallocated_by_batch[batch.batch_id]
        for batch in inputs.inventory
        if batch.shelf_life_hours <= 24.0
    )
    return MetricSet(
        total_available_kg=total_stock,
        quantity_delivered_kg=delivered,
        allocated_kg=delivered,
        unallocated_kg=unallocated,
        total_demand_kg=total_demand,
        unfulfilled_demand_kg=max(0.0, total_demand - delivered),
        demand_fulfillment_pct=(delivered / total_demand * 100.0) if total_demand > 0 else 0.0,
        estimated_unsold_kg=unallocated,
        at_risk_kg=at_risk,
        physically_expired_kg=None,
        gross_sales_inr=gross_sales,
        transport_cost_inr=transport_cost,
        discount_revenue_tradeoff_inr=0.0,
        other_operating_costs_inr=0.0,
        net_revenue_inr=gross_sales - transport_cost,
    )


def compare_plans(inputs: PlanInput, baseline: StrategyPlan, optimized: StrategyPlan) -> ComparisonResult:
    fields = {
        "quantity_delivered_kg": (optimized.metrics.quantity_delivered_kg, baseline.metrics.quantity_delivered_kg),
        "demand_fulfillment_pct": (optimized.metrics.demand_fulfillment_pct, baseline.metrics.demand_fulfillment_pct),
        "unallocated_kg": (optimized.metrics.unallocated_kg, baseline.metrics.unallocated_kg),
        "estimated_unsold_kg": (optimized.metrics.estimated_unsold_kg, baseline.metrics.estimated_unsold_kg),
        "at_risk_kg": (optimized.metrics.at_risk_kg, baseline.metrics.at_risk_kg),
        "gross_sales_inr": (optimized.metrics.gross_sales_inr, baseline.metrics.gross_sales_inr),
        "transport_cost_inr": (optimized.metrics.transport_cost_inr, baseline.metrics.transport_cost_inr),
        "net_revenue_inr": (optimized.metrics.net_revenue_inr, baseline.metrics.net_revenue_inr),
    }
    differences: dict[str, MetricDifference] = {}
    for name, (new, old) in fields.items():
        delta = new - old
        differences[name] = MetricDifference(
            optimized_minus_baseline=delta,
            percent_vs_baseline=(delta / abs(old) * 100.0) if abs(old) > 1e-9 else None,
        )
    allocated_by_destination: dict[str, float] = defaultdict(float)
    for row in optimized.allocations:
        allocated_by_destination[row.destination_id] += row.quantity_kg
    destination_summary = [
        DestinationSummary(
            destination_id=destination.destination_id,
            name=destination.name,
            demand_kg=sum(destination.demand_by_commodity.values()),
            allocated_kg=allocated_by_destination[destination.destination_id],
            unfulfilled_demand_kg=max(0.0, sum(destination.demand_by_commodity.values()) - allocated_by_destination[destination.destination_id]),
        )
        for destination in sorted(inputs.destinations, key=lambda item: item.destination_id)
    ]
    return ComparisonResult(
        baseline=baseline,
        optimized=optimized,
        differences=differences,
        destination_summary=destination_summary,
        explanation=(
            "Both strategies use identical inventory, demand, shelf-life, eligibility, route capacity, "
            "prices and transport costs. Percentage differences are omitted when the baseline denominator is zero."
        ),
    )
