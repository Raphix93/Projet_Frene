# annotation-app 2.0

Version simple et fonctionnelle du prototype d'annotation du Projet Frêne.

## Installation

1. Remplacer les fichiers de `annotation-app` par ceux de cette archive.
2. Conserver ou recréer `node_modules` avec :

```powershell
npm.cmd install
```

3. Copier la TEI réelle :

```powershell
Copy-Item `
  "..\data\Frene_volume_1.xml" `
  ".\public\data\Frene_volume_1.xml" `
  -Force
```

4. Lancer :

```powershell
npm.cmd run dev
```

## Principe

- la TEI complète est chargée ;
- `teiHeader` et `sourceDoc` restent dans le fichier source ;
- seul `text/body` est transformé en HTML standard et annoté ;
- le JSON exporté contient le SHA-256 du fichier TEI.

## Diagnostic

En cas d'erreur, ouvrir les outils de développement avec F12 puis consulter
l'onglet Console. Cette version affiche l'erreur Recogito réelle au lieu de
la masquer derrière un message générique.
