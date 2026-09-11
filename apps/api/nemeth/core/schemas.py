"""Schema fragments shared by every module (no domain imports here, to avoid cycles)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AuditFields(BaseModel):
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str
