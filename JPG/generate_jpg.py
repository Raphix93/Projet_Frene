#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Génère les JPEG dérivés à partir des TIFF maîtres du Projet Frêne.

Exemple :
    python scripts/generate_jpg.py \
      --input data/Frene_volume_1/Images \
      --output data/Frene_volume_1/exports/jpg \
      --quality 90
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageOps


TIFF_EXTENSIONS = {".tif", ".tiff"}


def find_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "data").exists() and (candidate / "site").exists():
            return candidate
    raise FileNotFoundError("Impossible de trouver la racine du dépôt Projet_Frene.")


def list_tiffs(input_dir: Path) -> list[Path]:
    if not input_dir.exists():
        raise FileNotFoundError(f"Dossier TIFF introuvable : {input_dir}")
    return sorted(
        file for file in input_dir.iterdir()
        if file.is_file() and file.suffix.lower() in TIFF_EXTENSIONS
    )


def convert_tiff_to_jpg(tiff_file: Path, output_dir: Path, quality: int, overwrite: bool) -> Path:
    output_file = output_dir / f"{tiff_file.stem}.jpg"

    if output_file.exists() and not overwrite:
        return output_file

    with Image.open(tiff_file) as image:
        image = ImageOps.exif_transpose(image)

        # JPEG ne supporte pas les modes avec transparence ni certains modes TIFF.
        if image.mode not in {"RGB", "L"}:
            image = image.convert("RGB")
        elif image.mode == "L":
            image = image.convert("RGB")

        image.save(
            output_file,
            "JPEG",
            quality=quality,
            optimize=True,
            progressive=True,
        )

    return output_file


def build_parser() -> argparse.ArgumentParser:
    root = find_project_root()
    parser = argparse.ArgumentParser(
        description="Convertit les TIFF maîtres du Projet Frêne en JPEG dérivés."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=root / "data" / "Frene_volume_1" / "Images",
        help="Dossier source contenant les TIFF.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "data" / "Frene_volume_1" / "exports" / "jpg",
        help="Dossier de sortie des JPEG dérivés.",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=90,
        help="Qualité JPEG de 1 à 95. Recommandé : 85-92.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Régénère les JPEG même s'ils existent déjà.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    if not 1 <= args.quality <= 95:
        raise ValueError("La qualité JPEG doit être comprise entre 1 et 95.")

    input_dir = args.input.resolve()
    output_dir = args.output.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    tiff_files = list_tiffs(input_dir)
    if not tiff_files:
        raise FileNotFoundError(f"Aucun TIFF trouvé dans : {input_dir}")

    created_or_found = []
    for tiff_file in tiff_files:
        jpg = convert_tiff_to_jpg(
            tiff_file=tiff_file,
            output_dir=output_dir,
            quality=args.quality,
            overwrite=args.overwrite,
        )
        created_or_found.append(jpg)
        print(f"{tiff_file.name} -> {jpg.name}")

    print(f"JPEG disponibles : {len(created_or_found)}")
    print(f"Dossier : {output_dir}")


if __name__ == "__main__":
    main()
