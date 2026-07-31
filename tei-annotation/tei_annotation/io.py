from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from lxml import etree

from .models import Annotation

TEI_NS = "http://www.tei-c.org/ns/1.0"
NS = {"tei": TEI_NS}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_tei(path: Path) -> etree._ElementTree:
    parser = etree.XMLParser(
        remove_blank_text=False,
        resolve_entities=False,
        no_network=True,
        recover=False,
        huge_tree=True,
    )
    return etree.parse(str(path), parser)


def load_annotations(path: Path) -> tuple[dict[str, Any], list[Annotation]]:
    with path.open("r", encoding="utf-8") as stream:
        payload = json.load(stream)

    result: list[Annotation] = []
    for raw in payload.get("annotations", []):
        bodies = raw.get("bodies") or []
        selector_list = (raw.get("target") or {}).get("selector") or []
        if not selector_list:
            continue
        selector = selector_list[0]

        tagging = next(
            (body.get("value") for body in bodies if body.get("purpose") == "tagging"),
            None,
        )
        if not tagging:
            continue

        replacement = None
        if tagging == "normalization":
            replacement = next(
                (body.get("value") for body in bodies if body.get("purpose") == "normalizing"),
                None,
            )
        elif tagging == "correction":
            replacement = next(
                (body.get("value") for body in bodies if body.get("purpose") == "correcting"),
                None,
            )

        uri = next(
            (body.get("value") for body in bodies if body.get("purpose") == "linking"),
            None,
        )

        exact = selector.get("exact") or selector.get("quote") or ""
        start = int(selector.get("start", -1))
        end = int(selector.get("end", start + len(exact)))
        result.append(
            Annotation(
                annotation_id=str(raw.get("id", "")),
                kind=str(tagging),
                exact=str(exact),
                exported_start=start,
                exported_end=end,
                replacement=replacement,
                uri=uri,
                raw=raw,
            )
        )

    return payload, result


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
