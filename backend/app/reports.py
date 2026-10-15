from __future__ import annotations

import csv
import html
import io
from datetime import datetime, timezone

from .models import ComparisonResult, PlanInput, StrategyPlan


def allocations_csv(plan: StrategyPlan) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow([
        "strategy", "batch_id", "commodity", "destination_id", "destination_name", "quantity_kg",
        "arrival_hours", "shelf_life_remaining_on_arrival_hours", "selling_price_inr_per_kg",
        "transport_cost_inr_per_kg", "transport_cost_inr", "net_contribution_inr", "explanation",
    ])
    for row in plan.allocations:
        writer.writerow([
            plan.strategy, row.batch_id, row.commodity, row.destination_id, row.destination_name,
            f"{row.quantity_kg:.6f}", f"{row.arrival_hours:.4f}",
            f"{row.shelf_life_remaining_on_arrival_hours:.4f}", f"{row.selling_price_inr_per_kg:.4f}",
            f"{row.transport_cost_inr_per_kg:.4f}", f"{row.transport_cost_inr:.4f}",
            f"{row.net_contribution_inr:.4f}", row.explanation,
        ])
    return output.getvalue()


def comparison_csv(comparison: ComparisonResult) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["metric", "unit", "fefo_baseline", "optimized", "optimized_minus_baseline", "percent_vs_baseline"])
    rows = [
        ("quantity_delivered_kg", "kg"), ("demand_fulfillment_pct", "%"), ("unallocated_kg", "kg"),
        ("estimated_unsold_kg", "kg"), ("at_risk_kg", "kg"), ("gross_sales_inr", "INR"),
        ("transport_cost_inr", "INR"), ("net_revenue_inr", "INR"),
    ]
    for key, unit in rows:
        baseline = getattr(comparison.baseline.metrics, key)
        optimized = getattr(comparison.optimized.metrics, key)
        difference = comparison.differences[key]
        writer.writerow([key, unit, f"{baseline:.4f}", f"{optimized:.4f}", f"{difference.optimized_minus_baseline:.4f}", "" if difference.percent_vs_baseline is None else f"{difference.percent_vs_baseline:.4f}"])
    return output.getvalue()


