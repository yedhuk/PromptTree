from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class NodeMetadata(BaseModel):
    encrypted: bool = False
    model: str = "gpt-4o"
    temperature: float = 0.7

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tags: list[str] = Field(default_factory=list)


class RegistryNode(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    parent_id: Optional[str] = None
    name: str = ""          # prompt family name, shared across all versions
    display_name: str = ""  # short label shown on graph node, unique per version
    metadata: NodeMetadata = Field(default_factory=NodeMetadata)
    content: str = ""
