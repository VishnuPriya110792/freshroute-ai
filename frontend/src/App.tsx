import { useEffect, useState } from 'react'
import { AlertCircle, BarChart3, Boxes, FileDown, Leaf, LoaderCircle, Map, PackageCheck, RefreshCw, Route, SlidersHorizontal, Truck } from 'lucide-react'
import { compare, exportAllocations, exportComparison, exportReport, inventoryTemplate, loadSample, simulate, uploadInventory, validateInputs } from './api'
import type { ComparisonResult, DiscountRecommendation, PlanInput, ScenarioResult } from './types'
import Overview from './components/Overview'
import Inventory from './components/Inventory'
import Planner from './components/Planner'
import Scenario from './components/Scenario'
import Comparison from './components/Comparison'
import Discounts from './components/Discounts'

const navItems = [
  { id: 'overview', label: 'Overview', icon: BarChart3 },
  { id: 'inventory', label: 'Inventory & inputs', icon: Boxes },
  { id: 'planner', label: 'Distribution planner', icon: Route },
  { id: 'comparison', label: 'Baseline comparison', icon: Map },
  { id: 'scenario', label: 'What-if simulator', icon: SlidersHorizontal },
  { id: 'discounts', label: 'Discounts & exports', icon: FileDown },
] as const

type Page = typeof navItems[number]['id']

