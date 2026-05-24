# -----------------------------------------------------------
# Code original : Kelly Christensen
# Classe Python pour extraire les attributs des éléments
# du <sourceDoc> TEI à partir des fichiers ALTO.
# -----------------------------------------------------------

from lxml import etree
import re
from collections import namedtuple


# Namespace utilisé par les fichiers ALTO v4
NS = {'a': "http://www.loc.gov/standards/alto/ns-v4#"}


class Attributes:
    def __init__(self, doc, folio, alto_root, tags, config):
        self.doc = doc
        self.folio = folio
        self.root = alto_root
        self.tags = tags

        # Paramètres IIIF.
        # On utilise get() pour éviter une erreur si le projet n’utilise pas IIIF.
        self.scheme = config.get("scheme")
        self.server = config.get("server")
        self.prefix = config.get("image_prefix")

    def surface(self):
        """Crée les attributs du <surface> TEI à partir du <Page> ALTO.

        Attributs TEI produits :
            - @xml:id : identifiant de la surface/page
            - @n      : numéro physique de l’image/page
            - @ulx    : coordonnée x du coin supérieur gauche
            - @uly    : coordonnée y du coin supérieur gauche
            - @lrx    : coordonnée x du coin inférieur droit
            - @lry    : coordonnée y du coin inférieur droit

        Returns:
            attributes (dict): dictionnaire des attributs TEI.
        """

        # Récupération des attributs de l’élément <Page> dans le fichier ALTO
        att_list = self.root.find('.//a:Page', namespaces=NS).attrib

        # Conversion des attributs ALTO vers des attributs TEI
        attributes = {
            "{http://www.w3.org/XML/1998/namespace}id": f"f{self.folio}",
            "n": att_list["PHYSICAL_IMG_NR"],
            "ulx": "0",
            "uly": "0",
            "lrx": att_list["WIDTH"],
            "lry": att_list["HEIGHT"]
        }

        return attributes

    def zones(self, parent, target, segmonto_labels):
        """Crée les attributs des <zone> TEI à partir des éléments ALTO.

        Cette méthode sert pour deux niveaux principaux :
            1. les <TextBlock> ALTO ;
            2. les <TextLine> ALTO.

        Args:
            parent (str): élément parent ALTO à parcourir.
                Exemple :
                'TextBlock[@ID="eSc_textblock_20c2f4d8"]'

            target (str): élément ALTO à transformer en <zone>.
                Exemple :
                'TextLine'

            segmonto_labels: liste ou dictionnaire des labels SegmOnto connus.

        Returns:
            output (list): liste de namedtuple ZoneData(attributes, id).
        """

        # Structure légère pour stocker les attributs TEI et l’identifiant ALTO
        ZoneData = namedtuple("ZoneData", ["attributes", "id"])
        output = []

        # Liste des éléments ALTO ciblés
        element_list = [
            z for z in self.root.findall(
                f'.//a:{parent}/a:{target}',
                namespaces=NS
            )
        ]

        for element in element_list:
            # On ne traite que les éléments possédant un identifiant ALTO
            if "ID" in element.attrib:
                attributes = {}
                id = element.attrib["ID"]

                # Création de la structure de sortie pour l’élément courant
                data = ZoneData(attributes, id)

                # Cas des éléments ayant une référence à une balise SegmOnto
                if "TAGREFS" in element.attrib and element.attrib["TAGREFS"] in self.tags:
                    tag = str(self.tags[element.attrib["TAGREFS"]])

                    # Découpage du label SegmOnto.
                    # Exemple attendu :
                    # MainZone:column#1
                    #
                    # Le regex extrait :
                    # - MainZone
                    # - column
                    # - 1
                    tag_parts = re.match(r"(\w+):?(\w+)?#?(\d?)?", tag)

                    data.attributes["type"] = tag_parts.group(1) or "none"
                    main_type = data.attributes["type"]

                    # Si le type principal correspond à un label SegmOnto connu,
                    # on crée un lien vers sa définition dans le teiHeader.
                    if segmonto_labels is not None and main_type in segmonto_labels:
                        data.attributes["corresp"] = f"#{main_type}"

                    data.attributes["subtype"] = tag_parts.group(2) or "none"
                    data.attributes["n"] = tag_parts.group(3) or "none"

                # Cas des éléments sans @TAGREFS :
                # par exemple segment, espace ou glyphe.
                else:
                    main_type = etree.QName(element).localname

                    if main_type == "SP":
                        main_type = "Space"

                    data.attributes["type"] = main_type

                # Récupération des coordonnées rectangulaires si elles existent
                if "HPOS" in element.attrib:
                    x = element.attrib["HPOS"]
                    y = element.attrib["VPOS"]
                    w = element.attrib["WIDTH"]
                    h = element.attrib["HEIGHT"]

                    data.attributes["ulx"] = x
                    data.attributes["uly"] = y
                    data.attributes["lrx"] = str(int(w) + int(x))
                    data.attributes["lry"] = str(int(h) + int(y))

                # Récupération du polygone si l’élément possède un <Polygon>
                if (
                    element.find('.//a:Polygon', namespaces=NS) is not None
                    and element.find('.//a:Polygon', namespaces=NS).attrib.get("POINTS") is not None
                ):
                    points = element.find('.//a:Polygon', namespaces=NS).attrib["POINTS"]

                    # Reformate les points ALTO :
                    # "2204 4621 2190 4528"
                    # devient :
                    # "2204,4621 2190,4528"
                    data.attributes["points"] = " ".join(
                        [
                            re.sub(r"\s", ",", x)
                            for x in re.findall(r"(\d+ \d+)", points)
                        ]
                    )

                # Ajout éventuel d’un lien IIIF vers la zone d’image.
                # Cette partie est désactivée automatiquement si aucune config IIIF n’est fournie.
                if (
                    "HPOS" in element.attrib
                    and self.scheme
                    and self.server
                    and self.prefix
                ):
                    data.attributes["source"] = (
                        f"{self.scheme}://{self.server}"
                        f"{self.prefix}/{self.doc}/f{self.folio}/"
                        f"{x},{y},{w},{h}/full/0/native.jpg"
                    )

                output.append(data)

        return output