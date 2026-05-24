# -----------------------------------------------------------
# Code original : Kelly Christensen
# Classe Python pour construire les éléments contenus dans le
# <sourceDoc> et y mapper les données issues des fichiers ALTO.
# -----------------------------------------------------------

from lxml import etree
import re


# Namespace utilisé par les fichiers ALTO v4
NS = {'a': "http://www.loc.gov/standards/alto/ns-v4#"}


class SurfaceTree:
    """Construit un élément <surface> et ses descendants pour une page
    (un fichier ALTO) d’un document.
    """

    def __init__(self, doc, folio, alto_root):
        self.doc = doc
        self.folio = folio
        self.root = alto_root

    def surface(self, surface_group, page_attributes):
        """Construit le <surface> TEI correspondant à une page ALTO.

        Args:
            surface_group: élément parent (<sourceDoc>).
            page_attributes (dict): attributs du <surface>.

        Returns:
            surface: élément TEI <surface>.
        """

        surface = etree.SubElement(
            surface_group,
            "surface",
            page_attributes
        )

        # Création de l’élément <graphic>.
        # L’URL Gallica originale a été supprimée.
        graphic_url = f"./Images/Image{self.folio:05d}.tif"

        etree.SubElement(
            surface,
            "graphic",
            url=graphic_url
        )

        return surface

    def zone1(
        self,
        surface,
        attributes,
        block_id,
        blocks_on_page
    ):
        """Construit le premier niveau de <zone>
        correspondant à un <TextBlock> ALTO.
        """

        xml_id = {
            "{http://www.w3.org/XML/1998/namespace}id":
            f"f{self.folio}-{block_id}-blockCount{blocks_on_page}"
        }

        zone = etree.SubElement(
            surface,
            "zone",
            xml_id
        )

        for k, v in attributes.items():
            zone.attrib[k] = v

        return zone

    def zone2(
        self,
        textblock,
        block_parent,
        attributes,
        line_id,
        lines_on_page
    ):
        """Construit le deuxième niveau de <zone>
        correspondant à une ligne ALTO <TextLine>.
        """

        zone_id = {
            "{http://www.w3.org/XML/1998/namespace}id":
            f"f{self.folio}-{block_parent}-{line_id}"
            f"-lineCount{lines_on_page}"
        }

        zone = etree.SubElement(
            textblock,
            "zone",
            zone_id
        )

        for k, v in attributes.items():
            zone.attrib[k] = v

        # Construction de la ligne de base (baseline)
        path_id = {
            "{http://www.w3.org/XML/1998/namespace}id":
            f"f{self.folio}-{block_parent}-{line_id}"
            f"-lineCount{lines_on_page}-baseline"
        }

        baseline = etree.SubElement(
            zone,
            "path",
            path_id
        )

        line = self.root.find(
            f'.//a:TextLine[@ID="{line_id}"]',
            namespaces=NS
        )

        if line is not None and line.get("BASELINE"):

            b = line.get("BASELINE")

            baseline.attrib["points"] = " ".join(
                [
                    re.sub(r"\s", ",", x)
                    for x in re.findall(
                        r"(\d+ \d+)",
                        b
                    )
                ]
            )

        return zone

    def line(
        self,
        textline,
        block_parent,
        line_parent,
        lines_on_page,
        extracted_words
    ):
        """Construit un élément <line> TEI."""

        xml_id = {
            "{http://www.w3.org/XML/1998/namespace}id":
            f"f{self.folio}-{block_parent}-{line_parent}"
            f"-lineCount{lines_on_page}-text"
        }

        line = etree.SubElement(
            textline,
            "line",
            xml_id
        )

        line.attrib["n"] = str(lines_on_page)

        if extracted_words:
            line.text = extracted_words

        else:
            string_element = self.root.find(
                f'.//a:TextLine[@ID="{line_parent}"]/a:String',
                namespaces=NS
            )

            if string_element is not None:
                line.text = string_element.get(
                    "CONTENT",
                    ""
                )

        return line

    def zone3(
        self,
        textline,
        block_parent,
        line_parent,
        attributes,
        seg_id,
        strings_on_page
    ):
        """Construit un troisième niveau de <zone>
        correspondant à un segment (<String>) ALTO.
        """

        xml_id = {
            "{http://www.w3.org/XML/1998/namespace}id":
            f"f{self.folio}-{block_parent}-{line_parent}"
            f"-{seg_id}-segCount{strings_on_page}"
        }

        zone = etree.SubElement(
            textline,
            "zone",
            xml_id
        )

        for k, v in attributes.items():
            zone.attrib[k] = v

        return zone

    def zone4(
        self,
        string,
        block_parent,
        line_parent,
        seg_parent,
        attributes,
        glyph_id,
        glyphs_on_page
    ):
        """Construit une zone correspondant à un glyphe."""

        xml_id = {
            "{http://www.w3.org/XML/1998/namespace}id":
            f"f{self.folio}-{block_parent}-{line_parent}"
            f"-{seg_parent}-{glyph_id}"
            f"-glyphCount{glyphs_on_page}"
        }

        zone = etree.SubElement(
            string,
            "zone",
            xml_id
        )

        for k, v in attributes.items():
            zone.attrib[k] = v

        return zone

    def car(
        self,
        zone,
        glyph,
        block_parent,
        line_parent,
        seg_parent,
        glyph_id,
        glyphs_on_page
    ):
        """Construit un caractère TEI <c>
        correspondant à un glyphe ALTO.
        """

        xml_id = {
            "{http://www.w3.org/XML/1998/namespace}id":
            f"f{self.folio}-{block_parent}-{line_parent}"
            f"-{seg_parent}-{glyph_id}"
            f"-glyphCount{glyphs_on_page}-text"
        }

        car = etree.SubElement(
            zone,
            "c",
            xml_id
        )

        car.text = glyph.attrib["CONTENT"]

        return car
