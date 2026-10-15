import { useState } from 'react'
import { Activity, AlertTriangle, ArrowDownRight, ArrowUpRight, RotateCcw, SlidersHorizontal, Zap } from 'lucide-react'
import type { PlanInput, ScenarioResult } from '../types'

const format = (value: number, suffix = '') => `${value > 0 ? '+' : ''}${value.toLocaleString('en-IN', { maximumFractionDigits: 1 })}${suffix}`
type Multipliers = { travel_time_multiplier: number; demand_multiplier: number; capacity_multiplier: number }
type Props = { inputs: PlanInput; result: ScenarioResult | null; busy: boolean; multipliers: Multipliers; onMultipliers: (next: Multipliers) => void; onRun: () => void; onReset: () => void }

function Control({ label, help, unit, value, min, max, step, onChange }: { label: string; help: string; unit: string; value: number; min: number; max: number; step: number; onChange: (value: number) => void }) {
  return <label className="scenario-control"><span className="control-heading"><strong>{label}</strong><b>{value.toFixed(1)}×</b></span><span className="control-help">{help}</span><input aria-label={label} type="range" min={min} max={max} step={step} value={value} onChange={(event) => onChange(Number(event.target.value))} /><span className="range-labels"><span>{min.toFixed(1)}×</span><span>{unit}</span><span>{max.toFixed(1)}×</span></span></label>
}

export default function Scenario({ inputs, result, busy, multipliers, onMultipliers, onRun, onReset }: Props) {
  const original = result?.original.optimized.metrics
  const current = result?.scenario.optimized.metrics
  return <>
    <section className="page-heading"><div><div className="eyebrow">RESILIENCE CHECK <span className="eyebrow-divider">/</span> WHAT-IF SIMULATION</div><h1>Pressure-test the dispatch</h1><p>Change one or more operating assumptions, then recalculate both strategies against a separate copy of the current data.</p></div><div className="heading-actions"><button className="button button-secondary" onClick={onReset} disabled={busy}><RotateCcw size={15} />Reset scenario</button><button className="button button-primary" onClick={onRun} disabled={busy}><Zap size={15} />{busy ? 'Recalculating…' : 'Run scenario'}</button></div></section>
    <div className="scenario-layout"><section className="panel scenario-controls"><div className="panel-heading"><div><span className="section-kicker">SCENARIO INPUTS</span><h2>Change the conditions</h2><p>Multipliers apply to all destinations for this simulated planning horizon.</p></div><SlidersHorizontal size={18} /></div>
      <Control label="Travel time" help="Affects arrival hours and whether delivery fits the estimated shelf-life window." unit="multiplier of original hours" value={multipliers.travel_time_multiplier} min={0.5} max={2} step={0.1} onChange={(v) => onMultipliers({ ...multipliers, travel_time_multiplier: v })} />
      <Control label="Destination demand" help="Changes each commodity’s modeled market demand ceiling; price response is not inferred." unit="multiplier of original kg demand" value={multipliers.demand_multiplier} min={0.5} max={2} step={0.1} onChange={(v) => onMultipliers({ ...multipliers, demand_multiplier: v })} />
      <Control label="Transport capacity" help="Scales each destination’s shared aggregate capacity across all commodities." unit="multiplier of original kg capacity" value={multipliers.capacity_multiplier} min={0} max={1.5} step={0.1} onChange={(v) => onMultipliers({ ...multipliers, capacity_multiplier: v })} />
      <div className="scenario-assumption"><AlertTriangle size={16} /><span>Original inventory and destination data stay unchanged. Scenario calculations are local estimates, not live road or market data.</span></div>
      <button className="button button-primary full-width" onClick={onRun} disabled={busy}>{busy ? 'Recalculating baseline + optimizer…' : 'Recompute baseline and optimized plans'}</button>
    </section>
    <section className="panel scenario-results"><div className="panel-heading"><div><span className="section-kicker">OUTCOME DELTA</span><h2>{result ? 'Scenario vs. original inputs' : 'No scenario run yet'}</h2><p>{result ? 'Changes below are recalculated by the backend and compared with the original optimized plan.' : 'Adjust the controls and run a scenario to see actual metric and assignment changes.'}</p></div><Activity size={18} /></div>
      {!result ? <div className="scenario-empty"><span><Activity size={23} /></span><strong>Waiting for a scenario run</strong><p>The original sample has {inputs.inventory.length} batches and {inputs.destinations.length} markets. The sliders do not change the plan until you run the calculation.</p></div> : <>
        <div className="scenario-delta-grid">{[
          ['Delivered quantity', 'quantity_delivered_kg', ' kg'], ['Demand fulfillment', 'demand_fulfillment_pct', ' pp'], ['Unallocated stock', 'unallocated_kg', ' kg'], ['At-risk inventory', 'at_risk_kg', ' kg'], ['Transport cost', 'transport_cost_inr', ' INR'], ['Net revenue', 'net_revenue_inr', ' INR'],
        ].map(([label, key, unit]) => {
          const delta = result.metric_changes[key]
          const Icon = delta >= 0 ? ArrowUpRight : ArrowDownRight
          return <div className="delta-card" key={key}><span>{label}</span><strong className={delta >= 0 ? 'delta-good-text' : 'delta-caution-text'}><Icon size={15} />{format(delta, unit)}</strong><small>original {format(original?.[key as keyof typeof original] ?? 0, unit.trim() === 'INR' ? ' INR' : unit)}</small></div>
        })}</div>
        <div className="scenario-note-list"><strong>Why the plan changed</strong>{result.explanations.map((text, index) => <p key={index}><span className="tiny-dot" />{text}</p>)}<p><span className="tiny-dot" />Scenario delivered {current?.quantity_delivered_kg.toLocaleString('en-IN', { maximumFractionDigits: 1 })} kg and left {current?.unallocated_kg.toLocaleString('en-IN', { maximumFractionDigits: 1 })} kg unallocated. Unallocated does not mean physically spoiled.</p></div>
        <div className="table-scroll scenario-change-table"><table className="data-table"><thead><tr><th>Changed assignment</th><th>Market</th><th>Quantity change</th></tr></thead><tbody>{result.allocation_changes.length ? result.allocation_changes.map((row) => <tr key={`${row.batch_id}-${row.destination_id}`}><td className="mono-cell">{row.batch_id}</td><td>{row.destination_id}</td><td className={row.quantity_change_kg >= 0 ? 'delta-good-text' : 'delta-caution-text'}>{row.quantity_change_kg > 0 ? '+' : ''}{format(row.quantity_change_kg, ' kg')}</td></tr>) : <tr><td colSpan={3} className="muted-cell">No optimized allocation quantities changed under these assumptions.</td></tr>}</tbody></table></div>
      </>}
    </section></div>
  </>
}
