#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Génère un manifeste IIIF Presentation API 3.0.

Important :
- ce script ne contient pas de DEFAULT_METADATA ;
- les métadonnées descriptives viennent de metadata/flora_metadata.py ;
- les JPEG sont utilisés comme images principales dans les Canvas ;
- les TIFF correspondants sont proposés comme fichiers téléchargeables ;
- le PDF/A-2u et le XML-TEI sont exposés dans la propriété "rendering"
  du manifeste.

Exemple :
    python manifest_IIIF/generate_iiif_manifest.py \
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
from urllib.parse import quote

from PIL import Image


JPEG_EXTENSIONS = {".jpg", ".jpeg"}
TIFF_EXTENSIONS = {".tif", ".tiff"}

# Paramètres techniques ou éditoriaux du manifeste.
# Ce ne sont pas les métadonnées descriptives Flora.
DEFAULT_ARK = "https://floraweb.ne.ch/flora/ark:/37964/001136"
DEFAULT_BASE_URL = "https://raphix93.github.io/Projet_Frene"
DEFAULT_RIGHTS = "https://creativecommons.org/licenses/by/4.0/"
DEFAULT_LICENSE_LABEL = "CC-BY 4.0"
DEFAULT_LANGUAGE = "français"
DEFAULT_PROVIDER_ID = "https://www.ne.ch/autorites/DJSC/OAEN/"

# Chemins publics relatifs à DEFAULT_BASE_URL.
# Ils supposent que data/ est synchronisé vers site/data/.
DEFAULT_PDF_PATH = (
    "data/Frêne_volume_1/exports/pdf/Frene_volume1_pdfa2u.pdf"
)
DEFAULT_TEI_PATH = "data/Frêne_volume_1.xml"
DEFAULT_TIFF_DIR = "data/Frêne_volume_1/Images"


def find_project_root(start: Path | None = None) -> Path:
    """Retrouve la racine du dépôt Projet_Frene."""
    current = (start or Path.cwd()).resolve()

    for candidate in [current, *current.parents]:
        if (candidate / "alto2tei").exists() and (candidate / "site").exists():
            return candidate

    raise FileNotFoundError(
        "Impossible de trouver la racine du dépôt Projet_Frene."
    )


