"""
Scan d'attaque automatique avec OWASP ZAP (plan de tests, étape C4).

    .venv/Scripts/python.exe zap/lancer_zap.py [--zap <chemin de zap.bat>]
                                               [--sortie <dossier des rapports>]
                                               [--duree <minutes par compte>]

Prérequis :
  - ZAP installé (zaproxy.org, installeur Windows) avec Java 17 ou plus ;
  - la base jetable `edt_zap`, migrée puis remplie par seed.py
    (DB_NAME=edt_zap). Le scan actif crée, modifie et supprime des
    données : jamais la base de travail, ni edt_charge.

Déroulé : un serveur Django à part (127.0.0.1:8012, base edt_zap, clé
secrète tirée au hasard, fichiers dans un dossier temporaire, limite de
requêtes relevée), puis un scan passif et actif de toute l'API, une fois avec
la session d'un chef de département et une fois avec celle d'un étudiant.
Rapports HTML et JSON dans le dossier de sortie (par défaut un dossier
temporaire, hors du dépôt). Le dossier de travail, avec les sessions, est
effacé à la fin ; les sessions ne valent rien ailleurs.

Phase B, à travers nginx et HTTPS : lancer d'abord la simulation de mise en
ligne sur edt_zap, limite de requêtes relevée,
    set DJANGO_THROTTLE_USER=100000/min
    .venv/Scripts/python.exe deploiement/simulation_production.py --base edt_zap --garder 40
puis viser son adresse avec la clé secrète qu'elle a tirée :
    .venv/Scripts/python.exe zap/lancer_zap.py --cible https://127.0.0.1:8443         --cle-secrete <dossier de travail de la simulation>/cle_secrete
"""
import argparse
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON = os.path.join(RACINE, ".venv", "Scripts", "python.exe")
PORT = 8012
API_LOCALE = f"http://127.0.0.1:{PORT}/api/"
EMPLACEMENTS_ZAP = [
    r"C:\Program Files\ZAP\Zed Attack Proxy\zap.bat",
    r"C:\Program Files (x86)\ZAP\Zed Attack Proxy\zap.bat",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\ZAP\Zed Attack Proxy\zap.bat"),
]


def trouver_zap(chemin):
    for candidat in [chemin] if chemin else EMPLACEMENTS_ZAP:
        if candidat and os.path.exists(candidat):
            return candidat
    sys.exit("ZAP introuvable : l'installer, ou indiquer --zap <chemin de zap.bat>.")


def env_java_recent():
    """
    Environnement de ZAP avec un Java 17 ou plus en tête du PATH : zap.bat
    lance le premier `java` trouvé, et un Java 8 installé par ailleurs
    (java.com) passe devant et empêche ZAP de démarrer.
    """
    candidats = []
    for base in (r"C:\Program Files\Eclipse Adoptium", r"C:\Program Files\Java"):
        if os.path.isdir(base):
            for nom in os.listdir(base):
                chiffres = re.findall(r"\d+", nom)
                if chiffres and int(chiffres[0]) >= 17 and os.path.exists(os.path.join(base, nom, "bin", "java.exe")):
                    candidats.append((int(chiffres[0]), os.path.join(base, nom)))
    if not candidats:
        sys.exit("Aucun Java 17 ou plus trouvé (Eclipse Temurin, adoptium.net) : ZAP ne démarrerait pas.")
    java_home = max(candidats)[1]
    print(f"Java utilisé par ZAP : {java_home}", flush=True)
    return {**os.environ, "JAVA_HOME": java_home,
            "PATH": os.path.join(java_home, "bin") + os.pathsep + os.environ.get("PATH", "")}


