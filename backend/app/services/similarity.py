from abc import ABC, abstractmethod

from app.schemas.contracts import SimilarProduct


class SimilarityProvider(ABC):
    @abstractmethod
    def suggest(self, product_key: str) -> list[SimilarProduct]:
        raise NotImplementedError


class StubSimilarityProvider(SimilarityProvider):
    def suggest(self, product_key: str) -> list[SimilarProduct]:
        base = "https://example.com/product"
        return [
            SimilarProduct(
                id=f"{product_key}-sim-{idx}",
                title=f"Reference Product {idx + 1}",
                thumbnail=f"https://picsum.photos/seed/{product_key}{idx}/300/300",
                source="StubCatalog",
                url=f"{base}/{idx + 1}",
            )
            for idx in range(5)
        ]
