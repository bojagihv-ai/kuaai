from app.schemas.contracts import PlanRequest, PlanResponse, PlanSection, SECTIONS


class PlanBuilder:
    def build(self, req: PlanRequest) -> PlanResponse:
        sections: list[PlanSection] = []
        keyword_line = ", ".join(req.self_analysis.keywords[:3]) or "quality"
        tone_line = ", ".join(req.competitor_structure.tone[:2])
        for name in SECTIONS:
            sections.append(
                PlanSection(
                    name=name,
                    title=f"{name.title()} strategy",
                    bullets=[
                        f"Focus on {keyword_line} with original wording.",
                        f"Structure inspired by competitor layout ({tone_line}) without copying.",
                        f"Support positioning: {req.self_analysis.positioning}.",
                    ],
                    icon="⬜",
                )
            )
        return PlanResponse(product_key=req.product_key, sections=sections)
