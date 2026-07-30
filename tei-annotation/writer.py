from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lxml import etree


def write_json_report(
    payload: dict[str, Any],
    path: str | Path,
) -> Path:
    """Écrit un rapport JSON UTF-8 lisible."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def write_tei(
    tree: etree._ElementTree,
    path: str | Path,
) -> Path:
    """Écrit une TEI en conservant sa déclaration XML."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(
        str(output_path),
        encoding="utf-8",
        xml_declaration=True,
        pretty_print=False,
    )
    return output_path
