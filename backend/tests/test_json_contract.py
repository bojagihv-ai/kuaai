from pydantic import BaseModel

from app.schemas.contracts import JsonContractHelper


class Demo(BaseModel):
    hello: str


def test_json_contract_parses_clean_json():
    result = JsonContractHelper.parse_with_repair('{"hello":"world"}', Demo)
    assert result.hello == "world"


def test_json_contract_repairs_code_fence():
    raw = '```json\n{"hello":"world"}\n```'
    result = JsonContractHelper.parse_with_repair(raw, Demo)
    assert result.hello == "world"
