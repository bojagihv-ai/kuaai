from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel import Session

from app.core.settings import settings
from app.db.session import get_session
from app.models.entities import ImageAsset, Job
from app.schemas.contracts import (
    CompetitorAnalyzeRequest,
    JobResponse,
    PlanRequest,
    PlanResponse,
    RenderRequest,
    SelfAnalyzeRequest,
    SimilarProductsRequest,
    SimilarProductsResponse,
    UploadResponse,
)
from app.services.analysis import analyze_image
from app.services.competitor import CompetitorAnalyzer
from app.services.image_providers import get_provider
from app.services.jobs import create_job, update_job
from app.services.planner import PlanBuilder
from app.services.renderer import TemplateRenderer
from app.services.similarity import StubSimilarityProvider
from app.utils.product_key import build_product_key

router = APIRouter(prefix="/api", tags=["api"])


@router.post("/upload-image", response_model=UploadResponse)
def upload_image(file: UploadFile = File(...), session: Session = Depends(get_session)):
    raw = file.file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")
    product_key = build_product_key(len(raw))
    target_dir = Path(settings.uploads_dir) / product_key
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / file.filename
    with path.open("wb") as f:
        f.write(raw)

    asset = ImageAsset(product_key=product_key, path=str(path), original_name=file.filename, size_bytes=len(raw))
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return UploadResponse(product_key=product_key, image_id=asset.id)


@router.post("/self-analyze")
def self_analyze(req: SelfAnalyzeRequest, session: Session = Depends(get_session)):
    image = session.get(ImageAsset, req.image_id)
    if not image:
        raise HTTPException(404, "Image not found")
    return analyze_image(image.path)


@router.post("/similar-products", response_model=SimilarProductsResponse)
def similar_products(req: SimilarProductsRequest):
    provider = StubSimilarityProvider()
    return SimilarProductsResponse(product_key=req.product_key, suggestions=provider.suggest(req.product_key))


@router.post("/competitor/analyze")
def competitor_analyze(req: CompetitorAnalyzeRequest, session: Session = Depends(get_session)):
    analyzer = CompetitorAnalyzer()
    if req.url:
        return analyzer.analyze_from_url(req.url)
    if req.uploaded_assets_ids:
        assets = [session.get(ImageAsset, aid) for aid in req.uploaded_assets_ids]
        paths = [a.path for a in assets if a]
        return analyzer.analyze_from_assets(paths)
    return analyzer.analyze_from_assets([])


@router.post("/plan", response_model=PlanResponse)
def plan(req: PlanRequest):
    return PlanBuilder().build(req)


@router.post("/render")
def render(req: RenderRequest, session: Session = Depends(get_session)):
    job = create_job(session, req.product_key, "Render started")
    update_job(session, job, status="running", progress=40, message="Rendering sections")
    renderer = TemplateRenderer(settings.outputs_dir)
    provider = get_provider(req.provider or settings.default_image_provider)
    result = renderer.render(
        req.plan,
        target_width=req.target_width,
        max_height_per_image=req.max_height_per_image,
        provider=provider,
    )
    update_job(session, job, status="completed", progress=100, message="Render complete", result=result.model_dump())
    return {"job_id": job.id, **result.model_dump()}


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: int, session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return JobResponse(
        id=job.id,
        product_key=job.product_key,
        status=job.status,
        progress=job.progress,
        message=job.message,
        result=json.loads(job.result_json or "{}"),
    )
