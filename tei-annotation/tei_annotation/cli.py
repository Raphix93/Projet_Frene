from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lxml import etree

from .injector import inject_annotations
from .io import load_annotations, load_tei, sha256_file, write_json
from .linearizer import linearize_body
from .matcher import detect_overlaps, match_annotations
from .provenance import add_provenance
from .report import make_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Réintègre les annotations JSON de Projet Frêne dans <text><body> d'une TEI."
    )
    parser.add_argument("--tei", required=True, type=Path, help="TEI source")
    parser.add_argument("--annotations", required=True, type=Path, help="JSON d'annotations")
    parser.add_argument("--output", required=True, type=Path, help="TEI enrichie")
    parser.add_argument("--report", type=Path, help="Rapport JSON")
    parser.add_argument(
        "--allow-sha-mismatch",
        action="store_true",
        help="Continue même si le SHA-256 déclaré ne correspond pas au fichier TEI.",
    )
    parser.add_argument(
        "--fail-on-unmatched",
        action="store_true",
        help="Retourne un code d'erreur si une annotation ne peut pas être appliquée.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.tei.is_file():
        raise FileNotFoundError(f"TEI introuvable : {args.tei}")
    if not args.annotations.is_file():
        raise FileNotFoundError(f"JSON introuvable : {args.annotations}")

    source_sha = sha256_file(args.tei)
    payload, annotations = load_annotations(args.annotations)
    declared_sha = (payload.get("document") or {}).get("sha256")
    sha_matches = declared_sha in {None, "", source_sha, f"sha256:{source_sha}"}
    if not sha_matches and not args.allow_sha_mismatch:
        raise ValueError(
            "Le SHA-256 du JSON ne correspond pas à la TEI source. "
            "Utilise --allow-sha-mismatch uniquement après vérification manuelle."
        )

    tree = load_tei(args.tei)
    text, segments = linearize_body(tree)
    match_annotations(text, segments, annotations)
    detect_overlaps(annotations)
    applied = inject_annotations(segments, annotations)
    add_provenance(tree, applied, args.annotations.name)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    tree.write(
        str(args.output),
        encoding="UTF-8",
        xml_declaration=True,
        pretty_print=True,
    )

    report_path = args.report or args.output.with_suffix(".report.json")
    report = make_report(
        args.tei,
        args.annotations,
        args.output,
        source_sha,
        declared_sha,
        annotations,
    )
    write_json(report_path, report)

    failed = [item for item in annotations if item.status != "applied"]
    print(f"Annotations appliquées : {applied}/{len(annotations)}")
    print(f"TEI enrichie : {args.output}")
    print(f"Rapport : {report_path}")
    if failed:
        print(f"Annotations non appliquées : {len(failed)}", file=sys.stderr)
        for item in failed:
            print(f"- {item.annotation_id}: {item.status} — {item.message}", file=sys.stderr)
    return 1 if args.fail_on_unmatched and failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
