from __future__ import annotations

from lxml import etree

from .io import TEI_NS
from .models import Annotation


def qname(local_name: str) -> str:
    return f"{{{TEI_NS}}}{local_name}"


def build_wrapper(annotation: Annotation) -> etree._Element | None:
    if annotation.kind == "person":
        element = etree.Element(qname("persName"))
    elif annotation.kind == "place":
        element = etree.Element(qname("placeName"))
    elif annotation.kind == "date":
        element = etree.Element(qname("date"))
    elif annotation.kind == "normalization":
        element = etree.Element(qname("choice"))
        etree.SubElement(element, qname("orig"))
        reg = etree.SubElement(element, qname("reg"))
        reg.text = annotation.replacement or ""
    elif annotation.kind == "correction":
        # Décision éditoriale du projet : remplacement direct, sans <sic>/<corr>.
        return None
    else:
        raise ValueError(f"Type d'annotation inconnu : {annotation.kind}")

    if annotation.uri and annotation.kind in {"person", "place"}:
        element.set("ref", annotation.uri)
    return element