def summary_html(inputs: PlanInput, comparison: ComparisonResult, discounts: list[dict], scenario_label: str) -> str:
    def money(value: float) -> str:
        return f"₹{value:,.2f}"

    def esc(value: object) -> str:
        return html.escape(str(value))

    m0, m1 = comparison.baseline.metrics, comparison.optimized.metrics
    metric_keys = [
        ("Delivered", "quantity_delivered_kg", "kg"),
        ("Demand fulfillment", "demand_fulfillment_pct", "%"),
        ("Unallocated / projected unsold", "unallocated_kg", "kg"),
        ("At risk (≤24 estimated hours)", "at_risk_kg", "kg"),
        ("Gross sales", "gross_sales_inr", "INR"),
        ("Transport cost", "transport_cost_inr", "INR"),
        ("Net revenue", "net_revenue_inr", "INR"),
    ]
    metric_rows: list[str] = []
    for label, key, unit in metric_keys:
        base_value = getattr(m0, key)
        opt_value = getattr(m1, key)
        if unit == "INR":
            base, opt = money(base_value), money(opt_value)
            delta = money(comparison.differences[key].optimized_minus_baseline)
        elif unit == "%":
            base, opt = f"{base_value:.1f}%", f"{opt_value:.1f}%"
            delta = f"{comparison.differences[key].optimized_minus_baseline:+.1f} pp"
        else:
            base, opt = f"{base_value:,.1f} kg", f"{opt_value:,.1f} kg"
            delta = f"{comparison.differences[key].optimized_minus_baseline:+,.1f} kg"
        pct = comparison.differences[key].percent_vs_baseline
        pct_text = "—" if pct is None else f"{pct:+.1f}%"
        metric_rows.append(f"<tr><th>{esc(label)}</th><td>{esc(base)}</td><td>{esc(opt)}</td><td>{esc(delta)}</td><td>{esc(pct_text)}</td></tr>")
    metric_rows.append('<tr><th>Physical expiry observed</th><td>Not observed</td><td>Not observed</td><td>Not inferred</td><td>—</td></tr>')
    body_metrics = "".join(metric_rows)

    inventory_rows = "".join(
        "<tr>"
        f"<td>{esc(batch.batch_id)}</td><td>{esc(batch.commodity)}</td><td>{batch.quantity_kg:,.2f}</td>"
        f"<td>{batch.shelf_life_hours:,.2f} h</td><td>{esc(batch.handling_notes or '—')}</td>"
        f"<td>{esc('; '.join(batch.eligible_destinations) if batch.eligible_destinations else 'No batch-specific restriction')}</td>"
        "</tr>"
        for batch in sorted(inputs.inventory, key=lambda item: item.batch_id)
    ) or '<tr><td colspan="6">No inventory batches.</td></tr>'

    destination_rows = "".join(
        "<tr>"
        f"<td>{esc(destination.destination_id)} · {esc(destination.name)}</td>"
        f"<td>{destination.travel_hours:,.2f} h</td><td>{destination.handling_hours:,.2f} h</td>"
        f"<td>{money(destination.transport_cost_inr_per_kg)}/kg</td><td>{destination.capacity_kg:,.2f} kg</td>"
        f"<td>{esc('; '.join(f'{name}: {value:g} kg' for name, value in sorted(destination.demand_by_commodity.items())) or 'None modeled')}</td>"
        f"<td>{esc('; '.join(f'{name}: ₹{value:g}/kg' for name, value in sorted(destination.price_by_commodity.items())) or 'None modeled')}</td>"
        "</tr>"
        for destination in sorted(inputs.destinations, key=lambda item: item.destination_id)
    ) or '<tr><td colspan="7">No destinations.</td></tr>'

    alloc_rows = "".join(
        f"<tr><td>{esc(a.batch_id)}</td><td>{esc(a.commodity)}</td><td>{esc(a.destination_id)}</td><td>{a.quantity_kg:,.2f} kg</td><td>{a.arrival_hours:.1f} h</td><td>{money(a.transport_cost_inr)}</td><td>{esc(a.explanation)}</td></tr>"
        for a in comparison.optimized.allocations
    ) or '<tr><td colspan="7">No allocations were selected. Review the plan diagnostics and constraints.</td></tr>'

    discount_rows = "".join(
        f"<tr><td>{esc(d['batch_id'])}</td><td>{esc(d['commodity'])}</td><td>{float(d['unallocated_kg']):,.1f} kg</td>"
        f"<td>{float(d['recommended_discount_pct']):.0f}%</td><td>{money(float(d['discounted_price_inr_per_kg']))}/kg</td>"
        f"<td>{money(float(d['estimated_revenue_tradeoff_inr']))}</td><td>{esc(d['reason'])}</td></tr>"
        for d in discounts
    ) or '<tr><td colspan="7">No batch currently meets the rule-based discount criteria.</td></tr>'

    diagnostic_rows = "".join(f"<li>{esc(message)}</li>" for message in comparison.optimized.diagnostics.messages)
    inventory_count = len(inputs.inventory)
    market_count = len(inputs.destinations)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>FreshRoute AI — Dispatch summary</title>
