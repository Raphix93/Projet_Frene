# Mise à jour immédiate d'annotation-app

Cette archive remplace uniquement les fichiers nécessaires pour charger
la véritable TEI. Elle conserve le prototype d'annotation existant
(`src/annotator.js` et `src/style.css`).

## Fichiers à copier

Depuis cette archive vers `Projet_Frene/annotation-app/` :

```text
public/config.json
public/data/README.md
src/main.js
src/tei-loader.js
src/document-state.js
src/annotations-io.js
src/tei-loader.css
```

## Copier la vraie TEI

Depuis la racine du dépôt, dans PowerShell :

```powershell
Copy-Item `
  "data/Frene_volume_1.xml" `
  "annotation-app/public/data/Frene_volume_1.xml" `
  -Force
```

Cette copie est volontaire pour obtenir rapidement un résultat visible
avec Vite. On pourra automatiser cette synchronisation plus tard dans
GitHub Actions.

## Lancer l'application

```powershell
cd "C:\Users\rroll\Documents\GitHub\Projet_Frene\annotation-app"
npm install
npm run dev
```

## Résultat attendu

- chargement du fichier TEI complet ;
- calcul de son SHA-256 ;
- affichage exclusif de `<text><body>` ;
- `<teiHeader>` et `<sourceDoc>` non affichés ;
- annotation du véritable texte ;
- export JSON version 2.0 avec :
  - fichier ;
  - portée `text/body` ;
  - SHA-256 de la TEI ;
  - nombre d'annotations ;
- refus d'importer un JSON lié à une autre version de la TEI.

## Important

Le fichier `src/annotator.js` existant n'est pas remplacé. Il conserve
les types déjà réalisés :

- Personne ;
- Lieu ;
- Date ;
- Normalisation ;
- Correction libre.
