import json
from typing import Type

from pydantic import BaseModel

from app.schemas.contracts import JsonContractHelper


def enforce_json_contract(raw_text: str, schema: Type[BaseModel]) -> BaseModel:
    return JsonContractHelper.parse_with_repair(raw_text, schema)


def to_strict_json(model: BaseModel) -> str:
    return json.dumps(model.model_dump(), ensure_ascii=False)
