from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from backend.app.data import SAMPLE_DATA, sample_input
from backend.app.evaluation import compare_plans
from backend.app.models import InventoryBatch, PlanInput, ScenarioRequest
from backend.app.planner import fefo_baseline, optimize
from backend.app.scenarios import simulate


def test_optimizer_respects_inventory_demand_capacity_eligibility_and_shelf_life():
    inputs = sample_input()
    result = optimize(inputs)
    assert result.status == "feasible"
    by_batch = {batch.batch_id: 0.0 for batch in inputs.inventory}
    by_market_commodity: dict[tuple[str, str], float] = {}
    by_market: dict[str, float] = {}
    batches = {batch.batch_id: batch for batch in inputs.inventory}
    destinations = {destination.destination_id: destination for destination in inputs.destinations}
    for row in result.allocations:
        by_batch[row.batch_id] += row.quantity_kg
        by_market_commodity[(row.destination_id, row.commodity)] = by_market_commodity.get((row.destination_id, row.commodity), 0) + row.quantity_kg
        by_market[row.destination_id] = by_market.get(row.destination_id, 0) + row.quantity_kg
        batch = batches[row.batch_id]
        destination = destinations[row.destination_id]
        assert destination.travel_hours + destination.handling_hours <= batch.shelf_life_hours + 1e-7
        assert not batch.eligible_destinations or row.destination_id in batch.eligible_destinations
        assert row.quantity_kg >= 0
    for batch in inputs.inventory:
        assert by_batch[batch.batch_id] <= batch.quantity_kg + 1e-6
    for destination in inputs.destinations:
        assert by_market.get(destination.destination_id, 0) <= destination.capacity_kg + 1e-6
        for commodity, demand in destination.demand_by_commodity.items():
            assert by_market_commodity.get((destination.destination_id, commodity), 0) <= demand + 1e-6
    assert abs(result.metrics.allocated_kg + result.metrics.unallocated_kg - result.metrics.total_available_kg) < 1e-6


def tiny_input() -> PlanInput:
    return PlanInput.model_validate({
        "inventory": [{"batch_id": "B1", "commodity": "Tomatoes", "quantity_kg": 10, "shelf_life_hours": 12, "handling_notes": "", "eligible_destinations": ["M1"]}],
        "destinations": [{"destination_id": "M1", "name": "Market 1", "travel_hours": 2, "handling_hours": 1, "transport_cost_inr_per_kg": 3, "capacity_kg": 8, "demand_by_commodity": {"Tomatoes": 6}, "price_by_commodity": {"Tomatoes": 20}}],
    })


def test_manual_revenue_transport_and_net_calculation():
    result = optimize(tiny_input())
    assert len(result.allocations) == 1
    assert result.allocations[0].quantity_kg == pytest.approx(6)
    assert result.metrics.gross_sales_inr == pytest.approx(120)
    assert result.metrics.transport_cost_inr == pytest.approx(18)
    assert result.metrics.net_revenue_inr == pytest.approx(102)
    assert result.metrics.unallocated_kg == pytest.approx(4)
    assert result.metrics.demand_fulfillment_pct == pytest.approx(100)


def test_negative_inventory_quantity_is_rejected():
    with pytest.raises(ValidationError):
        InventoryBatch.model_validate({"batch_id": "B", "commodity": "Tomatoes", "quantity_kg": -1, "shelf_life_hours": 12})


def test_zero_demand_produces_zero_optimized_allocation():
    raw = tiny_input().model_dump()
    raw["destinations"][0]["demand_by_commodity"]["Tomatoes"] = 0
    result = optimize(PlanInput.model_validate(raw))
    assert result.allocations == []
    assert result.metrics.quantity_delivered_kg == 0
    assert result.metrics.demand_fulfillment_pct == 0


def test_zero_capacity_prevents_transport():
    raw = tiny_input().model_dump()
    raw["destinations"][0]["capacity_kg"] = 0
    result = optimize(PlanInput.model_validate(raw))
    assert result.allocations == []
    assert result.diagnostics.capacity_limited_kg == pytest.approx(10)


def test_ineligible_destination_is_rejected():
    raw = tiny_input().model_dump()
    raw["destinations"][0]["price_by_commodity"]["Tomatoes"] = 100
    raw["destinations"].append({
        "destination_id": "M2", "name": "Market 2", "travel_hours": 1, "handling_hours": 1,
        "transport_cost_inr_per_kg": 2, "capacity_kg": 10,
        "demand_by_commodity": {}, "price_by_commodity": {},
    })
    raw["inventory"][0]["eligible_destinations"] = ["M2"]
    result = optimize(PlanInput.model_validate(raw))
    assert result.allocations == []
    assert result.diagnostics.rejected_by_eligibility_kg == pytest.approx(10)


def test_shelf_life_infeasibility_is_structured_and_does_not_create_allocations():
    raw = tiny_input().model_dump()
    raw["inventory"][0]["shelf_life_hours"] = 2
    inputs = PlanInput.model_validate(raw)
    result = optimize(inputs)
    assert result.allocations == []
    assert result.diagnostics.rejected_by_shelf_life_kg == pytest.approx(10)
    assert result.diagnostics.unallocated_batches[0].reason


def test_baseline_and_optimizer_use_same_economic_inputs_and_reconcile():
    inputs = sample_input()
    baseline = fefo_baseline(inputs)
    optimized = optimize(inputs)
    for result in (baseline, optimized):
        assert result.metrics.net_revenue_inr == pytest.approx(result.metrics.gross_sales_inr - result.metrics.transport_cost_inr)
        assert result.metrics.allocated_kg + result.metrics.unallocated_kg == pytest.approx(result.metrics.total_available_kg)
        for row in result.allocations:
            destination = next(d for d in inputs.destinations if d.destination_id == row.destination_id)
            assert row.selling_price_inr_per_kg == destination.price_by_commodity[row.commodity]
            assert row.transport_cost_inr_per_kg == destination.transport_cost_inr_per_kg
    compared = compare_plans(inputs, baseline, optimized)
    assert compared.differences["net_revenue_inr"].optimized_minus_baseline == pytest.approx(optimized.metrics.net_revenue_inr - baseline.metrics.net_revenue_inr)


def test_identical_inputs_return_deterministic_allocations():
    inputs = sample_input()
    first = optimize(inputs)
    second = optimize(inputs)
    signature = lambda plan: [(row.batch_id, row.destination_id, round(row.quantity_kg, 8)) for row in plan.allocations]
    assert signature(first) == signature(second)


def test_scenario_changes_computation_without_mutating_original_inputs():
    raw = tiny_input().model_dump()
    raw["inventory"][0]["shelf_life_hours"] = 4
    inputs = PlanInput.model_validate(raw)
    original_dump = inputs.model_dump()
    request = ScenarioRequest(inputs=inputs, travel_time_multiplier=2.0)
    result = simulate(request)
    assert result["original"].optimized.metrics.quantity_delivered_kg == pytest.approx(6)
    assert result["scenario"].optimized.metrics.quantity_delivered_kg == pytest.approx(0)
    assert result["metric_changes"]["quantity_delivered_kg"] < 0
    assert inputs.model_dump() == original_dump


def test_fefo_can_match_optimizer_on_delivered_quantity():
    inputs = sample_input()
    comparison = compare_plans(inputs, fefo_baseline(inputs), optimize(inputs))
    # Matching the optimized plan on delivered kg is a valid competitive baseline outcome.
    assert comparison.baseline.metrics.quantity_delivered_kg == pytest.approx(comparison.optimized.metrics.quantity_delivered_kg)
