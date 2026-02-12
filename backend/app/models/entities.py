from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class ImageAsset(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    product_key: str = Field(index=True)
    path: str
    original_name: str
    size_bytes: int
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Job(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    product_key: str = Field(index=True)
    status: str = "pending"
    progress: int = 0
    message: str = ""
    result_json: str = "{}"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
