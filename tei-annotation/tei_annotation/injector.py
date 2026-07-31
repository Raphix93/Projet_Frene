from __future__ import annotations

from copy import deepcopy
from collections import defaultdict

from lxml import etree

from .builders import build_wrapper
from .linearizer import AbSegment
from .models import Annotation


def _append_text(parent: etree._Element, text: str) -> None:
    if not text:
        return
    if len(parent):
        last = parent[-1]
        last.tail = (last.tail or "") + text
    else:
        parent.text = (parent.text or "") + text


def _copy_child_without_tail(child: etree._Element) -> etree._Element:
    copied = deepcopy(child)
    copied.tail = None
    return copied


def _mixed_tokens(ab: etree._Element) -> list[tuple[str, object]]:
    tokens: list[tuple[str, object]] = []
    if ab.text and not ab.text.isspace():
        tokens.append(("text", ab.text))
    for child in ab:
        tokens.append(("element", _copy_child_without_tail(child)))
        if child.tail and not child.tail.isspace():
            tokens.append(("text", child.tail))
    return tokens


def _rebuild_ab(ab: etree._Element, annotations: list[Annotation]) -> None:
    tokens = _mixed_tokens(ab)
    anns = sorted(annotations, key=lambda item: item.local_start or 0)
    starts = {item.local_start: item for item in anns}
    ends = {item.local_end: item for item in anns}
    boundaries = sorted({0, *starts.keys(), *ends.keys()})

    for child in list(ab):
        ab.remove(child)
    ab.text = None

    cursor = 0
    active: Annotation | None = None
    active_parent: etree._Element = ab

    def close_at(position: int) -> None:
        nonlocal active, active_parent
        if active is not None and active.local_end == position:
            active = None
            active_parent = ab

    def open_at(position: int) -> None:
        nonlocal active, active_parent
        if active is not None:
            return
        annotation = starts.get(position)
        if annotation is None:
            return
        if annotation.kind == "correction":
            # La correction remplace la plage au moment du traitement du texte.
            active = annotation
            active_parent = ab
            return
        wrapper = build_wrapper(annotation)
        if wrapper is None:
            raise RuntimeError("Un wrapper était attendu.")
        ab.append(wrapper)
        active = annotation
        active_parent = wrapper

    for token_type, value in tokens:
        close_at(cursor)
        if token_type == "element":
            active_parent.append(value)  # type: ignore[arg-type]
            open_at(cursor)
            continue

        text = str(value)
        local = 0
        token_end = cursor + len(text)
        cuts = [point for point in boundaries if cursor <= point <= token_end]
        cuts = sorted(set([cursor, token_end, *cuts]))

        for left, right in zip(cuts, cuts[1:]):
            close_at(left)
            open_at(left)
            segment = text[left - cursor:right - cursor]

            if active is not None and active.kind == "correction":
                # Écrire une seule fois la correction, puis ignorer le texte original couvert.
                if left == active.local_start:
                    _append_text(ab, active.replacement or "")
            elif active is not None and active.kind == "normalization":
                wrapper = active_parent
                orig = wrapper[0]
                _append_text(orig, segment)
            else:
                _append_text(active_parent, segment)

        cursor = token_end

    close_at(cursor)


def inject_annotations(
    segments: list[AbSegment],
    annotations: list[Annotation],
) -> int:
    grouped: dict[int, list[Annotation]] = defaultdict(list)
    for annotation in annotations:
        if annotation.status == "matched" and annotation.ab_index is not None:
            grouped[annotation.ab_index].append(annotation)

    applied = 0
    for segment in segments:
        group = grouped.get(segment.index, [])
        if not group:
            continue
        _rebuild_ab(segment.element, group)
        for annotation in group:
            annotation.status = "applied"
            annotation.message = "Annotation injectée dans la TEI."
            applied += 1
    return applied
