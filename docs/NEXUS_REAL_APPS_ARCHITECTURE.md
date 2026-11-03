# NOVA CONTROL CENTER — applications réelles

Le Control Center est l'hôte Full Qt. Ses panneaux Paramètres et Sessions sont intégrés au shell. Terminal, Remote Explorer, Network Inspector et IA-TB CLI Dashboard sont des applications Qt indépendantes à installer et activer, jamais des simulations.

## Remote Explorer — SFTP
- SFTP sécurisé avec authentification SSH et validation de la clé d'hôte; FTP non chiffré seulement si explicitement demandé.
- QTreeView en chargement paresseux: dossiers, fichiers, taille, permissions, date de modification, breadcrumbs et recherche.
- Recherche intelligente: correspondances floues sur nom et chemin, filtres extension/date/taille; parcours distant limité, annulable, non bloquant.
- Téléchargement et visualisation, édition/envoi après confirmation, mode lecture seule par défaut.
- Rafraîchissement automatique ciblé quand un événement resource.changed est reçu, puis revérification distante.

## Network Inspector — HTTP/API
- Vue navigateur Qt WebEngine et ouverture indépendante dans le navigateur par défaut.
- Mode de base: capture des métadonnées de requêtes émises par sa vue Qt, sans prétendre lire les réponses d'autres programmes.
- Mode avancé à activer explicitement: mitmproxy/mitmdump en processus séparé, avec configuration du proxy côté client, et confiance TLS seulement avec accord explicite.
- Tableau filtrable: host, méthode, URL nettoyée, code HTTP, durée, taille, erreurs, aperçu JSON redigé, export HAR expurgé.
- Aucun déchiffrement global du trafic VPS, aucune modification automatique de requêtes.

## IA-TB CLI Dashboard — VPS
- Adapter l'outil IA-TB-CLI existant: découvrir sa version, ses commandes et formats de sorties exacts avant de les invoquer.
- Vues: CPU/RAM/disque VPS, services et conteneurs, statut Engines IA-TB, environnement DEBUG/RELEASE, logs et métriques horodatées.
- Afficher N/D si une mesure n'est pas fournie. Aucune donnée fictive.
- QProcess asynchrone; commandes en arguments séparés, délais, annulation, sortie d'erreurs et journal d'audit.
- Permissions: lecture seule par défaut; confirmation des actions de restart/stop/publish et contrôle de l'environnement cible.

## Flux entre applications
Exemple d'événement publié après modification distante:
{
 "topic": "resource.changed",
 "source": "nova.terminal",
 "connection_id": "gen1",
 "resource": "/srv/iatb-debug/config.json",
 "payload": {"operation": "write"}
}

Le SFTP invalide le chemin et relit les métadonnées; la vue Web ne recharge qu'après vérification d'une URL/service concerné. Les identifiants de connexion sont transmis, jamais les clés ou tokens.

## Base logicielle
src/nova_control_center/app_contracts.py définit AppManifest, Capability, ConnectionBroker, HostEvents et ApplicationHost. Les manifestes descriptifs ne déclenchent pas d'import Python dynamique; l'activation de code Qt doit être approuvée.

## Responsive et performance
Les fenêtres QWidget peuvent être libres ou en 2x2, 2+1+1 et 1+1+2. DPI 100/125/150%, cache des ressources, proportions natives pour les logos et sprites, 9-slice pour les cadres, aucune requête réseau dans le thread graphique. La colonne gauche montre les applications réellement installées et activées uniquement.

## Étapes suivantes
1. Retrouver la version et la documentation exactes IA-TB-CLI et tester ses sorties en lecture seule.
2. Implémenter SFTP avec serveur de test, parcours asynchrone et tests.
3. Implémenter Qt WebEngine, puis proxy optionnel avec accord utilisateur.
4. Relier chaque app à Sessions, au broker de connexions et au bus d'événements.
5. Valider les rendus et tailles originales sur Linux Mint XFCE.
