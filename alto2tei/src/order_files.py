# -----------------------------------------------------------
# Code original : Kelly Christensen
# Classe Python pour organiser les chemins des fichiers
# présents dans le dossier de données.
# -----------------------------------------------------------

import re
from collections import namedtuple


class Files:
    def __init__(self, document, filepaths):
        # Nom du document, généralement le nom du dossier contenant les fichiers ALTO
        self.d = document

        # Liste des chemins vers les fichiers ALTO-XML
        self.fl = filepaths

    def order_files(self):
        """Trie les fichiers XML selon le numéro présent à la fin de leur nom.

        Exemple :
            Image00001.xml
            Image00002.xml
            Image00011.xml

        Returns:
            ordered_files (list): liste de namedtuple File(num, filepath),
            triée par numéro de page/image.
        """

        # Structure légère associant un numéro extrait du nom de fichier
        # et le chemin complet du fichier.
        File = namedtuple("File", ["num", "filepath"])

        ordered_files = sorted(
            [
                File(
                    int(re.search(r"(\d+).xml$", f.name).group(1)),
                    f
                )
                for f in self.fl
                if re.search(r"(\d+).xml$", f.name)
            ]
        )

        return ordered_files