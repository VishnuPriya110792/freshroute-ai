import { useState } from 'react'
import { AlertTriangle, ArrowRight, CheckCircle2, CircleHelp, Route, Truck } from 'lucide-react'
import type { ComparisonResult, PlanInput } from '../types'

const qty = (value: number) => value.toLocaleString('en-IN', { maximumFractionDigits: 1 })
const inr = (value: number) => `₹${value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`

type Props = { comparison: ComparisonResult | null; inputs: PlanInput | null; busy: boolean; onGenerate: () => void }

export default function Planner({ comparison, inputs, busy, onGenerate }: Props) {
  const [sort, setSort] = useState<{ key: keyof NonNullable<typeof comparison>['optimized']['allocations'][number]; direction: 1 | -1 }>({ key: 'arrival_hours', direction: 1 })
  const plan = comparison?.optimized
  const sortedAllocations = plan?.allocations.slice().sort((a, b) => {
    const left = a[sort.key]
    const right = b[sort.key]
    const order = typeof left === 'number' && typeof right === 'number' ? left - right : String(left).localeCompare(String(right))
    return order * sort.direction
  }) ?? []
  function sortBy(key: typeof sort.key) {
    setSort((current) => ({ key, direction: current.key === key ? current.direction === 1 ? -1 : 1 : 1 }))
  }
  function heading(label: string, key: typeof sort.key) {
    return <button type="button" className="sort-button" onClick={() => sortBy(key)}>{label}<span aria-hidden="true">{sort.key === key ? sort.direction === 1 ? '↑' : '↓' : '↕'}</span></button>
  }
  return <>
    <section className="page-heading"><div><div className="eyebrow">DECISION SUPPORT <span className="eyebrow-divider">/</span> ALLOCATION ENGINE</div><h1>Distribution planner</h1><p>A deterministic plan that connects batch age, eligible markets, demand, route capacity, and transport economics.</p></div><button className="button button-primary" onClick={onGenerate} disabled={!inputs || busy}><Truck size={16} />{busy ? 'Solving…' : 'Generate distribution plan'}</button></section>
    <div className="objective-banner"><div className="objective-icon"><Route size={18} /></div><div><strong>Objective · maximize expected net contribution</strong><span>Allocated kg × (selling price per kg − transport cost per kg), subject to inventory, demand, capacity, eligibility, and arrival shelf life.</span></div><span className="objective-method">SCIPY · LINEAR PROGRAM</span></div>
    {!plan ? <div className="empty-card panel"><span className="empty-card-icon"><Truck size={24} /></span><h2>Ready when your inputs are</h2><p>The planner will return a feasible allocation or structured reasons for unallocated stock. No results are fabricated when a route fails a hard constraint.</p><button className="button button-primary" disabled={!inputs || busy} onClick={onGenerate}>Calculate plan <ArrowRight size={16} /></button></div> : <>
      <section className="planner-kpis">
        <div className="planner-kpi"><span>ALLOCATED</span><strong>{qty(plan.metrics.allocated_kg)} <small>kg</small></strong><em>of {qty(plan.metrics.total_available_kg)} kg available</em></div>
        <div className="planner-kpi"><span>UNALLOCATED</span><strong>{qty(plan.metrics.unallocated_kg)} <small>kg</small></strong><em>projected unsold at cutoff</em></div>
        <div className="planner-kpi"><span>UNFULFILLED DEMAND</span><strong>{qty(plan.metrics.unfulfilled_demand_kg)} <small>kg</small></strong><em>{qty(plan.metrics.demand_fulfillment_pct,)}% fulfilled</em></div>
        <div className="planner-kpi"><span>SHELF-LIFE REJECTED</span><strong>{qty(plan.diagnostics.rejected_by_shelf_life_kg)} <small>kg</small></strong><em>no eligible arrival-feasible market</em></div>
        <div className="planner-kpi"><span>CAPACITY-LIMITED</span><strong>{qty(plan.diagnostics.capacity_limited_kg)} <small>kg</small></strong><em>demand remains, route ceiling binds</em></div>
      </section>

      <section className="panel planner-table-panel"><div className="panel-heading"><div><span className="section-kicker">OPTIMIZED ALLOCATIONS</span><h2>Dispatch assignments</h2><p>Sorted by arrival feasibility, then batch and market identifiers.</p></div><span className="solver-badge"><CheckCircle2 size={14} />{plan.diagnostics.solver_status === 'optimal' ? 'Optimal LP solution' : plan.status}</span></div>
        {plan.allocations.length ? <div className="table-scroll"><table className="data-table planner-table"><thead><tr><th>{heading('Batch', 'batch_id')}</th><th>{heading('Produce', 'commodity')}</th><th>{heading('Destination', 'destination_name')}</th><th>{heading('Quantity', 'quantity_kg')}</th><th>{heading('Arrival', 'arrival_hours')}</th><th>{heading('Usable on arrival', 'shelf_life_remaining_on_arrival_hours')}</th><th>{heading('Transport', 'transport_cost_inr')}</th><th>Feasibility & explanation</th></tr></thead><tbody>{sortedAllocations.map((row) => <tr key={`${row.batch_id}-${row.destination_id}`}><td className="mono-cell">{row.batch_id}</td><td>{row.commodity}</td><td>{row.destination_name}<small className="sub-cell">{row.destination_id}</small></td><td className="numeric-cell">{qty(row.quantity_kg)} kg</td><td>{qty(row.arrival_hours)} h</td><td><span className={`life-pill ${row.shelf_life_remaining_on_arrival_hours <= 12 ? 'life-critical' : row.shelf_life_remaining_on_arrival_hours <= 24 ? 'life-warn' : ''}`}>{qty(row.shelf_life_remaining_on_arrival_hours)} h</span></td><td>{inr(row.transport_cost_inr)}</td><td className="explanation-cell"><span className="feasibility-tag"><CheckCircle2 size={12} />Feasible</span>{row.explanation}</td></tr>)}</tbody></table></div> : <div className="table-empty"><AlertTriangle size={18} />No assignments were selected. The optimizer may decline nonpositive contributions or no route may meet the hard constraints; review the diagnostics below.</div>}
      </section>

      <section className="diagnostic-grid"><article className="panel diagnostic-panel"><div className="panel-heading compact-heading"><div><span className="section-kicker">WHY STOCK REMAINS</span><h2>Unallocated inventory</h2></div><CircleHelp size={16} /></div>{plan.diagnostics.unallocated_batches.length ? <div className="reason-list">{plan.diagnostics.unallocated_batches.map((item) => <div className="reason-row" key={item.batch_id}><div><strong>{item.batch_id} · {item.commodity}</strong><span>{item.reason}</span></div><b>{qty(item.remaining_kg)} kg</b></div>)}</div> : <div className="success-inline"><CheckCircle2 size={16} />All available stock was assigned within the modeled constraints.</div>}</article>
      <article className="panel diagnostic-panel"><div className="panel-heading compact-heading"><div><span className="section-kicker">ACTIVE LIMITS</span><h2>Constraint notes</h2></div><AlertTriangle size={16} /></div><ul className="diagnostic-notes">{plan.diagnostics.messages.map((message, index) => <li key={index}>{message}</li>)}</ul><div className="horizon-note"><strong>Capacity interpretation</strong><span>Each destination's capacity is one aggregate ceiling across all commodities for this single planning horizon—not capacity per trip.</span></div></article></section>
    </>}
  </>
}
