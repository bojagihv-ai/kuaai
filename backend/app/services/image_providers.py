from __future__ import annotations

from abc import ABC, abstractmethod
from io import BytesIO

import httpx
from PIL import Image, ImageDraw

from app.core.settings import settings


class ImageProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, width: int = 860, height: int = 1200) -> bytes:
        raise NotImplementedError


class MockProvider(ImageProvider):
    def generate(self, prompt: str, width: int = 860, height: int = 1200) -> bytes:
        img = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(img)
        draw.text((20, 20), f"Mock image\n{prompt[:120]}", fill="black")
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()


class NanoBananaProvider(ImageProvider):
    def generate(self, prompt: str, width: int = 860, height: int = 1200) -> bytes:
        if not settings.nanobanana_url:
            raise RuntimeError("nanobanana_url is not configured")
        payload = {"prompt": prompt, "width": width, "height": height}
        with httpx.Client(timeout=60) as client:
            resp = client.post(settings.nanobanana_url, json=payload)
            resp.raise_for_status()
            return resp.content


class ComfyUIProvider(ImageProvider):
    def generate(self, prompt: str, width: int = 860, height: int = 1200) -> bytes:
        payload = {"prompt": prompt, "width": width, "height": height}
        with httpx.Client(timeout=60) as client:
            resp = client.post(f"{settings.comfyui_url.rstrip('/')}/generate", json=payload)
            resp.raise_for_status()
            return resp.content


def get_provider(name: str) -> ImageProvider:
    providers = {
        "mock": MockProvider(),
        "nanobanana": NanoBananaProvider(),
        "comfyui": ComfyUIProvider(),
    }
    return providers.get(name, MockProvider())