function App() {
  const [page, setPage] = useState<Page>('overview')
  const [inputs, setInputs] = useState<PlanInput | null>(null)
  const [comparison, setComparison] = useState<ComparisonResult | null>(null)
  const [scenarioResult, setScenarioResult] = useState<ScenarioResult | null>(null)
  const [discounts, setDiscounts] = useState<DiscountRecommendation[]>([])
  const [busy, setBusy] = useState(false)
  const [loadingSample, setLoadingSample] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [scenarioMultipliers, setScenarioMultipliers] = useState({ travel_time_multiplier: 1, demand_multiplier: 1, capacity_multiplier: 1 })

  const activeComparison = scenarioResult?.scenario ?? comparison
  const activeInputs = scenarioResult?.scenario_inputs ?? inputs
  const totalStock = activeComparison?.optimized.metrics.total_available_kg ?? null

  async function restoreSample() {
    setLoadingSample(true)
    setError('')
    setNotice('')
    try {
      const sample = await loadSample()
      setInputs(sample)
      setComparison(null)
      setScenarioResult(null)
      setDiscounts([])
      setNotice('Synthetic sample loaded. Generate a plan to calculate allocations and outcomes.')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not load the sample dataset.')
    } finally {
      setLoadingSample(false)
    }
  }

  useEffect(() => { void restoreSample() }, [])

  function updateInputs(next: PlanInput) {
    setInputs(next)
    setComparison(null)
    setScenarioResult(null)
    setDiscounts([])
    setError('')
    setNotice('Inputs changed. Revalidate and regenerate the plan to refresh calculated results.')
  }

  async function generatePlan() {
    if (!inputs) return
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const result = await compare(inputs)
      setComparison(result)
      setScenarioResult(null)
      const response = await fetch('/api/discounts', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ inputs }),
      })
      if (!response.ok) throw new Error('The plan was generated, but discount recommendations could not be loaded.')
      setDiscounts(await response.json() as DiscountRecommendation[])
      setNotice('Plan recalculated from the current inputs. Review the baseline as well as the optimized result.')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Plan generation failed. Review the inputs and try again.')
    } finally {
      setBusy(false)
    }
  }

  async function runScenario() {
    if (!inputs) return
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const result = await simulate(inputs, scenarioMultipliers)
      setScenarioResult(result)
      const response = await fetch('/api/discounts', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ inputs: result.scenario_inputs }),
      })
      if (!response.ok) throw new Error('The scenario was calculated, but scenario discount recommendations could not be loaded.')
      setDiscounts(await response.json() as DiscountRecommendation[])
      setNotice('Scenario recalculated against a separate copy. Your original inputs are unchanged.')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Scenario simulation failed. Review the inputs and try again.')
    } finally {
      setBusy(false)
    }
  }

  async function resetScenario() {
    setScenarioMultipliers({ travel_time_multiplier: 1, demand_multiplier: 1, capacity_multiplier: 1 })
    setScenarioResult(null)
    setError('')
    if (inputs && comparison) {
      try {
        const response = await fetch('/api/discounts', {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ inputs }),
        })
        if (!response.ok) throw new Error('Base-plan recommendations could not be restored.')
        setDiscounts(await response.json() as DiscountRecommendation[])
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : 'Could not restore base-plan recommendations.')
      }
    } else {
      setDiscounts([])
    }
    setNotice('Scenario reset. Original data and the latest base plan remain unchanged.')
  }

  async function checkInputs() {
    if (!inputs) return
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const result = await validateInputs(inputs)
      setNotice(`${result.messages.join(' ')} ${result.inventory_batches} batches · ${result.destinations} destinations · ${result.total_inventory_kg.toLocaleString()} kg.`)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Input validation failed.')
    } finally {
      setBusy(false)
    }
  }

  async function importCsv(file: File) {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const result = await uploadInventory(file)
      if (!inputs) return
      updateInputs({ ...inputs, inventory: result.inventory })
      setNotice(`${result.imported_rows} inventory rows imported. Destination data was preserved; validate inputs before generating a plan.`)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'CSV import failed; no rows were changed.')
    } finally {
      setBusy(false)
    }
  }

  async function runExport(action: () => Promise<void>, success: string) {
    if (!inputs) return
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await action()
      setNotice(success)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Export failed. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  if (loadingSample) {
    return <main className="boot-screen"><img className="brand-mark brand-mark-image" src="/freshroute-mark.svg" alt="" /><LoaderCircle className="spin" size={20} /> Loading the synthetic planning dataset…</main>
  }

  const currentLabel = scenarioResult ? 'Scenario copy' : 'Sample · illustrative'
  const pageTitle = navItems.find((item) => item.id === page)?.label ?? 'Overview'
  const exportProps = {
    ready: Boolean(inputs),
    hasPlan: Boolean(activeComparison),
    busy,
    onOptimizedCsv: () => void runExport(() => exportAllocations(activeInputs!, 'optimized'), 'Optimized allocation CSV downloaded.'),
    onBaselineCsv: () => void runExport(() => exportAllocations(activeInputs!, 'fefo_baseline'), 'FEFO baseline allocation CSV downloaded.'),
    onComparisonCsv: () => void runExport(() => exportComparison(activeInputs!), 'Baseline comparison CSV downloaded.'),
    onReport: () => void runExport(() => exportReport(activeInputs!, scenarioResult ? 'What-if scenario' : 'Current inputs'), 'Printable HTML summary downloaded. Open it and use Print / Save as PDF.'),
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup"><img className="brand-mark brand-mark-image" src="/freshroute-mark.svg" alt="" /><span><strong>FreshRoute</strong><small>AI · DISTRIBUTION INTELLIGENCE</small></span></div>
        <div className="sidebar-label">WORKSPACE</div>
        <nav className="main-nav" aria-label="Main navigation">
          {navItems.map(({ id, label, icon: Icon }) => (
            <button key={id} type="button" className={`nav-item ${page === id ? 'active' : ''}`} onClick={() => setPage(id)} aria-current={page === id ? 'page' : undefined}>
              <Icon size={17} strokeWidth={1.9} /><span>{label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="dataset-card"><span className="status-dot" /><div><strong>{currentLabel}</strong><small>{inputs?.inventory.length ?? 0} batches · {inputs?.destinations.length ?? 0} markets</small></div></div>
          <div className="synthetic-note"><span className="note-rule" />Sample prices, demand, times and shelf-life values are illustrative synthetic inputs.</div>
          <div className="sidebar-footer"><span className="footer-mark">FR</span><span>Less waste. Smarter routes.<br />Better margins.</span></div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumb"><span>Operations</span><span className="crumb-slash">/</span><strong>{pageTitle}</strong></div>
          <div className="top-actions"><span className={`scenario-chip ${scenarioResult ? 'scenario-on' : ''}`}><span className="status-dot" />{scenarioResult ? 'Scenario active' : 'One dispatch horizon'}</span><button className="button button-primary button-compact" onClick={() => void generatePlan()} disabled={!inputs || busy}><Truck size={16} />{busy ? 'Calculating…' : 'Generate plan'}</button></div>
        </header>

        <div className="workspace-content">
          {error && <div className="toast toast-error" role="alert"><AlertCircle size={18} /><div><strong>Could not complete that action</strong><span>{error}</span></div><button aria-label="Dismiss error" onClick={() => setError('')}>×</button></div>}
          {notice && !error && <div className="toast toast-success" role="status"><PackageCheck size={18} /><span>{notice}</span><button aria-label="Dismiss notice" onClick={() => setNotice('')}>×</button></div>}

          {page === 'overview' && <Overview inputs={activeInputs} comparison={activeComparison} totalStock={totalStock} busy={busy} onGenerate={() => void generatePlan()} onNavigate={setPage} />}
          {page === 'inventory' && inputs && <Inventory inputs={inputs} busy={busy} onChange={updateInputs} onUpload={(file) => void importCsv(file)} onValidate={() => void checkInputs()} onRestore={() => void restoreSample()} onTemplate={inventoryTemplate} />}
          {page === 'planner' && <Planner comparison={activeComparison} inputs={inputs} busy={busy} onGenerate={() => void generatePlan()} />}
          {page === 'comparison' && <Comparison comparison={activeComparison} />}
          {page === 'scenario' && inputs && <Scenario inputs={inputs} result={scenarioResult} busy={busy} multipliers={scenarioMultipliers} onMultipliers={setScenarioMultipliers} onRun={() => void runScenario()} onReset={() => void resetScenario()} />}
          {page === 'discounts' && <Discounts recommendations={discounts} comparison={activeComparison} exports={exportProps} />}

          <footer className="workspace-footer"><span><Leaf size={14} /> FreshRoute AI</span><span>Estimates are decision support, not a dispatch guarantee.</span><span className="footer-units">kg · hours · INR</span></footer>
        </div>
      </main>
    </div>
  )
}

export default App