<style>
:root{{--ink:#202923;--green:#174c3c;--muted:#65736b;--line:#d9e0d8;--paper:#fbfaf6;--amber:#9b640d}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:13px/1.55 Inter,system-ui,sans-serif}}main{{max-width:1160px;margin:32px auto;padding:0 26px 48px}}header{{display:flex;justify-content:space-between;align-items:flex-start;border-bottom:2px solid var(--green);padding-bottom:18px}}h1{{margin:0;color:var(--green);font-size:28px}}h2{{font-size:17px;margin:27px 0 9px;color:var(--green)}}.eyebrow,.muted{{color:var(--muted)}}.badge{{border:1px solid var(--line);border-radius:999px;padding:5px 10px;font-size:11px}}button{{background:var(--green);color:white;border:0;padding:10px 16px;border-radius:6px;font-weight:650;cursor:pointer}}.facts{{display:flex;gap:10px;flex-wrap:wrap;margin:14px 0}}.facts span{{padding:7px 10px;background:#f0f3ee;border-radius:6px;font-size:11px}}table{{width:100%;border-collapse:collapse;margin:8px 0 18px;font-size:11px}}th,td{{text-align:left;padding:7px 8px;border-bottom:1px solid var(--line);vertical-align:top}}thead th{{color:var(--muted);font-size:9px;text-transform:uppercase;letter-spacing:.05em}}th{{font-weight:650}}.disclosure{{padding:11px 13px;border-left:3px solid var(--amber);background:#fff8e8;margin:13px 0}}.scroll{{overflow-x:auto}}@media print{{body{{background:white;font-size:10px}}main{{margin:0 auto;padding:0 8px}}.no-print{{display:none!important}}h2{{break-after:avoid}}table{{break-inside:auto}}tr{{break-inside:avoid}}}}
</style></head><body><main><header><div><div class="eyebrow">FRESHROUTE AI · DISPATCH INTELLIGENCE</div><h1>Distribution plan summary</h1><div class="muted">{esc(scenario_label)} · Generated {now}</div></div><button class="no-print" onclick="window.print()">Print / Save as PDF</button></header>
<div class="facts"><span>{inventory_count} inventory batches</span><span>{market_count} destinations</span><span>Illustrative synthetic inputs</span><span>One planning horizon</span><span>kg · hours · INR</span></div>
<h2>Strategy comparison</h2><div class="scroll"><table><thead><tr><th>Metric</th><th>FEFO baseline</th><th>Optimized</th><th>Optimized − baseline</th><th>Percent vs baseline</th></tr></thead><tbody>{body_metrics}</tbody></table></div>
<h2>Inventory and batch assumptions</h2><div class="scroll"><table><thead><tr><th>Batch</th><th>Produce</th><th>Quantity</th><th>Estimated usable life</th><th>Handling notes</th><th>Eligible destinations</th></tr></thead><tbody>{inventory_rows}</tbody></table></div>
<h2>Destination and route assumptions</h2><div class="scroll"><table><thead><tr><th>Market</th><th>Travel</th><th>Handling</th><th>Transport cost</th><th>Shared capacity</th><th>Demand</th><th>Selling prices</th></tr></thead><tbody>{destination_rows}</tbody></table></div>
<h2>Optimized allocations</h2><div class="scroll"><table><thead><tr><th>Batch</th><th>Produce</th><th>Destination</th><th>Quantity</th><th>Arrival</th><th>Route cost</th><th>Decision explanation</th></tr></thead><tbody>{alloc_rows}</tbody></table></div>
<h2>Discount recommendations</h2><div class="scroll"><table><thead><tr><th>Batch</th><th>Produce</th><th>Residual</th><th>Discount</th><th>Illustrative price</th><th>Revenue trade-off</th><th>Reason</th></tr></thead><tbody>{discount_rows}</tbody></table></div>
<h2>Constraints and diagnostics</h2><ul>{diagnostic_rows}</ul>
<h2>Formulas and limitations</h2><p>Objective: maximize allocated kg × (selling price per kg − transport cost per kg), subject to inventory, per-commodity market demand, destination-wide route capacity, eligibility, and delivery + handling time no greater than estimated remaining shelf life. Destination capacity is shared across all commodities for this one planning horizon; route cost is INR/kg.</p>
<p>Demand fulfillment = delivered kg ÷ total modeled demand kg (0% when total demand is zero). Net revenue = gross sales − transport cost; no other operating cost is modeled. Unallocated stock is projected unsold at the planning cutoff, not confirmed spoilage. At-risk stock is unallocated stock with ≤24 estimated usable hours. Physical expiry is not observed and is not inferred. Discount trade-offs assume unchanged volume at a lower price; demand response is not modeled. Shelf-life estimates and all bundled prices, demand, times, capacities, and outcomes are illustrative synthetic inputs—not current market data or guaranteed results.</p>
<div class="disclosure">This decision-support output is a model estimate, not a dispatch guarantee. Verify inventory, route conditions, capacity and market inputs before operational use.</div>
<p class="muted">FreshRoute AI · Less waste. Smarter routes. Better margins.</p></main></body></html>'''
