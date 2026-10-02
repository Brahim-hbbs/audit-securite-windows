# Audit de sécurité Windows

Script Python qui réalise un **audit de sécurité de base** d'un poste Windows et génère un rapport daté : comptes utilisateurs, ports ouverts, pare-feu et mises à jour.

Projet personnel réalisé dans le cadre de ma reconversion en administration systèmes, réseaux et cybersécurité.

## À quoi ça sert

Avant de sécuriser une machine, il faut savoir ce qu'il y a dessus : qui peut s'y connecter, quels services écoutent sur le réseau, si le système est à jour. Ce script automatise ces vérifications et classe chaque constat par niveau de gravité (`OK`, `ATTENTION`, `A VERIFIER`, `CRITIQUE`).

## Ce que le script vérifie

| Contrôle | Détail |
|---|---|
| **Système** | Nom de la machine, version de Windows, processeur, RAM |
| **Comptes utilisateurs** | Liste des comptes locaux, comptes actifs ou désactivés, mot de passe exigé ou non |
| **Ports ouverts** | Ports en écoute sur le réseau, programme associé, explication et niveau pour chaque port connu ; les ports locaux (127.0.0.1) sont comptés à part |
| **Pare-feu Windows** | État des trois profils (Domaine, Privé, Public) |
| **Mises à jour** | Fin de support de Windows 10, date du dernier correctif installé, mises à jour en attente |

À la fin, le rapport est enregistré dans un fichier texte daté, dans le dossier `rapports/`.

## Exemple de résultat

```
=== PORTS OUVERTS (en écoute sur le réseau) ===
- [OK] Port 135 - svchost.exe : RPC (appels de procédure à distance)
- [ATTENTION] Port 445 - System : SMB (partage de fichiers)
- [A VERIFIER] Port 623 - LMS.exe : Intel AMT (gestion à distance)

Ports locaux seulement (non exposés) : 10
Résumé : 8 OK, 4 à surveiller, 2 à vérifier

=== PARE-FEU WINDOWS ===
- [OK] Profil Domaine : pare-feu actif
- [OK] Profil Privé : pare-feu actif
- [OK] Profil Public : pare-feu actif
```

## Prérequis

- Windows 10 ou 11
- Python 3
- Une connexion internet (pour la recherche des mises à jour en attente)

## Installation et utilisation

Dans PowerShell :

```powershell
git clone https://github.com/Brahim-hbbs/audit-securite-windows.git
cd audit-securite-windows
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python audit.py
```

Pour que le script puisse identifier tous les programmes qui utilisent des ports, lance PowerShell **en tant qu'administrateur**. Sinon, certains programmes apparaissent comme « inconnu ».

## Limites connues

- Le script est en **lecture seule** : il constate, il ne modifie rien sur la machine.
- Un port « en écoute » n'est pas forcément joignable depuis l'extérieur : le pare-feu et la box internet peuvent le bloquer.
- « Mot de passe non exigé » est un **indicateur à vérifier**, pas la preuve qu'un compte n'a pas de mot de passe.
- Les explications de ports reposent sur une liste de ports courants ; les ports inconnus sont marqués `A VERIFIER`.
- Fonctionne uniquement sous Windows pour l'instant.

## Ce que j'ai appris

- Utiliser Python pour interroger le système : `psutil` pour les ports et processus, `subprocess` pour lancer des commandes PowerShell (`Get-LocalUser`, `Get-NetFirewallProfile`, `Get-HotFix`).
- Lire des données structurées (JSON) et gérer les erreurs avec `try/except`.
- Résoudre un problème d'encodage des accents entre PowerShell et Python.
- Interpréter les résultats plutôt que les afficher bruts : distinguer un service normal d'un service à surveiller.
- Utiliser Git et GitHub : `.gitignore`, `requirements.txt`, commits et push.

## Améliorations prévues

- Rapport au format HTML
- Envoi du rapport par e-mail ou sur Discord
- Exécution planifiée (Planificateur de tâches Windows)
- Version Linux
- Audit de plusieurs machines