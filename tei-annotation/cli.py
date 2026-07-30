from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .parser import extract_body_text, load_annotations, load_tei
from .validators import validate_annotations
from .writer import write_json_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Valide un export d’annotations avant enrichissement "
            "d’une TEI du Projet Frêne."
        )
    )
    parser.add_argument(
        "--tei",
        type=Path,
        required=True,
        help="Fichier XML-TEI source.",
    )
    parser.add_argument(
        "--annotations",
        type=Path,
        required=True,
        help="Export JSON de l’application d’annotation.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Chemin du rapport JSON de validation.",
    )
    parser.add_argument(
        "--verify-hash",
        action="store_true",
        help="Vérifie le SHA-256 déclaré dans le manifeste.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        tree = load_tei(args.tei)
        document_text = extract_body_text(tree)
        manifest = load_annotations(args.annotations)
        report = validate_annotations(
            manifest,
            document_text,
            verify_hash=args.verify_hash,
        )
    except Exception as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 2

    payload = {
        "engine": {
            "name": "Projet Frêne annotation_engine",
            "version": "0.4.0",
        },
        "source": {
            "tei": str(args.tei),
            "annotations": str(args.annotations),
        },
        "manifest": {
            "project": manifest.project,
            "document": manifest.document,
            "format": manifest.format_name,
            "version": manifest.format_version,
            "source_tei": manifest.source_tei,
            "source_sha256": manifest.source_sha256,
        },
        "validation": report.to_dict(),
    }

    if args.report:
        write_json_report(payload, args.report)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if report.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
