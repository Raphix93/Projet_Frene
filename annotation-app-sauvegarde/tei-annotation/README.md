# Projet Frêne — moteur d’enrichissement TEI

Version initiale `0.4.0`.

Cette première version pose l’architecture du moteur indépendant de l’interface web.

## Fonctionnalités présentes

- lecture d’une TEI avec `lxml` ;
- lecture d’un export JSON contenant soit une liste brute d’annotations, soit un manifeste ;
- conversion des annotations Recogito en objets Python ;
- reconnaissance des types :
  - `person`
  - `place`
  - `date`
  - `normalization`
  - `correction`
- lecture des URI Wikidata ;
- lecture des textes de normalisation et de correction ;
- validation structurelle de base ;
- vérification facultative du SHA-256 du texte ;
- génération d’un rapport JSON ;
- interface en ligne de commande.

L’injection dans le corps de la TEI et la création des listes d’autorités seront ajoutées dans les versions suivantes.

## Installation

Depuis la racine du dépôt `Projet_Frene` :

```powershell
python -m pip install -r annotation_engine_requirements.txt
```

Copier ensuite le dossier :

```text
alto2tei/annotation_engine/
```

dans le dossier `alto2tei/` du projet.

## Utilisation

```powershell
python -m alto2tei.annotation_engine `
  --tei data/Frene_volume_1.xml `
  --annotations annotations/Frene_volume_1.annotations.json `
  --report exports/annotations/Frene_volume_1.validation.json
```

Pour activer la vérification du hash déclaré dans le manifeste :

```powershell
python -m alto2tei.annotation_engine `
  --tei data/Frene_volume_1.xml `
  --annotations annotations/Frene_volume_1.annotations.json `
  --report exports/annotations/Frene_volume_1.validation.json `
  --verify-hash
```

## Format de manifeste recommandé

```json
{
  "format": "projet-frene-annotations",
  "version": "1.0",
  "project": "Projet Frêne",
  "document": "Frene_volume_1",
  "source": {
    "tei": "Frene_volume_1.xml",
    "sha256": "..."
  },
  "annotations": []
}
```
