from __future__ import annotations

from dataclasses import dataclass

from lxml import etree

from .io import NS


@dataclass(slots=True)
class AbSegment:
    element: etree._Element
    index: int
    global_start: int
    global_end: int
    text: str


def mixed_text(element: etree._Element) -> str:
    """Retourne uniquement le texte éditorial d'un élément, sans indentation XML."""
    parts: list[str] = []
    if element.text and not element.text.isspace():
        parts.append(element.text)
    for child in element:
        # Les éléments de mise en page tels que lb/pb n'ajoutent aucun caractère.
        if child.text and not child.text.isspace():
            parts.append(child.text)
        if child.tail and not child.tail.isspace():
            parts.append(child.tail)
    return "".join(parts)


def linearize_body(tree: etree._ElementTree) -> tuple[str, list[AbSegment]]:
    body = tree.find(".//tei:text/tei:body", namespaces=NS)
    if body is None:
        raise ValueError("Le document ne contient pas de <text><body> TEI.")

    segments: list[AbSegment] = []
    text_parts: list[str] = []
    cursor = 0
    abs_found = body.xpath(".//tei:ab", namespaces=NS)

    for index, ab in enumerate(abs_found):
        text = mixed_text(ab)
        start = cursor
        cursor += len(text)
        segments.append(AbSegment(ab, index, start, cursor, text))
        text_parts.append(text)

    if not segments:
        raise ValueError("Aucun élément <ab> n'a été trouvé dans <text><body>.")

    return "".join(text_parts), segments
