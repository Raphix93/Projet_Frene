# -----------------------------------------------------------
# Code original : Kelly Christensen
# Script principal pour lancer la conversion ALTO vers TEI.
# -----------------------------------------------------------

import argparse
import os
import yaml

from collections import namedtuple
from pathlib import Path
from time import perf_counter

from src.build import TEI
from src.write_output import Write


def file_path(string):
    """Vérifie que l’argument --config correspond bien à un fichier existant.

    Args:
        string (str): chemin vers le fichier de configuration YAML.

    Raises:
        FileNotFoundError: si le chemin indiqué ne correspond pas à un fichier.

    Returns:
        str: chemin validé vers le fichier de configuration.
    """

    if os.path.isfile(string):
        return string

    raise FileNotFoundError(string)


def get_args():
    """Lit les arguments passés en ligne de commande.

    Vérifie notamment :
        1. que le fichier de configuration existe ;
        2. quelles parties du TEI doivent être produites.
    """

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--config",
        nargs=1,
        type=file_path,
        required=True,
        help="chemin vers le fichier de configuration YAML"
    )

    parser.add_argument(
        "--version",
        nargs=1,
        type=str,
        required=True,
        help="version de Kraken utilisée pour créer les fichiers ALTO-XML"
    )

    parser.add_argument(
        "--header",
        default=False,
        action="store_true",
        help="produire un XML-TEI avec <teiHeader>"
    )

    parser.add_argument(
        "--sourcedoc",
        default=False,
        action="store_true",
        help="produire un XML-TEI avec <sourceDoc>"
    )

    parser.add_argument(
        "--body",
        default=False,
        action="store_true",
        help="produire un XML-TEI avec <body>"
    )

    args = parser.parse_args()

    return (
        args.config,
        args.version,
        args.header,
        args.sourcedoc,
        args.body
    )


def collect_xml_files(document_dir):
    """Récupère les fichiers ALTO-XML d’un dossier documentaire.

    Le code cherche d’abord dans un sous-dossier XML-Alto.
    Si ce dossier n’existe pas, il cherche directement dans le dossier du document.

    Args:
        document_dir (Path): dossier du document.

    Returns:
        list: liste des chemins vers les fichiers XML.
    """

    xml_alto_dir = document_dir / "XML-Alto"

    if xml_alto_dir.is_dir():
        return [
            f for f in xml_alto_dir.iterdir()
            if f.suffix.lower() == ".xml"
        ]

    return [
        f for f in document_dir.iterdir()
        if f.suffix.lower() == ".xml"
    ]


def main():
    # Lecture des arguments de ligne de commande
    config, version, header, sourcedoc, body = get_args()

    # Le <body> dépend du <sourceDoc>.
    # On empêche donc la génération d’un <body> seul.
    if body and not sourcedoc:
        warning = (
            "\n    Impossible de produire <body> sans <sourceDoc>."
            "\n    Pour utiliser l’option --body, ajoute aussi l’option --sourcedoc."
        )

        raise Exception(warning)

    # Lecture du fichier de configuration YAML
    with open(config[0], encoding="utf-8") as cf_file:
        config = yaml.safe_load(cf_file.read())

    # Pour chaque dossier présent dans le chemin indiqué dans config.yml,
    # on récupère :
    # - le nom du dossier documentaire ;
    # - les chemins vers ses fichiers ALTO-XML.
    Docs = namedtuple(
        "Docs",
        [
            "doc_name",
            "filepaths"
        ]
    )

    data_path = Path(config.get("data")["path"])

    docs = [
        Docs(
            d.name,
            collect_xml_files(d)
        )
        for d in data_path.iterdir()
        if d.is_dir()
    ]

    for d in docs:
        # On ignore les dossiers qui ne contiennent aucun XML
        if not d.filepaths:
            print(f"\33[31mAucun fichier XML trouvé pour {d.doc_name}\x1b[0m")
            continue

        # Instanciation de la classe TEI pour le document courant
        tree = TEI(
            d.doc_name,
            d.filepaths
        )

        # Création de la racine <TEI>
        tree.build_tree()

        print("\n=====================================")
        print(f"\33[32m~ traitement du document {d.doc_name} ~\x1b[0m")

        if header:
            print(f"\33[33mconstruction du <teiHeader>\x1b[0m")

            t0 = perf_counter()

            tree.build_header(
                config,
                version[0]
            )

            print(
                "|________terminé en {:.4f} secondes".format(
                    perf_counter() - t0
                )
            )

        if sourcedoc:
            print(f"\33[33mconstruction du <sourceDoc>\x1b[0m")

            t0 = perf_counter()

            tree.build_sourcedoc(config)

            print(
                "|________terminé en {:.4f} secondes".format(
                    perf_counter() - t0
                )
            )

        if body:
            print(f"\33[33mconstruction du <body>\x1b[0m")

            t0 = perf_counter()

            tree.build_body()

            print(
                "|________terminé en {:.4f} secondes".format(
                    perf_counter() - t0
                )
            )

        # Écriture du fichier XML-TEI final
        if not os.path.exists("./data/"):
            os.mkdir("./data/")

        Write(
            d.doc_name,
            tree.root
        ).write()


if __name__ == "__main__":
    main()
    