# N3XV5 NETTRACE CLI — Diagnostic client ↔ VPS

Application périphérique de la suite officielle **N3XV5 N0v4 HUD**, version **0.1.0**.
Le CLI fonctionne seul ou, après installation native et autorisation du HUB,
peut utiliser le canal privé IPC v1 pour demander son profil et la liste
**non sensible** des connexions.

## Pourquoi cet outil ?

En complément de l'onglet Réseau de Firefox, NetTrace permet de savoir
**où** une requête se dégrade entre un client, son DNS, le réseau, TLS,
un proxy (Caddy/Nginx), l'application VPS et son upstream.

Architecture des composants :

```text
[CLIENT Linux / Firefox / HUB]
       |  1. HAR export ou NetTrace CLI
       v
   DNS -- TCP -- TLS -- HTTP(S)
       |  X-Request-ID: n3xv5-...
       v
 [Reverse Proxy Caddy/Nginx]
       |  request_id dans log JSONL
       v
 [VPS / API / services IA-TB]
       |
       +-- erreurs 401/403 : session/permissions
       +-- erreurs 502/503/504 : backend, socket, timeout
       +-- lenteurs : DNS, TCP, TLS, TTFB, serveur
```

## Framework retenu

- **Python 3.10+ standard library** (`argparse`, `socket`, `ssl`,
  `http.client`, `json`, `subprocess`) : pas de module pip à installer.
- **curl** optionnel et recommandé : mesures DNS, connexion TCP,
  TLS, premier octet (TTFB), total, HTTP/2 et headers. Si curl n'est pas
  installé, `--engine auto` passe au moteur HTTP/1.1 Python intégré.
- **Firefox HAR 1.2** : import local, synthèse des erreurs et phases
  blocked/dns/connect/ssl/send/wait/receive. Corps et en-têtes privés ignorés.
- **VPS JSONL** : rapprochement par `X-Request-ID`, sans SSH automatique
  ni exigence de donner des privilèges au CLI.
- **HUB IPC v1** : `PeripheralClient` dans `n3xv5_core.ipc`; autorisations
  `profile.read` / `connections.read` accordées par l'utilisateur.
- **Qt GUI futur** : widget Console, waterfall, timeline et tri des requêtes ;
  non inclus dans le CLI V0.1.

Le mode `hub` n'est disponible qu'aux exécutables démarrés par le HUB
avec leur canal IPC hérité. En dehors du HUB, utiliser les commandes de
diagnostic autonomes.

## Installation et utilisation

Depuis le dépôt :

```bash
python3 N3XV5/Applications/NexusNetTrace/nettrace.py --help
python3 N3XV5/Applications/NexusNetTrace/nettrace.py probe \
  'https://architecture.iatb.duckdns.org/' --engine auto
```

Si disponible, la CI fournit aussi un `n3xv5-nettrace.pyz` exécutable via
`python3 n3xv5-nettrace.pyz` et un binaire Linux PyInstaller. Le zipapp
nécessite Python 3.10+ ; le binaire PyInstaller inclut Python.

Commandes utiles :

```bash
# HTTPS simple avec rapport privé (JSON anonymisé)
n3xv5-nettrace --json --output ./probe-client.json probe \
  'https://ia.iatb.duckdns.org/login' --method HEAD

# Test CORS OPTIONS — origin explicite, non navigateur
n3xv5-nettrace probe 'https://ia.iatb.duckdns.org/api/overview' \
  --method OPTIONS --origin 'https://ia.iatb.duckdns.org'

# Séparer les couches d'une panne
n3xv5-nettrace dns ia.iatb.duckdns.org
n3xv5-nettrace tcp ia.iatb.duckdns.org 443
n3xv5-nettrace tls ia.iatb.duckdns.org

# Firefox : F12 > Réseau > actualiser > Save All As HAR
n3xv5-nettrace har ~/Téléchargements/connexion.har

# Comparer à un journal JSONL préalablement exporté du VPS
n3xv5-nettrace correlate ./probe-client.json ./proxy-logs.jsonl

# Profil N3XV5 uniquement dans une app authentifiée via le HUB
n3xv5-nettrace hub
n3xv5-nettrace hub --connections
```

## Exemple : erreur HTTP 502, client fonctionnel mais VPS KO

