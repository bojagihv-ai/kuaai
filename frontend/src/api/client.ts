import type { CompetitorStructure, PlanResponse, SelfAnalysis, SimilarProduct } from '../types'

const API = 'http://127.0.0.1:8000/api'

export async function uploadImage(file: File): Promise<{ product_key: string; image_id: number }> {
  const fd = new FormData()
  fd.append('file', file)
  const res = await fetch(`${API}/upload-image`, { method: 'POST', body: fd })
  if (!res.ok) throw new Error('Upload failed')
  return res.json()
}

export async function selfAnalyze(image_id: number): Promise<SelfAnalysis> {
  const res = await fetch(`${API}/self-analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image_id })
  })
  return res.json()
}

export async function similarProducts(product_key: string): Promise<SimilarProduct[]> {
  const res = await fetch(`${API}/similar-products`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ product_key })
  })
  const body = await res.json()
  return body.suggestions
}

export async function analyzeCompetitor(payload: {
  product_key: string
  url?: string
  uploaded_assets_ids?: number[]
}): Promise<CompetitorStructure> {
  const res = await fetch(`${API}/competitor/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  return res.json()
}

export async function buildPlan(payload: {
  product_key: string
  self_analysis: SelfAnalysis
  competitor_structure: CompetitorStructure
}): Promise<PlanResponse> {
  const res = await fetch(`${API}/plan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  return res.json()
}

export async function renderPlan(payload: {
  product_key: string
  plan: PlanResponse
  target_width: number
  max_height_per_image: number
  provider: string
}): Promise<{ job_id: number; preview_urls: string[]; files: string[]; output_dir: string }> {
  const res = await fetch(`${API}/render`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  return res.json()
}
