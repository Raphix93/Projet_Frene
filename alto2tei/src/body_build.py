# -----------------------------------------------------------
# Code original : Kelly Christensen
# Adaptation : Raphaël Rollinet
# Script Python pour construire le <body> d’un fichier TEI
# à partir du texte des zones principales issues d’un fichier ALTO.
# -----------------------------------------------------------

from lxml import etree


def body(root, data):
    """Construit la partie <text><body> du fichier TEI.

    Args:
        root: élément racine TEI auquel ajouter le <text>.
        data: liste d’objets représentant les lignes extraites de l’ALTO.
              Chaque ligne doit contenir notamment :
              - line.id
              - line.text
              - line.n
              - line.page_id
              - line.zone_id
              - line.zone_type
              - line.line_type
    """

    # Création de la structure textuelle principale du TEI
    text = etree.SubElement(root, "text")
    body = etree.SubElement(text, "body")
    div = etree.SubElement(body, "div")

    for line in data:
        # Préparation des attributs de la zone ALTO associée à la ligne
        zone_atts = {
            "corresp": f"#{line.zone_id}",
            "type": line.zone_type
        }

        # Création d’un saut de ligne TEI <lb/>
        # L’attribut @corresp pointe vers l’identifiant de la ligne ALTO/sourceDoc
        lb = etree.Element("lb", corresp=f"#{line.id}")
        lb.tail = f"{line.text}"

        # Si la ligne est la première de la page, on ajoute un saut de page <pb/>
        # @corresp pointe vers l’identifiant de la page dans le sourceDoc
        if int(line.n) == 1:
            pb = etree.Element("pb", corresp=f"#{line.page_id}")
            div.append(pb)

        # Si aucun élément n’a encore été ajouté au <div>,
        # on crée un point d’ancrage minimal pour éviter une erreur avec div[-1]
        if len(div) == 0:
            div.append(etree.Element("pb", corresp=f"#{line.page_id}"))

        # Dernier élément ajouté au <div>
        last_element = div[-1]

        # Cas des zones de type foliotage, réclame ou titre courant
        if line.zone_type in ["NumberingZone", "QuireMarksZone", "RunningTitleZone"]:
            # Ces éléments sont encodés en TEI avec <fw> : forme work / forme fixe
            fw = etree.Element("fw", zone_atts)
            last_element.addnext(fw)
            fw.append(lb)

        # Cas des notes marginales
        elif line.zone_type == "MarginTextZone":
            # Si l’élément précédent n’est pas déjà une note, on crée une nouvelle <note>
            if last_element.tag != "note":
                note = etree.Element("note", zone_atts)
                last_element.addnext(note)
                note.append(lb)
            else:
                # Sinon, on ajoute la ligne à la note existante
                last_element.append(lb)

        # Cas des zones principales du texte
        elif line.zone_type.startswith("Main"):
            # Si l’élément précédent n’est pas déjà un bloc textuel <ab>,
            # on crée un nouveau bloc anonyme
            if last_element.tag != "ab":
                ab = etree.Element("ab", zone_atts)
                last_element.addnext(ab)
                last_element = div[-1]

            # Cas des lignes mises en valeur : lettrines, titres, etc.
            if line.line_type in ["DropCapitalLine", "HeadingLine"]:
                enfants_ab = list(last_element)

                # Si aucun <hi> équivalent n’existe encore, on le crée
                if (
                    len(enfants_ab) == 0
                    or enfants_ab[-1].tag != "hi"
                    or enfants_ab[-1].get("rend") != line.line_type
                ):
                    hi = etree.Element("hi", rend=line.line_type)
                    last_element.append(hi)
                    hi.append(lb)

                # Si le dernier élément est déjà un <hi>, on y ajoute la ligne
                else:
                    enfants_ab[-1].append(lb)

            # Cas général : lignes ordinaires ou autres types de lignes
            else:
                last_element.append(lb)

    return root