# Réintégration des annotations dans la TEI — Projet Frêne

Ce module lit :

- la TEI source : `data/Frene_volume_1/exports/TEI/Frene_volume_1.xml` ;
- le JSON exporté par Annotation App dans :
  `data/Frene_volume_1/exports/Annotation/`.

Il produit :

- `data/Frene_volume_1/exports/TEI/Frene_volume_1_annotated.xml` ;
- `data/Frene_volume_1/exports/Annotation/Frene_volume_1.integration-report.json`.

Seul le contenu de `<text><body>` est enrichi. Le `<teiHeader>` et le
`<sourceDoc>` sont conservés, à l'exception d'une entrée de provenance ajoutée
au `teiHeader`.

## Correspondance JSON → TEI

| Annotation | Sortie TEI |
|---|---|
| `person` | `<persName>` |
| `place` | `<placeName>` |
| `date` | `<date>` |
| `normalization` | `<choice><orig>…</orig><reg>…</reg></choice>` |
| `correction` | remplacement direct du texte |
| URI Wikidata | attribut `ref` de `<persName>` ou `<placeName>` |

Les éléments de mise en page, notamment `<lb/>`, sont conservés. Une entité qui
traverse un saut de ligne peut donc contenir un `<lb/>`.

## Installation dans le dépôt

Copier :

```text
tei-annotation/
.github/workflows/tei-annotation.yml
```

à la racine du dépôt `Projet_Frene`.

## Exécution locale

Depuis la racine du dépôt :

```bash
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
# .venv\Scripts\Activate.ps1    # Windows PowerShell
pip install -r tei-annotation/requirements.txt

python tei-annotation/run.py \
  --tei data/Frene_volume_1/exports/TEI/Frene_volume_1.xml \
  --annotations data/Frene_volume_1/exports/Annotation/Frene_volume_1.annotations.json \
  --output data/Frene_volume_1/exports/TEI/Frene_volume_1_annotated.xml \
  --report data/Frene_volume_1/exports/Annotation/Frene_volume_1.integration-report.json \
  --fail-on-unmatched
```

Sous PowerShell, remplacer les `\` de continuation par des accents graves
(backticks) ou placer la commande sur une seule ligne.

## Sécurité de l'appariement

Le SHA-256 contenu dans le JSON doit correspondre à celui de la TEI. Les
positions `start/end` servent de guide, mais chaque annotation est validée avec
son texte `exact`. Cela tolère les différences de séparateurs introduites par
le rendu HTML tout en évitant une injection au mauvais endroit.

Le workflow utilise le fichier `Frene_volume_1.annotations.json` placé dans le
dossier Annotation. Il échoue si une annotation est introuvable, traverse deux
éléments `<ab>` ou chevauche une autre annotation.
