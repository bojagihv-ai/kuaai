from app.schemas.contracts import CompetitorStructure, PlanRequest, SECTIONS, SelfAnalysis
from app.services.planner import PlanBuilder


def test_plan_always_has_seven_sections():
    req = PlanRequest(
        product_key='abc',
        self_analysis=SelfAnalysis(),
        competitor_structure=CompetitorStructure(source='fallback')
    )
    plan = PlanBuilder().build(req)
    assert [s.name for s in plan.sections] == SECTIONS
