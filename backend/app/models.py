from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InventoryBatch(StrictModel):
    batch_id: str = Field(min_length=1, max_length=64)
    commodity: str = Field(min_length=1, max_length=64)
    quantity_kg: float = Field(gt=0, le=1_000_000_000)
    shelf_life_hours: float = Field(ge=0, le=100_000)
    handling_notes: str = Field(default="", max_length=240)
    # An empty list means no batch-specific destination restriction.
    eligible_destinations: list[str] = Field(default_factory=list)

    @field_validator("batch_id", "commodity")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned


class Destination(StrictModel):
    destination_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=100)
    travel_hours: float = Field(ge=0, le=100_000)
    handling_hours: float = Field(ge=0, le=100_000)
    transport_cost_inr_per_kg: float = Field(ge=0, le=1_000_000)
    capacity_kg: float = Field(ge=0, le=1_000_000_000)
    demand_by_commodity: dict[str, float] = Field(default_factory=dict)
    price_by_commodity: dict[str, float] = Field(default_factory=dict)

    @field_validator("destination_id", "name")
    @classmethod
    def trim_destination_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned

    @field_validator("demand_by_commodity")
    @classmethod
    def nonnegative_demands(cls, value: dict[str, float]) -> dict[str, float]:
        if any(not key.strip() or amount < 0 for key, amount in value.items()):
            raise ValueError("demand commodity names must be nonblank and demand must be nonnegative")
        return {key.strip(): amount for key, amount in value.items()}

    @field_validator("price_by_commodity")
    @classmethod
    def nonnegative_prices(cls, value: dict[str, float]) -> dict[str, float]:
        if any(not key.strip() or price < 0 for key, price in value.items()):
            raise ValueError("price commodity names must be nonblank and prices must be nonnegative")
        return {key.strip(): price for key, price in value.items()}


class PlanInput(StrictModel):
    inventory: list[InventoryBatch]
    destinations: list[Destination]

    @model_validator(mode="after")
    def unique_ids_and_valid_eligibility(self) -> "PlanInput":
        batch_ids = [batch.batch_id for batch in self.inventory]
        if len(batch_ids) != len(set(batch_ids)):
            raise ValueError("batch_id values must be unique")
        destination_ids = [destination.destination_id for destination in self.destinations]
        if len(destination_ids) != len(set(destination_ids)):
            raise ValueError("destination_id values must be unique")
        known_destinations = set(destination_ids)
        for batch in self.inventory:
            unknown = sorted(set(batch.eligible_destinations) - known_destinations)
            if unknown:
                raise ValueError(
                    f"batch {batch.batch_id} has unknown eligible destination(s): {', '.join(unknown)}"
                )
        return self


class InputRequest(StrictModel):
    inputs: PlanInput


class Allocation(StrictModel):
    batch_id: str
    commodity: str
    destination_id: str
    destination_name: str
    quantity_kg: float
    travel_hours: float
    handling_hours: float
    arrival_hours: float
    shelf_life_remaining_on_arrival_hours: float
    selling_price_inr_per_kg: float
    transport_cost_inr_per_kg: float
    transport_cost_inr: float
    net_contribution_inr: float
    feasibility: Literal["feasible"] = "feasible"
    explanation: str


class MetricSet(StrictModel):
    total_available_kg: float
    quantity_delivered_kg: float
    allocated_kg: float
    unallocated_kg: float
    total_demand_kg: float
    unfulfilled_demand_kg: float
    demand_fulfillment_pct: float
    estimated_unsold_kg: float
    at_risk_kg: float
    physically_expired_kg: float | None
    gross_sales_inr: float
    transport_cost_inr: float
    discount_revenue_tradeoff_inr: float = 0.0
    other_operating_costs_inr: float = 0.0
    net_revenue_inr: float


class UnallocatedBatch(StrictModel):
    batch_id: str
    commodity: str
    remaining_kg: float
    shelf_life_hours: float
    reason: str


class PlanDiagnostics(StrictModel):
    solver_status: Literal["optimal", "feasible", "infeasible"]
    objective_net_contribution_inr: float
    rejected_by_shelf_life_kg: float
    rejected_by_eligibility_kg: float
    capacity_limited_kg: float
    capacity_limited_destinations: list[str]
    unallocated_batches: list[UnallocatedBatch]
    messages: list[str]


class StrategyPlan(StrictModel):
    strategy: Literal["optimized", "fefo_baseline"]
    status: Literal["feasible", "infeasible"]
    allocations: list[Allocation]
    metrics: MetricSet
    diagnostics: PlanDiagnostics


class MetricDifference(StrictModel):
    optimized_minus_baseline: float
    percent_vs_baseline: float | None


class DestinationSummary(StrictModel):
    destination_id: str
    name: str
    demand_kg: float
    allocated_kg: float
    unfulfilled_demand_kg: float


class ComparisonResult(StrictModel):
    baseline: StrategyPlan
    optimized: StrategyPlan
    differences: dict[str, MetricDifference]
    destination_summary: list[DestinationSummary]
    explanation: str


class ScenarioRequest(StrictModel):
    inputs: PlanInput
    travel_time_multiplier: float = Field(default=1.0, ge=0.5, le=2.0)
    demand_multiplier: float = Field(default=1.0, ge=0.5, le=2.0)
    capacity_multiplier: float = Field(default=1.0, ge=0.0, le=1.5)


class AllocationExportRequest(StrictModel):
    inputs: PlanInput
    strategy: Literal["optimized", "fefo_baseline"] = "optimized"


class ReportRequest(StrictModel):
    inputs: PlanInput
    scenario_label: str = Field(default="Current inputs", max_length=100)