def load_metadata_adapter(
    project_root: Path,
    adapter_script: Path | None = None,
):
    """Charge dynamiquement l'adaptateur metadata/flora_metadata.py."""
    adapter_file = adapter_script or (
        project_root / "metadata" / "flora_metadata.py"
    )

    if not adapter_file.exists():
        raise FileNotFoundError(
            f"Adaptateur Flora introuvable : {adapter_file}"
        )

    spec = importlib.util.spec_from_file_location(
        "flora_metadata",
        adapter_file,
    )

    if spec is None or spec.loader is None:
        raise ImportError(f"Impossible de charger : {adapter_file}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, "get_flora_metadata"):
        raise AttributeError(
            f"Fonction get_flora_metadata absente de : {adapter_file}"
        )

    return module.get_flora_metadata


def iiif_lang(
    value: Any,
    lang: str = "fr",
) -> dict[str, list[str]]:
    """Transforme une valeur en Language Map IIIF."""
    if value is None:
        return {lang: [""]}

    return {lang: [str(value)]}


def public_url(base_url: str, relative_path: str) -> str:
    """
    Construit une URL publique en encodant correctement les caractères
    spéciaux de chaque segment, notamment le ê de Frêne.
    """
    encoded_path = quote(
        relative_path.replace("\\", "/").lstrip("/"),
        safe="/",
    )
    return f"{base_url.rstrip('/')}/{encoded_path}"


def list_jpegs(images_dir: Path) -> list[Path]:
    """Liste les JPEG publiés, dans l'ordre alphabétique."""
    if not images_dir.exists():
        raise FileNotFoundError(
            f"Dossier JPEG introuvable : {images_dir}"
        )

    return sorted(
        file
        for file in images_dir.iterdir()
        if file.is_file()
        and file.suffix.lower() in JPEG_EXTENSIONS
    )


def read_image_size(image_file: Path) -> tuple[int, int]:
    """Lit les dimensions d'un JPEG."""
    with Image.open(image_file) as image:
        return image.size


def non_empty(value: Any) -> bool:
    """Indique si une valeur de métadonnée est exploitable."""
    if value is None:
        return False

    if isinstance(value, str) and not value.strip():
        return False

    if isinstance(value, (list, dict)) and not value:
        return False

    return True


def metadata_entries(
    metadata: dict[str, Any],
) -> list[dict[str, dict[str, list[str]]]]:
    """Construit les entrées IIIF à partir du dictionnaire Flora normalisé."""
    entries = [
        ("Titre", metadata.get("title")),
        ("Sous-titre", metadata.get("subtitle")),
        ("Auteur", metadata.get("creator")),
        ("Date", metadata.get("date")),
        (
            "Institution de conservation",
            metadata.get("repository"),
        ),
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
        {
            "label": iiif_lang(label),
            "value": iiif_lang(value),
        }
        for label, value in entries
        if non_empty(value)
    ]


def find_tiff_filename(
    image_file: Path,
    tiff_source_dir: Path | None,
) -> str:
    """
    Détermine le nom du TIFF correspondant au JPEG.

    Si le dossier TIFF local est disponible, le script détecte
    automatiquement .tif ou .tiff. Sinon, il utilise par défaut .tif.
    """
    if tiff_source_dir and tiff_source_dir.exists():
        for extension in sorted(TIFF_EXTENSIONS):
            candidate = tiff_source_dir / f"{image_file.stem}{extension}"

            if candidate.exists():
                return candidate.name

    return f"{image_file.stem}.tif"


def create_canvas(
    image_file: Path,
    page_number: int,
    base_url_images: str,
    base_url_iiif: str,
    base_url: str,
    tiff_dir: str | None = None,
    tiff_source_dir: Path | None = None,
) -> dict[str, Any]:
    """
    Crée un Canvas IIIF.

    Le JPEG reste le corps de l'annotation painting.
    Le TIFF correspondant est ajouté dans rendering au niveau du Canvas.
    """
    width, height = read_image_size(image_file)

    image_url = public_url(
        base_url_images,
        image_file.name,
    )

    canvas_id = (
        f"{base_url_iiif.rstrip('/')}/canvas/volume1/p{page_number}"
    )
    annotation_page_id = f"{canvas_id}/annotation-page"
    annotation_id = f"{canvas_id}/annotation/image"

    canvas: dict[str, Any] = {
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

    if tiff_dir:
        tiff_filename = find_tiff_filename(
            image_file=image_file,
            tiff_source_dir=tiff_source_dir,
        )

        tiff_relative_path = (
            f"{tiff_dir.rstrip('/')}/{tiff_filename}"
        )

        canvas["rendering"] = [
            {
                "id": public_url(
                    base_url,
                    tiff_relative_path,
                ),
                "type": "Image",
                "label": iiif_lang(
                    f"Télécharger le TIFF original — page {page_number}"
                ),
                "format": "image/tiff",
            }
        ]

    return canvas


def build_rendering(
    base_url: str,
    pdf_path: str | None,
    tei_path: str | None,
) -> list[dict[str, Any]]:
    """
    Construit les ressources téléchargeables au niveau du manifeste.

    Le PDF/A-2u et le XML-TEI sont tous les deux placés dans rendering.
    """
    rendering: list[dict[str, Any]] = []

    if pdf_path:
        rendering.append(
            {
                "id": public_url(base_url, pdf_path),
                "type": "Text",
                "label": iiif_lang(
                    "Télécharger le PDF/A-2u"
                ),
                "format": "application/pdf",
            }
        )

    if tei_path:
        rendering.append(
            {
                "id": public_url(base_url, tei_path),
                "type": "Dataset",
                "label": iiif_lang(
                    "Télécharger la transcription XML-TEI"
                ),
                "format": "application/tei+xml",
            }
        )

    return rendering


def build_manifest(
    image_files: list[Path],
    output_file: Path,
    base_url: str,
    metadata: dict[str, Any],
    pdf_path: str | None = None,
    tei_path: str | None = None,
    tiff_dir: str | None = None,
    tiff_source_dir: Path | None = None,
) -> dict[str, Any]:
    """Construit le manifeste IIIF Presentation API 3.0."""
    base_url = base_url.rstrip("/")
    base_url_images = f"{base_url}/images/volume_1"
    base_url_iiif = f"{base_url}/iiif"
    manifest_id = f"{base_url_iiif}/{output_file.name}"

    title = metadata["title"]
    description = (
        metadata.get("description")
        or metadata.get("subtitle")
        or metadata["title"]
    )
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
        "rendering": build_rendering(
            base_url=base_url,
            pdf_path=pdf_path,
            tei_path=tei_path,
        ),
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
                base_url=base_url,
                tiff_dir=tiff_dir,
                tiff_source_dir=tiff_source_dir,
            )
            for index, image_file in enumerate(
                image_files,
                start=1,
            )
        ],
    }


