#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Génère un manifeste IIIF Presentation API 3.0 compatible TIFY.

Important : ce script ne contient pas de DEFAULT_METADATA.
Les métadonnées descriptives viennent de :
    alto2tei/src/metadata/flora_metadata.py
qui réutilise :
    alto2tei/src/teiheader_metadata/flora_data.py

Exemple :
    python scripts/generate_iiif_manifest.py \
      --ark https://floraweb.ne.ch/flora/ark:/37964/001136 \
      --images site/images/volume_1 \
      --output site/iiif/manifest_Frene_volume_1.json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

from PIL import Image


JPEG_EXTENSIONS = {".jpg", ".jpeg"}

# Paramètres techniques ou éditoriaux du manifeste.
# Ce ne sont pas les métadonnées descriptives Flora.
DEFAULT_ARK = "https://floraweb.ne.ch/flora/ark:/37964/001136"
DEFAULT_BASE_URL = "https://raphix93.github.io/Projet_Frene"
DEFAULT_RIGHTS = "https://creativecommons.org/licenses/by/4.0/"
DEFAULT_LICENSE_LABEL = "CC-BY 4.0"
DEFAULT_LANGUAGE = "français"
DEFAULT_PROVIDER_ID = "https://www.ne.ch/autorites/DJSC/OAEN/"


def find_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "alto2tei").exists() and (candidate / "site").exists():
            return candidate
    raise FileNotFoundError("Impossible de trouver la racine du dépôt Projet_Frene.")


def load_metadata_adapter(project_root: Path, adapter_script: Path | None = None):
    adapter_file = adapter_script or (
        project_root / "alto2tei" / "src" / "metadata" / "flora_metadata.py"
    )

    if not adapter_file.exists():
        raise FileNotFoundError(f"Adaptateur Flora introuvable : {adapter_file}")

    spec = importlib.util.spec_from_file_location("flora_metadata", adapter_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Impossible de charger : {adapter_file}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, "get_flora_metadata"):
        raise AttributeError(f"Fonction get_flora_metadata absente de : {adapter_file}")

    return module.get_flora_metadata


def iiif_lang(value: Any, lang: str = "fr") -> dict[str, list[str]]:
    if value is None:
        return {lang: [""]}
    return {lang: [str(value)]}


def list_jpegs(images_dir: Path) -> list[Path]:
    if not images_dir.exists():
        raise FileNotFoundError(f"Dossier JPEG introuvable : {images_dir}")
    return sorted(
        file for file in images_dir.iterdir()
        if file.is_file() and file.suffix.lower() in JPEG_EXTENSIONS
    )


def read_image_size(image_file: Path) -> tuple[int, int]:
    with Image.open(image_file) as image:
        return image.size


def non_empty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    if isinstance(value, (list, dict)) and not value:
        return False
    return True


def metadata_entries(metadata: dict[str, Any]) -> list[dict[str, dict[str, list[str]]]]:
    """Construit les entrées IIIF à partir du dictionnaire Flora normalisé."""
    entries = [
        ("Titre", metadata.get("title")),
        ("Sous-titre", metadata.get("subtitle")),
        ("Auteur", metadata.get("creator")),
        ("Date", metadata.get("date")),
        ("Institution de conservation", metadata.get("repository")),
        ("Lieu", metadata.get("pub_place")),
        ("Cote", metadata.get("identifier")),
        ("Niveau de description", metadata.get("level")),
        ("Importance matérielle", metadata.get("extent")),
        ("Conditions d'accès", metadata.get("access")),
        ("Langue", metadata.get("language")),
        ("Licence", metadata.get("license_label")),
        ("ARK", metadata.get("ark")),
        ("Identifiant Flora", metadata.get("record_id")),
        ("Source des métadonnées", metadata.get("source")),
    ]

    creator_identifiers = metadata.get("creator_identifiers") or {}
    if isinstance(creator_identifiers, dict):
        for key, value in creator_identifiers.items():
            entries.append((f"Auteur — {key}", value))

    return [
        {"label": iiif_lang(label), "value": iiif_lang(value)}
        for label, value in entries
        if non_empty(value)
    ]


def create_canvas(
    image_file: Path,
    page_number: int,
    base_url_images: str,
    base_url_iiif: str,
) -> dict[str, Any]:
    width, height = read_image_size(image_file)
    image_url = f"{base_url_images.rstrip('/')}/{image_file.name}"

    canvas_id = f"{base_url_iiif.rstrip('/')}/canvas/volume1/p{page_number}"
    annotation_page_id = f"{canvas_id}/annotation-page"
    annotation_id = f"{canvas_id}/annotation/image"

    return {
        "id": canvas_id,
        "type": "Canvas",
        "label": iiif_lang(f"Page {page_number}"),
        "height": height,
        "width": width,
        "items": [
            {
                "id": annotation_page_id,
                "type": "AnnotationPage",
                "items": [
                    {
                        "id": annotation_id,
                        "type": "Annotation",
                        "motivation": "painting",
                        "body": {
                            "id": image_url,
                            "type": "Image",
                            "format": "image/jpeg",
                            "height": height,
                            "width": width,
                        },
                        "target": canvas_id,
                    }
                ],
            }
        ],
    }


