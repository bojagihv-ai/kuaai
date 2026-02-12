# Detail Page Studio (Local MVP)

A local-first full-stack MVP for generating product detail-page section images with a fixed 7-section framework:
`hook / empathy / contrast / proof / detail / offer / faq`.

## Stack
- Backend: Python 3.11, FastAPI, SQLite (SQLModel), Pillow, Playwright + BeautifulSoup
- Frontend: React + Vite + TypeScript
- Image providers: Mock (default), NanoBanana adapter, ComfyUI adapter

## Core Guarantees
- `product_key` format: `{YYYYMMDD_HHMMSS}_{uploaded_file_size_bytes}`
- Always generates all 7 fixed sections.
- Competitor analysis is structure-only inspiration. No verbatim reuse.
- Manual competitor mode supported (`uploaded_assets_ids`) when URL scraping fails.
- JSON-contract parser with repair retry for strict schema handling.

## Project Layout
```
repo/
  backend/
  frontend/
  README.md
  .env.example
```

## Run (Windows PowerShell)

### 1) Backend
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install pydantic-settings
playwright install chromium
cd ..
copy .env.example .env
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2) Frontend
```powershell
cd frontend
npm install
npm run dev
```

Open: `http://127.0.0.1:5173`

## API Endpoints
- `POST /api/upload-image`
- `POST /api/self-analyze`
- `POST /api/similar-products`
- `POST /api/competitor/analyze`
- `POST /api/plan`
- `POST /api/render`
- `GET /api/jobs/{id}`
- Static previews: `/outputs/...`

## Tests
```powershell
cd backend
pytest
```

## Notes
- Render outputs write to: `outputs/{product_key}/{section}/000.png...`
- Section renderer supports:
  - `target_width` (default `860`)
  - `max_height_per_image` (default `2000`)
  - automatic slicing when section exceeds height limit

## Next Steps
1. Replace stub similarity with CLIP + FAISS index.
2. Build drag-drop template designer and richer typography controls.
3. Add brand preset packs (fonts/colors/layout).
4. Add batch processing queue for multiple SKUs.
5. Add caching/rate limiting and persistent job workers.