def validate_manifest(
    manifest: dict[str, Any],
    expected_base_url: str,
    expect_pdf: bool = False,
    expect_tei: bool = False,
    expect_tiff: bool = False,
) -> None:
    """Effectue des contrôles de cohérence sur le manifeste généré."""
    if manifest.get("type") != "Manifest":
        raise ValueError(
            "Le document généré n'est pas un Manifest IIIF."
        )

    items = manifest.get("items") or []

    if not items:
        raise ValueError(
            "Le manifeste ne contient aucun Canvas."
        )

    expected_jpeg_prefix = (
        f"{expected_base_url.rstrip('/')}/images/volume_1/"
    )

    for canvas in items:
        body = canvas["items"][0]["items"][0]["body"]
        image_url = body["id"]

        if not image_url.startswith(expected_jpeg_prefix):
            raise ValueError(
                f"URL JPEG inattendue : {image_url}"
            )

        if image_url.lower().endswith((".tif", ".tiff")):
            raise ValueError(
                "Le corps painting doit rester un JPEG : "
                f"{image_url}"
            )

        if body.get("format") != "image/jpeg":
            raise ValueError(
                "Format de l'image painting inattendu : "
                f"{body.get('format')}"
            )

        if expect_tiff:
            canvas_rendering = canvas.get("rendering") or []

            if not canvas_rendering:
                raise ValueError(
                    "Le Canvas ne contient aucun TIFF dans rendering : "
                    f"{canvas.get('id')}"
                )

            tiff_resource = canvas_rendering[0]
            tiff_url = tiff_resource.get("id", "")

            if tiff_resource.get("format") != "image/tiff":
                raise ValueError(
                    "Format TIFF inattendu dans le Canvas : "
                    f"{tiff_resource.get('format')}"
                )

            if not tiff_url.lower().endswith((".tif", ".tiff")):
                raise ValueError(
                    f"URL TIFF inattendue : {tiff_url}"
                )

    rendering = manifest.get("rendering") or []
    rendering_formats = {
        resource.get("format")
        for resource in rendering
    }

    if expect_pdf and "application/pdf" not in rendering_formats:
        raise ValueError(
            "Le PDF/A-2u est absent de rendering."
        )

    if expect_tei and "application/tei+xml" not in rendering_formats:
        raise ValueError(
            "Le XML-TEI est absent de rendering."
        )


