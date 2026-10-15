import { Download, FileText, Percent, Printer, ShieldAlert } from 'lucide-react'
import type { ComparisonResult, DiscountRecommendation } from '../types'

type Exports = { ready: boolean; hasPlan: boolean; busy: boolean; onOptimizedCsv: () => void; onBaselineCsv: () => void; onComparisonCsv: () => void; onReport: () => void }
type Props = { recommendations: DiscountRecommendation[]; comparison: ComparisonResult | null; exports: Exports }
const inr = (value: number) => `₹${value.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`

export default function Discounts({ recommendations, comparison, exports }: Props) {
  return <>
    <section className="page-heading"><div><div className="eyebrow">RECOVERY & HANDOVER <span className="eyebrow-divider">/</span> RULE-BASED ESTIMATES</div><h1>Discounts & exports</h1><p>Surface residual stock that may miss its sale window, then export the real plan and assumptions.</p></div></section>
    <section className="panel discount-panel"><div className="panel-heading"><div><span className="section-kicker">RESIDUAL INVENTORY</span><h2>Discount recommendations</h2><p>Rules consider unallocated quantity, remaining usable life, feasible demand, delivery time, and available prices.</p></div><span className="rule-badge"><Percent size={14} />DETERMINISTIC RULES</span></div>
      {!comparison ? <div className="table-empty"><ShieldAlert size={18} />Generate a plan to identify residual batches that meet the discount rules.</div> : recommendations.length ? <div className="table-scroll"><table className="data-table"><thead><tr><th>Batch</th><th>Produce</th><th>Residual</th><th>Markdown</th><th>Illustrative price after markdown</th><th>Revenue trade-off</th><th>Why</th></tr></thead><tbody>{recommendations.map((row) => <tr key={row.batch_id}><td className="mono-cell">{row.batch_id}</td><td>{row.commodity}</td><td>{row.unallocated_kg.toLocaleString('en-IN', { maximumFractionDigits: 1 })} kg</td><td><span className="discount-pill">{row.recommended_discount_pct}%</span></td><td>{inr(row.discounted_price_inr_per_kg)} / kg</td><td>{inr(row.estimated_revenue_tradeoff_inr)}</td><td className="explanation-cell">{row.reason}</td></tr>)}</tbody></table></div> : <div className="success-inline"><span className="success-icon">✓</span>No residual batch currently meets the deterministic recommendation rules.</div>}
      <div className="discount-disclosure"><ShieldAlert size={16} /><span><strong>Rule-based estimate, not demand forecasting.</strong> Revenue trade-off assumes the same residual volume sells at the lower price. No demand increase is claimed or modeled without validated demand-response data.</span></div>
    </section>

    <section className="export-section"><div className="export-section-heading"><div><span className="section-kicker">REAL BACKEND OUTPUTS</span><h2>Export this run</h2><p>Exports are generated from the current inputs at download time.</p></div></div><div className="export-grid">
      <ExportCard icon={<Download size={18} />} title="Optimized allocations" description="Batch, destination, quantity, arrival window, transport cost and explanation." actionLabel="Download CSV" onClick={exports.onOptimizedCsv} disabled={!exports.ready || !exports.hasPlan || exports.busy} />
      <ExportCard icon={<Download size={18} />} title="FEFO baseline allocations" description="The reproducible earliest-expiry-first assignments on the same assumptions." actionLabel="Download CSV" onClick={exports.onBaselineCsv} disabled={!exports.ready || !exports.hasPlan || exports.busy} />
      <ExportCard icon={<Download size={18} />} title="Strategy comparison" description="Delivered kg, fulfillment, unallocated stock, sales, route cost, and net revenue." actionLabel="Download CSV" onClick={exports.onComparisonCsv} disabled={!exports.ready || !exports.hasPlan || exports.busy} />
      <ExportCard icon={<Printer size={18} />} title="Printable summary report" description="Inputs, strategy metrics, assignments, discounts, constraints, formulas, and limitations." actionLabel="Download printable HTML" onClick={exports.onReport} disabled={!exports.ready || !exports.hasPlan || exports.busy} />
    </div><div className="report-footnote"><FileText size={16} /><span>The report is generated from real backend results. Open the HTML file and use its <strong>Print / Save as PDF</strong> button to create a printout.</span></div></section>
  </>
}

function ExportCard({ icon, title, description, actionLabel, onClick, disabled }: { icon: React.ReactNode; title: string; description: string; actionLabel: string; onClick: () => void; disabled: boolean }) {
  return <article className="panel export-card"><span className="export-icon">{icon}</span><h3>{title}</h3><p>{description}</p><button className="button button-secondary button-small" onClick={onClick} disabled={disabled}>{actionLabel}<Download size={14} /></button></article>
}
