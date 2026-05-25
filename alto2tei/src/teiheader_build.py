# -----------------------------------------------------------
# Script Python pour assembler le <teiHeader> d’un fichier TEI.
# -----------------------------------------------------------

from src.teiheader_default import DefaultTree
from src.teiheader_full import FullTree

def teiheader(
    metadata,
    document,
    root,
    count_pages,
    config,
    version,
    filepaths,
    segmonto_zones,
    segmonto_lines
):
    """Construit l’ensemble du <teiHeader>.

    Args:
        metadata (dict): métadonnées du document.
        document (str): nom du dossier contenant les fichiers ALTO du document.
        root: racine de l’arbre XML-TEI.
        count_pages (int): nombre de fichiers/pages ALTO.
        config (dict): configuration du projet.
        version (str): version de Kraken utilisée pour produire les ALTO.
        filepaths (list): liste des chemins vers les fichiers ALTO.
        segmonto_zones: taxonomie des zones SegmOnto, si déjà construite.
        segmonto_lines: taxonomie des lignes SegmOnto, si déjà construite.

    Returns:
        tuple: racine TEI mise à jour, taxonomie des zones SegmOnto,
        taxonomie des lignes SegmOnto.
    """

    # Étape 1 : générer la structure minimale/par défaut du <teiHeader>
    elements = DefaultTree(
        config,
        document,
        root,
        metadata,
        count_pages,
        version
    )

    elements.build()

    # Étape 2 : insérer les métadonnées disponibles dans les éléments pertinents
    # du <teiHeader>
    htree = FullTree(
        elements.children,
        metadata
    )

    # Ajout des informations d’auteur/responsabilité
    htree.author_data()

    # Ajout des informations bibliographiques et descriptives
    htree.bib_data()

    # Construction de la taxonomie SegmOnto à partir des fichiers ALTO
    segmonto_zones, segmonto_lines = htree.segmonto_taxonomy(
        filepaths
    )

    return root, segmonto_zones, segmonto_lines