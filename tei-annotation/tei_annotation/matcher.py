from __future__ import annotations

from collections import defaultdict

from .linearizer import AbSegment
from .models import Annotation

SUPPORTED_TYPES = {"person", "place", "date", "normalization", "correction"}


def _occurrences(text: str, quote: str) -> list[int]:
    starts: list[int] = []
    cursor = 0
    while quote:
        pos = text.find(quote, cursor)
        if pos < 0:
            break
        starts.append(pos)
        cursor = pos + 1
    return starts


def match_annotations(
    text: str,
    segments: list[AbSegment],
    annotations: list[Annotation],
) -> None:
    """Associe les sélecteurs au texte TEI, avec les offsets comme indice et non vérité absolue."""
    used: set[tuple[int, int]] = set()
    previous_exported = 0
    previous_matched = 0

    for annotation in sorted(annotations, key=lambda item: item.exported_start):
        if annotation.kind not in SUPPORTED_TYPES:
            annotation.status = "ignored"
            annotation.message = f"Type non pris en charge : {annotation.kind}"
            continue
        if not annotation.exact:
            annotation.status = "ignored"
            annotation.message = "Sélecteur exact vide."
            continue
        if annotation.kind in {"normalization", "correction"} and annotation.replacement is None:
            annotation.status = "ignored"
            annotation.message = "Valeur de remplacement absente."
            continue

        candidates = _occurrences(text, annotation.exact)
        if not candidates:
            annotation.status = "unmatched"
            annotation.message = "Texte exact introuvable dans le corps TEI."
            continue

        # Les offsets du navigateur peuvent contenir des séparateurs de blocs absents du XML.
        # On estime donc la position attendue à partir du dernier appariement réussi.
        expected = previous_matched + (annotation.exported_start - previous_exported)
        if previous_exported == previous_matched == 0:
            expected = annotation.exported_start

        available = [
            pos for pos in candidates
            if (pos, pos + len(annotation.exact)) not in used
        ] or candidates
        start = min(available, key=lambda pos: abs(pos - expected))
        end = start + len(annotation.exact)

        containing = [
            segment for segment in segments
            if segment.global_start <= start and end <= segment.global_end
        ]
        if not containing:
            annotation.status = "conflict"
            annotation.message = "L'annotation traverse plusieurs éléments <ab>."
            continue

        segment = containing[0]
        annotation.matched_start = start
        annotation.matched_end = end
        annotation.ab_index = segment.index
        annotation.local_start = start - segment.global_start
        annotation.local_end = end - segment.global_start
        annotation.status = "matched"
        annotation.message = "Annotation appariée."
        used.add((start, end))
        previous_exported = annotation.exported_start
        previous_matched = start


def detect_overlaps(annotations: list[Annotation]) -> None:
    by_ab: dict[int, list[Annotation]] = defaultdict(list)
    for annotation in annotations:
        if annotation.status == "matched" and annotation.ab_index is not None:
            by_ab[annotation.ab_index].append(annotation)

    for group in by_ab.values():
        group.sort(key=lambda item: (item.local_start or 0, item.local_end or 0))
        previous: Annotation | None = None
        for current in group:
            if (
                previous is not None
                and current.local_start is not None
                and previous.local_end is not None
                and current.local_start < previous.local_end
            ):
                current.status = "conflict"
                current.message = f"Chevauchement avec l'annotation {previous.annotation_id}."
                previous.status = "conflict"
                previous.message = f"Chevauchement avec l'annotation {current.annotation_id}."
            elif current.status == "matched":
                previous = current
