import os
import sys
import re
from pathlib import Path
from lxml import etree


NS = {"a": "http://www.loc.gov/standards/alto/ns-v4#"}


def order_files(directory):
    """Trie les fichiers XML selon le numéro contenu dans leur nom."""
    directory = Path(directory)
    files = [file for file in directory.iterdir() if file.suffix.lower() == ".xml"]

    def extract_number(path):
        match = re.search(r"(\d+)", path.stem)
        return int(match.group(1)) if match else float("inf")

    return sorted(files, key=extract_number)


def extract_text_from_mainzones(files):
    """Extrait le texte des zones MainZone des fichiers ALTO."""
    text = []

    for file_path in files:
        root = etree.parse(str(file_path)).getroot()

        mainzone_ids = [
            tag.get("ID")
            for tag in root.findall(".//a:OtherTag", namespaces=NS)
            if tag.get("LABEL") in {"MainZone", "MainZone#1", "MainZone#2"}
        ]

        for zone_id in mainzone_ids:
            lines = root.findall(
                f'.//a:TextBlock[@TAGREFS="{zone_id}"]/a:TextLine',
                namespaces=NS
            )

            for line in lines:
                strings = line.findall(".//a:String", namespaces=NS)
                line_text = " ".join(
                    string.get("CONTENT", "") for string in strings
                ).strip()

                if line_text:
                    text.append(line_text)

    return text


def dump_text(text, directory):
    """Nettoie et exporte le texte extrait en fichier TXT."""
    directory = Path(directory)

    s = "%%".join(text)

    # Normalisations simples
    s = re.sub(r"⁊", "et", s)

    # Réunit les mots coupés en fin de ligne : Re¬ %% convillier -> Reconvillier
    s = re.sub(r"[¬-]%%", "", s)

    # Remplace les autres fins de ligne par des espaces
    s = re.sub(r"%%", " ", s)

    # Découpage léger en paragraphes
    s = re.sub(r"(\.\s)([A-ZÉÀÈÙÂÊÎÔÛÄËÏÖÜÇ])", r"\1\n\n\2", s)
    s = re.sub(r"(?<!\n\n)(⁋|¶)", r"\n\n\1", s)
    s = re.sub(r"([;?!:])\s", r"\1\n\n", s)

    output_path = directory.parent / f"{directory.name}.txt"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(s)

    print(f"Fichier TXT créé : {output_path}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        directories = [Path(path) for path in sys.argv[1:] if Path(path).is_dir()]

        for directory in directories:
            ordered_files = order_files(directory)
            text = extract_text_from_mainzones(ordered_files)
            dump_text(text, directory)
    else:
        print("Aucun dossier donné.")