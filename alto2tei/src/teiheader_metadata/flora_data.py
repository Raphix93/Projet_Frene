# -----------------------------------------------------------
# Script pour récupérer et nettoyer une notice Flora
# SIA : Archives de l'État de Neuchâtel / Flora
# -----------------------------------------------------------

from lxml import etree, html
import requests
import re


class Flora:
    """Classe pour récupérer et nettoyer les métadonnées d'une notice Flora."""

    def __init__(self, record_id=None, ark_url=None, base_url="https://floraweb.ne.ch/flora/"):
        """
        Args:
            record_id (str): identifiant interne Flora, ex. 'archive:ARCH_HOLDINGS:136'
            ark_url (str): URL ARK publique, ex. 'https://floraweb.ne.ch/flora/ark:/37964/001136'
            base_url (str): URL de base de Flora
        """
        self.record_id = record_id
        self.ark_url = ark_url
        self.base_url = base_url.rstrip("/") + "/"

    def request_html(self):
        """Récupère la page HTML publique Flora."""
        if not self.ark_url:
            raise ValueError("Une URL ARK est nécessaire pour récupérer le HTML.")

        response = requests.get(self.ark_url, timeout=30)
        response.raise_for_status()
        return response.text

    def find_record_id_from_html(self, html_text):
        """Extrait l'identifiant interne Flora depuis le HTML."""
        match = re.search(r"record=archive%3AARCH_HOLDINGS%3A(\d+)", html_text)

        if match:
            self.record_id = f"archive:ARCH_HOLDINGS:{match.group(1)}"
            return self.record_id

        match = re.search(r"archive:ARCH_HOLDINGS:\d+", html_text)

        if match:
            self.record_id = match.group(0)
            return self.record_id

        return None

    def request_xml(self):
        """Récupère l'export XML de la notice Flora."""
        if not self.record_id:
            html_text = self.request_html()
            self.find_record_id_from_html(html_text)

        if not self.record_id:
            raise ValueError("Impossible de déterminer le record_id Flora.")

        url = self.base_url + "servlet/RecordRead"
        params = {
            "action": "export_xml",
            "record": self.record_id,
        }

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        return etree.fromstring(response.content)

    def clean_from_html(self, html_text):
        """
        Nettoie les métadonnées depuis le HTML public.
        Solution de secours si l'export XML n'est pas exploitable.
        """
        doc = html.fromstring(html_text)

        data = {
            "site": None,
            "parent": None,
            "cote": None,
            "title": None,
            "date": None,
            "level": None,
            "abstract": None,
            "access": None,
            "linked_records": [],
            "record_id": self.record_id,
            "source": "html",
        }

        rows = doc.xpath("//tr")

        for row in rows:
            label = row.xpath(".//th[contains(@class, 'view-field-label')]/text()")
            value = row.xpath(".//td[contains(@class, 'view-field-value')]//text()")

            if not label or not value:
                continue

            label = " ".join(x.strip() for x in label if x.strip())
            value = " ".join(x.strip() for x in value if x.strip())

            if label == "Site":
                data["site"] = value
            elif label == "Niveau supérieur":
                data["parent"] = value
            elif label == "Cote":
                data["cote"] = value
            elif label == "Intitulé du fonds":
                data["title"] = value
            elif label == "Années extrêmes":
                data["date"] = value
            elif label == "Niveau de description":
                data["level"] = value
            elif label == "Présentation du contenu":
                data["abstract"] = value
            elif label == "Statut juridique du fonds":
                data["access"] = value
            elif label == "Voir Archives":
                data["linked_records"] = self.extract_linked_records(row)

        return data

    def extract_linked_records(self, row):
        """Extrait les notices liées, par exemple les volumes du fonds."""
        linked_records = []

        text_parts = row.xpath(".//td[contains(@class, 'view-field-value')]//text()")
        links = row.xpath(".//a[contains(@href, 'record=archive%3AARCH_HOLDINGS')]/@href")

        cleaned_lines = [
            " ".join(part.split())
            for part in text_parts
            if "Journal de ma vie" in part
        ]

        for i, line in enumerate(cleaned_lines):
            record_id = None

            if i < len(links):
                match = re.search(r"record=archive%3AARCH_HOLDINGS%3A(\d+)", links[i])
                if match:
                    record_id = f"archive:ARCH_HOLDINGS:{match.group(1)}"

            linked_records.append({
                "label": line,
                "record_id": record_id,
            })

        return linked_records

    def clean(self):
        """
        Méthode principale.
        Essaie d'abord l'export XML.
        Si cela échoue, utilise le HTML public.
        """
        html_text = self.request_html()

        if not self.record_id:
            self.find_record_id_from_html(html_text)

        try:
            xml_root = self.request_xml()
            xml_data = self.clean_from_xml(xml_root)

            # Si l'XML ne donne pas les champs principaux,
            # on revient au HTML, qui est plus lisible dans Flora.
            if not xml_data.get("title") or not xml_data.get("cote"):
                return self.clean_from_html(html_text)

            return xml_data

        except Exception:
            return self.clean_from_html(html_text)

    def clean_from_xml(self, xml_root):
        """
        Nettoie les métadonnées depuis le XML Flora.
        """
        data = {
            "site": None,
            "parent": None,
            "cote": None,
            "title": None,
            "date": None,
            "level": None,
            "abstract": None,
            "access": None,
            "linked_records": [],
            "record_id": self.record_id,
            "source": "xml",
        }

        xml_text = etree.tostring(xml_root, encoding="unicode")

        def find_text(pattern):
            match = re.search(pattern, xml_text, flags=re.DOTALL | re.IGNORECASE)
            if match:
                return re.sub(r"\s+", " ", match.group(1)).strip()
            return None

        data["cote"] = find_text(r"<[^>]*COTE[^>]*>(.*?)</[^>]+>")
        data["title"] = find_text(r"<[^>]*(?:INTITULE|TITLE|TITRE)[^>]*>(.*?)</[^>]+>")
        data["date"] = find_text(r"<[^>]*(?:DATE|ANNEE)[^>]*>(.*?)</[^>]+>")
        data["level"] = find_text(r"<[^>]*(?:NIVEAU|LEVEL)[^>]*>(.*?)</[^>]+>")
        data["abstract"] = find_text(r"<[^>]*(?:CONTENU|PRESENTATION|ABSTRACT|SCOPE)[^>]*>(.*?)</[^>]+>")
        data["access"] = find_text(r"<[^>]*(?:ACCES|ACCESS|STATUT)[^>]*>(.*?)</[^>]+>")

        return data

    def extract_dates(self, date_text):
        """Extrait les dates extrêmes sous forme {'from': ..., 'to': ...}."""
        if not date_text:
            return {
                "from": None,
                "to": None,
            }

        match = re.search(r"(\d{4})\D+(\d{4})", date_text)

        if not match:
            return {
                "from": date_text,
                "to": date_text,
            }

        return {
            "from": match.group(1),
            "to": match.group(2),
        }

    def extract_extent(self, abstract):
        """Extrait le nombre de volumes et de pages depuis le résumé."""
        if not abstract:
            return {
                "volumes": None,
                "pages": None,
            }

        match = re.search(
            r"(\d+)\s+volumes?.*?([\d']+)\s+pages?",
            abstract,
            flags=re.IGNORECASE
        )

        if not match:
            return {
                "volumes": None,
                "pages": None,
            }

        return {
            "volumes": int(match.group(1)),
            "pages": int(match.group(2).replace("'", "")),
        }

    def to_tei_metadata(self):
        """
        Convertit les données Flora dans la structure attendue
        pour la construction du teiHeader.
        """
        data = self.clean()

        return {
            "title": data.get("title"),

            "subtitle": "Souvenirs d'un pasteur de campagne jurassien au XVIIIe siècle",

            "author": {
                "name": "Théophile Rémy Frêne",
                "viaf": "https://viaf.org/viaf/24931371",
                "wikidata": "https://www.wikidata.org/wiki/Q119860",
            },

            "repository": "Office des archives de l'État de Neuchâtel",

            "pubPlace": "Neuchâtel",

            "fonds_id": data.get("cote"),

            "ark": self.ark_url,

            "level": data.get("level", "").lower() if data.get("level") else None,

            "fonds_dates": self.extract_dates(data.get("date")),

            "extent": self.extract_extent(data.get("abstract")),

            "access": data.get("access"),

            "abstract": data.get("abstract"),

            "linked_records": data.get("linked_records", []),

            "record_id": data.get("record_id"),

            "source": data.get("source"),
        }


if __name__ == "__main__":
    notice = Flora(
        ark_url="https://floraweb.ne.ch/flora/ark:/37964/001136"
    )

    data = notice.to_tei_metadata()

    for key, value in data.items():
        print(f"{key}: {value}")