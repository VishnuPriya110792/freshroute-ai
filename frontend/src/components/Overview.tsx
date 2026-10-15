import { ArrowDownRight, ArrowRight, ArrowUpRight, CircleHelp, Clock3, Package, ShieldAlert, Truck } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, Cell, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ComparisonResult, PlanInput } from '../types'

type Props = { inputs: PlanInput | null; comparison: ComparisonResult | null; totalStock: number | null; busy: boolean; onGenerate: () => void; onNavigate: (page: 'planner' | 'inventory' | 'comparison') => void }
const number = (value: number, digits = 0) => value.toLocaleString('en-IN', { maximumFractionDigits: digits, minimumFractionDigits: digits })
const money = (value: number) => `₹${number(value, 0)}`

function MetricCard({ label, value, unit, definition, icon: Icon, tone = '' }: { label: string; value: string; unit?: string; definition: string; icon: typeof Package; tone?: string }) {
  return <article className={`metric-card ${tone}`}><div className="metric-top"><span>{label}</span><span className="help-dot" title={definition} aria-label={definition}><CircleHelp size={14} /></span></div><div className="metric-value">{value}<small>{unit}</small></div><div className="metric-definition">{definition}</div><Icon className="metric-icon" size={18} /></article>
}

export default function Overview({ inputs, comparison, totalStock, busy, onGenerate, onNavigate }: Props) {
  const plan = comparison?.optimized
  const m = plan?.metrics
  const riskData = (inputs?.inventory ?? []).slice().sort((a, b) => a.shelf_life_hours - b.shelf_life_hours).map((batch) => ({ batch: batch.batch_id, shelf: batch.shelf_life_hours, commodity: batch.commodity }))
  const demandData = comparison?.destination_summary.map((market) => ({
    market: market.destination_id,
    demand: market.demand_kg,
    allocation: market.allocated_kg,
  })) ?? []
  const priorityRows = plan?.allocations.slice().sort((a, b) => a.shelf_life_remaining_on_arrival_hours - b.shelf_life_remaining_on_arrival_hours).slice(0, 5) ?? []
  const improvement = comparison?.differences.net_revenue_inr.optimized_minus_baseline ?? 0
  const changeIcon = improvement >= 0 ? ArrowUpRight : ArrowDownRight

  return <>
    <section className="page-heading"><div><div className="eyebrow">DISPATCH OPERATIONS <span className="eyebrow-divider">/</span> TODAY</div><h1>Fresh inventory, clearer decisions.</h1><p>See what can move, what may miss its window, and where the next dispatch makes sense.</p></div><div className="heading-actions"><button className="button button-secondary" onClick={() => onNavigate('inventory')}><Package size={16} />Review inputs</button><button className="button button-primary" onClick={onGenerate} disabled={!inputs || busy}><Truck size={16} />{busy ? 'Calculating…' : plan ? 'Recalculate plan' : 'Generate distribution plan'}</button></div></section>

    <section className="overview-meta-row"><div className="meta-title"><span className="signal-square"><Clock3 size={16} /></span><div><strong>{comparison ? 'Plan calculated from current inputs' : 'Planning workspace ready'}</strong><span>{comparison ? 'Baseline and optimized strategies use the same demand, cost and capacity assumptions.' : 'Load or edit your inventory, validate it, then calculate a dispatch plan.'}</span></div></div><div className="meta-horizon"><span className="tiny-dot" /> ONE DISPATCH HORIZON · KG / HOURS / INR</div></section>

    <section className="metric-grid" aria-label="Current plan metrics">
      <MetricCard label="Available stock" value={totalStock === null ? '—' : number(totalStock)} unit={totalStock === null ? '' : 'kg'} definition="Total quantity_kg across active inventory batches, calculated by the backend when a plan is generated." icon={Package} />
      <MetricCard label="Allocated" value={m ? number(m.allocated_kg) : '—'} unit={m ? 'kg' : ''} definition="Total kilograms assigned to feasible destinations by the optimized strategy." icon={Truck} tone="metric-positive" />
      <MetricCard label="Unallocated" value={m ? number(m.unallocated_kg) : '—'} unit={m ? 'kg' : ''} definition="Available stock not assigned by the plan. Treated as projected unsold at the modeled cutoff, not confirmed spoilage." icon={ArrowDownRight} tone="metric-warning" />
      <MetricCard label="Demand filled" value={m ? `${number(m.demand_fulfillment_pct, 1)}%` : '—'} unit="" definition="Delivered kilograms divided by total modeled demand kilograms; 0% when total demand is zero." icon={CircleHelp} />
      <MetricCard label="At risk" value={m ? number(m.at_risk_kg) : '—'} unit={m ? 'kg' : ''} definition="Unallocated kilograms whose estimated usable shelf life at dispatch is 24 hours or less. Not a physical spoilage observation." icon={ShieldAlert} tone="metric-warning" />
      <MetricCard label="Transport cost" value={m ? money(m.transport_cost_inr) : '—'} unit="" definition="Sum of allocated kilograms multiplied by each destination's synthetic route cost per kg." icon={Truck} />
      <MetricCard label="Net revenue" value={m ? money(m.net_revenue_inr) : '—'} unit="" definition="Estimated gross sales less modeled transport cost; no other operating costs are modeled." icon={Package} tone="metric-positive" />
      <MetricCard label="vs FEFO baseline" value={comparison ? `${improvement >= 0 ? '+' : '−'}${money(Math.abs(improvement))}` : '—'} unit="" definition="Optimized net revenue minus earliest-expiry-first baseline net revenue on identical inputs. A negative result is shown without hiding it." icon={changeIcon} tone={improvement >= 0 ? 'metric-positive' : 'metric-warning'} />
    </section>

    {!comparison && <div className="empty-plan"><div className="empty-icon"><RouteIcon /></div><div><strong>No distribution plan yet</strong><p>Plan-dependent metrics and destination allocations will appear after the backend evaluates your inventory, demand, shelf life, prices, and route limits.</p></div><button className="button button-primary" disabled={!inputs || busy} onClick={onGenerate}><Truck size={16} />{busy ? 'Calculating…' : 'Generate distribution plan'}</button></div>}

    <section className="chart-grid">
      <article className="panel chart-panel"><div className="panel-heading"><div><span className="section-kicker">INVENTORY HEALTH</span><h2>Shelf-life windows</h2></div><span className="chart-unit">Estimated hours remaining</span></div>
        <div className="chart-wrap chart-short">{riskData.length ? <ResponsiveContainer width="100%" height="100%"><BarChart data={riskData} margin={{ top: 8, right: 10, left: -14, bottom: 8 }}><CartesianGrid vertical={false} stroke="#e6ebe5" /><XAxis dataKey="batch" tick={{ fontSize: 10, fill: '#748078' }} axisLine={false} tickLine={false} interval={0} angle={-18} textAnchor="end" height={42} /><YAxis tick={{ fontSize: 10, fill: '#748078' }} axisLine={false} tickLine={false} /><Tooltip formatter={(value) => [`${number(Number(value), 1)} h`, 'Usable life']} labelFormatter={(label, payload) => `${label} · ${payload?.[0]?.payload?.commodity ?? ''}`} /><Bar dataKey="shelf" radius={[4, 4, 0, 0]} maxBarSize={28}>{riskData.map((item, index) => <Cell key={`${item.batch}-${index}`} fill={item.shelf <= 24 ? '#c4882c' : item.shelf <= 48 ? '#78a28b' : '#174c3c'} />)}</Bar></BarChart></ResponsiveContainer> : <div className="chart-empty">Load inventory to view shelf-life windows.</div>}</div>
        <div className="legend-row"><span><i className="legend-swatch legend-risk" />≤24h · attention</span><span><i className="legend-swatch legend-watch" />25–48h · watch</span><span><i className="legend-swatch legend-good" />&gt;48h · more time</span></div>
      </article>
      <article className="panel chart-panel"><div className="panel-heading"><div><span className="section-kicker">MARKET COVERAGE</span><h2>Demand vs. allocation</h2></div><button className="text-button" onClick={() => onNavigate('comparison')}>Compare strategies <ArrowRight size={14} /></button></div>
        <div className="chart-wrap chart-short">{comparison ? <ResponsiveContainer width="100%" height="100%"><BarChart data={demandData} margin={{ top: 8, right: 10, left: -10, bottom: 8 }}><CartesianGrid vertical={false} stroke="#e6ebe5" /><XAxis dataKey="market" tick={{ fontSize: 11, fill: '#748078' }} axisLine={false} tickLine={false} /><YAxis tick={{ fontSize: 10, fill: '#748078' }} axisLine={false} tickLine={false} /><Tooltip formatter={(value) => [`${number(Number(value))} kg`]} /><Legend iconType="circle" wrapperStyle={{ fontSize: 11, paddingTop: 6 }} /><Bar dataKey="demand" name="Demand" fill="#dce4dc" radius={[4, 4, 0, 0]} maxBarSize={38} /><Bar dataKey="allocation" name="Optimized allocation" fill="#174c3c" radius={[4, 4, 0, 0]} maxBarSize={38} /></BarChart></ResponsiveContainer> : <div className="chart-empty"><div><RouteIcon /><span>Generate a plan to compare destination demand with calculated allocations.</span></div></div>}</div>
        {comparison && <div className={`chart-note ${improvement < 0 ? 'note-amber' : ''}`}><span className="note-pip" />Optimized net revenue {improvement >= 0 ? 'is' : 'is'} <strong>{improvement >= 0 ? 'above' : 'below'}</strong> the FEFO baseline by {money(Math.abs(improvement))} on these inputs.</div>}
      </article>
    </section>

    <section className="panel priority-panel"><div className="panel-heading"><div><span className="section-kicker">NEXT BEST ACTION</span><h2>Dispatch priorities</h2><p>Feasible assignments with the least usable time on arrival appear first.</p></div><button className="text-button" onClick={() => onNavigate('planner')}>Open planner <ArrowRight size={14} /></button></div>
      {priorityRows.length ? <div className="table-scroll"><table className="data-table"><thead><tr><th>Batch</th><th>Produce</th><th>Destination</th><th>Allocated</th><th>Arrival</th><th>Life on arrival</th><th>Route cost</th></tr></thead><tbody>{priorityRows.map((row) => <tr key={`${row.batch_id}-${row.destination_id}`}><td className="mono-cell">{row.batch_id}</td><td>{row.commodity}</td><td>{row.destination_name}</td><td>{number(row.quantity_kg, 1)} kg</td><td>{number(row.arrival_hours, 1)} h</td><td><span className={`life-pill ${row.shelf_life_remaining_on_arrival_hours <= 12 ? 'life-critical' : row.shelf_life_remaining_on_arrival_hours <= 24 ? 'life-warn' : ''}`}>{number(row.shelf_life_remaining_on_arrival_hours, 1)} h</span></td><td>₹{number(row.transport_cost_inr, 0)}</td></tr>)}</tbody></table></div> : <div className="table-empty"><Clock3 size={18} />{comparison ? 'No feasible allocation was found for the current inputs.' : 'Dispatch priorities appear here after a plan is generated.'}</div>}
    </section>
  </>
}

function RouteIcon() { return <Truck size={22} strokeWidth={1.7} /> }
