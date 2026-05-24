# -----------------------------------------------------------
# Code original : Kelly Christensen
# Script Python pour convertir les données d’un fichier ALTO
# vers le <sourceDoc> d’un fichier TEI.
# -----------------------------------------------------------

from collections import defaultdict

from lxml import etree

from src.order_files import Files
from src.sourcedoc_attributes import Attributes
from src.sourcedoc_elements import SurfaceTree


# Namespace utilisé par les fichiers ALTO v4
NS = {'a': "http://www.loc.gov/standards/alto/ns-v4#"}


def labels(filepath):
    """Récupère les balises déclarées dans la section <Tags> du fichier ALTO.

    Args:
        filepath: chemin vers un fichier ALTO-XML.

    Returns:
        tags (dict): dictionnaire associant les identifiants de tags ALTO
        à leurs labels SegmOnto.

        Exemple :
            {
                "BT12": "MainZone",
                "LT8": "DefaultLine"
            }
    """

    # Lecture du fichier ALTO
    root = etree.parse(filepath).getroot()

    # Récupération de tous les <OtherTag>
    elements = [
        t.attrib
        for t in root.findall('.//a:OtherTag', namespaces=NS)
    ]

    # Association ID -> LABEL
    collect = defaultdict(dict)

    for d in elements:
        collect[d["ID"]] = d["LABEL"]

    tags = dict(collect)

    return tags


