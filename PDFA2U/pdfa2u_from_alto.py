#!/usr/bin/env python3
"""
Génération d'un PDF/A-2u à partir d'images et de fichiers ALTO.

Usage local :
    python scripts/pdfa2u_from_alto.py --data data/Frêne_volume_1 --validate

Par défaut, le script lit les JPEG dérivés dans :
    <data>/exports/jpg

Usage GitHub Actions :
    python scripts/pdfa2u_from_alto.py \
      --data data/Frêne_volume_1 \
      --font fonts/Noto_Serif/static/NotoSerif-Regular.ttf \
      --icc data/PROFIL_ICC/sRGB.icm \
      --verapdf verapdf \
      --validate
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from fontTools.ttLib import TTFont as FontToolsTTFont
from lxml import etree
from PIL import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

import pikepdf
from pikepdf import Array, Dictionary, Name, Stream

NS_ALTO = {"alto": "http://www.loc.gov/standards/alto/ns-v4#"}
NOM_POLICE = "NotoSerifPDF"


def analyser_arguments() -> argparse.Namespace:
    """Analyse les paramètres de la ligne de commande."""
    parseur = argparse.ArgumentParser(
        description="Produit un PDF/A-2u à partir d'images et de transcriptions ALTO."
    )
    parseur.add_argument("--data", required=True, type=Path, help="Dossier du volume, ex. data/Frêne_volume_1")
    parseur.add_argument("--images", type=Path, help="Dossier des JPEG. Par défaut : <data>/exports/jpg")
    parseur.add_argument("--alto", type=Path, help="Dossier des ALTO. Par défaut : <data>")
    parseur.add_argument("--out", type=Path, help="Dossier de sortie. Par défaut : <data>/exports/pdf")
    parseur.add_argument("--font", type=Path, default=Path("fonts/Noto_Serif/static/NotoSerif-Regular.ttf"))
    parseur.add_argument("--icc", type=Path, default=Path("/usr/share/color/icc/colord/sRGB.icc"))
    parseur.add_argument("--dpi", type=int, default=300)
    parseur.add_argument("--verapdf", default="verapdf", help="Commande veraPDF ou chemin vers l'exécutable")
    parseur.add_argument("--validate", action="store_true", help="Valide le PDF final avec veraPDF")
    parseur.add_argument("--title", default="Journal du pasteur Théophile Frêne")
    parseur.add_argument("--author", default="Raphaël Rollinet")
    parseur.add_argument("--subject", default="PDF/A-2u généré à partir d'images et de transcriptions ALTO")
    parseur.add_argument("--keywords", default="Frêne; ALTO; HTR; PDF/A-2u")
    return parseur.parse_args()


def verifier_fichier(chemin: Path, libelle: str) -> None:
    """Vérifie qu'un fichier ou dossier existe."""
    if not chemin.exists():
        raise FileNotFoundError(f"{libelle} introuvable : {chemin}")


def charger_tables_unicode(police_ttf: Path):
    """Charge les tables Unicode de la police TrueType."""
    police = FontToolsTTFont(str(police_ttf))
    tables = [table for table in police["cmap"].tables if table.isUnicode()]
    if not tables:
        raise RuntimeError(f"Aucune table Unicode trouvée dans la police : {police_ttf}")
    return tables


def caractere_present_dans_police(caractere: str, tables_unicode) -> bool:
    """Vérifie si la police contient un glyphe pour le caractère."""
    code = ord(caractere)
    return any(code in table.cmap for table in tables_unicode)


def nettoyer_texte_reportlab_pdfa(texte: str, tables_unicode) -> tuple[str, list[tuple[str, str]]]:
    """Supprime les caractères incompatibles avec PDF/A ou absents de la police."""
    texte_nettoye: list[str] = []
    suppressions: list[tuple[str, str]] = []

    for caractere in texte:
        code = ord(caractere)
        if code in (0x0000, 0xFEFF, 0xFFFE):
            suppressions.append((caractere, "interdit PDF/A"))
            continue
        if code < 32:
            suppressions.append((caractere, "caractère de contrôle"))
            continue
        if not caractere_present_dans_police(caractere, tables_unicode):
            suppressions.append((caractere, "absent de la police"))
            continue
        texte_nettoye.append(caractere)

    return "".join(texte_nettoye), suppressions


