import type { ComparisonResult, Destination, InventoryBatch, PlanInput, ScenarioResult } from './types'

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init)
  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try {
      const body = await response.json()
      if (typeof body.detail === 'string') message = body.detail
      else if (body.detail?.message) message = body.detail.message
      else if (Array.isArray(body.details)) message = body.details.map((item: { location?: string; message?: string }) => `${item.location ? `${item.location}: ` : ''}${item.message ?? 'Invalid input'}`).join('; ')
      else if (Array.isArray(body.detail?.errors)) message = body.detail.errors.join('; ')
      else if (body.error) message = body.error
    } catch {
      // Keep the status fallback when the server did not return JSON.
    }
    throw new Error(message)
  }
  return response.json() as Promise<T>
}

export async function loadSample(): Promise<PlanInput> {
  return request<PlanInput>('/api/sample-data')
}

export async function validateInputs(inputs: PlanInput): Promise<{ valid: boolean; inventory_batches: number; destinations: number; messages: string[]; total_inventory_kg: number }> {
  return request('/api/inventory/validate', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ inputs }),
  })
}

export async function compare(inputs: PlanInput): Promise<ComparisonResult> {
  return request('/api/compare', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ inputs }),
  })
}

export async function simulate(inputs: PlanInput, multipliers: { travel_time_multiplier: number; demand_multiplier: number; capacity_multiplier: number }): Promise<ScenarioResult> {
  return request('/api/scenarios/simulate', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ inputs, ...multipliers }),
  })
}

export async function uploadInventory(file: File): Promise<{ valid: boolean; inventory: InventoryBatch[]; imported_rows: number }> {
  const form = new FormData()
  form.append('file', file)
  return request('/api/inventory/import', { method: 'POST', body: form })
}

async function saveFile(url: string, body: unknown, fallbackName: string): Promise<void> {
  const response = await fetch(url, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  })
  if (!response.ok) {
    let message = `Export failed (${response.status})`
    try {
      const payload = await response.json()
      message = payload.detail?.message ?? payload.error ?? message
    } catch { /* use fallback */ }
    throw new Error(message)
  }
  const blob = await response.blob()
  const disposition = response.headers.get('content-disposition') ?? ''
  const name = disposition.match(/filename=\"?([^\";]+)\"?/i)?.[1] ?? fallbackName
  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = name
  document.body.append(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(objectUrl)
}

export function exportAllocations(inputs: PlanInput, strategy: 'optimized' | 'fefo_baseline'): Promise<void> {
  return saveFile('/api/exports/allocations', { inputs, strategy }, 'freshroute-allocations.csv')
}

export function exportComparison(inputs: PlanInput): Promise<void> {
  return saveFile('/api/exports/comparison', { inputs }, 'freshroute-comparison.csv')
}

export function exportReport(inputs: PlanInput, scenarioLabel: string): Promise<void> {
  return saveFile('/api/reports/export', { inputs, scenario_label: scenarioLabel }, 'freshroute-report.html')
}

export function inventoryTemplate(): void {
  const link = document.createElement('a')
  link.href = '/api/templates/inventory.csv'
  link.download = 'freshroute-inventory-template.csv'
  document.body.append(link)
  link.click()
  link.remove()
}

export function updateDestination(inputs: PlanInput, index: number, update: Partial<Destination>): PlanInput {
  return { ...inputs, destinations: inputs.destinations.map((item, i) => i === index ? { ...item, ...update } : item) }
}
