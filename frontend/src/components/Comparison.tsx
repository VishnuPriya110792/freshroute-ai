import { ArrowDownRight, ArrowUpRight, GitCompareArrows, Info } from 'lucide-react'
import type { ComparisonResult } from '../types'

const definitions: Record<string, string> = {
  quantity_delivered_kg: 'Kilograms assigned to feasible deliveries.',
  demand_fulfillment_pct: 'Delivered kilograms divided by total modeled destination demand.',
  unallocated_kg: 'Inventory left at the modeled planning cutoff; this is not confirmed spoilage.',
  estimated_unsold_kg: 'Defined here as unallocated inventory at the planning cutoff.',
  at_risk_kg: 'Unallocated stock with at most 24 estimated usable hours remaining.',
  gross_sales_inr: 'Allocated kilograms × destination selling price/kg.',
  transport_cost_inr: 'Allocated kilograms × destination route cost/kg.',
  net_revenue_inr: 'Gross sales minus transport cost; no other operating cost is modeled.',
}
const labels: Record<string, string> = {
  quantity_delivered_kg: 'Quantity delivered', demand_fulfillment_pct: 'Demand fulfillment', unallocated_kg: 'Unallocated stock',
  estimated_unsold_kg: 'Projected unsold', at_risk_kg: 'At-risk quantity', gross_sales_inr: 'Gross sales',
  transport_cost_inr: 'Transport cost', net_revenue_inr: 'Net revenue',
}
const formatValue = (name: string, value: number) => name.endsWith('_inr') ? `₹${value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}` : name.endsWith('_pct') ? `${value.toFixed(1)}%` : `${value.toLocaleString('en-IN', { maximumFractionDigits: 1 })} kg`
type Props = { comparison: ComparisonResult | null }

export default function Comparison({ comparison }: Props) {
  return <>
    <section className="page-heading"><div><div className="eyebrow">STRATEGY REVIEW <span className="eyebrow-divider">/</span> SAME INPUTS</div><h1>Baseline vs. optimized</h1><p>A reproducible FEFO rule and the contribution-maximizing plan, evaluated under identical constraints and economics.</p></div></section>
    {!comparison ? <div className="empty-card panel"><span className="empty-card-icon"><GitCompareArrows size={24} /></span><h2>Comparison awaits a plan</h2><p>Generate a distribution plan to calculate both strategies from your current inputs.</p></div> : <>
      <div className="strategy-cards"><article className="strategy-card"><div className="strategy-card-top"><span className="strategy-index">01</span><span className="strategy-chip">DOCUMENTED RULE</span></div><h2>FEFO baseline</h2><p>Assigns the shortest estimated remaining shelf life first. For each batch, routes are ranked by net contribution/kg, then destination ID. It obeys the same demand, stock, capacity, eligibility, and arrival constraints.</p><div className="strategy-result"><strong>{formatValue('net_revenue_inr', comparison.baseline.metrics.net_revenue_inr)}</strong><span>net revenue</span></div></article>
        <article className="strategy-card strategy-optimized"><div className="strategy-card-top"><span className="strategy-index">02</span><span className="strategy-chip chip-green">SCIPY LP</span></div><h2>Optimized allocation</h2><p>Maximizes expected contribution across all feasible batch-market assignments. It may leave stock unallocated when demand, capacity, shelf life, or margin does not support a shipment.</p><div className="strategy-result"><strong>{formatValue('net_revenue_inr', comparison.optimized.metrics.net_revenue_inr)}</strong><span>net revenue</span></div></article></div>
      <section className="panel comparison-panel"><div className="panel-heading"><div><span className="section-kicker">CALCULATED OUTCOMES</span><h2>What changed</h2><p>Positive/negative directions are shown as calculated; no metric is guaranteed to improve.</p></div></div><div className="table-scroll"><table className="data-table comparison-table"><thead><tr><th>Metric</th><th>FEFO baseline</th><th>Optimized</th><th>Optimized − baseline</th><th>Difference</th></tr></thead><tbody>{Object.keys(labels).map((key) => {
        const baseline = comparison.baseline.metrics[key as keyof typeof comparison.baseline.metrics] as number
        const optimized = comparison.optimized.metrics[key as keyof typeof comparison.optimized.metrics] as number
        const delta = comparison.differences[key]
        const goodWhenHigher = ['quantity_delivered_kg', 'demand_fulfillment_pct', 'gross_sales_inr', 'net_revenue_inr'].includes(key)
        const goodWhenLower = ['unallocated_kg', 'estimated_unsold_kg', 'at_risk_kg', 'transport_cost_inr'].includes(key)
        const favorable = (goodWhenHigher && delta.optimized_minus_baseline >= 0) || (goodWhenLower && delta.optimized_minus_baseline <= 0)
        const ValueIcon = delta.optimized_minus_baseline >= 0 ? ArrowUpRight : ArrowDownRight
        return <tr key={key}><td><strong>{labels[key]}</strong><span className="metric-tip" title={definitions[key]}><Info size={13} /></span><small className="sub-cell">{definitions[key]}</small></td><td>{formatValue(key, baseline)}</td><td className="optimized-number">{formatValue(key, optimized)}</td><td className={favorable ? 'delta-good' : 'delta-caution'}><ValueIcon size={14} />{delta.optimized_minus_baseline > 0 ? '+' : ''}{formatValue(key, delta.optimized_minus_baseline)}</td><td>{delta.percent_vs_baseline === null ? <span className="muted-cell">—<small>baseline = 0</small></span> : <span className={favorable ? 'delta-good-text' : 'delta-caution-text'}>{delta.percent_vs_baseline > 0 ? '+' : ''}{delta.percent_vs_baseline.toFixed(1)}%</span>}</td></tr>
      })}</tbody></table></div><div className="comparison-disclosure"><Info size={16} /><span>{comparison.explanation} Estimated unsold equals unallocated kg at cutoff; it is not confirmed physical spoilage. Physical expiration is not observed or inferred by this dataset.</span></div></section>
    </>}
  </>
}
