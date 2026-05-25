# -----------------------------------------------------------
# Classe Python pour générer le fichier XML-TEI final.
# -----------------------------------------------------------

import os
from lxml import etree


class Write:
    def __init__(self, document, root):

        # Nom du document utilisé pour le nom du fichier de sortie
        self.d = document

        # Racine de l’arbre XML-TEI
        self.r = root

    def write(self):
        """Écrit le document TEI sur disque."""

        # Création du dossier de sortie s’il n’existe pas
        os.makedirs("./data", exist_ok=True)

        output_path = f"./data/{self.d}.xml"

        with open(output_path, "wb") as f:

            etree.ElementTree(self.r).write(
                f,

                # Encodage UTF-8 recommandé pour TEI
                encoding="utf-8",

                # Ajout de la déclaration XML
                xml_declaration=True,

                # Mise en forme du XML
                pretty_print=True
            )         
