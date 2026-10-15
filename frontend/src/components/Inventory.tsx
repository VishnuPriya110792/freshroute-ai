import { useEffect, useState } from 'react'
import { AlertTriangle, Check, Download, FileUp, RotateCcw, ShieldCheck } from 'lucide-react'
import type { Destination, InventoryBatch, PlanInput } from '../types'

type Props = {
  inputs: PlanInput
  busy: boolean
  onChange: (next: PlanInput) => void
  onUpload: (file: File) => void
  onValidate: () => void
  onRestore: () => void
  onTemplate: () => void
}

function numberValue(value: string): number {
  return value.trim() === '' ? 0 : Number(value)
}

function parsePairs(text: string): Record<string, number> {
  if (!text.trim()) return {}
  const result: Record<string, number> = {}
  for (const part of text.split(';')) {
    const [rawName, rawValue] = part.split(':')
    if (!rawName?.trim() || rawValue === undefined || !Number.isFinite(Number(rawValue.trim())) || Number(rawValue.trim()) < 0) {
      throw new Error('Use “Commodity: quantity” pairs separated by semicolons, for example Tomatoes: 250; Onions: 100.')
    }
    result[rawName.trim()] = Number(rawValue.trim())
  }
  return result
}

const mapText = (map: Record<string, number>) => Object.entries(map).map(([name, value]) => `${name}: ${value}`).join('; ')

function MarketRow({ destination, onChange }: { destination: Destination; onChange: (update: Partial<Destination>) => void }) {
  const [demand, setDemand] = useState(mapText(destination.demand_by_commodity))
  const [prices, setPrices] = useState(mapText(destination.price_by_commodity))
  const [parseError, setParseError] = useState('')
  useEffect(() => { setDemand(mapText(destination.demand_by_commodity)); setPrices(mapText(destination.price_by_commodity)) }, [destination.demand_by_commodity, destination.price_by_commodity])
  function commitMap(field: 'demand_by_commodity' | 'price_by_commodity', text: string) {
    try { onChange({ [field]: parsePairs(text) }); setParseError('') }
    catch (error) { setParseError(error instanceof Error ? error.message : 'Invalid commodity values.') }
  }
  return <tr>
    <td><strong>{destination.name}</strong><small className="sub-cell">{destination.destination_id}</small></td>
    <td><input aria-label={`${destination.name} travel time in hours`} className="compact-input numeric-input" type="number" min="0" step="0.5" value={destination.travel_hours} onChange={(e) => onChange({ travel_hours: numberValue(e.target.value) })} /><span className="input-suffix">h</span></td>
    <td><input aria-label={`${destination.name} handling time in hours`} className="compact-input numeric-input" type="number" min="0" step="0.5" value={destination.handling_hours} onChange={(e) => onChange({ handling_hours: numberValue(e.target.value) })} /><span className="input-suffix">h</span></td>
    <td><input aria-label={`${destination.name} transport cost per kg`} className="compact-input numeric-input" type="number" min="0" step="0.1" value={destination.transport_cost_inr_per_kg} onChange={(e) => onChange({ transport_cost_inr_per_kg: numberValue(e.target.value) })} /><span className="input-suffix">₹/kg</span></td>
    <td><input aria-label={`${destination.name} route capacity in kg`} className="compact-input numeric-input" type="number" min="0" step="10" value={destination.capacity_kg} onChange={(e) => onChange({ capacity_kg: numberValue(e.target.value) })} /><span className="input-suffix">kg</span></td>
    <td className="market-map-cell"><input aria-label={`${destination.name} commodity demand`} value={demand} onChange={(e) => setDemand(e.target.value)} onBlur={() => commitMap('demand_by_commodity', demand)} placeholder="Tomatoes: 250; Onions: 100" /><small>Demand by commodity (kg); separate pairs with semicolons</small></td>
    <td className="market-map-cell"><input aria-label={`${destination.name} commodity prices`} value={prices} onChange={(e) => setPrices(e.target.value)} onBlur={() => commitMap('price_by_commodity', prices)} placeholder="Tomatoes: 30; Onions: 22" /><small>Illustrative selling price (₹/kg)</small>{parseError && <small className="inline-error" role="alert">{parseError}</small>}</td>
  </tr>
}

