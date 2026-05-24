# -----------------------------------------------------------
# Code original : Kelly Christensen
# Classe Python pour construire l’architecture par défaut
# d’un <teiHeader>.
# -----------------------------------------------------------

from lxml import etree
from datetime import datetime
from collections import defaultdict


class DefaultTree:
    children = defaultdict(list)

    def __init__(self, config, document, root, metadata, count_pages, version):
        self.config = config
        self.document = document
        self.root = root

        # Métadonnées SRU/IIIF conservées pour compatibilité avec le code original.
        # Dans le projet Frêne, elles peuvent rester vides.
        self.sru = metadata.get("sru", {})
        self.iiif = metadata.get("iiif", {})

        # Métadonnées locales du projet
        self.metadata = metadata

        # Nombre de pages/images traitées
        self.count = str(count_pages)

        # Version de Kraken utilisée pour produire les ALTO
        self.version = version

    def build(self):
        """Construit la structure par défaut du <teiHeader> TEI."""

        # Valeur générique utilisée lorsque certaines informations manquent
        default_text = "Information non disponible."

        # Dans le code original, le nombre d’auteurs venait du SRU BnF.
        # Ici on utilise les métadonnées locales.
        num_authors = 1

        # ---------------------------------------------------
        # <teiHeader>
        # ---------------------------------------------------
        teiHeader = etree.SubElement(self.root, "teiHeader")

        # Trois grands enfants du <teiHeader>
        fileDesc = etree.SubElement(teiHeader, "fileDesc")
        profileDesc = etree.SubElement(teiHeader, "profileDesc")
        encodingDesc = etree.SubElement(teiHeader, "encodingDesc")

        # ---------------------------------------------------
        # <fileDesc>
        # ---------------------------------------------------
        titleStmt = etree.SubElement(fileDesc, "titleStmt")
        self.children["titleStmt"] = titleStmt

        # Titre principal du fichier TEI
        self.children["ts_title"] = etree.SubElement(titleStmt, "title")
        self.children["ts_title"].text = self.metadata.get(
            "title",
            default_text
        )

        # Sous-titre éventuel
        if self.metadata.get("subtitle"):
            subtitle = etree.SubElement(titleStmt, "title", type="sub")
            subtitle.text = self.metadata["subtitle"]

        # Auteur du document
        for i in range(num_authors):
            etree.SubElement(titleStmt, "author")

        # Mention de responsabilité pour la conversion ALTO -> TEI
        respStmt = etree.SubElement(titleStmt, "respStmt")

        resp = etree.SubElement(respStmt, "resp")
        resp.text = self.config["responsibility"]["text"]

        # Contributeurs déclarés dans config.yml
        for i in range(len(self.config["responsibility"]["resp"])):
            persName = etree.SubElement(respStmt, "persName")

            forename = etree.SubElement(persName, "forename")
            forename.text = self.config["responsibility"]["resp"][i]["forename"]

            surname = etree.SubElement(persName, "surname")
            surname.text = self.config["responsibility"]["resp"][i]["surname"]

            # Ajout facultatif d’un identifiant externe, par exemple ORCID
            if "ptr" in self.config["responsibility"]["resp"][i]:
                etree.SubElement(
                    persName,
                    "ptr",
                    self.config["responsibility"]["resp"][i]["ptr"]
                )

        # Étendue de la ressource numérique produite
        extent = etree.SubElement(fileDesc, "extent")
        etree.SubElement(extent, "measure", unit="images", n=self.count)

        # Si les métadonnées locales contiennent une étendue archivistique,
        # on ajoute aussi le nombre de volumes et de pages du fonds.
        if self.metadata.get("extent"):
            if self.metadata["extent"].get("volumes"):
                etree.SubElement(
                    extent,
                    "measure",
                    unit="volumes",
                    n=str(self.metadata["extent"]["volumes"])
                )

            if self.metadata["extent"].get("pages"):
                etree.SubElement(
                    extent,
                    "measure",
                    unit="pages",
                    n=str(self.metadata["extent"]["pages"])
                )

        # ---------------------------------------------------
        # <publicationStmt>
        # ---------------------------------------------------
        publicationStmt = etree.SubElement(fileDesc, "publicationStmt")

        publisher = etree.SubElement(publicationStmt, "publisher")
        publisher.text = self.config["responsibility"]["publisher"]

        authority = etree.SubElement(publicationStmt, "authority")
        authority.text = self.config["responsibility"]["authority"]

        availability = etree.SubElement(
            publicationStmt,
            "availability",
            self.config["responsibility"]["availability"]
        )

        # Condition d’accès locale
        if self.metadata.get("access"):
            p_access = etree.SubElement(availability, "p")
            p_access.text = self.metadata["access"]

        etree.SubElement(
            availability,
            "licence",
            self.config["responsibility"]["licence"]
        )

        # Date de génération du fichier TEI
        today = datetime.today().strftime("%Y-%m-%d")
        etree.SubElement(publicationStmt, "date", when=today)

        # ---------------------------------------------------
        # <sourceDesc>
        # ---------------------------------------------------
        sourceDesc = etree.SubElement(fileDesc, "sourceDesc")

        # Description bibliographique simple
        bibl = etree.SubElement(sourceDesc, "bibl")
        self.children["bibl"] = bibl

        self.children["ptr"] = etree.SubElement(bibl, "ptr")

        for i in range(num_authors):
            etree.SubElement(bibl, "author")

        self.children["bib_title"] = etree.SubElement(bibl, "title")
        self.children["bib_title"].text = self.metadata.get(
            "title",
            default_text
        )

        self.children["pubPlace"] = etree.SubElement(bibl, "pubPlace")
        self.children["pubPlace"].text = default_text

        self.children["publisher"] = etree.SubElement(bibl, "publisher")
        self.children["publisher"].text = self.metadata.get(
            "repository",
            default_text
        )

        self.children["date"] = etree.SubElement(bibl, "date")
        self.children["date"].text = (
            f'{self.metadata.get("fonds_dates", {}).get("from", "")}-'
            f'{self.metadata.get("fonds_dates", {}).get("to", "")}'
        )

        # ---------------------------------------------------
        # <msDesc>
        # ---------------------------------------------------
        msDesc = etree.SubElement(sourceDesc, "msDesc")

        # Niveau de description archivistique
        if self.metadata.get("level"):
            msDesc.attrib["type"] = self.metadata["level"]

        msIdentifier = etree.SubElement(msDesc, "msIdentifier")

        self.children["country"] = etree.SubElement(msIdentifier, "country")
        self.children["country"].text = "Suisse"

        self.children["settlement"] = etree.SubElement(msIdentifier, "settlement")
        self.children["settlement"].text = "Neuchâtel"

        self.children["repository"] = etree.SubElement(msIdentifier, "repository")
        self.children["repository"].text = self.metadata.get(
            "repository",
            default_text
        )

        self.children["idno"] = etree.SubElement(msIdentifier, "idno")
        self.children["idno"].text = self.metadata.get(
            "fonds_id",
            default_text
        )

        # Identifiant ARK local OAEN
        altIdentifier = etree.SubElement(msIdentifier, "altIdentifier")
        alt_idno = etree.SubElement(altIdentifier, "idno", type="ark")
        alt_idno.text = self.metadata.get("ark", self.document)

        # Description physique
        physDesc = etree.SubElement(msDesc, "physDesc")
        objectDesc = etree.SubElement(physDesc, "objectDesc")

        self.children["p"] = etree.SubElement(objectDesc, "p")
        self.children["p"].text = self.metadata.get(
            "abstract",
            default_text
        )

        # ---------------------------------------------------
        # <profileDesc>
        # ---------------------------------------------------
        profileDesc = profileDesc

        langUsage = etree.SubElement(profileDesc, "langUsage")

        self.children["language"] = etree.SubElement(langUsage, "language")
        self.children["language"].attrib["ident"] = "fr"
        self.children["language"].text = "français"

        # ---------------------------------------------------
        # <encodingDesc>
        # ---------------------------------------------------
        appInfo = etree.SubElement(encodingDesc, "appInfo")

        application = etree.SubElement(appInfo, "application")
        application.attrib["ident"] = "Kraken"
        application.attrib["version"] = self.version

        app_label = etree.SubElement(application, "label")
        app_label.text = "Kraken"

        app_ptr = etree.SubElement(application, "ptr")
        app_ptr.attrib["target"] = "https://github.com/mittagessen/kraken"

        # Déclaration de la taxonomie SegmOnto
        classDecl = etree.SubElement(encodingDesc, "classDecl")

        taxonomy_id = {
            "{http://www.w3.org/XML/1998/namespace}id": "SegmOnto"
        }

        self.children["taxonomy"] = etree.SubElement(
            classDecl,
            "taxonomy",
            taxonomy_id
        )

        tax_bibl = etree.SubElement(self.children["taxonomy"], "bibl")

        tax_title = etree.SubElement(tax_bibl, "title")
        tax_title.text = "SegmOnto"

        tax_ptr = etree.SubElement(tax_bibl, "ptr")
        tax_ptr.attrib["target"] = "https://github.com/segmonto"