def build_manifest(
    image_files: list[Path],
    output_file: Path,
    base_url: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    base_url = base_url.rstrip("/")
    base_url_images = f"{base_url}/images/volume_1"
    base_url_iiif = f"{base_url}/iiif"
    manifest_id = f"{base_url_iiif}/{output_file.name}"

    title = metadata["title"]
    description = metadata.get("description") or metadata.get("subtitle") or metadata["title"]
    repository = metadata["repository"]
    ark = metadata["ark"]

    return {
        "@context": "http://iiif.io/api/presentation/3/context.json",
        "id": manifest_id,
        "type": "Manifest",
        "label": iiif_lang(title),
        "summary": iiif_lang(description),
        "metadata": metadata_entries(metadata),
        "rights": metadata["rights"],
        "requiredStatement": {
            "label": iiif_lang("Attribution"),
            "value": iiif_lang(repository),
        },
        "homepage": [
            {
                "id": ark,
                "type": "Text",
                "label": iiif_lang("Notice Flora"),
                "format": "text/html",
            }
        ],
        "provider": [
            {
                "id": DEFAULT_PROVIDER_ID,
                "type": "Agent",
                "label": iiif_lang(repository),
            }
        ],
        "items": [
            create_canvas(
                image_file=image_file,
                page_number=index,
                base_url_images=base_url_images,
                base_url_iiif=base_url_iiif,
            )
            for index, image_file in enumerate(image_files, start=1)
        ],
    }


def validate_manifest(manifest: dict[str, Any], expected_base_url: str) -> None:
    if manifest.get("type") != "Manifest":
        raise ValueError("Le document généré n'est pas un Manifest IIIF.")

    items = manifest.get("items") or []
    if not items:
        raise ValueError("Le manifeste ne contient aucun canvas.")

    expected_prefix = f"{expected_base_url.rstrip('/')}/images/volume_1/"
    for canvas in items:
        body = canvas["items"][0]["items"][0]["body"]
        image_url = body["id"]
        if not image_url.startswith(expected_prefix):
            raise ValueError(f"URL image inattendue : {image_url}")
        if image_url.lower().endswith((".tif", ".tiff")):
            raise ValueError(f"Le manifeste référence encore un TIFF : {image_url}")
        if body.get("format") != "image/jpeg":
            raise ValueError(f"Format image inattendu : {body.get('format')}")


def build_parser() -> argparse.ArgumentParser:
    root = find_project_root()
    parser = argparse.ArgumentParser(
        description="Génère le manifeste IIIF 3.0 du Projet Frêne depuis les métadonnées Flora."
    )
    parser.add_argument("--ark", default=DEFAULT_ARK, help="URL ARK Flora.")
    parser.add_argument(
        "--images",
        type=Path,
        default=root / "site" / "images" / "volume_1",
        help="Dossier des JPEG publiés.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "site" / "iiif" / "manifest_Frene_volume_1.json",
        help="Fichier manifeste de sortie.",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="URL publique GitHub Pages du site.",
    )
    parser.add_argument(
        "--adapter-script",
        type=Path,
        default=None,
        help="Chemin optionnel vers alto2tei/src/metadata/flora_metadata.py.",
    )
    parser.add_argument(
        "--rights",
        default=DEFAULT_RIGHTS,
        help="URI des droits/licence IIIF.",
    )
    parser.add_argument(
        "--license-label",
        default=DEFAULT_LICENSE_LABEL,
        help="Libellé humain de la licence.",
    )
    parser.add_argument(
        "--language",
        default=DEFAULT_LANGUAGE,
        help="Langue du document.",
    )
    parser.add_argument(
        "--metadata-json",
        type=Path,
        default=None,
        help="Optionnel : écrit un JSON de contrôle des métadonnées utilisées.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    root = find_project_root()

    images_dir = args.images.resolve()
    output_file = args.output.resolve()
    output_file.parent.mkdir(parents=True, exist_ok=True)

    image_files = list_jpegs(images_dir)
    if not image_files:
        raise FileNotFoundError(f"Aucun JPEG trouvé dans : {images_dir}")

    get_flora_metadata = load_metadata_adapter(root, args.adapter_script)
    metadata = get_flora_metadata(ark_url=args.ark, project_root=root)

    # Ajouts techniques IIIF qui ne viennent pas de Flora.
    metadata["rights"] = args.rights
    metadata["license_label"] = args.license_label
    metadata["language"] = args.language

    manifest = build_manifest(
        image_files=image_files,
        output_file=output_file,
        base_url=args.base_url,
        metadata=metadata,
    )
    validate_manifest(manifest, expected_base_url=args.base_url)

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(manifest, file, ensure_ascii=False, indent=2)

    if args.metadata_json:
        args.metadata_json.parent.mkdir(parents=True, exist_ok=True)
        with args.metadata_json.open("w", encoding="utf-8") as file:
            json.dump(metadata, file, ensure_ascii=False, indent=2)

    print(f"Manifest IIIF créé : {output_file}")
    print(f"Canvas : {len(manifest['items'])}")
    print(f"Titre Flora : {metadata['title']}")


if __name__ == "__main__":
    main()
