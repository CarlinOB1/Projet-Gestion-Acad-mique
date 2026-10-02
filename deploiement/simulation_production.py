"""
Simulation locale de la mise en ligne (Phase B du plan de tests), sans
serveur Linux : monte sur cette machine l'équivalent de DEPLOIEMENT.md, puis
le vérifie avec deploiement/verifier_production.py.

    .venv/Scripts/python.exe deploiement/simulation_production.py
            [--nginx <nginx.exe>] [--base edt_charge|edt_zap] [--garder <minutes>]

Ce qui tourne :
  - Django en mode production (DJANGO_DEBUG=False, HTTPS, NUM_PROXIES=1,
    cache fichier, documents servis par X-Accel-Redirect), servi par waitress
    sur 127.0.0.1:8013 : gunicorn ne fonctionne pas sous Windows ;
  - nginx pour Windows devant, avec la configuration de DEPLOIEMENT.md
    elle-même, lue dans le fichier puis adaptée à la machine (voir
    adapter_configuration) : HTTPS sur le port 8443 avec un certificat
    auto-signé, redirection depuis le port 8081 ;
  - l'interface construite (edt-frontend/dist : `npm run build` avant).

Sans --garder, tout s'arrête après la vérification. Avec --garder N, la
simulation reste en place N minutes (ou jusqu'à la création du fichier
`arreter` dans son dossier de travail) pour le test de charge et le scan
ZAP ; le dossier de travail contient alors `sessions.json` (sessions de
charge) et `cle_secrete` (pour zap/lancer_zap.py --cible), valables pour
cette seule simulation et effacés à la fin.

Prérequis : nginx pour Windows (nginx.org, zip), waitress (pip), openssl
(fourni avec Git pour Windows), une base jetable remplie par seed.py.
Différences avec le vrai serveur : Windows, waitress, ports 8443/8081,
certificat auto-signé, base jetable.
"""
import argparse
import glob
import http.client
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
from urllib.parse import urlsplit

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON = os.path.join(RACINE, ".venv", "Scripts", "python.exe")
PORT_DJANGO, PORT_HTTPS, PORT_HTTP = 8013, 8443, 8081
URL = f"https://localhost:{PORT_HTTPS}"


def chemin_nginx(chemin):
    candidats = [chemin] if chemin else sorted(
        glob.glob(os.path.expandvars(r"%LOCALAPPDATA%\edt-phase-b\nginx-*\nginx.exe")), reverse=True,
    )
    for candidat in candidats:
        if candidat and os.path.exists(candidat):
            return candidat
    sys.exit("nginx introuvable : le télécharger (nginx.org, version Windows) ou indiquer --nginx.")


def chemin_openssl():
    for candidat in (shutil.which("openssl"), r"C:\Program Files\Git\mingw64\bin\openssl.exe",
                     r"C:\Program Files\Git\usr\bin\openssl.exe"):
        if candidat and os.path.exists(candidat):
            return candidat
    sys.exit("openssl introuvable (il est fourni avec Git pour Windows).")


def verifier_ports_libres():
    for port in (PORT_DJANGO, PORT_HTTPS, PORT_HTTP):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                sys.exit(f"Le port {port} est déjà pris : arrêter le programme qui l'utilise.")


def unix(chemin):
    """Chemin Windows écrit comme nginx l'attend (barres obliques)."""
    return chemin.replace("\\", "/")


