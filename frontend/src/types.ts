export interface InventoryBatch {
  batch_id: string
  commodity: string
  quantity_kg: number
  shelf_life_hours: number
  handling_notes: string
  eligible_destinations: string[]
}

export interface Destination {
  destination_id: string
  name: string
  travel_hours: number
  handling_hours: number
  transport_cost_inr_per_kg: number
  capacity_kg: number
  demand_by_commodity: Record<string, number>
  price_by_commodity: Record<string, number>
}

export interface PlanInput {
  inventory: InventoryBatch[]
  destinations: Destination[]
}

export interface Allocation {
  batch_id: string
  commodity: string
  destination_id: string
  destination_name: string
  quantity_kg: number
  travel_hours: number
  handling_hours: number
  arrival_hours: number
  shelf_life_remaining_on_arrival_hours: number
  selling_price_inr_per_kg: number
  transport_cost_inr_per_kg: number
  transport_cost_inr: number
  net_contribution_inr: number
  feasibility: 'feasible'
  explanation: string
}

export interface MetricSet {
  total_available_kg: number
  quantity_delivered_kg: number
  allocated_kg: number
  unallocated_kg: number
  total_demand_kg: number
  unfulfilled_demand_kg: number
  demand_fulfillment_pct: number
  estimated_unsold_kg: number
  at_risk_kg: number
  physically_expired_kg: number | null
  gross_sales_inr: number
  transport_cost_inr: number
  discount_revenue_tradeoff_inr: number
  other_operating_costs_inr: number
  net_revenue_inr: number
}

export interface UnallocatedBatch {
  batch_id: string
  commodity: string
  remaining_kg: number
  shelf_life_hours: number
  reason: string
}

export interface PlanDiagnostics {
  solver_status: 'optimal' | 'feasible' | 'infeasible'
  objective_net_contribution_inr: number
  rejected_by_shelf_life_kg: number
  rejected_by_eligibility_kg: number
  capacity_limited_kg: number
  capacity_limited_destinations: string[]
  unallocated_batches: UnallocatedBatch[]
  messages: string[]
}

export interface StrategyPlan {
  strategy: 'optimized' | 'fefo_baseline'
  status: 'feasible' | 'infeasible'
  allocations: Allocation[]
  metrics: MetricSet
  diagnostics: PlanDiagnostics
}

export interface ComparisonResult {
  baseline: StrategyPlan
  optimized: StrategyPlan
  differences: Record<string, { optimized_minus_baseline: number; percent_vs_baseline: number | null }>
  destination_summary: { destination_id: string; name: string; demand_kg: number; allocated_kg: number; unfulfilled_demand_kg: number }[]
  explanation: string
}

export interface DiscountRecommendation {
  batch_id: string
  commodity: string
  unallocated_kg: number
  reference_price_inr_per_kg: number
  recommended_discount_pct: number
  discounted_price_inr_per_kg: number
  estimated_revenue_tradeoff_inr: number
  reason: string
  disclosure: string
}

export interface ScenarioResult {
  scenario_inputs: PlanInput
  multipliers: {
    travel_time_multiplier: number
    demand_multiplier: number
    capacity_multiplier: number
  }
  original: ComparisonResult
  scenario: ComparisonResult
  metric_changes: Record<string, number>
  allocation_changes: { batch_id: string; destination_id: string; quantity_change_kg: number }[]
  explanations: string[]
}
