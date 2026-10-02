import json
import platform
import subprocess
from datetime import datetime
from pathlib import Path

import psutil

PORTS_CONNUS = {
    135: ("RPC (appels de procédure à distance)", "OK"),
    139: ("NetBIOS (ancien partage de fichiers)", "ATTENTION"),
    445: ("SMB (partage de fichiers)", "ATTENTION"),
    623: ("Intel AMT (gestion à distance)", "A VERIFIER"),
    16992: ("Intel AMT (interface web de gestion)", "A VERIFIER"),
    2179: ("Hyper-V (machines virtuelles)", "OK"),
    5040: ("Windows (appareils connectés)", "OK"),
    5357: ("Découverte réseau Windows (WSDAPI)", "ATTENTION"),
}

NOMS_PROFILS = {
    "Domain": "Domaine",
    "Private": "Privé",
    "Public": "Public",
}

rapport = []


def afficher(texte=""):
    print(texte, flush=True)
    rapport.append(texte)


def nom_processus(pid):
    if pid is None:
        return "inconnu"
    try:
        return psutil.Process(pid).name()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return "inconnu"


def evaluer_port(port, processus):
    if port in PORTS_CONNUS:
        return PORTS_CONNUS[port]
    if processus == "spoolsv.exe":
        return ("Spouleur d'impression (à désactiver sans imprimante)", "ATTENTION")
    if port >= 49152:
        return ("Port dynamique Windows (RPC)", "OK")
    return ("Port inconnu, à vérifier", "A VERIFIER")


afficher("=== AUDIT SYSTEME ===")
afficher(f"Date de l'audit : {datetime.now():%d/%m/%Y %H:%M}")
afficher(f"Nom de la machine : {platform.node()}")
afficher(f"Système : {platform.system()} {platform.release()}")
afficher(f"Version : {platform.version()}")
afficher(f"Processeur : {platform.processor()}")
afficher(f"RAM totale (Go) : {round(psutil.virtual_memory().total / (1024**3), 1)}")

afficher()
afficher("=== COMPTES UTILISATEURS ===")
commande = "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Get-LocalUser | Select-Object Name, Enabled, PasswordRequired | ConvertTo-Json"
resultat = subprocess.run(
    ["powershell", "-NoProfile", "-Command", commande],
    capture_output=True,
    encoding="utf-8",
)
comptes = json.loads(resultat.stdout)

for compte in comptes:
    etat = "actif" if compte["Enabled"] else "désactivé"
    mdp = "mot de passe requis" if compte["PasswordRequired"] else "PAS de mot de passe requis"
    afficher(f"- {compte['Name']} : {etat}, {mdp}")

afficher()
afficher("=== PORTS OUVERTS (en écoute sur le réseau) ===")
ports_reseau = set()
ports_locaux = set()
for conn in psutil.net_connections(kind="inet"):
    if conn.status != psutil.CONN_LISTEN:
        continue
    port = conn.laddr.port
    if conn.laddr.ip in ("127.0.0.1", "::1"):
        ports_locaux.add(port)
    else:
        ports_reseau.add((port, nom_processus(conn.pid)))

compteur = {"OK": 0, "ATTENTION": 0, "A VERIFIER": 0}
for port, processus in sorted(ports_reseau):
    description, niveau = evaluer_port(port, processus)
    compteur[niveau] += 1
    afficher(f"- [{niveau}] Port {port} - {processus} : {description}")

afficher()
afficher(f"Ports locaux seulement (non exposés) : {len(ports_locaux)}")
afficher(f"Résumé : {compteur['OK']} OK, {compteur['ATTENTION']} à surveiller, {compteur['A VERIFIER']} à vérifier")

afficher()
afficher("=== PARE-FEU WINDOWS ===")
commande = "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Get-NetFirewallProfile | Select-Object Name, @{n='Enabled';e={$_.Enabled.ToString()}} | ConvertTo-Json"
resultat = subprocess.run(
    ["powershell", "-NoProfile", "-Command", commande],
    capture_output=True,
    encoding="utf-8",
)
profils = json.loads(resultat.stdout)

for profil in profils:
    nom = NOMS_PROFILS.get(profil["Name"], profil["Name"])
    if profil["Enabled"] == "True":
        afficher(f"- [OK] Profil {nom} : pare-feu actif")
    else:
        afficher(f"- [CRITIQUE] Profil {nom} : pare-feu DÉSACTIVÉ")

afficher()
afficher("=== MISES A JOUR ===")
if platform.system() == "Windows" and platform.release() == "10":
    afficher("- [ATTENTION] Windows 10 : fin de support Microsoft le 14/10/2025, correctifs de sécurité uniquement via le programme ESU (à vérifier dans Windows Update)")

commande = "Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 1 | ForEach-Object { $_.InstalledOn.ToString('yyyy-MM-dd') }"
resultat = subprocess.run(
    ["powershell", "-NoProfile", "-Command", commande],
    capture_output=True,
    encoding="utf-8",
)
date_texte = resultat.stdout.strip()
try:
    derniere = datetime.strptime(date_texte, "%Y-%m-%d")
    jours = (datetime.now() - derniere).days
    niveau = "OK" if jours <= 60 else "ATTENTION"
    afficher(f"- [{niveau}] Dernier correctif installé : {date_texte} (il y a {jours} jours)")
except ValueError:
    afficher("- [A VERIFIER] Impossible de lire la date du dernier correctif")

print("Recherche des mises à jour en attente (peut prendre jusqu'à 1 minute)...", flush=True)
commande = "$s = New-Object -ComObject Microsoft.Update.Session; $r = $s.CreateUpdateSearcher().Search('IsInstalled=0'); $t = @($r.Updates | ForEach-Object { $_.Title }); ConvertTo-Json -InputObject $t"
try:
    resultat = subprocess.run(
        ["powershell", "-NoProfile", "-Command", commande],
        capture_output=True,
        encoding="utf-8",
        timeout=300,
    )
    en_attente = json.loads(resultat.stdout)
except (subprocess.TimeoutExpired, json.JSONDecodeError):
    en_attente = None

if en_attente is None:
    afficher("- [A VERIFIER] Impossible de vérifier les mises à jour en attente (connexion internet ?)")
elif len(en_attente) == 0:
    afficher("- [OK] Aucune mise à jour en attente")
else:
    afficher(f"- [ATTENTION] {len(en_attente)} mise(s) à jour en attente :")
    for titre in en_attente:
        afficher(f"    * {titre}")

dossier = Path(__file__).parent / "rapports"
dossier.mkdir(exist_ok=True)
fichier = dossier / f"rapport_audit_{datetime.now():%Y-%m-%d_%H-%M}.txt"
fichier.write_text("\n".join(rapport), encoding="utf-8")
print()
print(f"Rapport enregistré dans : {fichier}")