def adapter_configuration(bloc, media, statiques):
    """
    Configuration nginx de DEPLOIEMENT.md, adaptée à cette machine. Chaque
    adaptation doit s'appliquer : si le guide change de forme, la simulation
    s'arrête au lieu de tester autre chose que lui.
    """
    remplacements = [
        (r"listen 443 ssl( http2)?;", rf"listen {PORT_HTTPS} ssl\1;"),
        (r"listen 80;", f"listen {PORT_HTTP};"),
        (r"server_name \S+;", "server_name localhost;"),
        (r"#\s*ssl_certificate[^\n]*", "ssl_certificate cert.pem; ssl_certificate_key cle.pem;"),
        (r"root /srv/edt/edt-frontend/dist;", f'root "{unix(os.path.join(RACINE, "edt-frontend", "dist"))}";'),
        (r"alias /srv/edt/staticfiles/;", f'alias "{unix(statiques)}/";'),
        (r"alias /var/lib/edt/media/([^;]*);", lambda m: f'alias "{unix(media)}/{m.group(1)}";'),
        # Socket unix de gunicorn → port local de waitress.
        (r"proxy_pass http://unix:[^;]+;", f"proxy_pass http://127.0.0.1:{PORT_DJANGO};"),
        # Ports non standard : les garder dans les redirections.
        (r"return 301 https://\$host\$request_uri;", f"return 301 https://$host:{PORT_HTTPS}$request_uri;"),
        (r"proxy_set_header Host \$host;", "proxy_set_header Host $http_host;"),
    ]
    for motif, remplacement in remplacements:
        bloc, nombre = re.subn(motif, remplacement, bloc)
        if not nombre:
            sys.exit(f"DEPLOIEMENT.md a changé : « {motif} » introuvable dans la configuration nginx.")
    return (
        "worker_processes 1;\nerror_log logs/error.log warn;\npid logs/nginx.pid;\n"
        "events { worker_connections 256; }\n"
        "http {\n    include mime.types;\n    default_type application/octet-stream;\n"
        "    sendfile on;\n    access_log logs/access.log;\n\n"
        + bloc + "\n}\n"
    )


def configuration_du_guide():
    with open(os.path.join(RACINE, "DEPLOIEMENT.md"), encoding="utf-8") as f:
        texte = f.read()
    bloc = re.search(r"```nginx\n(.*?)```", texte, re.S)
    if not bloc:
        sys.exit("Bloc ```nginx introuvable dans DEPLOIEMENT.md.")
    return bloc.group(1)


