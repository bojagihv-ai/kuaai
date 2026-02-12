from pathlib import Path

from PIL import Image

from app.schemas.contracts import PlanResponse, PlanSection
from app.services.image_providers import ImageProvider
from app.services.renderer import TemplateRenderer


class BrokenProvider(ImageProvider):
    def generate(self, prompt: str, width: int = 860, height: int = 1200) -> bytes:
        raise RuntimeError("provider failure")


def test_slice_image_splits_large_canvas(tmp_path: Path):
    renderer = TemplateRenderer(str(tmp_path))
    image = Image.new('RGB', (100, 2300), 'white')
    chunks = renderer._slice_image(image, 2000)
    assert len(chunks) == 2
    assert chunks[0].height == 2000
    assert chunks[1].height == 300


def test_render_exports_pngs(tmp_path: Path):
    renderer = TemplateRenderer(str(tmp_path))
    plan = PlanResponse(product_key='k', sections=[PlanSection(name='hook', title='t', bullets=['a'], icon='')])
    result = renderer.render(plan, target_width=860, max_height_per_image=2000)
    assert result.files
    assert Path(result.files[0]).exists()


def test_render_auto_fills_missing_sections(tmp_path: Path):
    renderer = TemplateRenderer(str(tmp_path))
    plan = PlanResponse(product_key='k2', sections=[PlanSection(name='hook', title='Hook', bullets=['a'], icon='')])
    result = renderer.render(plan, target_width=860, max_height_per_image=2000)
    assert len(result.files) >= 7


def test_render_survives_provider_failure(tmp_path: Path):
    renderer = TemplateRenderer(str(tmp_path))
    plan = PlanResponse(product_key='k3', sections=[PlanSection(name='hook', title='Hook', bullets=['a'], icon='')])
    result = renderer.render(plan, provider=BrokenProvider())
    assert result.files
