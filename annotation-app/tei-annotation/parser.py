from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lxml import etree

from .constants import NSMAP
from .models import Annotation, AnnotationManifest, TextSelector
from .utils import normalize_wikidata_uri


class AnnotationFormatError(ValueError):
    """Erreur de structure dans le fichier d’annotations."""


def load_tei(path: str | Path) -> etree._ElementTree:
    """Charge une TEI sans modifier son contenu."""

    tei_path = Path(path)
    if not tei_path.exists():
        raise FileNotFoundError(f"TEI introuvable : {tei_path}")

    parser = etree.XMLParser(
        remove_blank_text=False,
        resolve_entities=False,
        no_network=True,
        huge_tree=True,
    )

    tree = etree.parse(str(tei_path), parser)
    root = tree.getroot()

    if etree.QName(root).localname != "TEI":
        raise ValueError(
            f"Le document racine doit être <TEI>, trouvé : "
            f"<{etree.QName(root).localname}>"
        )

    return tree


def extract_body_text(tree: etree._ElementTree) -> str:
    """
    Extrait le texte du <body> dans l’ordre documentaire.

    Cette fonction sera alignée précisément sur le texte affiché par
    CETEIcean lorsque l’exemple réel de TEI sera intégré.
    """

    bodies = tree.xpath("//tei:text/tei:body", namespaces=NSMAP)
    if not bodies:
        raise ValueError("Aucun élément <text><body> trouvé dans la TEI.")

    return "".join(bodies[0].itertext())


def load_annotations(path: str | Path) -> AnnotationManifest:
    """Charge une liste brute ou un manifeste d’annotations."""

    annotation_path = Path(path)
    if not annotation_path.exists():
        raise FileNotFoundError(
            f"Fichier d’annotations introuvable : {annotation_path}"
        )

    with annotation_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if isinstance(payload, list):
        raw_annotations = payload
        manifest_data: dict[str, Any] = {}
    elif isinstance(payload, dict):
        raw_annotations = payload.get("annotations")
        if not isinstance(raw_annotations, list):
            raise AnnotationFormatError(
                "Le manifeste doit contenir une propriété "
                "'annotations' de type liste."
            )
        manifest_data = payload
    else:
        raise AnnotationFormatError(
            "Le JSON doit être une liste ou un objet manifeste."
        )

    annotations = [
        parse_annotation(item, index)
        for index, item in enumerate(raw_annotations)
    ]

    source = manifest_data.get("source")
    if not isinstance(source, dict):
        source = {}

    known_keys = {
        "format",
        "version",
        "project",
        "document",
        "source",
        "annotations",
    }

    return AnnotationManifest(
        annotations=annotations,
        project=_optional_string(manifest_data.get("project")),
        document=_optional_string(manifest_data.get("document")),
        format_name=_optional_string(manifest_data.get("format")),
        format_version=_optional_string(manifest_data.get("version")),
        source_tei=_optional_string(source.get("tei")),
        source_sha256=_optional_string(source.get("sha256")),
        metadata={
            key: value
            for key, value in manifest_data.items()
            if key not in known_keys
        },
    )


def parse_annotation(raw: Any, index: int) -> Annotation:
    """Convertit une annotation Recogito en objet normalisé."""

    if not isinstance(raw, dict):
        raise AnnotationFormatError(
            f"L’annotation à l’index {index} n’est pas un objet JSON."
        )

    annotation_id = _optional_string(raw.get("id")) or f"annotation-{index + 1}"
    bodies = raw.get("bodies", raw.get("body", []))

    if isinstance(bodies, dict):
        bodies = [bodies]
    if not isinstance(bodies, list):
        raise AnnotationFormatError(
            f"{annotation_id} : 'bodies' doit être une liste."
        )

    annotation_type = _body_value(bodies, "tagging")
    if not annotation_type:
        raise AnnotationFormatError(
            f"{annotation_id} : type absent "
            "(body avec purpose='tagging')."
        )

    replacement_text: str | None = None
    if annotation_type == "normalization":
        replacement_text = _body_value(bodies, "normalizing")
    elif annotation_type == "correction":
        replacement_text = _body_value(bodies, "correcting")

    authority_uri = normalize_wikidata_uri(
        _body_value(bodies, "linking")
    )

    selector = _extract_selector(raw, annotation_id)

    return Annotation(
        annotation_id=annotation_id,
        annotation_type=annotation_type,
        selector=selector,
        replacement_text=replacement_text,
        authority_uri=authority_uri,
        raw=raw,
    )


def _extract_selector(
    raw: dict[str, Any],
    annotation_id: str,
) -> TextSelector:
    target = raw.get("target")
    if not isinstance(target, dict):
        raise AnnotationFormatError(
            f"{annotation_id} : cible 'target' absente ou invalide."
        )

    selectors = target.get("selector")
    if isinstance(selectors, dict):
        selectors = [selectors]
    if not isinstance(selectors, list):
        raise AnnotationFormatError(
            f"{annotation_id} : sélecteur absent ou invalide."
        )

    text_quote = None
    text_position = None

    for selector in selectors:
        if not isinstance(selector, dict):
            continue

        selector_type = selector.get("type")

        if selector_type == "TextQuoteSelector" or "exact" in selector:
            text_quote = selector

        if (
            selector_type == "TextPositionSelector"
            or "start" in selector
            or "end" in selector
        ):
            text_position = selector

    if text_quote is None and text_position is None:
        raise AnnotationFormatError(
            f"{annotation_id} : aucun sélecteur textuel exploitable."
        )

    exact = ""
    prefix = ""
    suffix = ""

    if text_quote is not None:
        exact = str(text_quote.get("exact", ""))
        prefix = str(text_quote.get("prefix", ""))
        suffix = str(text_quote.get("suffix", ""))

    start = _optional_integer(
        text_position.get("start")
        if text_position is not None
        else text_quote.get("start")
        if text_quote is not None
        else None
    )
    end = _optional_integer(
        text_position.get("end")
        if text_position is not None
        else text_quote.get("end")
        if text_quote is not None
        else None
    )

    return TextSelector(
        exact=exact,
        start=start,
        end=end,
        prefix=prefix,
        suffix=suffix,
    )


def _body_value(
    bodies: list[Any],
    purpose: str,
) -> str | None:
    for body in bodies:
        if not isinstance(body, dict):
            continue
        if body.get("purpose") != purpose:
            continue

        value = body.get("value")
        if value is None:
            continue

        normalized = str(value).strip()
        if normalized:
            return normalized

    return None


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _optional_integer(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise AnnotationFormatError(
            "Une position textuelle ne peut pas être booléenne."
        )
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise AnnotationFormatError(
            f"Position textuelle invalide : {value!r}"
        ) from exc
