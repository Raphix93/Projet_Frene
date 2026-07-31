from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .models import Annotation


def make_report(
    tei_input: Path,
    json_input: Path,
    tei_output: Path,
    source_sha256: str,
    declared_sha256: str | None,
    annotations: list[Annotation],
) -> dict:
    counts: dict[str, int] = {}
    for annotation in annotations:
        counts[annotation.status] = counts.get(annotation.status, 0) + 1

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "input": {
            "tei": str(tei_input),
            "annotations": str(json_input),
            "sha256": source_sha256,
            "declaredSha256": declared_sha256,
            "sha256Matches": declared_sha256 in {None, "", f"sha256:{source_sha256}", source_sha256},
        },
        "output": {"tei": str(tei_output)},
        "summary": {
            "total": len(annotations),
            **counts,
        },
        "annotations": [
            {
                "id": item.annotation_id,
                "type": item.kind,
                "exact": item.exact,
                "replacement": item.replacement,
                "uri": item.uri,
                "exportedStart": item.exported_start,
                "exportedEnd": item.exported_end,
                "matchedStart": item.matched_start,
                "matchedEnd": item.matched_end,
                "abIndex": item.ab_index,
                "localStart": item.local_start,
                "localEnd": item.local_end,
                "status": item.status,
                "message": item.message,
            }
            for item in annotations
        ],
    }
