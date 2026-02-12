from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.schemas.contracts import PlanResponse, PlanSection, RenderResponse, SECTIONS
from app.services.image_providers import ImageProvider


class TemplateRenderer:
    def __init__(self, outputs_dir: str):
        self.outputs_dir = Path(outputs_dir)

    def render(
        self,
        plan: PlanResponse,
        target_width: int = 860,
        max_height_per_image: int = 2000,
        provider: ImageProvider | None = None,
    ) -> RenderResponse:
        files: list[str] = []
        preview_urls: list[str] = []
        root = self.outputs_dir / plan.product_key
        root.mkdir(parents=True, exist_ok=True)

        section_map = {s.name: s for s in plan.sections}
        ordered_sections = [
            section_map.get(name, PlanSection(name=name, title=f"{name.title()} strategy", bullets=["(Auto-filled minimal content)"], icon="⬜"))
            for name in SECTIONS
        ]

        for section in ordered_sections:
            section_dir = root / section.name
            section_dir.mkdir(parents=True, exist_ok=True)
            ref_image = self._generate_reference_image(provider, section, target_width)
            canvas = self._draw_section(section, target_width, ref_image)
            chunks = self._slice_image(canvas, max_height_per_image)
            for idx, chunk in enumerate(chunks):
                out_path = section_dir / f"{idx:03d}.png"
                chunk.save(out_path, format="PNG")
                files.append(str(out_path))
                preview_urls.append(f"/outputs/{plan.product_key}/{section.name}/{idx:03d}.png")

        return RenderResponse(product_key=plan.product_key, files=files, preview_urls=preview_urls, output_dir=str(root.resolve()))

    def _generate_reference_image(self, provider: ImageProvider | None, section: PlanSection, width: int) -> Image.Image | None:
        if provider is None:
            return None
        prompt = f"Create clean non-branded abstract background for {section.name} section"
        try:
            raw = provider.generate(prompt=prompt, width=width, height=260)
            with Image.open(BytesIO(raw)) as im:
                return im.convert("RGB")
        except Exception:
            return None

    def _draw_section(self, section: PlanSection, width: int, reference: Image.Image | None = None) -> Image.Image:
        line_height = 44
        extra_top = 280 if reference else 0
        base_height = 180 + extra_top + max(len(section.bullets), 1) * line_height
        im = Image.new("RGB", (width, base_height), "white")
        draw = ImageDraw.Draw(im)
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()

        y_start = 24
        if reference:
            im.paste(reference.resize((width, 260)), (0, 0))
            draw.rectangle((0, 0, width - 1, 259), outline="#cccccc", width=1)
            y_start = 300

        draw.text((30, y_start), f"[{section.name.upper()}] {section.title}", fill="black", font=title_font)
        y = y_start + 60
        for bullet in section.bullets or ["(No content provided)"]:
            draw.rectangle((30, y + 6, 42, y + 18), outline="black", width=1)
            draw.text((56, y), bullet, fill="black", font=body_font)
            y += line_height
        draw.text((30, y + 10), "Icon placeholder: ◻", fill="gray", font=body_font)
        return im

    def _slice_image(self, image: Image.Image, max_height: int) -> list[Image.Image]:
        if image.height <= max_height:
            return [image]
        result: list[Image.Image] = []
        top = 0
        while top < image.height:
            bottom = min(top + max_height, image.height)
            result.append(image.crop((0, top, image.width, bottom)))
            top = bottom
        return result