**Symptôme** : Firefox affiche `502 Bad Gateway` sur
`https://architecture.iatb.duckdns.org/api/overview`.

1. Le client exécute une requête NetTrace en créant un ID unique.
2. NetTrace affiche, par exemple (valeurs illustratives, **pas une mesure réelle**) :
   DNS 9 ms ; TCP 24 ms ; TLS 55 ms ; TTFB 1250 ms ; HTTP **502**.
3. Le serveur Caddy ou Nginx reçoit le header `X-Request-ID` et ajoute
   l'ID aux logs ; NetTrace peut corréler les deux exports.
4. Si le proxy montre `upstream_status=502` ou un refus de socket,
   vérifier **sur le VPS** :
   `systemctl status mon-service`,
   `ss -ltn`,
   puis `journalctl -u mon-service --since '10 minutes ago'`.
5. Corriger le vrai problème : par exemple le service backend est arrêté,
   écoute sur un mauvais port, ou a dépassé son timeout. Corriger la
   configuration du proxy et/ou redémarrer **seulement ce service après
   diagnostic**, puis refaire exactement le même test.
6. La réponse attendue devient HTTP 200 (ou 401 pour une route protégée
   sans authentification) et les durées TTFB chutent.

L'exemple ne prétend pas que ton VPS a effectivement une erreur 502.

### Exemple de journal côté proxy

Format JSONL minimal accepté :

```json
{"request_id":"n3xv5-f4c8","status":502,"upstream_status":502,"request_time":1.25,"upstream_response_time":1.20,"route":"/api/overview"}
```

Le reverse proxy doit **être configuré explicitement** pour conserver
le `X-Request-ID` fourni par le client. Si le proxy le remplace, il faut
utiliser son ID propre et propager un lien de corrélation ; les formats
de logs Caddy et Nginx varient. L'application côté VPS doit idéalement
propager cet ID jusqu'à son backend.

## Limites importantes (et pourquoi)

- **HTTPS est chiffré** : NetTrace ne voit pas les flux secrets des autres
  processus. Pour voir les requêtes d'un onglet Firefox, importer son HAR.
  Aucun MITM, certificat racine injecté ou capture invisible des sessions.
- Un HAR brut peut contenir cookies, tokens, identifiants et corps privés.
  **Ne transmets pas le HAR brut** ; le rapport NetTrace est une version
  réduite et nettoyée par allowlist d'en-têtes.
- Le mode probe n'envoie pas d'Authorization/Cookie ; il ne reproduit pas une
  session utilisateur authentifiée. Tester un endpoint sensible en HEAD peut
  renvoyer 405, sans impliquer une panne.
- CORS est contrôlé par le navigateur : un probe OPTIONS n'est pas un
  véritable preflight complet et ne remplace pas les détails Firefox.
- Le moteur Python stdlib supporte HTTP/1.1 ; pour HTTP/2, timings plus fins,
  proxy et négociation plus proche d'un vrai client, utiliser curl.
- Les métriques curl sont **cumulatives** depuis le début, donc
  `time_starttransfer` contient DNS + TCP + TLS + traitement serveur.
- Les OPTIONS/GET/HEAD sont habituellement sans effet secondaire, mais toute
  requête peut déclencher des effets côté serveur mal configuré.
  Limiter les diagnostics à des hôtes que tu administres.
- Les données de requête dans une URL (ex. `?token=...`) sont envoyées à la
  cible : NetTrace masque leur valeur **dans le rapport** mais ne peut
  empêcher leur exposition dans les logs du serveur ou la table des processus.
- Rapports JSON écrits sans écrasement, permissions 0600 sous Unix.

## Extensions suivantes

1. Comparateur de deux traces et waterfall animé dans un widget HUB
   configurable (1×1, 2×2, 4×2 unités de grille).
2. Collecteur de logs VPS via la connexion SSH du Core et
   permissions `connections.read` + nouvelle capacité dédiée `logs.read`.
3. Diagnostics HTTP/2, WebSocket handshake, SSE, DNS IPv4/IPv6, Proxy
   CONNECT, mTLS et tests CORS plus complets.
4. Build portable Windows `.exe` et macOS `.app`/`.dmg`,
   avec le SDK d'IPC adapté à ces systèmes.
