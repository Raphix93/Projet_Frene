from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Annotation:
    annotation_id: str
    kind: str
    exact: str
    exported_start: int
    exported_end: int
    replacement: str | None = None
    uri: str | None = None
    matched_start: int | None = None
    matched_end: int | None = None
    ab_index: int | None = None
    local_start: int | None = None
    local_end: int | None = None
    status: str = "pending"
    message: str = ""
    raw: dict[str, Any] = field(default_factory=dict)