def attendre(url, delai=60):
    """Attend une réponse, quelle qu'elle soit (une redirection compte)."""
    parties = urlsplit(url)
    fin = time.time() + delai
    while time.time() < fin:
        conn = http.client.HTTPConnection(parties.hostname, parties.port, timeout=3)
        try:
            conn.request("GET", parties.path or "/")
            conn.getresponse()
            return
        except OSError:
            time.sleep(0.5)
        finally:
            conn.close()
    sys.exit(f"{url} ne répond pas.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--nginx")
    parser.add_argument("--base", default="edt_charge", choices=["edt_charge", "edt_zap"])
    parser.add_argument("--garder", type=int, default=0, help="minutes de maintien après la vérification")
    args = parser.parse_args()

    nginx = chemin_nginx(args.nginx)
    openssl = chemin_openssl()
    if not os.path.exists(os.path.join(RACINE, "edt-frontend", "dist", "index.html")):
        sys.exit("Interface non construite : lancer `npm --prefix edt-frontend run build`.")
    verifier_ports_libres()

    travail = tempfile.mkdtemp(prefix="edt-phase-b-")
    conf = os.path.join(travail, "conf")
    for dossier in ("conf", "logs", "temp", "media", "cache", "logs-django"):
        os.makedirs(os.path.join(travail, dossier))
    media = os.path.join(travail, "media")
    statiques = os.path.join(RACINE, "staticfiles")
    cle_secrete = secrets.token_hex(32)
    env = {
        **os.environ,
        "DB_NAME": args.base,
        "DJANGO_DEBUG": "False",
        "DJANGO_SECRET_KEY": cle_secrete,
        "DJANGO_ALLOWED_HOSTS": "localhost,127.0.0.1",
        "DJANGO_CORS_ALLOWED_ORIGINS": URL,
        "DJANGO_CSRF_TRUSTED_ORIGINS": URL,
        "DJANGO_NUM_PROXIES": "1",
        "DJANGO_CACHE_DIR": os.path.join(travail, "cache"),
        "DJANGO_LOG_DIR": os.path.join(travail, "logs-django"),
        "DJANGO_MEDIA_ROOT": media,
        "DJANGO_PROTECTED_MEDIA_PREFIX": "/protected_media/",
        "PYTHONIOENCODING": "utf-8",
    }
    prefixe = ["-p", unix(travail) + "/", "-c", "conf/nginx.conf"]
    waitress = journal = None
    nginx_lance = False
    etat = os.path.join(travail, "etat.json")
    try:
        print(f"Dossier de travail : {travail}", flush=True)
        shutil.copy(os.path.join(os.path.dirname(nginx), "conf", "mime.types"), conf)
        subprocess.run(
            [openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "2",
             "-keyout", os.path.join(conf, "cle.pem"), "-out", os.path.join(conf, "cert.pem"),
             "-subj", "/CN=localhost", "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1"],
            check=True, capture_output=True,
        )
        with open(os.path.join(conf, "nginx.conf"), "w", encoding="utf-8") as f:
            f.write(adapter_configuration(configuration_du_guide(), media, statiques))

        print("Contrôle de configuration (manage.py check --deploy) :", flush=True)
        subprocess.run([PYTHON, "manage.py", "check", "--deploy"], cwd=RACINE, env=env, check=False)
        subprocess.run([PYTHON, "manage.py", "collectstatic", "--noinput", "-v", "0"], cwd=RACINE, env=env, check=True)
        subprocess.run([PYTHON, os.path.join("deploiement", "preparer_simulation.py"), "preparer", etat],
                       cwd=RACINE, env=env, check=True)

        journal = open(os.path.join(travail, "logs", "waitress.log"), "w", encoding="utf-8")
        # Les en-têtes X-Forwarded-* posés par nginx doivent parvenir à
        # Django (comme avec gunicorn) : waitress les efface par défaut.
        waitress = subprocess.Popen(
            [PYTHON, "-m", "waitress", f"--listen=127.0.0.1:{PORT_DJANGO}", "--threads=8",
             "--no-clear-untrusted-proxy-headers", "Gestion_edt.wsgi:application"],
            cwd=RACINE, env=env, stdout=journal, stderr=subprocess.STDOUT,
        )
        attendre(f"http://127.0.0.1:{PORT_DJANGO}/api/")

        test = subprocess.run([nginx, "-t", *prefixe], capture_output=True, text=True)
        print(test.stderr.strip(), flush=True)
        if test.returncode:
            sys.exit("Configuration nginx refusée.")
        subprocess.Popen([nginx, *prefixe], cwd=travail)
        nginx_lance = True
        attendre(f"http://127.0.0.1:{PORT_HTTP}/")

        with open(etat, encoding="utf-8") as f:
            donnees = json.load(f)
        print(f"\nSimulation en place : {URL}\n", flush=True)
        subprocess.run(
            [sys.executable, os.path.join(RACINE, "deploiement", "verifier_production.py"),
             "--url", URL, "--http", f"http://localhost:{PORT_HTTP}", "--auto-signe",
             "--document", str(donnees["document"])],
            env={**os.environ, "EDT_VERIF_JETON": donnees["jeton_etudiant"], "PYTHONIOENCODING": "utf-8"},
            check=False,
        )

        if args.garder:
            if args.base == "edt_charge":  # sessions du test de charge, préparées pour cette base seule
                subprocess.run([PYTHON, os.path.join("charge", "generer_sessions.py"),
                                os.path.join(travail, "sessions.json")], cwd=RACINE, env=env, check=True)
            with open(os.path.join(travail, "cle_secrete"), "w", encoding="utf-8") as f:
                f.write(cle_secrete)
            arret = os.path.join(travail, "arreter")
            print(f"\nSimulation maintenue {args.garder} min (ou jusqu'à la création de {arret}).", flush=True)
            fin = time.time() + args.garder * 60
            while time.time() < fin and not os.path.exists(arret):
                time.sleep(2)
    finally:
        if nginx_lance:
            subprocess.run([nginx, "-s", "stop", *prefixe], capture_output=True)
        if os.path.exists(etat):
            subprocess.run([PYTHON, os.path.join("deploiement", "preparer_simulation.py"), "nettoyer", etat],
                           cwd=RACINE, env=env, check=False)
        if waitress:
            waitress.terminate()
            waitress.wait(timeout=30)
        if journal:
            journal.close()
        # Journaux gardés pour l'analyse, le reste (sessions, clé, certificat) effacé.
        sortie = os.path.join(tempfile.gettempdir(), "edt-phase-b-journaux")
        shutil.rmtree(sortie, ignore_errors=True)
        for dossier in ("logs", "logs-django"):
            if os.path.isdir(os.path.join(travail, dossier)):
                shutil.copytree(os.path.join(travail, dossier), os.path.join(sortie, dossier))
        time.sleep(1)
        shutil.rmtree(travail, ignore_errors=True)
        print(f"\nJournaux de nginx et de Django : {sortie}", flush=True)


if __name__ == "__main__":
    main()
