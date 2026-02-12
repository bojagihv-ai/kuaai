from __future__ import annotations

import json
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, ValidationError

SECTIONS = ["hook", "empathy", "contrast", "proof", "detail", "offer", "faq"]


class UploadResponse(BaseModel):
    product_key: str
    image_id: int


class SelfAnalyzeRequest(BaseModel):
    image_id: int


class SelfAnalysis(BaseModel):
    materials: List[str] = Field(default_factory=list)
    colors: List[str] = Field(default_factory=list)
    shape: str = ""
    use_case: List[str] = Field(default_factory=list)
    positioning: str = ""
    keywords: List[str] = Field(default_factory=list)


class SimilarProductsRequest(BaseModel):
    product_key: str


class SimilarProduct(BaseModel):
    id: str
    title: str
    thumbnail: str
    source: str
    url: str


class SimilarProductsResponse(BaseModel):
    product_key: str
    suggestions: List[SimilarProduct]


class CompetitorAnalyzeRequest(BaseModel):
    product_key: str
    url: Optional[str] = None
    uploaded_assets_ids: List[int] = Field(default_factory=list)


class CompetitorStructure(BaseModel):
    source: Literal["url", "manual_assets", "fallback"]
    layout: List[str] = Field(default_factory=list)
    sectioning: List[str] = Field(default_factory=list)
    tone: List[str] = Field(default_factory=list)
    notes: str = ""


class PlanRequest(BaseModel):
    product_key: str
    self_analysis: SelfAnalysis
    competitor_structure: CompetitorStructure


class PlanSection(BaseModel):
    name: str
    title: str
    bullets: List[str] = Field(default_factory=list)
    icon: str = ""


class PlanResponse(BaseModel):
    product_key: str
    sections: List[PlanSection]


class RenderRequest(BaseModel):
    product_key: str
    plan: PlanResponse
    target_width: int = 860
    max_height_per_image: int = 2000
    provider: str = "mock"


class RenderResponse(BaseModel):
    product_key: str
    files: List[str]
    preview_urls: List[str]
    output_dir: str


class JobResponse(BaseModel):
    id: int
    product_key: str
    status: str
    progress: int
    message: str
    result: Dict[str, Any]


class JsonContractHelper:
    @staticmethod
    def parse_with_repair(raw: str, schema_cls: type[BaseModel]) -> BaseModel:
        attempts = [raw]
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.replace("json", "", 1).strip()
            attempts.append(cleaned)
        if "\n" in cleaned:
            attempts.append(cleaned.replace("\n", " "))

        last_error: ValidationError | None = None
        for attempt in attempts:
            try:
                payload = json.loads(attempt)
                return schema_cls.model_validate(payload)
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = exc if isinstance(exc, ValidationError) else None
                continue
        if last_error:
            raise last_error
        raise ValueError("Unable to parse JSON output")
