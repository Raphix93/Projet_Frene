class Metadata:
    """Métadonnées locales utilisées pour construire le teiHeader."""

    metadata = {
        "title": "Journal du pasteur Théophile Frêne",
        "subtitle": "Souvenirs d'un pasteur de campagne jurassien au XVIIIe siècle",
        "author": {
            "name": "Théophile Rémy Frêne",
            "viaf": "https://viaf.org/viaf/24931371",
            "wikidata": "https://www.wikidata.org/wiki/Q119860",
        },
        "repository": "Office des archives de l'État de Neuchâtel",
        "fonds_id": "FRENE THEOPHILE-REMY",
        "ark": "https://floraweb.ne.ch/flora/ark:/37964/001136",
        "level": "fonds",
        "fonds_dates": {
            "from": "1741",
            "to": "1804",
        },
        "extent": {
            "volumes": 7,
            "pages": 3114,
        },
        "access": "Consultation libre",
        "abstract": "Journal autobiographique couvrant la période 1741-1804.",
    }

    def __init__(self, document=None, config=None):
        self.document = document
        self.config = config

    def prepare(self):
        return self.metadata