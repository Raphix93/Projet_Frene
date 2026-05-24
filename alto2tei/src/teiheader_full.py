# -----------------------------------------------------------
# Code original : Kelly Christensen
# Classe Python pour insérer les métadonnées du document
# et du projet dans le <teiHeader> par défaut.
# -----------------------------------------------------------

from lxml import etree
import re

from .sourcedoc_build import labels


class FullTree:
    def __init__(self, children, metadata):
        self.children = children

        # Anciennes métadonnées BnF/Gallica conservées pour compatibilité
        self.sru = metadata.get("sru", {})
        self.iiif = metadata.get("iiif", {})

        # Métadonnées locales du projet Frêne
        self.metadata = metadata

    def author_data(self):
        """Ajoute les données d’auteur dans <titleStmt> et <bibl>."""

        self.authors(self.children["titleStmt"], True)
        self.authors(self.children["bibl"], False)

    def authors(self, parent, is_first_id):
        """Ajoute l’auteur du document dans <titleStmt> ou <bibl>.

        Args:
            parent: élément parent, soit <titleStmt>, soit <bibl>.
            is_first_id (bool): si True, ajoute xml:id ; sinon ajoute ref.
        """

        author_root = parent.find("./author")

        if author_root is None:
            author_root = etree.SubElement(parent, "author")

        author = self.metadata.get("author", {})
        author_name = author.get("name", "Théophile Rémy Frêne")

        xml_id = "{http://www.w3.org/XML/1998/namespace}id"

        if is_first_id:
            author_root.attrib[xml_id] = "frene"
        else:
            author_root.attrib["ref"] = "#frene"

        persName = etree.SubElement(author_root, "persName")

        persName.attrib["ref"] = author.get(
            "viaf",
            "https://viaf.org/viaf/24931371"
        )

        persName.attrib["sameAs"] = author.get(
            "wikidata",
            "https://www.wikidata.org/wiki/Q119860"
        )

        persName.text = author_name

    def bib_data(self):
        """Ajoute les données bibliographiques et archivistiques."""

        # Titre dans <titleStmt>
        self.entry(
            self.metadata.get("title"),
            self.children["ts_title"],
            None
        )

        # Lien vers la notice OAEN
        self.entry(
            self.metadata.get("ark"),
            self.children["ptr"],
            "target"
        )

        # Titre dans <bibl>
        self.entry(
            self.metadata.get("title"),
            self.children["bib_title"],
            None
        )

        # Institution conservatrice
        self.entry(
            self.metadata.get("repository"),
            self.children["publisher"],
            None
        )

        self.entry(
            self.metadata.get("repository"),
            self.children["repository"],
            None
        )

        # Cote / identifiant du fonds
        self.entry(
            self.metadata.get("fonds_id"),
            self.children["idno"],
            None
        )

        # Dates extrêmes du fonds
        fonds_dates = self.metadata.get("fonds_dates", {})

        date_text = None

        if fonds_dates.get("from") and fonds_dates.get("to"):
            date_text = f'{fonds_dates["from"]}-{fonds_dates["to"]}'

        self.entry(
            date_text,
            self.children["date"],
            None
        )

        if fonds_dates.get("from"):
            self.children["date"].attrib["from"] = fonds_dates["from"]

        if fonds_dates.get("to"):
            self.children["date"].attrib["to"] = fonds_dates["to"]

        # Description synthétique du fonds
        self.entry(
            self.metadata.get("abstract"),
            self.children["p"],
            None
        )

        # Langue
        self.children["language"].attrib["ident"] = "fr"
        self.children["language"].text = "français"

    def entry(self, data, tei_element, attribute):
        """Insère une donnée dans un élément TEI.

        Args:
            data: valeur à insérer.
            tei_element: élément TEI cible.
            attribute: nom d’attribut à remplir ; si None, remplit le texte.
        """

        if data is None:
            return

        if attribute:
            tei_element.attrib[attribute] = data
        else:
            tei_element.text = data

    def segmonto_taxonomy(self, filepaths):
        """Construit la taxonomie SegmOnto à partir des tags ALTO utilisés."""

        SegmOntoZones = {
            "CustomZone": "https://segmonto.github.io/gd/gdZ/CustomZone/",
            "DamageZone": "https://segmonto.github.io/gd/gdZ/DamageZone",
            "DecorationZone": "https://segmonto.github.io/gd/gdZ/DecorationZone",
            "DigitizationArtefactZone": "https://segmonto.github.io/gd/gdZ/DigitizationArtefactZone",
            "DropCapitalZone": "https://segmonto.github.io/gd/gdZ/DropCapitalZone",
            "GraphicZone": "https://segmonto.github.io/gd/gdZ/GraphicZone",
            "MainZone": "https://segmonto.github.io/gd/gdZ/MainZone",
            "MarginTextZone": "https://segmonto.github.io/gd/gdZ/MarginTextZone",
            "MusicZone": "https://segmonto.github.io/gd/gdZ/MusicZone",
            "NumberingZone": "https://segmonto.github.io/gd/gdZ/NumberingZone",
            "QuireMarksZone": "https://segmonto.github.io/gd/gdZ/QuireMarksZone",
            "RunningTitleZone": "https://segmonto.github.io/gd/gdZ/RunningTitleZone",
            "SealZone": "https://segmonto.github.io/gd/gdZ/SealZone",
            "StampZone": "https://segmonto.github.io/gd/gdZ/StampZone",
            "TableZone": "https://segmonto.github.io/gd/gdZ/TableZone",
            "TitlePageZone": "https://segmonto.github.io/gd/gdZ/TitlePageZone",
        }

        SegmOntoLines = {
            "CustomLine": "https://segmonto.github.io/gd/gdL/CustomLine/",
            "DefaultLine": "https://segmonto.github.io/gd/gdL/DefaultLine",
            "DropCapitalLine": "https://segmonto.github.io/gd/gdL/DropCapitalLine",
            "HeadingLine": "https://segmonto.github.io/gd/gdL/HeadingLine",
            "InterlinearLine": "https://segmonto.github.io/gd/gdL/InterlinearLine",
            "MusicLine": "https://segmonto.github.io/gd/gdL/MusicLine",
        }

        # Récupère tous les dictionnaires de tags utilisés dans les fichiers ALTO
        all_tag_dicts = [labels(f) for f in filepaths]

        # Extrait la partie principale du label SegmOnto :
        # MainZone:column#1 devient MainZone
        unique_labels = list(
            set(
                re.match(r"(\w+):?(\w+)?#?(\d?)?", value).group(1)
                for dic in all_tag_dicts
                for value in dic.values()
                if re.match(r"(\w+):?(\w+)?#?(\d?)?", value)
            )
        )

        # Sépare les zones et les lignes
        document_zones = [
            label for label in unique_labels
            if "Zone" in label
        ]

        document_lines = [
            label for label in unique_labels
            if "Line" in label
        ]

        # Catégorie des zones SegmOnto
        cat_id = {
            "{http://www.w3.org/XML/1998/namespace}id": "SegmOntoZones"
        }

        category = etree.SubElement(
            self.children["taxonomy"],
            "category",
            cat_id
        )

        for z in set(SegmOntoZones).intersection(set(document_zones)):
            self.enter_taxonomy_category(
                category,
                z,
                SegmOntoZones[z]
            )

        # Catégorie des lignes SegmOnto
        cat_id = {
            "{http://www.w3.org/XML/1998/namespace}id": "SegmOntoLines"
        }

        category = etree.SubElement(
            self.children["taxonomy"],
            "category",
            cat_id
        )

        for l in set(SegmOntoLines).intersection(set(document_lines)):
            self.enter_taxonomy_category(
                category,
                l,
                SegmOntoLines[l]
            )

        return document_zones, document_lines

    def enter_taxonomy_category(self, category, tag, url):
        """Ajoute une catégorie SegmOnto dans la taxonomie TEI."""

        catDesc_id = {
            "{http://www.w3.org/XML/1998/namespace}id": f"{tag}"
        }

        catDesc = etree.SubElement(
            category,
            "catDesc",
            catDesc_id
        )

        title = etree.SubElement(catDesc, "title")
        title.text = tag

        ptr = etree.SubElement(catDesc, "ptr")
        ptr.attrib["target"] = url
        
