from __future__ import annotations

from .constants import SUPPORTED_TYPES
from .models import (
    AnnotationManifest,
    ValidationIssue,
    ValidationReport,
)
from .utils import sha256_text, wikidata_id


def validate_annotations(
    manifest: AnnotationManifest,
    document_text: str,
    *,
    verify_hash: bool = False,
) -> ValidationReport:
    """Valide les annotations sans modifier la TEI."""

    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    document_hash = sha256_text(document_text)

    if verify_hash and manifest.source_sha256:
        if manifest.source_sha256.lower() != document_hash.lower():
            errors.append(
                ValidationIssue(
                    level="error",
                    code="SOURCE_HASH_MISMATCH",
                    message=(
                        "Le SHA-256 du texte TEI ne correspond pas "
                        "au SHA-256 déclaré dans le manifeste."
                    ),
                )
            )
    elif verify_hash and not manifest.source_sha256:
        warnings.append(
            ValidationIssue(
                level="warning",
                code="SOURCE_HASH_MISSING",
                message=(
                    "La vérification du hash a été demandée, mais "
                    "le manifeste ne déclare aucun SHA-256."
                ),
            )
        )

    seen_ids: set[str] = set()

    for annotation in manifest.annotations:
        annotation_id = annotation.annotation_id

        if annotation_id in seen_ids:
            errors.append(
                ValidationIssue(
                    level="error",
                    code="DUPLICATE_ANNOTATION_ID",
                    message="Identifiant d’annotation dupliqué.",
                    annotation_id=annotation_id,
                )
            )
        seen_ids.add(annotation_id)

        if annotation.annotation_type not in SUPPORTED_TYPES:
            errors.append(
                ValidationIssue(
                    level="error",
                    code="UNSUPPORTED_TYPE",
                    message=(
                        f"Type non pris en charge : "
                        f"{annotation.annotation_type!r}."
                    ),
                    annotation_id=annotation_id,
                )
            )

        selector = annotation.selector

        if not selector.exact:
            errors.append(
                ValidationIssue(
                    level="error",
                    code="EMPTY_EXACT_TEXT",
                    message="Le texte exact de l’annotation est vide.",
                    annotation_id=annotation_id,
                )
            )

        if (selector.start is None) != (selector.end is None):
            errors.append(
                ValidationIssue(
                    level="error",
                    code="INCOMPLETE_POSITION",
                    message=(
                        "Les positions start et end doivent être "
                        "présentes ensemble."
                    ),
                    annotation_id=annotation_id,
                )
            )

        if selector.start is not None and selector.end is not None:
            if selector.start < 0:
                errors.append(
                    ValidationIssue(
                        level="error",
                        code="NEGATIVE_START",
                        message="La position start est négative.",
                        annotation_id=annotation_id,
                    )
                )

            if selector.end <= selector.start:
                errors.append(
                    ValidationIssue(
                        level="error",
                        code="INVALID_RANGE",
                        message="La position end doit être supérieure à start.",
                        annotation_id=annotation_id,
                    )
                )

            if selector.end > len(document_text):
                errors.append(
                    ValidationIssue(
                        level="error",
                        code="RANGE_OUT_OF_BOUNDS",
                        message=(
                            "La sélection dépasse la longueur du texte "
                            "de référence."
                        ),
                        annotation_id=annotation_id,
                    )
                )
            elif document_text[selector.start:selector.end] != selector.exact:
                errors.append(
                    ValidationIssue(
                        level="error",
                        code="EXACT_TEXT_MISMATCH",
                        message=(
                            "Le texte situé entre start et end ne "
                            "correspond pas au champ exact."
                        ),
                        annotation_id=annotation_id,
                    )
                )
        else:
            occurrences = document_text.count(selector.exact)
            if occurrences == 0:
                errors.append(
                    ValidationIssue(
                        level="error",
                        code="TEXT_NOT_FOUND",
                        message=(
                            "Le texte exact n’a pas été retrouvé dans "
                            "le document."
                        ),
                        annotation_id=annotation_id,
                    )
                )
            elif occurrences > 1:
                warnings.append(
                    ValidationIssue(
                        level="warning",
                        code="AMBIGUOUS_TEXT",
                        message=(
                            "Le texte exact apparaît plusieurs fois ; "
                            "des positions start/end sont nécessaires."
                        ),
                        annotation_id=annotation_id,
                    )
                )

        if annotation.annotation_type in {
            "normalization",
            "correction",
        } and not annotation.replacement_text:
            errors.append(
                ValidationIssue(
                    level="error",
                    code="REPLACEMENT_TEXT_MISSING",
                    message=(
                        "La normalisation ou correction ne contient "
                        "aucun texte de remplacement."
                    ),
                    annotation_id=annotation_id,
                )
            )

        if annotation.authority_uri:
            if annotation.annotation_type not in {"person", "place"}:
                warnings.append(
                    ValidationIssue(
                        level="warning",
                        code="URI_ON_NON_AUTHORITY_TYPE",
                        message=(
                            "Une URI est présente sur un type qui "
                            "n’utilise pas encore les autorités."
                        ),
                        annotation_id=annotation_id,
                    )
                )
            elif wikidata_id(annotation.authority_uri) is None:
                errors.append(
                    ValidationIssue(
                        level="error",
                        code="INVALID_WIKIDATA_URI",
                        message=(
                            "L’URI ne correspond pas à une entité "
                            "Wikidata de forme Q123."
                        ),
                        annotation_id=annotation_id,
                    )
                )

    return ValidationReport(
        valid=not errors,
        annotations_total=len(manifest.annotations),
        errors=errors,
        warnings=warnings,
        document_sha256=document_hash,
    )
