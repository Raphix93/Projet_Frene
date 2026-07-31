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


## URI Wikidata facultatifs

Les annotations de type `Personne` et `Lieu` ouvrent une petite fenêtre
permettant d'ajouter une URI Wikidata. Le champ peut rester vide.

Exemples acceptés :

```text
Q123
https://www.wikidata.org/wiki/Q123
```

L'export JSON enregistre l'identifiant sous la forme :

```json
{
  "purpose": "linking",
  "value": "https://www.wikidata.org/wiki/Q123"
}
```

L'empreinte SHA-256 reste calculée et enregistrée dans le JSON pour la
validation, mais elle n'est plus affichée dans l'interface.


## Fonctionnement du lien Wikidata dans le menu

L'annotation `Personne` ou `Lieu` est créée immédiatement, sans demander d'URI.

Pour ajouter ensuite un lien :

1. cliquer sur l'annotation existante ;
2. choisir `Ajouter une URI Wikidata` dans le menu contextuel ;
3. saisir un identifiant `Q…` ou une URI Wikidata complète.

Lorsque l'annotation possède déjà un lien, le bouton devient
`Modifier l’URI Wikidata`. Il se trouve juste au-dessus de
`Supprimer l’annotation`, comme dans le prototype initial.

Vider le champ puis enregistrer supprime le lien Wikidata sans supprimer
l'annotation.
