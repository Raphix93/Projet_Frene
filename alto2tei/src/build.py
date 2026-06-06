from lxml import etree

from src.teiheader_metadata.clean_data import Metadata
from src.teiheader_build import teiheader
from src.sourcedoc_build import sourcedoc
from src.text_data import Text
from src.body_build import body


class TEI:
    """Classe principale pour construire un fichier XML-TEI à partir de fichiers ALTO."""

    def __init__(self, document, filepaths):
        # Nom du document, généralement le nom du dossier contenant les fichiers ALTO
        self.d = document

        # Liste des chemins vers les fichiers ALTO-XML du document
        self.fp = filepaths

        # Métadonnées utilisées pour construire le <teiHeader>
        self.metadata = {}

        # Dictionnaire des balises SegmOnto trouvées dans les fichiers ALTO
        self.tags = {}

        # Racine de l’arbre XML-TEI
        self.root = None

        # Liste ou structure des zones SegmOnto utilisées dans le document
        self.segmonto_zones = None

        # Liste ou structure des types de lignes SegmOnto utilisés dans le document
        self.segmonto_lines = None

    def build_tree(self):
        """Initialise la racine du document XML-TEI."""

        tei_root_att = {
            "xmlns": "http://www.tei-c.org/ns/1.0",
            "{http://www.w3.org/XML/1998/namespace}id": f"tei_{self.d}"
        }

        self.root = etree.Element("TEI", tei_root_att)

    def build_header(self, config, version):
        """Construit le <teiHeader> du document TEI."""

        self.metadata = Metadata(
            self.d,
            {
                "ark_url": "https://floraweb.ne.ch/flora/ark:/37964/001136"
            }
        ).prepare()

        self.root, self.segmonto_zones, self.segmonto_lines = teiheader(
            self.metadata,
            self.d,
            self.root,
            len(self.fp),
            config,
            version,
            self.fp,
            self.segmonto_zones,
            self.segmonto_lines
        )

    def build_sourcedoc(self, config):
        """Construit le <sourceDoc> à partir des fichiers ALTO."""

        sourcedoc(
            self.d,
            self.root,
            self.fp,
            self.tags,
            self.segmonto_zones,
            self.segmonto_lines,
            config.get("iiifURI", {})
        )

    def build_body(self):
        """Construit le <body> à partir du texte extrait du <sourceDoc>."""

        text = Text(self.root)

        body(self.root, text.data)