def port_libre():
    """Port libre pour le proxy interne de ZAP (8080 par défaut, souvent
    déjà pris, par exemple par Oracle)."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def attendre_serveur(delai=90):
    fin = time.time() + delai
    while time.time() < fin:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/admin/login/", timeout=3)
            return
        except urllib.error.HTTPError:
            return  # le serveur répond
        except OSError:
            time.sleep(1)
    sys.exit("Le serveur Django du scan n'a pas démarré.")


def plan(role, jeton, requetes, sortie, duree, api):
    """Plan d'automatisation ZAP (JSON, accepté comme du YAML)."""
    return {
        "env": {
            "contexts": [{
                "name": "edt-api",
                "urls": [api],
                "includePaths": [f"{api}.*"],
                # La connexion a sa propre limitation, déjà testée par
                # LimitationTentativesTest : inutile de la marteler.
                "excludePaths": [f"{api}token/.*"],
            }],
            "parameters": {"failOnError": False, "failOnWarning": False, "progressToStdout": True},
        },
        "jobs": [
            {
                "type": "replacer",
                "parameters": {"deleteAllRules": True},
                "rules": [{
                    "description": "session de test",
                    "url": "",
                    "matchType": "req_header",
                    "matchString": "Authorization",
                    "matchRegex": False,
                    "replacementString": f"Bearer {jeton}",
                    "tokenProcessing": False,
                }],
            },
            {
                "type": "requestor",
                "requests": [
                    {
                        "url": api + r["url"],
                        "method": r["method"],
                        **({"data": json.dumps(r["data"]), "headers": ["Content-Type: application/json"]}
                           if "data" in r else {}),
                    }
                    for r in requetes
                ],
            },
            {"type": "passiveScan-wait", "parameters": {"maxDuration": 5}},
            {
                "type": "activeScan",
                "parameters": {"context": "edt-api", "maxScanDurationInMins": duree, "threadPerHost": 4},
            },
            {"type": "passiveScan-wait", "parameters": {"maxDuration": 5}},
            {"type": "report", "parameters": {
                "template": "traditional-html", "reportDir": sortie, "reportFile": f"zap-{role}",
                "reportTitle": f"Scan ZAP de l'API EDT (session {role})"}},
            {"type": "report", "parameters": {
                "template": "traditional-json", "reportDir": sortie, "reportFile": f"zap-{role}"}},
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--zap")
    parser.add_argument("--sortie", default=os.path.join(tempfile.gettempdir(), "edt-zap-rapports"))
    parser.add_argument("--duree", type=int, default=20, help="minutes de scan actif par compte")
    parser.add_argument("--cible", help="serveur déjà en place (simulation de mise en ligne), ex. https://127.0.0.1:8443")
    parser.add_argument("--cle-secrete", help="fichier contenant la clé secrète du serveur visé par --cible")
    args = parser.parse_args()
    if bool(args.cible) != bool(args.cle_secrete):
        sys.exit("--cible et --cle-secrete vont ensemble.")
    api = args.cible.rstrip("/") + "/api/" if args.cible else API_LOCALE

    zap = trouver_zap(args.zap)
    env_zap = env_java_recent()
    os.makedirs(args.sortie, exist_ok=True)
    travail = tempfile.mkdtemp(prefix="edt-zap-")
    env = {
        **os.environ,
        "DB_NAME": "edt_zap",
        "DJANGO_SECRET_KEY": (
            open(args.cle_secrete, encoding="utf-8").read().strip() if args.cle_secrete else secrets.token_hex(32)
        ),
        "DJANGO_MEDIA_ROOT": os.path.join(travail, "media"),
        "DJANGO_THROTTLE_USER": "100000/min",
        "PYTHONIOENCODING": "utf-8",
    }
    serveur = journal = None
    try:
        etat_chemin = os.path.join(travail, "etat.json")
        subprocess.run([PYTHON, os.path.join("zap", "preparer_zap.py"), etat_chemin], cwd=RACINE, env=env, check=True)
        with open(etat_chemin, encoding="utf-8") as f:
            etat = json.load(f)

        if not args.cible:
            journal = open(os.path.join(args.sortie, "serveur-django.log"), "w", encoding="utf-8")
            serveur = subprocess.Popen(
                [PYTHON, "manage.py", "runserver", f"127.0.0.1:{PORT}", "--noreload"],
                cwd=RACINE, env=env, stdout=journal, stderr=subprocess.STDOUT,
            )
            attendre_serveur()

        for role, jeton in etat["sessions"].items():
            chemin_plan = os.path.join(travail, f"plan-{role}.yaml")
            with open(chemin_plan, "w", encoding="utf-8") as f:
                json.dump(plan(role, jeton, etat["requetes"], args.sortie, args.duree, api), f, ensure_ascii=False, indent=1)
            print(f"\n=== Scan avec la session {role} ({etat['comptes'][role]}) ===", flush=True)
            # -silent : ZAP ne contacte aucun service extérieur (pas de
            # recherche de mises à jour) ; -dir : réglages jetables.
            subprocess.run(
                [zap, "-cmd", "-silent", "-port", str(port_libre()),
                 "-dir", os.path.join(travail, f"zap-{role}"), "-autorun", chemin_plan],
                cwd=os.path.dirname(zap), env=env_zap, check=False,
            )
    finally:
        if serveur:
            serveur.terminate()
            serveur.wait(timeout=30)
        if journal:
            journal.close()
        shutil.rmtree(travail, ignore_errors=True)
    print(f"\nRapports : {args.sortie}")


if __name__ == "__main__":
    main()