def sourcedoc(
    document_name,
    output_tei_root,
    filepath_list,
    tags,
    segmonto_zones,
    segmonto_lines,
    config
):
    """Construit le <sourceDoc> d’un fichier XML-TEI.

    Le <sourceDoc> rassemble les données spatiales et textuelles issues
    de plusieurs fichiers ALTO. Chaque fichier ALTO représente généralement
    une page ou une image du document.

    Args:
        document_name (str): nom du document ou du dossier documentaire.
        output_tei_root: racine du fichier XML-TEI.
        filepath_list (list): liste des chemins vers les fichiers ALTO.
        tags (dict): dictionnaire des tags ALTO/SegmOnto.
        segmonto_zones: labels SegmOnto des zones.
        segmonto_lines: labels SegmOnto des lignes.
        config (dict): configuration IIIF éventuelle.
    """

    # Tri des fichiers ALTO selon leur numéro
    ordered_files = Files(document_name, filepath_list).order_files()

    # Création de l’élément <sourceDoc>
    sourceDoc = etree.SubElement(output_tei_root, "sourceDoc")

    for file in ordered_files:

        # Récupération des labels SegmOnto du fichier ALTO courant
        tags = labels(file.filepath)

        # Compteurs utilisés pour numéroter les éléments créés dans la page
        blocks_on_page = 0
        lines_on_page = 0
        strings_on_page = 0
        glyphs_on_page = 0

        # Lecture du fichier ALTO courant
        input_alto_root = etree.parse(file.filepath).getroot()

        # Classes auxiliaires :
        # - Attributes extrait les attributs ALTO utiles
        # - SurfaceTree construit les éléments TEI correspondants
        attributes = Attributes(
            document_name,
            file.num,
            input_alto_root,
            tags,
            config
        )

        surface_tree = SurfaceTree(
            document_name,
            file.num,
            input_alto_root
        )

        # ---------------------------------------------------
        # SURFACE
        # ---------------------------------------------------
        # Pour chaque page ALTO, création d’un <surface> TEI.
        surface = surface_tree.surface(
            sourceDoc,
            attributes.surface()
        )

        # ---------------------------------------------------
        # TEXTBLOCK
        # ---------------------------------------------------
        # Chaque <TextBlock> ALTO devient une <zone> TEI.
        textblocks = attributes.zones(
            "PrintSpace",
            "TextBlock",
            segmonto_zones
        )

        for tb in textblocks:

            # On ne traite que les blocs ayant un identifiant ALTO
            if tb.id:
                blocks_on_page += 1

                textblock = surface_tree.zone1(
                    surface,
                    tb.attributes,
                    tb.id,
                    blocks_on_page
                )

            # ---------------------------------------------------
            # TEXTLINE
            # ---------------------------------------------------
            # Chaque <TextLine> dans un <TextBlock> devient une zone TEI.
            textlines = attributes.zones(
                f'TextBlock[@ID="{tb.id}"]',
                "TextLine",
                segmonto_lines
            )

            for tl in textlines:

                # On ne traite que les lignes ayant un identifiant ALTO
                if tl.id:
                    lines_on_page += 1

                    textline = surface_tree.zone2(
                        textblock,
                        tb.id,
                        tl.attributes,
                        tl.id,
                        lines_on_page
                    )

                    words = ""

                    # Récupération de l’élément <String> de la ligne,
                    # s’il existe.
                    string_element = input_alto_root.find(
                        f'.//a:TextLine[@ID="{tl.id}"]/a:String',
                        namespaces=NS
                    )

                    # Si aucune balise <String> n’est trouvée,
                    # on ignore la ligne pour éviter une erreur.
                    if string_element is None:
                        continue

                    content = string_element.get("CONTENT")

                    # ---------------------------------------------------
                    # CAS 1 : la ligne contient directement tout le texte
                    # dans String[@CONTENT], sans glyphes enfants.
                    # ---------------------------------------------------
                    if (
                        content is not None
                        and len(list(string_element)) == 0
                    ):
                        # Création d’un élément TEI <line>
                        surface_tree.line(
                            textline,
                            tb.id,
                            tl.id,
                            lines_on_page,
                            None
                        )

                    # ---------------------------------------------------
                    # CAS 2 : le texte est détaillé au niveau des glyphes.
                    # Les caractères sont donc reconstruits depuis les
                    # enfants <Glyph>.
                    # ---------------------------------------------------
                    elif (
                        content is not None
                        and content != ""
                        and len(list(string_element)) > 0
                    ):

                        # Enfants de la ligne : <String> et éventuellement <SP>
                        textline_element = input_alto_root.find(
                            f'.//a:TextLine[@ID="{tl.id}"]',
                            namespaces=NS
                        )

                        textline_children = list(textline_element)

                        for textline_child in textline_children:

                            child_name = etree.QName(textline_child).localname

                            # -------------------------------
                            # Cas d’un espace <SP>
                            # -------------------------------
                            if child_name == "SP":
                                textline_child_id = textline_child.attrib["ID"]

                                space_data = attributes.zones(
                                    f'TextLine[@ID="{tl.id}"]',
                                    f'SP[@ID="{textline_child_id}"]',
                                    None
                                )[0]

                                strings_on_page += 1

                                surface_tree.zone3(
                                    textline,
                                    tb.id,
                                    tl.id,
                                    space_data.attributes,
                                    space_data.id,
                                    strings_on_page
                                )

                            # -------------------------------
                            # Cas d’un segment textuel <String>
                            # -------------------------------
                            elif child_name == "String":
                                textline_child_id = textline_child.attrib["ID"]

                                string_data = attributes.zones(
                                    f'TextLine[@ID="{tl.id}"]',
                                    f'String[@ID="{textline_child_id}"]',
                                    None
                                )[0]

                                strings_on_page += 1

                                string = surface_tree.zone3(
                                    textline,
                                    tb.id,
                                    tl.id,
                                    string_data.attributes,
                                    string_data.id,
                                    strings_on_page
                                )

                                # Récupération des glyphes du segment
                                string_children = input_alto_root.findall(
                                    f'.//a:String[@ID="{textline_child_id}"]/a:Glyph',
                                    namespaces=NS
                                )

                                # Reconstruction du mot depuis les glyphes
                                glyph_text = "".join(
                                    [
                                        g.get("CONTENT", "")
                                        for g in string_children
                                    ]
                                )

                                if words == "":
                                    words = glyph_text
                                else:
                                    words = words + " " + glyph_text

                                # Chaque <Glyph> devient une zone TEI
                                for glyph_child in string_children:
                                    glyph_id = glyph_child.attrib["ID"]

                                    glyph_data = attributes.zones(
                                        f'String[@ID="{textline_child_id}"]',
                                        f'Glyph[@ID="{glyph_id}"]',
                                        None
                                    )[0]

                                    glyphs_on_page += 1

                                    glyph = surface_tree.zone4(
                                        string,
                                        tb.id,
                                        tl.id,
                                        textline_child_id,
                                        glyph_data.attributes,
                                        glyph_id,
                                        glyphs_on_page
                                    )

                                    # Ajout du caractère dans la zone du glyphe
                                    surface_tree.car(
                                        glyph,
                                        glyph_child,
                                        tb.id,
                                        tl.id,
                                        textline_child_id,
                                        glyph_id,
                                        glyphs_on_page
                                    )

                        # Création de l’élément <line> avec le texte reconstruit
                        surface_tree.line(
                            textline,
                            tb.id,
                            tl.id,
                            lines_on_page,
                            words
                        )

    return output_tei_root