# Fichier TEI

Copier ici la TEI réelle utilisée par l'application :

```text
annotation-app/public/data/Frene_volume_1.xml
```

Depuis la racine de `Projet_Frene`, sous PowerShell :

```powershell
Copy-Item `
  "data/Frene_volume_1.xml" `
  "annotation-app/public/data/Frene_volume_1.xml" `
  -Force
```

Le fichier complet est chargé, mais seul `<text><body>` est rendu et annoté.
`<teiHeader>` et `<sourceDoc>` ne sont jamais affichés.
