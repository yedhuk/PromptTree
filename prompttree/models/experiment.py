from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class LabExperiment(BaseModel):
    id: str = Field(default_factory=lambda: f"lab_{uuid.uuid4().hex[:8]}")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    prompt_text: str
    model: str
    temperature: float = 0.7
    vars: dict[str, Any] = Field(default_factory=dict)
    images: list[str] = Field(default_factory=list)
    response: Optional[str] = None
    error: Optional[str] = None
    promoted: bool = False
    promoted_to: Optional[str] = None
