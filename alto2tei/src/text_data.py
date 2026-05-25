# -----------------------------------------------------------
# Classe Python pour extraire et stocker les données textuelles
# présentes dans le <sourceDoc>.
# -----------------------------------------------------------

from collections import namedtuple


class Text:
    def __init__(self, root):
        # Racine de l’arbre XML-TEI
        self.root = root

        # Liste des lignes textuelles extraites du <sourceDoc>
        self.data = self.line_data()

    def line_data(self):
        """Extrait les données contextuelles et les attributs de chaque ligne.

        Returns:
            data (list): liste de namedtuple Line contenant les informations
            nécessaires à la construction du <body>.
        """

        # Structure légère pour stocker les informations d’une ligne
        Line = namedtuple(
            "Line",
            [
                "id",          # xml:id de la zone correspondant à la ligne
                "n",           # numéro de ligne
                "text",        # contenu textuel de la ligne
                "line_type",   # type SegmOnto de la ligne
                "zone_type",   # type SegmOnto du bloc parent
                "zone_id",     # xml:id du bloc parent
                "page_id"      # xml:id de la page/surface
            ]
        )

        # Pour chaque élément <line> présent dans le <sourceDoc>,
        # on remonte dans l’arbre XML pour récupérer :
        # - sa zone de ligne ;
        # - son bloc parent ;
        # - sa page parent.
        data = [
            Line(
                # xml:id de la zone de ligne
                ln.getparent().get(
                    "{http://www.w3.org/XML/1998/namespace}id"
                ),

                # Numéro de la ligne
                ln.get("n"),

                # Texte contenu dans l’élément <line>
                ln.text,

                # Type de la zone de ligne, par exemple DefaultLine
                ln.getparent().get("type"),

                # Type de la zone du bloc parent, par exemple MainZone
                ln.getparent().getparent().get("type"),

                # xml:id de la zone du bloc parent
                ln.getparent().getparent().get(
                    "{http://www.w3.org/XML/1998/namespace}id"
                ),

                # xml:id de la surface/page parent
                ln.getparent().getparent().getparent().get(
                    "{http://www.w3.org/XML/1998/namespace}id"
                )
            )
            for ln in self.root.findall(".//line")
        ]

        return data