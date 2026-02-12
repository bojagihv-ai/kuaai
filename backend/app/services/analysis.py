from pathlib import Path

from PIL import Image

from app.schemas.contracts import SelfAnalysis


def analyze_image(path: str) -> SelfAnalysis:
    image_path = Path(path)
    with Image.open(image_path) as im:
        rgb = im.convert("RGB")
        resized = rgb.resize((1, 1))
        r, g, b = resized.getpixel((0, 0))
    palette = []
    if r > g and r > b:
        palette.append("warm red")
    if g >= r and g >= b:
        palette.append("natural green")
    if b >= r and b >= g:
        palette.append("cool blue")
    if not palette:
        palette.append("neutral")

    return SelfAnalysis(
        materials=["composite", "fabric", "metal accent"],
        colors=palette,
        shape="streamlined",
        use_case=["daily use", "gift scenario", "workspace"],
        positioning="Affordable premium with practical design",
        keywords=["durable", "comfortable", "modern", "value"],
    )