def nettoyer_texte_pdfa(texte: str) -> str:
    """Supprime les caractères Unicode strictement interdits par PDF/A-2u."""
    return "".join(c for c in texte if ord(c) not in (0x0000, 0xFEFF, 0xFFFE))


def lire_alto(fichier_alto: Path):
    """Lit un fichier ALTO XML."""
    return etree.parse(str(fichier_alto))


def extraire_dimensions_page(racine) -> tuple[float, float]:
    """Extrait les dimensions de la page ALTO."""
    page = racine.find(".//alto:Page", namespaces=NS_ALTO)
    if page is None:
        raise ValueError("Aucune balise <Page> trouvée dans l'ALTO.")
    return float(page.get("WIDTH")), float(page.get("HEIGHT"))


def extraire_lignes_alto(racine) -> list[list[dict[str, float | str]]]:
    """Extrait les mots ALTO avec leurs coordonnées."""
    lignes = []
    for ligne in racine.findall(".//alto:TextLine", namespaces=NS_ALTO):
        mots = []
        for string in ligne.findall(".//alto:String", namespaces=NS_ALTO):
            contenu = nettoyer_texte_pdfa(string.get("CONTENT", ""))
            if not contenu.strip():
                continue
            mots.append({
                "texte": contenu,
                "x": float(string.get("HPOS", 0)),
                "y": float(string.get("VPOS", 0)),
                "w": float(string.get("WIDTH", 0)),
                "h": float(string.get("HEIGHT", 0)),
            })
        if mots:
            lignes.append(mots)
    return lignes


def trouver_paires_images_alto(dossier_images: Path, dossier_alto: Path) -> list[tuple[Path, Path]]:
    """Associe les images aux ALTO portant le même nom de base."""
    extensions = {".jpg", ".jpeg"}
    images = sorted(
        p for p in dossier_images.iterdir()
        if p.is_file() and p.suffix.lower() in extensions
    )
    paires = []
    fichiers_manquants = []

    for image in images:
        alto = dossier_alto / f"{image.stem}.xml"
        if alto.exists():
            paires.append((image, alto))
        else:
            fichiers_manquants.append(image.name)

    print(f"{len(paires)} paire(s) image/ALTO trouvée(s).")
    if fichiers_manquants:
        print(f"{len(fichiers_manquants)} image(s) sans ALTO.")
        for nom in fichiers_manquants[:20]:
            print("-", nom)
    return paires


def convertir_image_rgb_si_necessaire(image_path: Path) -> Image.Image:
    """Ouvre une image et la convertit en RGB si nécessaire."""
    image = Image.open(image_path)
    if image.mode != "RGB":
        image = image.convert("RGB")
    return image


