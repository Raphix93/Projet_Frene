#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Adaptateur de métadonnées Flora pour le Projet Frêne.

But : créer une source de métadonnées normalisée et réutilisable
par les exports TEI, IIIF, PDF/A, etc.

Ce fichier ne contient pas de métadonnées descriptives.
Il importe la classe Flora existante depuis : alto2tei/src/teiheader_metadata/flora_data.py
"""

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


def find_project_root(start: Path | None = None) -> Path:
    """Retrouve la racine du dépôt Projet_Frene."""
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "alto2tei").exists() and (candidate / "data").exists():
            return candidate
    raise FileNotFoundError(
        "Impossible de trouver la racine du dépôt. "
        "Lance le script depuis Projet_Frene."
    )


def load_flora_class(project_root: Path, flora_script: Path | None = None):
    """Charge dynamiquement la classe Flora depuis flora_data.py."""
    flora_file = flora_script or (
        project_root / "alto2tei" / "src" / "teiheader_metadata" / "flora_data.py"
    )

    if not flora_file.exists():
        raise FileNotFoundError(f"flora_data.py introuvable : {flora_file}")

    spec = importlib.util.spec_from_file_location("flora_data", flora_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Impossible de charger : {flora_file}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, "Flora"):
        raise AttributeError(f"Aucune classe Flora trouvée dans : {flora_file}")

    return module.Flora


def stringify(value: Any) -> str | None:
    """Convertit proprement une valeur simple en chaîne."""
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return str(value)


def format_dates(dates: dict[str, Any] | None) -> str | None:
    """Convertit {'from': '1741', 'to': '1804'} en '1741-1804'."""
    if not isinstance(dates, dict):
        return stringify(dates)

    date_from = stringify(dates.get("from"))
    date_to = stringify(dates.get("to"))

    if date_from and date_to and date_from != date_to:
        return f"{date_from}-{date_to}"
    return date_from or date_to


def format_extent(extent: dict[str, Any] | None) -> str | None:
    """Convertit {'volumes': 7, 'pages': 3114} en texte lisible."""
    if not isinstance(extent, dict):
        return stringify(extent)

    parts: list[str] = []
    if extent.get("volumes"):
        parts.append(f"{extent['volumes']} volumes")
    if extent.get("pages"):
        parts.append(f"{extent['pages']} pages")

    return ", ".join(parts) if parts else None


def require(metadata: dict[str, Any], key: str) -> Any:
    """Récupère un champ obligatoire ou signale clairement le problème."""
    value = metadata.get(key)
    if value is None or value == "":
        raise ValueError(
            f"Champ obligatoire absent dans les métadonnées Flora : {key}. "
            "Corrige flora_data.py ou la notice source plutôt que d'ajouter un fallback ici."
        )
    return value


def flora_to_normalized_metadata(tei_metadata: dict[str, Any]) -> dict[str, Any]:
    """
    Transforme Flora.to_tei_metadata() en dictionnaire documentaire normalisé.

    La manière de faire n'est pas parfaite, mais je n'avais pas le temps de refaire le code dans Alto2TEI : les valeurs viennent
    de flora_data.py, qui récupère lui-même les données de Flora et ajoute
    déjà les enrichissements utiles au teiHeader.
    """
    author = require(tei_metadata, "author")
    if isinstance(author, dict):
        creator = require(author, "name")
        creator_identifiers = {
            key: value
            for key, value in author.items()
            if key != "name" and value
        }
    else:
        creator = author
        creator_identifiers = {}

    return {
        "title": require(tei_metadata, "title"),
        "subtitle": stringify(tei_metadata.get("subtitle")),
        "creator": creator,
        "creator_identifiers": creator_identifiers,
        "repository": require(tei_metadata, "repository"),
        "pub_place": stringify(tei_metadata.get("pubPlace")),
        "identifier": require(tei_metadata, "fonds_id"),
        "ark": require(tei_metadata, "ark"),
        "level": stringify(tei_metadata.get("level")),
        "date": format_dates(tei_metadata.get("fonds_dates")),
        "extent": format_extent(tei_metadata.get("extent")),
        "access": stringify(tei_metadata.get("access")),
        "description": stringify(tei_metadata.get("abstract")),
        "linked_records": tei_metadata.get("linked_records") or [],
        "record_id": stringify(tei_metadata.get("record_id")),
        "source": stringify(tei_metadata.get("source")),
    }


def get_flora_metadata(
    ark_url: str,
    project_root: Path | None = None,
    flora_script: Path | None = None,
) -> dict[str, Any]:
    """Point d'entrée réutilisable par les autres scripts."""
    root = project_root or find_project_root()
    Flora = load_flora_class(project_root=root, flora_script=flora_script)
    notice = Flora(ark_url=ark_url)
    return flora_to_normalized_metadata(notice.to_tei_metadata())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extrait les métadonnées Flora dans un JSON normalisé."
    )
    parser.add_argument(
        "--ark",
        required=True,
        help="URL ARK Flora, ex. https://floraweb.ne.ch/flora/ark:/37964/001136",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Fichier JSON de sortie.",
    )
    parser.add_argument(
        "--flora-script",
        type=Path,
        default=None,
        help="Chemin optionnel vers flora_data.py.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    root = find_project_root()
    metadata = get_flora_metadata(
        ark_url=args.ark,
        project_root=root,
        flora_script=args.flora_script,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as file:
        json.dump(metadata, file, ensure_ascii=False, indent=2)

    print(f"Métadonnées Flora écrites : {args.output}")


if __name__ == "__main__":
    main()
