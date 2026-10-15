from __future__ import annotations

from .models import PlanInput, StrategyPlan


def recommend_discounts(inputs: PlanInput, plan: StrategyPlan) -> list[dict]:
    """Rule-based price markdowns; no demand lift is assumed or claimed."""
    leftover = {batch.batch_id: batch.quantity_kg for batch in inputs.inventory}
    for allocation in plan.allocations:
        leftover[allocation.batch_id] = max(0.0, leftover[allocation.batch_id] - allocation.quantity_kg)
    recommendations: list[dict] = []
    for batch in sorted(inputs.inventory, key=lambda item: item.batch_id):
        remaining = leftover[batch.batch_id]
        if remaining <= 1e-6:
            continue
        routes = [
            destination for destination in inputs.destinations
            if destination.demand_by_commodity.get(batch.commodity, 0.0) > 0
            and batch.commodity in destination.price_by_commodity
            and (not batch.eligible_destinations or destination.destination_id in batch.eligible_destinations)
            and destination.travel_hours + destination.handling_hours <= batch.shelf_life_hours
        ]
        any_open_demand = any(
            destination.demand_by_commodity.get(batch.commodity, 0.0)
            - sum(a.quantity_kg for a in plan.allocations if a.destination_id == destination.destination_id and a.commodity == batch.commodity) > 1e-6
            for destination in routes
        )
        short_life = batch.shelf_life_hours <= 24
        no_feasible_sale = not routes or not any_open_demand
        if not (short_life or no_feasible_sale):
            continue
        if batch.shelf_life_hours <= 12:
            pct = 25.0
            reason = f"Only {batch.shelf_life_hours:g} estimated usable hours remain, so residual stock is at immediate shelf-life risk."
        elif batch.shelf_life_hours <= 24:
            pct = 15.0
            reason = f"Only {batch.shelf_life_hours:g} estimated usable hours remain and {remaining:g} kg is unallocated."
        else:
            pct = 10.0
            reason = "Residual stock has no remaining feasible modeled demand at the current price and route assumptions."
        available_prices = [d.price_by_commodity[batch.commodity] for d in routes]
        if not available_prices:
            continue
        reference_price = max(available_prices)
        recommendations.append({
            "batch_id": batch.batch_id,
            "commodity": batch.commodity,
            "unallocated_kg": remaining,
            "reference_price_inr_per_kg": reference_price,
            "recommended_discount_pct": pct,
            "discounted_price_inr_per_kg": reference_price * (1 - pct / 100.0),
            "estimated_revenue_tradeoff_inr": remaining * reference_price * pct / 100.0,
            "reason": reason,
            "disclosure": "Rule-based estimate only. Trade-off assumes the same residual volume sells at the lower price; no demand increase is modeled or promised.",
        })
    return recommendations
