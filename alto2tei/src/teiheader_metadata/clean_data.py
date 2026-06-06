from src.teiheader_metadata.flora_data import Flora


class Metadata:
    """Métadonnées Flora utilisées pour construire le teiHeader."""

    def __init__(self, document=None, config=None):
        self.document = document
        self.config = config or {}

    def prepare(self):
        flora = Flora(
            ark_url=self.config["ark_url"]
        )

        return flora.to_tei_metadata()