from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class TextSelector:
    """Sélecteur textuel sérialisé par l’interface d’annotation."""

    exact: str
    start: int | None = None
    end: int | None = None
    prefix: str = ""
    suffix: str = ""


@dataclass(slots=True)
class Annotation:
    """Représentation normalisée d’une annotation Recogito."""

    annotation_id: str
    annotation_type: str
    selector: TextSelector
    replacement_text: str | None = None
    authority_uri: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AnnotationManifest:
    """Conteneur documentaire des annotations."""

    annotations: list[Annotation]
    project: str | None = None
    document: str | None = None
    format_name: str | None = None
    format_version: str | None = None
    source_tei: str | None = None
    source_sha256: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ValidationIssue:
    """Anomalie détectée pendant la validation."""

    level: str
    code: str
    message: str
    annotation_id: str | None = None


@dataclass(slots=True)
class ValidationReport:
    """Résultat global de la validation."""

    valid: bool
    annotations_total: int
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)
    document_sha256: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "annotations_total": self.annotations_total,
            "document_sha256": self.document_sha256,
            "errors": [
                {
                    "level": issue.level,
                    "code": issue.code,
                    "message": issue.message,
                    "annotation_id": issue.annotation_id,
                }
                for issue in self.errors
            ],
            "warnings": [
                {
                    "level": issue.level,
                    "code": issue.code,
                    "message": issue.message,
                    "annotation_id": issue.annotation_id,
                }
                for issue in self.warnings
            ],
        }