def creer_pdf_avec_texte_invisible(
    paires: list[tuple[Path, Path]],
    fichier_pdf: Path,
    tables_unicode,
    titre: str,
    auteur: str,
    sujet: str,
    mots_cles: str,
    dpi: int,
) -> Path:
    """Crée un PDF image + texte invisible aligné sur les coordonnées ALTO."""
    fichier_pdf.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(fichier_pdf), pageCompression=1)
    c.setTitle(titre)
    c.setAuthor(auteur)
    c.setSubject(sujet)
    c.setKeywords(mots_cles)
    c.setCreator("scripts/pdfa2u_from_alto.py")

    suppressions_globales = []
    compteur_suppressions = Counter()

    for index, (image_path, alto_path) in enumerate(paires, start=1):
        image = convertir_image_rgb_si_necessaire(image_path)
        largeur_img_px, hauteur_img_px = image.size
        racine = lire_alto(alto_path)
        largeur_alto_px, hauteur_alto_px = extraire_dimensions_page(racine)
        lignes = extraire_lignes_alto(racine)

        largeur_page_pt = largeur_img_px / dpi * 72
        hauteur_page_pt = hauteur_img_px / dpi * 72
        facteur_x = largeur_page_pt / largeur_alto_px
        facteur_y = hauteur_page_pt / hauteur_alto_px

        c.setPageSize((largeur_page_pt, hauteur_page_pt))
        c.drawImage(ImageReader(image), 0, 0, width=largeur_page_pt, height=hauteur_page_pt, preserveAspectRatio=False, mask="auto")

        for ligne in lignes:
            mots_valides = []
            for mot in ligne:
                texte, suppressions = nettoyer_texte_reportlab_pdfa(str(mot["texte"]), tables_unicode)
                for caractere, raison in suppressions:
                    compteur_suppressions[(caractere, raison)] += 1
                if suppressions:
                    suppressions_globales.append((image_path.name, alto_path.name, repr(mot["texte"]), repr(texte)))
                if texte.strip():
                    mots_valides.append((mot, texte))

            if not mots_valides:
                continue

            texte_ligne = " ".join(texte for _, texte in mots_valides)
            texte_ligne, suppressions_ligne = nettoyer_texte_reportlab_pdfa(texte_ligne, tables_unicode)
            for caractere, raison in suppressions_ligne:
                compteur_suppressions[(caractere, raison)] += 1
            if not texte_ligne.strip():
                continue

            premier_mot = mots_valides[0][0]
            x_pt = float(premier_mot["x"]) * facteur_x
            y_pt = hauteur_page_pt - ((float(premier_mot["y"]) + float(premier_mot["h"])) * facteur_y)
            taille_police = max(3.0, float(premier_mot["h"]) * facteur_y * 0.80)

            text_obj = c.beginText()
            text_obj.setTextRenderMode(3)
            text_obj.setFont(NOM_POLICE, taille_police)
            text_obj.setTextOrigin(x_pt, y_pt)
            text_obj.textLine(texte_ligne)
            c.drawText(text_obj)

        c.showPage()
        print(f"Page {index} créée : {image_path.name}")

    c.save()

    if compteur_suppressions:
        print("\nCaractères supprimés pour compatibilité PDF/A et police :")
        for (caractere, raison), frequence in compteur_suppressions.most_common():
            print(f"- {repr(caractere)} {hex(ord(caractere))} — {raison} : {frequence}")
    else:
        print("\nAucun caractère incompatible détecté dans le texte ALTO.")

    print("PDF intermédiaire créé :", fichier_pdf)
    return fichier_pdf


def xml_escape(valeur: str) -> str:
    """Échappe les caractères XML usuels."""
    return valeur.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def ajouter_xmp_pdfa2u(pdf_path: Path, titre: str, auteur: str, sujet: str) -> Path:
    """Ajoute un paquet XMP minimal indiquant PDF/A-2u."""
    maintenant = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    xmp = f'''<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Python pikepdf">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description rdf:about="" xmlns:pdfaid="http://www.aiim.org/pdfa/ns/id/">
      <pdfaid:part>2</pdfaid:part>
      <pdfaid:conformance>U</pdfaid:conformance>
    </rdf:Description>
    <rdf:Description rdf:about="" xmlns:dc="http://purl.org/dc/elements/1.1/">
      <dc:title><rdf:Alt><rdf:li xml:lang="x-default">{xml_escape(titre)}</rdf:li></rdf:Alt></dc:title>
      <dc:creator><rdf:Seq><rdf:li>{xml_escape(auteur)}</rdf:li></rdf:Seq></dc:creator>
      <dc:description><rdf:Alt><rdf:li xml:lang="x-default">{xml_escape(sujet)}</rdf:li></rdf:Alt></dc:description>
    </rdf:Description>
    <rdf:Description rdf:about="" xmlns:xmp="http://ns.adobe.com/xap/1.0/">
      <xmp:CreatorTool>scripts/pdfa2u_from_alto.py</xmp:CreatorTool>
      <xmp:CreateDate>{maintenant}</xmp:CreateDate>
      <xmp:ModifyDate>{maintenant}</xmp:ModifyDate>
      <xmp:MetadataDate>{maintenant}</xmp:MetadataDate>
    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>'''

    with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
        pdf.Root.Metadata = Stream(pdf, xmp.encode("utf-8"))
        pdf.Root.Metadata.Type = Name.Metadata
        pdf.Root.Metadata.Subtype = Name.XML
        pdf.docinfo["/Title"] = titre
        pdf.docinfo["/Author"] = auteur
        pdf.docinfo["/Subject"] = sujet
        pdf.docinfo["/Creator"] = "scripts/pdfa2u_from_alto.py"
        pdf.save(pdf_path)
    return pdf_path


