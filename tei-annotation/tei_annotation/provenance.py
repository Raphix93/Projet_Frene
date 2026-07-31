from __future__ import annotations

from datetime import datetime, timezone

from lxml import etree

from .io import NS, TEI_NS

XML_NS = "http://www.w3.org/XML/1998/namespace"


def _qname(local: str) -> str:
    return f"{{{TEI_NS}}}{local}"


def add_provenance(tree: etree._ElementTree, applied: int, source_json: str) -> None:
    root = tree.getroot()
    header = root.find("tei:teiHeader", namespaces=NS)
    if header is None:
        return

    encoding = header.find("tei:encodingDesc", namespaces=NS)
    if encoding is None:
        encoding = etree.SubElement(header, _qname("encodingDesc"))
    app_info = encoding.find("tei:appInfo", namespaces=NS)
    if app_info is None:
        app_info = etree.SubElement(encoding, _qname("appInfo"))

    existing = app_info.xpath("tei:application[@ident='frene-tei-annotation']", namespaces=NS)
    if not existing:
        application = etree.SubElement(app_info, _qname("application"))
        application.set("ident", "frene-tei-annotation")
        application.set("version", "1.0.0")
        label = etree.SubElement(application, _qname("label"))
        label.text = "Projet Frêne — réintégration des annotations"

    revision = header.find("tei:revisionDesc", namespaces=NS)
    if revision is None:
        revision = etree.SubElement(header, _qname("revisionDesc"))
    change = etree.SubElement(revision, _qname("change"))
    change.set("when", datetime.now(timezone.utc).date().isoformat())
    change.text = (
        f"Réintégration automatique de {applied} annotations depuis {source_json}."
    )
