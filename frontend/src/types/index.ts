export type SelfAnalysis = {
  materials: string[]
  colors: string[]
  shape: string
  use_case: string[]
  positioning: string
  keywords: string[]
}

export type SimilarProduct = {
  id: string
  title: string
  thumbnail: string
  source: string
  url: string
}

export type CompetitorStructure = {
  source: 'url' | 'manual_assets' | 'fallback'
  layout: string[]
  sectioning: string[]
  tone: string[]
  notes: string
}

export type PlanSection = {
  name: string
  title: string
  bullets: string[]
  icon: string
}

export type PlanResponse = {
  product_key: string
  sections: PlanSection[]
}
