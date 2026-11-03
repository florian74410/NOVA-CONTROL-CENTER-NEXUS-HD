# NOVA SUITE — Dependancy / Shared Offline Library

Ce dossier s'appelle volontairement **Dependancy** pour respecter le nom choisi
par le projet. Il sera unique à la racine de la suite NOVA et partagé par
les applications. Aucun téléchargement automatique ne doit se produire durant
leur installation ou leur premier lancement.

## Les fichiers exacts à ajouter pour NOVA CONTROL CENTER 2.4.1-dev0

Système cible du premier build : **Linux x86_64 (Mint/Ubuntu)**.
Runtime Python du build : **CPython 3.11**. Le paquet PyInstaller existant
contient déjà le runtime Python et les composants Qt utilisés.

Dans `Common/Python/wheels/`, placer les wheels Linux x86_64 appropriées :
- `PySide6==6.8.3` (meta-package)
- `PySide6_Essentials==6.8.3` (QtCore, QtGui, QtWidgets…)
- `PySide6_Addons==6.8.3` (dont QtSvg)
- `shiboken6==6.8.3` (liaison Python/Qt)

Dans `Apps/NOVA-Control-Center/wheels/`, placer :
- `nova_control_center-2.4.1.dev0-py3-none-any.whl`
  (produit par notre build GitHub).

Pour produire **hors ligne** un nouveau binaire portable à partir des sources,
placer aussi dans `Build/Linux-x86_64/wheels/` :
- `PyInstaller==6.16.0` (version d'outil proposée à figer pour les builds suivants ;
  la compatibilité reste à valider)
- `altgraph`, `packaging`, `pyinstaller-hooks-contrib` : versions
  exactes à fixer après résolution dans le build de référence.
- `setuptools`, `wheel`, `build` : outils de compilation uniquement,
  pas nécessaires à l'exécution de la version portable existante.

**Remarque** : les noms concrets des fichiers .whl portent également des tags
Python/ABI/plateforme (ex. `cp39-abi3-manylinux_2_28_x86_64`).
Ne renomme pas les wheels ; télécharge les versions ci-dessus et conserve
leurs noms originaux. Évite les versions Windows/Mac ou ARM64 dans ce dossier
Linux. Les fichiers .whl seuls ne rendent PAS une application autonome :
l'exécutable final doit empaqueter son runtime et ses bibliothèques natives.

## Autres protocoles et futures applications

NOVA Core utilise actuellement `sqlite3`, `ssl`, `ftplib`, `smtplib`,
`socket`, `subprocess`, `urllib` et `json` de la bibliothèque standard
Python : **aucun wheel supplémentaire pour ces modules**.

Les connecteurs réseau **MySQL, FTP/SFTP avancé, et les applications futures**
nécessiteront d'autres wheels lorsqu'ils seront réellement intégrés :
aucune version ne doit être devinée avant que l'adaptateur soit sélectionné.
Le module GitHub est encore à développer ; aucune dépendance Github particulière
n'est requise actuellement.

Les identifiants stockés dans `ssh-agent` et le trousseau Linux ne sont
PAS des dépendances à placer ici.

## Organisation

```text
Dependancy/
├── README.md
├── catalog.json
├── Common/
│   └── Python/wheels/              # Wheels réutilisables par toutes les applications
├── Apps/
│   └── NOVA-Control-Center/wheels/  # Wheels spécifiques à NOVA
├── Build/
│   └── Linux-x86_64/wheels/         # Outils de compilation : facultatifs
├── Runtime/
│   └── Linux-x86_64/               # Bibliothèques natives vérifiées, si nécessaires
└── Checksums/
    └── SHA256SUMS.txt               # Empreintes après apport des fichiers
```

## Fonctionnement du futur Downloader

Chaque application embarque sa liste de dépendances verrouillées avec leurs
hashes SHA-256. Le Downloader vérifie le catalogue puis recherche dans
`Dependancy/Common` les artefacts déjà présents :
- déjà présent ET hash conforme : réutiliser, sans téléchargement ;
- absent : importer seulement le fichier livré par l'application ;
- même nom mais hash différent : ne jamais écraser silencieusement ;
- versions incompatibles : créer un environnement séparé pour chaque app
  et ne mutualiser que le stockage des artefacts.

Ne partage **pas** un même environnement Python pour toutes les applications :
cela provoquerait des conflits ABI, notamment pour Qt/Shiboken.

## Compatibilité portable

Nous visons **aucune dépendance applicative à télécharger** sur Linux :
un dossier exécutable contenant Python, Qt, plugins Qt et bibliothèques requises.
Le système doit toutefois fournir les composants bas niveau (noyau, glibc
compatible, pilotes graphiques, serveur X11/Wayland, etc.). Un même paquet
Linux ne fonctionne pas automatiquement sur Windows ou macOS.

**À faire après ajout des dépendances** : calculer les SHA-256 pour les fichiers
présents. La liste initiale SHA256SUMS.txt est volontairement vide.
Ne jamais interpréter une archive copiée comme fiable sans vérifier sa source.
