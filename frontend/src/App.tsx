import { useMemo, useState } from 'react'

import { analyzeCompetitor, buildPlan, renderPlan, selfAnalyze, similarProducts, uploadImage } from './api/client'
import type { CompetitorStructure, PlanResponse, SelfAnalysis, SimilarProduct } from './types'
import './styles.css'

const fixedSections = ['hook', 'empathy', 'contrast', 'proof', 'detail', 'offer', 'faq']

function App() {
  const [file, setFile] = useState<File | null>(null)
  const [productKey, setProductKey] = useState('')
  const [imageId, setImageId] = useState<number | null>(null)
  const [analysis, setAnalysis] = useState<SelfAnalysis | null>(null)
  const [similar, setSimilar] = useState<SimilarProduct[]>([])
  const [selected, setSelected] = useState<SimilarProduct | null>(null)
  const [manualMode, setManualMode] = useState(false)
  const [competitor, setCompetitor] = useState<CompetitorStructure | null>(null)
  const [plan, setPlan] = useState<PlanResponse | null>(null)
  const [renderResult, setRenderResult] = useState<{ preview_urls: string[]; files: string[]; output_dir: string } | null>(null)
  const [provider, setProvider] = useState('mock')

  const step = useMemo(() => {
    if (!imageId) return 1
    if (!selected) return 2
    if (!plan) return 3
    return 4
  }, [imageId, selected, plan])

  const doUpload = async () => {
    if (!file) return
    const up = await uploadImage(file)
    setProductKey(up.product_key)
    setImageId(up.image_id)
    setAnalysis(await selfAnalyze(up.image_id))
    setSimilar(await similarProducts(up.product_key))
  }

  const doCompetitor = async () => {
    if (!productKey || !selected) return
    const structure = manualMode
      ? await analyzeCompetitor({ product_key: productKey, uploaded_assets_ids: [imageId!], url: undefined })
      : await analyzeCompetitor({ product_key: productKey, url: selected.url })
    setCompetitor(structure)
    setPlan(await buildPlan({ product_key: productKey, self_analysis: analysis!, competitor_structure: structure }))
  }

  const doRender = async () => {
    if (!plan) return
    const rendered = await renderPlan({
      product_key: productKey,
      plan,
      target_width: 860,
      max_height_per_image: 2000,
      provider
    })
    setRenderResult(rendered)
  }

  const openOutputFolder = () => {
    if (!renderResult) return
    window.open(`file://${renderResult.output_dir}`, '_blank')
  }

  return (
    <main className="wrap">
      <h1>Detail Page Studio</h1>
      <p>Step {step} / 4</p>

      <section>
        <h2>Step 1: Upload</h2>
        <input type="file" accept="image/*" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        <button onClick={doUpload} disabled={!file}>Upload + Analyze</button>
        {productKey && <p>product_key: <code>{productKey}</code></p>}
      </section>

      {similar.length > 0 && (
        <section>
          <h2>Step 2: Similar products</h2>
          <div className="grid">
            {similar.map((p) => (
              <button key={p.id} className={selected?.id === p.id ? 'card selected' : 'card'} onClick={() => setSelected(p)}>
                <img src={p.thumbnail} alt={p.title} />
                <strong>{p.title}</strong>
                <small>{p.source}</small>
              </button>
            ))}
          </div>
        </section>
      )}

      {selected && (
        <section>
          <h2>Step 3: Competitor structure + plan</h2>
          <label>
            <input type="checkbox" checked={manualMode} onChange={(e) => setManualMode(e.target.checked)} />
            Manual input mode (use uploaded assets if scraping fails)
          </label>
          <button onClick={doCompetitor}>Analyze competitor + Build plan</button>
          {competitor && (
            <pre>{JSON.stringify(competitor, null, 2)}</pre>
          )}
          {plan && (
            <div>
              {fixedSections.map((name) => {
                const sec = plan.sections.find((s) => s.name === name)
                return (
                  <div key={name} className="section-edit">
                    <h3>{name.toUpperCase()}</h3>
                    <input
                      value={sec?.title ?? ''}
                      onChange={(e) => {
                        if (!plan) return
                        setPlan({
                          ...plan,
                          sections: plan.sections.map((s) => (s.name === name ? { ...s, title: e.target.value } : s))
                        })
                      }}
                    />
                  </div>
                )
              })}
            </div>
          )}
        </section>
      )}

      {plan && (
        <section>
          <h2>Step 4: Render + preview</h2>
          <label>
            Provider:
            <select value={provider} onChange={(e) => setProvider(e.target.value)}>
              <option value="mock">Mock</option>
              <option value="nanobanana">NanoBanana</option>
              <option value="comfyui">ComfyUI</option>
            </select>
          </label>
          <button onClick={doRender}>Render</button>
          {renderResult && (
            <>
              <p><strong>Output folder:</strong> {renderResult.output_dir}</p>
              <button onClick={openOutputFolder}>Open output folder</button>
              <div className="grid">
                {renderResult.preview_urls.map((u) => (
                  <img key={u} src={`http://127.0.0.1:8000${u}`} alt={u} className="preview" />
                ))}
              </div>
            </>
          )}
        </section>
      )}
    </main>
  )
}

export default App
