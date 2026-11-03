# N3XV5 N0v4 HUD — Architecture officielle

## Deux modes de distribution
1. **Portable host** : NOVA fonctionne sur Linux Mint/Ubuntu existant, sans
   installation en ligne de bibliothèques applicatives ; runtime Qt/Python
   embarqué et dossier commun `Dependancy`.
2. **N3XV5 Live ISO** : ISO hybride USB/VM amorçable contenant **son propre
   système Linux minimal**. Une application Qt ne peut pas fonctionner sans
   noyau, pilotes, libc, pile réseau, support graphique et gestion des processus.

La première cible ISO est **Debian Trixie x86_64 + X11 minimal + LightDM**.
XFCE est ramené à ses composants essentiels : session légère, window manager
compositeur, paramètres, terminal de secours. Le launcher de session exécute
NOVA Control Center directement. Pas de navigateur web généraliste ni de suite
bureautique installés par défaut.

## Ce qui doit se trouver dans l'image
- Noyau Linux, init, udev et pilotes noyau standards (réseau, USB, stockage,
  graphiques, clavier/souris).
- X11 / Qt / rendu GPU (rendu logiciel de secours selon VM).
- Gestion réseau : NetworkManager (Ethernet, Wi-Fi selon les firmwares
  disponibles), DNS, TLS CA, iproute2 et client OpenSSH.
- TCP/IP, HTTPS, SMTP, FTP/FTPS, MySQL, SQLite sont des **protocoles** :
  leurs adaptateurs applicatifs sont livrés par NOVA, non par des démons
  permanents à démarrer dans le système.
- Services minimaux pour authentification/permissions, USB, disque et audio.
- `/opt/n3xv5/Dependancy` : bibliothèque commune fournie au build.
- Paquets NOVA des applications dans l'ISO ; aucune installation réseau
  au premier démarrage.
- Terminal de secours fonctionnel si NOVA ne démarre pas.
- Profil de suite **créé à la première session, jamais livré avec l'ISO**.

## Profil universel de suite
Namespace officiel `n3xv5-n0v4-hud`.
Chemin : `~/.config/n3xv5-n0v4-hud/profiles/<UID>/active.json`.
Registre des connexions : `profiles/<UID>/connections-v2.json`.
Un même profil réunit un ID stable, un nom, le compte OS actuel, les
autorisations d'applications et les IDs des connexions. Le profil est reconnu
par toutes les apps de la suite via un contrat partagé ; ce n'est pas une
authentification root. Les clés privées, mots de passe et tokens ne sont
jamais inclus dans les exports de profil.

L'ancien registre `~/.config/nova-control-center/connections-v2.json` est
conservé et importé s'il correspond au compte actif et est privé.

Pour déplacer un profil vers un autre PC, exporter **seulement les métadonnées
non sensibles**, importer et réattribuer le compte OS et ses clés de confiance
avec consentement. Les profils Linux de UID différents ne doivent pas
partager directement leurs identifiants.

## Exemples de build
Préparer dans un dossier vide sur un hôte Linux disposant du .deb compilé :

```bash
python3 deploy/live_iso/build_live_iso.py stage \
  --dest /tmp/n3xv5-live \
  --deb ./NOVA-Control-Center_2.4.1-dev0_amd64.deb \
  --dependancy ./Dependancy
```

Compiler sur une VM Debian dédiée avec `live-build` et les dépôts Debian
accessibles pendant le **build uniquement** :

```bash
sudo apt-get install live-build
sudo python3 deploy/live_iso/build_live_iso.py build --dest /tmp/n3xv5-live
```

La sortie sera une ISO hybride créée par live-build. **Aucune ISO n'est
présentement publiée** et ce constructeur est une base expérimentale :
un test de boot UEFI et BIOS, une détection des périphériques et des
vérifications réseau doivent précéder toute diffusion.

## Contraintes à anticiper
- BIOS et UEFI, Secure Boot, tables GPT/MBR, GRUB/isolinux, outils USB.
- Build reproductible : snapshot des dépôts, versions verrouillées, manifestes,
  SHA256 et signatures, SBOM, licences tierces.
- glibc / kernels / GPU / pilotes Wi-Fi : compatibilité entre hôtes et VM.
- ISO Live généralement non persistante : proposer plus tard persistance USB
  chiffrée ou volume virtuel dédié pour sessions, logs SQLite, fichiers.
- Pas de clés API/SSH ni identifiants Live dans l'image ISO.
- Les firmwares Wi-Fi/Nvidia/AMD et Bluetooth doivent être gérés selon les
  matériels, les licences et les exigences de l'utilisateur.
- Rendu 1280×800, HiDPI, VMs sans accélération 3D, X11, Wayland éventuel.
- Installation offline signifie **pas de téléchargement à l'exécution**.
  La construction de l'ISO peut télécharger les paquets de base sur le PC
  de compilation, ou utiliser un miroir local hors ligne.
- Mise à jour du système Linux séparée des mises à jour de la suite ; ne pas
  remplacer aveuglément le noyau ou un driver.
- Isolation par processus, permissions minimales, authentification du compte
  OS et récupération en cas de crash graphique.

## Ordre d'intégration
1. Profil partagé entre apps et registre de connexions migré.
2. Constructor ISO dans une VM de build (aucun `sudo` automatique dans NOVA).
3. Boot-test QEMU / VirtualBox avec réseau et souris, écran 1280x800.
4. Persistance du profil + des logs, rollback et image de restauration.
5. Version ISO finale lorsque toutes les applications ont des binaires figés.