export default function Inventory({ inputs, busy, onChange, onUpload, onValidate, onRestore, onTemplate }: Props) {
  const [filter, setFilter] = useState('')
  const batches = inputs.inventory.filter((batch) => `${batch.batch_id} ${batch.commodity}`.toLowerCase().includes(filter.toLowerCase()))
  function updateBatch(index: number, update: Partial<InventoryBatch>) {
    const original = inputs.inventory.indexOf(batches[index])
    onChange({ ...inputs, inventory: inputs.inventory.map((batch, i) => i === original ? { ...batch, ...update } : batch) })
  }
  function updateDestination(index: number, update: Partial<Destination>) {
    onChange({ ...inputs, destinations: inputs.destinations.map((destination, i) => i === index ? { ...destination, ...update } : destination) })
  }
  return <>
    <section className="page-heading"><div><div className="eyebrow">DATA QUALITY <span className="eyebrow-divider">/</span> ACTIVE INPUTS</div><h1>Inventory & market inputs</h1><p>Review the batch-level facts and route assumptions behind every recommendation.</p></div><div className="heading-actions"><button className="button button-secondary" onClick={onRestore} disabled={busy}><RotateCcw size={15} />Restore sample</button><button className="button button-primary" onClick={onValidate} disabled={busy}><ShieldCheck size={16} />{busy ? 'Validating…' : 'Validate inputs'}</button></div></section>

    <div className="input-toolbar panel"><div className="toolbar-info"><span className="toolbar-icon"><FileUp size={17} /></span><div><strong>Import inventory CSV</strong><span>UTF-8 CSV with the template columns. Invalid uploads leave the current rows unchanged.</span></div></div><div className="toolbar-actions"><button className="button button-secondary button-small" onClick={onTemplate}><Download size={14} />Download CSV template</button><label className={`button button-primary button-small upload-label ${busy ? 'disabled' : ''}`}><FileUp size={14} />Upload CSV<input type="file" accept=".csv,text/csv" disabled={busy} onChange={(e) => { const file = e.target.files?.[0]; if (file) onUpload(file); e.currentTarget.value = '' }} /></label></div></div>

    <section className="panel input-panel"><div className="panel-heading"><div><span className="section-kicker">PERISHABLE STOCK</span><h2>Inventory batches <span className="count-badge">{inputs.inventory.length}</span></h2><p>Quantity is measured in kg; shelf life is estimated usable time remaining at dispatch.</p></div><input className="search-input" aria-label="Filter inventory" placeholder="Filter batches" value={filter} onChange={(e) => setFilter(e.target.value)} /></div>
      <div className="table-scroll"><table className="data-table editable-table"><thead><tr><th>Batch ID</th><th>Commodity</th><th>Available</th><th>Usable life</th><th>Handling notes</th><th>Eligible destinations</th></tr></thead><tbody>{batches.map((batch, visibleIndex) => {
        const index = inputs.inventory.indexOf(batch)
        return <tr key={`${batch.batch_id}-${index}`}>
          <td><input aria-label="Batch ID" value={batch.batch_id} onChange={(e) => updateBatch(visibleIndex, { batch_id: e.target.value })} /></td>
          <td><input aria-label="Commodity" value={batch.commodity} onChange={(e) => updateBatch(visibleIndex, { commodity: e.target.value })} /></td>
          <td><div className="number-field"><input aria-label="Available quantity in kilograms" type="number" min="0" step="1" value={batch.quantity_kg} onChange={(e) => updateBatch(visibleIndex, { quantity_kg: numberValue(e.target.value) })} /><span>kg</span></div></td>
          <td><div className="number-field"><input aria-label="Estimated shelf life in hours" type="number" min="0" step="1" value={batch.shelf_life_hours} onChange={(e) => updateBatch(visibleIndex, { shelf_life_hours: numberValue(e.target.value) })} /><span>h</span></div></td>
          <td><input aria-label="Handling notes" value={batch.handling_notes} onChange={(e) => updateBatch(visibleIndex, { handling_notes: e.target.value })} /></td>
          <td><input aria-label="Eligible destinations separated by semicolons" value={batch.eligible_destinations.join('; ')} placeholder="All markets with demand" onChange={(e) => updateBatch(visibleIndex, { eligible_destinations: e.target.value.split(';').map((item) => item.trim()).filter(Boolean) })} /></td>
        </tr>
      })}</tbody></table></div>
      <div className="table-bottomline"><span>{batches.length} batches shown · {inputs.inventory.length} total</span><span><i className="legend-swatch legend-risk" /> ≤24 estimated hours is the at-risk threshold</span></div>
    </section>

    <section className="panel input-panel"><div className="panel-heading"><div><span className="section-kicker">ROUTE & MARKET ECONOMICS</span><h2>Destinations and transport</h2><p>Capacity is shared by all commodities at each destination across the single planning horizon.</p></div><div className="synthetic-chip"><span className="tiny-dot" />Illustrative synthetic inputs</div></div>
      <div className="table-scroll"><table className="data-table market-table"><thead><tr><th>Market</th><th>Travel</th><th>Handling</th><th>Transport</th><th>Capacity</th><th>Demand map</th><th>Price map</th></tr></thead><tbody>{inputs.destinations.map((destination, index) => <MarketRow key={destination.destination_id} destination={destination} onChange={(update) => updateDestination(index, update)} />)}</tbody></table></div>
    </section>

    <div className="assumption-callout"><AlertTriangle size={17} /><div><strong>Input estimates are not guarantees.</strong><span> Prices, travel times, demand, capacities, and shelf-life figures in the sample are synthetic and illustrative. Verify operational data before dispatch.</span></div><span className="callout-check"><Check size={15} /></span></div>
  </>
}
