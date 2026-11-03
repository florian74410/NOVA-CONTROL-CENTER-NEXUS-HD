# N3XV5 NetTrace 0.3 — multi-Engine / multi-VPS topology

## Objectif

Diagnostic orienté **liaison Engine → Engine**, même si les Engines sont
répartis sur plusieurs VPS et communiquent via HTTP(S), TCP, TLS, DNS.

Un test **A → B** doit s'exécuter depuis le VPS A, pas depuis le PC où tourne
le HUB. Pour cela, NetTrace 0.3 dispose d'un agent CLI côté source, invoqué
via un compte SSH restreint. Les résultats sont renvoyés au CLI local,
puis au HUB dans une trame JSON via le socket Unix `nettrace.publish`.

**Il ne s'agit pas de traçage passif des échanges réels** : une liaison est
testée activement et indépendamment, selon sa configuration. Une liaison
n'est pas nécessairement une route réseau de paquets à travers les autres
Engines du graphe.

## Exemple

Fichier `mesh.example.json` avec quatre nœuds :

```text
PC CLIENT  →  Collector (VPS-A)
                   ↓  TCP :443
                Fundamental (VPS-B)
                   ↓  TLS :443
                Trading (VPS-C)
                   └──── HTTPS /health → Collector (VPS-A)
```

- Chaque nœud possède un ID, le nom du VPS, un type d'agent.
- Chaque liaison a un ID, un Engine source, un Engine cible, et un test.
- Chaque Engine source distant possède un compte SSH NetTrace dédié.
- **Aucune clé privée et aucun mot de passe** dans le fichier JSON.

```bash
n3xv5-nettrace --json mesh mesh.example.json
# Tests locaux exécutés ; tests distants refusés (résultat PermissionError).

n3xv5-nettrace --json mesh mesh.example.json --allow-remote
# Tests distants uniquement si leur agent SSH et leurs politiques sont prêts.

# Depuis le HUB : NetTrace > commande « mesh » > choisir JSON >
# confirmer explicitement les diagnostics SSH distants.
```

## Configuration côté VPS (obligatoire)

Chaque VPS distant doit recevoir NetTrace CLI 0.3 et un fichier
`/etc/n3xv5/nettrace-agent.json` contenant les liaisons **autorisées
sur ce VPS uniquement**. Un même fichier global partagé partout
accorderait davantage d'accès que nécessaire.

Le fichier doit être possédé par **root** et ne pas être modifiable par
groupe/autres utilisateurs, typiquement `root:root 0644`. Exemple de
création (après validation du contenu et uniquement sur le VPS de test) :

```bash
sudo install -d -m 755 /etc/n3xv5
sudo install -o root -g root -m 644 nettrace-agent.json /etc/n3xv5/nettrace-agent.json
```

Sur VPS-A, inclure `collector-to-fundamental` mais retirer les edges
dont la source est une autre machine. Sur VPS-B, uniquement
`fundamental-to-trading`, etc. `remote_enabled: true` est obligatoire
pour chaque liaison distante. Le serveur ne fait confiance **qu'à son
propre** fichier local, jamais à une URL envoyée par le client.

Le compte SSH `nettrace` doit être dédié et limité ; idéalement :
clé publique autorisée avec forced-command, ACL réseau et pas de sudo.
N'utilise pas un compte root ni les clés de production IA-TB pour ces tests.
NEXUS se connecte avec `BatchMode=yes`, `StrictHostKeyChecking=yes`
et `ConnectTimeout=8` : pas de désactivation des vérifications SSH.
Le CLI agent reçoit simplement `{"edge_id":"..."}` sur stdin,
exécute le test allowlisté et retourne un rapport technique JSON.

**Avant d'ouvrir l'accès SSH aux agents**, configurer le forced-command,
restreindre les droits d'accès et tester le mécanisme sur VPS de DEBUG.
La première implémentation ne provisionne ni compte ni clé SSH.

## Affichage dans le HUB (iFrame 9×9)

Le moteur de rendu des tuiles reste dans le HUB.
`NetTracePanel` propose une commande **mesh**, un sélecteur de JSON et une
confirmation séparée pour le diagnostic SSH.

- Petite (1×2 ou 2×1) : résumé `MESH 1 FAIL / 4`.
- Moyenne (2×3 par défaut) : nombre de nœuds, liaisons, erreurs.
- Grande (4×4 ou plus) : liaisons en échec en premier, IDs des Engines,
  statuts HTTP/TLS/TCP, durées et résultats synthétiques.

Déplacer, agrandir, réduire et fermer la tuile ne déclenche aucune nouvelle
requête réseau ; seuls les contrôles explicites relancent des tests.

## Sécurité et limitations

- SSH n'est **pas** automatiquement autorisé : le HUB et le CLI exigent
  une action explicite `--allow-remote`.
- La connexion Unix n'est utilisée que pour **CLI local → HUB** ;
  les VPS communiquent sur des canaux SSH chiffrés.
- Aucune exécution shell construite depuis une URL. Les IDs sont validés,
  la commande distante est fixe et la policy source est root-owned.
- Pas de capture HTTPS des Engines en direct, pas d'accès à leurs secrets,
  pas de modification des services de production.
- Pour les statistiques des communications **réelles**, il faudra une
  instrumentation OpenTelemetry par Engine ou les logs Caddy/HTTP
  des services, corrélés par `traceparent` / `X-Request-ID`.
- Aucune mesure ne doit être interprétée comme un résultat IA-TB réel
  sans exécuter le diagnostic sur les VPS correspondants.
- Les builds Windows/macOS et le routage automatique par Connection Manager
  restent à développer.