def build_parser() -> argparse.ArgumentParser:
    """Construit l'interface en ligne de commande."""
    root = find_project_root()

    parser = argparse.ArgumentParser(
        description=(
            "Génère le manifeste IIIF 3.0 du Projet Frêne "
            "depuis les métadonnées Flora."
        )
    )

    parser.add_argument(
        "--ark",
        default=DEFAULT_ARK,
        help="URL ARK Flora.",
    )

    parser.add_argument(
        "--images",
        type=Path,
        default=root / "site" / "images" / "volume_1",
        help="Dossier local des JPEG publiés.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=(
            root
            / "site"
            / "iiif"
            / "manifest_Frene_volume_1.json"
        ),
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
        help=(
            "Chemin optionnel vers "
            "metadata/flora_metadata.py."
        ),
    )

    parser.add_argument(
        "--rights",
        default=DEFAULT_RIGHTS,
        help="URI des droits ou de la licence IIIF.",
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
        help=(
            "Optionnel : écrit un JSON de contrôle "
            "des métadonnées utilisées."
        ),
    )

    parser.add_argument(
        "--pdf-path",
        default=DEFAULT_PDF_PATH,
        help=(
            "Chemin public du PDF/A-2u, relatif à --base-url. "
            "Il sera ajouté dans rendering."
        ),
    )

    parser.add_argument(
        "--tei-path",
        default=DEFAULT_TEI_PATH,
        help=(
            "Chemin public du XML-TEI, relatif à --base-url. "
            "Il sera ajouté dans rendering."
        ),
    )

    parser.add_argument(
        "--tiff-dir",
        default=DEFAULT_TIFF_DIR,
        help=(
            "Dossier public contenant les TIFF, relatif à --base-url. "
            "Chaque TIFF sera ajouté dans rendering du Canvas correspondant."
        ),
    )

    parser.add_argument(
        "--tiff-source-dir",
        type=Path,
        default=root / "data" / "Frêne_volume_1" / "Images",
        help=(
            "Dossier local des TIFF. Il sert à détecter automatiquement "
            "si l'extension réelle est .tif ou .tiff."
        ),
    )

    return parser


def main() -> None:
    """Point d'entrée du script."""
    args = build_parser().parse_args()
    root = find_project_root()

    images_dir = args.images.resolve()
    output_file = args.output.resolve()
    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    tiff_source_dir = (
        args.tiff_source_dir.resolve()
        if args.tiff_source_dir
        else None
    )

    image_files = list_jpegs(images_dir)

    if not image_files:
        raise FileNotFoundError(
            f"Aucun JPEG trouvé dans : {images_dir}"
        )

    get_flora_metadata = load_metadata_adapter(
        root,
        args.adapter_script,
    )

    metadata = get_flora_metadata(
        ark_url=args.ark,
        project_root=root,
    )

    # Ajouts techniques IIIF qui ne viennent pas de Flora.
    metadata["rights"] = args.rights
    metadata["license_label"] = args.license_label
    metadata["language"] = args.language

    manifest = build_manifest(
        image_files=image_files,
        output_file=output_file,
        base_url=args.base_url,
        metadata=metadata,
        pdf_path=args.pdf_path,
        tei_path=args.tei_path,
        tiff_dir=args.tiff_dir,
        tiff_source_dir=tiff_source_dir,
    )

    validate_manifest(
        manifest,
        expected_base_url=args.base_url,
        expect_pdf=bool(args.pdf_path),
        expect_tei=bool(args.tei_path),
        expect_tiff=bool(args.tiff_dir),
    )

    with output_file.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            manifest,
            file,
            ensure_ascii=False,
            indent=2,
        )

    if args.metadata_json:
        args.metadata_json.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with args.metadata_json.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                metadata,
                file,
                ensure_ascii=False,
                indent=2,
            )

    print(f"Manifest IIIF créé : {output_file}")
    print(f"Canvas : {len(manifest['items'])}")
    print(f"Titre Flora : {metadata['title']}")
    print(
        "Ressources rendering du manifeste : "
        f"{len(manifest.get('rendering', []))}"
    )
    print(
        "TIFF associés aux Canvas : "
        f"{sum(bool(canvas.get('rendering')) for canvas in manifest['items'])}"
    )


if __name__ == "__main__":
    main()