def ajouter_output_intent_rgb(pdf_path: Path, profil_icc: Path) -> Path:
    """Ajoute un OutputIntent sRGB au PDF."""
    icc_stream = None
    icc_bytes = profil_icc.read_bytes()
    with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
        icc_stream = pdf.make_indirect(Stream(pdf, icc_bytes, {"/N": 3}))
        output_intent = Dictionary({
            "/Type": Name.OutputIntent,
            "/S": Name.GTS_PDFA1,
            "/OutputConditionIdentifier": "sRGB IEC61966-2.1",
            "/Info": "sRGB IEC61966-2.1",
            "/DestOutputProfile": icc_stream,
        })
        pdf.Root["/OutputIntents"] = Array([pdf.make_indirect(output_intent)])
        with pdf.open_metadata(set_pikepdf_as_editor=False) as meta:
            meta["pdfaid:part"] = "2"
            meta["pdfaid:conformance"] = "U"
        pdf.save(pdf_path)
    return pdf_path


def valider_pdfa2u_verapdf(fichier_pdf: Path, verapdf: str, rapport_xml: Path) -> None:
    """Valide le PDF final avec veraPDF et écrit un rapport XML."""
    resultat_texte = subprocess.run(
        [verapdf, "--format", "text", "--flavour", "2u", str(fichier_pdf)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    print(resultat_texte.stdout)
    if resultat_texte.stderr:
        print(resultat_texte.stderr)

    resultat_xml = subprocess.run(
        [verapdf, "--format", "xml", "--flavour", "2u", str(fichier_pdf)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    rapport_xml.write_text(resultat_xml.stdout, encoding="utf-8")
    print("Rapport veraPDF créé :", rapport_xml)

    if resultat_texte.returncode != 0 or resultat_xml.returncode != 0:
        raise RuntimeError("Validation PDF/A-2u échouée. Voir le rapport veraPDF XML.")


def main() -> None:
    """Point d'entrée du script."""
    args = analyser_arguments()
    dossier_data = args.data
    dossier_images = args.images or dossier_data / "exports" / "jpg"
    dossier_alto = args.alto or dossier_data
    dossier_sortie = args.out or dossier_data / "exports" / "pdf"
    dossier_sortie.mkdir(parents=True, exist_ok=True)

    pdf_intermediaire = dossier_sortie / "document_image_texte_unicode.pdf"
    pdf_a2u = dossier_sortie / "document_pdfa2u.pdf"
    rapport_verapdf = dossier_sortie / "rapport_verapdf_pdfa2u.xml"

    verifier_fichier(dossier_images, "Dossier JPEG")
    verifier_fichier(dossier_alto, "Dossier ALTO")
    verifier_fichier(args.font, "Police Unicode")
    verifier_fichier(args.icc, "Profil ICC")

    pdfmetrics.registerFont(TTFont(NOM_POLICE, str(args.font)))
    tables_unicode = charger_tables_unicode(args.font)

    paires = trouver_paires_images_alto(dossier_images, dossier_alto)
    if not paires:
        raise RuntimeError("Aucune paire image/ALTO trouvée.")

    creer_pdf_avec_texte_invisible(
        paires=paires,
        fichier_pdf=pdf_intermediaire,
        tables_unicode=tables_unicode,
        titre=args.title,
        auteur=args.author,
        sujet=args.subject,
        mots_cles=args.keywords,
        dpi=args.dpi,
    )
    ajouter_xmp_pdfa2u(pdf_intermediaire, args.title, args.author, args.subject)
    shutil.copyfile(pdf_intermediaire, pdf_a2u)
    ajouter_output_intent_rgb(pdf_a2u, args.icc)
    print("PDF/A-2u final préparé :", pdf_a2u)

    if args.validate:
        valider_pdfa2u_verapdf(pdf_a2u, args.verapdf, rapport_verapdf)


if __name__ == "__main__":
    main()
