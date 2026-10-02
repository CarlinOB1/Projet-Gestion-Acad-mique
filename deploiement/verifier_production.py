"""
Vérification d'un serveur en ligne (Phase B du plan de tests) : ce que seul
un vrai serveur (nginx + HTTPS + DJANGO_DEBUG=False) permet de contrôler.

    python deploiement/verifier_production.py --url https://edt.exemple-universite.org
            [--http http://edt.exemple-universite.org]
            [--identifiant <compte étudiant de test> --document <id>]
            [--auto-signe] [--sans-rafale]

À lancer le jour de la mise en ligne, depuis un ordinateur HORS du réseau
interne (sinon /admin/ est ouvert, et c'est normal). Python seul suffit,
aucune bibliothèque à installer.

  --identifiant : connexion avec un compte étudiant de test, chronométrée.
      Le mot de passe est demandé au clavier, jamais passé en paramètre.
  --document : avec --identifiant, vérifie aussi le téléchargement protégé
      de ce document (redirection interne de nginx) ; le compte doit y avoir
      accès.
  --auto-signe : accepte un certificat auto-signé (simulation locale
      uniquement ; en ligne, le certificat doit être valide).
  --sans-rafale : saute le test de rafale de connexions, qui bloque
      ensuite les connexions depuis cet ordinateur pendant une minute.

Chaque contrôle affiche OK, ATTENTION (à examiner) ou ÉCHEC. Le script
s'arrête avec un code d'erreur s'il y a au moins un ÉCHEC.
"""
import argparse
import getpass
import http.client
import json
import os
import re
import secrets
import ssl
import sys
import time
from urllib.parse import urlsplit

resultats = []


def noter(niveau, libelle, detail=""):
    resultats.append(niveau)
    print(f"{niveau:<9} {libelle}" + (f"\n          → {detail}" if detail else ""), flush=True)


class Serveur:
    def __init__(self, url, auto_signe):
        parties = urlsplit(url)
        self.hote = parties.hostname
        self.port = parties.port or (443 if parties.scheme == "https" else 80)
        self.https = parties.scheme == "https"
        if auto_signe:
            self.contexte = ssl._create_unverified_context()  # noqa: S323 — simulation locale
        else:
            self.contexte = ssl.create_default_context()

    def connexion(self, delai=30):
        if self.https:
            return http.client.HTTPSConnection(self.hote, self.port, context=self.contexte, timeout=delai)
        return http.client.HTTPConnection(self.hote, self.port, timeout=delai)

    def requete(self, methode, chemin, corps=None, entetes=None):
        """(statut, en-têtes (liste de couples), corps en octets)."""
        conn = self.connexion()
        try:
            conn.request(methode, chemin, body=corps, headers=entetes or {})
            reponse = conn.getresponse()
            return reponse.status, reponse.getheaders(), reponse.read()
        finally:
            conn.close()


def valeurs(entetes, nom):
    return [v for k, v in entetes if k.lower() == nom.lower()]


def un_seul(entetes, nom):
    """Valeur d'un en-tête ; plusieurs exemplaires identiques comptent pour un."""
    trouvees = valeurs(entetes, nom)
    return trouvees[0] if trouvees else None


# ── Contrôles ────────────────────────────────────────────────────────────────

def controle_tls(serveur):
    conn = serveur.connexion()
    try:
        conn.connect()
        version = conn.sock.version()
    except ssl.SSLCertVerificationError as exc:
        noter("ÉCHEC", "Certificat HTTPS", f"refusé par le navigateur : {exc.verify_message}")
        return False
    except OSError as exc:
        noter("ÉCHEC", "Connexion HTTPS", str(exc))
        return False
    finally:
        conn.close()
    if version in ("TLSv1.2", "TLSv1.3"):
        noter("OK", f"Chiffrement {version}")
    else:
        noter("ÉCHEC", "Chiffrement", f"{version} : TLS 1.2 au minimum")
    return True


def controle_redirection_http(url_http, url_https):
    serveur = Serveur(url_http, False)
    try:
        statut, entetes, _ = serveur.requete("GET", "/etudiant/planning")
    except OSError as exc:
        noter("ÉCHEC", "Redirection HTTP → HTTPS", f"adresse HTTP injoignable : {exc}")
        return
    cible = un_seul(entetes, "Location") or ""
    if statut in (301, 308) and cible.startswith(url_https.rstrip("/")):
        noter("OK", "Redirection HTTP → HTTPS", f"{statut} vers {cible}")
    else:
        noter("ÉCHEC", "Redirection HTTP → HTTPS", f"réponse {statut}, Location={cible!r}")


def controle_interface(serveur):
    statut, entetes, corps = serveur.requete("GET", "/")
    if statut == 200 and b'id="root"' in corps:
        noter("OK", "Page d'accueil de l'interface")
    else:
        noter("ÉCHEC", "Page d'accueil de l'interface", f"réponse {statut}")
    statut, _, corps = serveur.requete("GET", "/etudiant/planning")
    if statut == 200 and b'id="root"' in corps:
        noter("OK", "Adresse interne de l'interface servie (rechargement d'une page)")
    else:
        noter("ÉCHEC", "Adresse interne de l'interface", f"/etudiant/planning → {statut}")
    script = re.search(rb'src="(/assets/[^"]+\.js)"', corps)
    if script:
        statut, entetes_js, _ = serveur.requete("GET", script.group(1).decode())
        type_js = un_seul(entetes_js, "Content-Type") or ""
        if statut == 200 and "javascript" in type_js:
            noter("OK", "Fichiers de l'interface servis avec le bon type")
        else:
            noter("ÉCHEC", "Fichiers de l'interface", f"{script.group(1).decode()} → {statut} {type_js}")
    return entetes


def controle_entetes(libelle, entetes, hsts_obligatoire=True):
    problemes, avertissements = [], []
    attendus = {
        "X-Content-Type-Options": lambda v: v == "nosniff",
        "X-Frame-Options": lambda v: v.upper() == "DENY",
        "Referrer-Policy": lambda v: v == "same-origin",
        "Content-Security-Policy": lambda v: "default-src 'self'" in v and "frame-ancestors 'none'" in v,
    }
    for nom, test in attendus.items():
        trouvees = valeurs(entetes, nom)
        if not trouvees:
            problemes.append(f"{nom} absent")
        elif not all(test(v) for v in trouvees):
            problemes.append(f"{nom} inattendu : {trouvees}")
        elif len(trouvees) > 1:
            avertissements.append(f"{nom} envoyé {len(trouvees)} fois (sans effet, valeurs identiques)")
    hsts = un_seul(entetes, "Strict-Transport-Security")
    duree = re.search(r"max-age=(\d+)", hsts or "")
    if not duree:
        # Django pose HSTS sur l'API ; sur les pages de l'interface, c'est à
        # nginx de le faire. Sans lui, le navigateur l'apprend au premier
        # appel à l'API, mais les testeurs en ligne le signalent.
        (problemes if hsts_obligatoire else avertissements).append("Strict-Transport-Security (HSTS) absent")
    elif int(duree.group(1)) < 3600:
        problemes.append(f"HSTS trop court : {hsts}")
    if len(valeurs(entetes, "Strict-Transport-Security")) > 1:
        problemes.append("HSTS envoyé plusieurs fois (contraire à la norme) : voir le `map $hsts_nginx`")
    serveur = un_seul(entetes, "Server") or ""
    if re.search(r"\d", serveur):
        problemes.append(f"le serveur annonce sa version : {serveur!r}")
    if problemes:
        noter("ÉCHEC", f"En-têtes de sécurité ({libelle})", " ; ".join(problemes))
    elif avertissements:
        noter("ATTENTION", f"En-têtes de sécurité ({libelle})", " ; ".join(avertissements))
    else:
        noter("OK", f"En-têtes de sécurité ({libelle})")


def controle_api(serveur):
    statut, entetes, corps = serveur.requete("GET", "/api/seances/")
    type_ = un_seul(entetes, "Content-Type") or ""
    if statut == 401 and "json" in type_:
        noter("OK", "API sans session : refus 401 en JSON")
    else:
        noter("ÉCHEC", "API sans session", f"réponse {statut} {type_}")
    controle_entetes("réponses de l'API", entetes)

    statut, _, corps = serveur.requete("GET", "/api/adresse-inexistante/")
    if b"Django tried these URL patterns" in corps or b"DEBUG = True" in corps or b"Traceback" in corps:
        noter("ÉCHEC", "Mode débogage", "une page d'erreur détaillée de Django est envoyée : DJANGO_DEBUG doit être False")
    else:
        noter("OK", "Pas de page d'erreur détaillée (mode débogage coupé)", f"adresse inconnue → {statut}")

    # En mode débogage, un envoi sur une adresse sans « / » final plante
    # (erreur 500, point 46) ; en production, Django redirige.
    statut, _, _ = serveur.requete("POST", "/api/token", corps=b"{}",
                                   entetes={"Content-Type": "application/json"})
    if statut >= 500:
        noter("ÉCHEC", "Envoi sur une adresse sans « / » final", f"erreur {statut}")
    else:
        noter("OK", "Envoi sur une adresse sans « / » final", f"réponse {statut}, pas d'erreur serveur")


def controle_acces_fermes(serveur):
    statut, _, _ = serveur.requete("GET", "/admin/")
    if statut == 403:
        noter("OK", "Administration Django fermée depuis l'extérieur (403)")
    else:
        noter("ATTENTION", "Administration Django ouverte depuis cet ordinateur",
              f"réponse {statut} : normal seulement depuis le réseau interne de l'université")
    for chemin in ("/media/documents/essai.pdf", "/media/", "/protected_media/documents/essai.pdf"):
        statut, _, _ = serveur.requete("GET", chemin)
        if statut == 404:
            noter("OK", f"{chemin} inaccessible (404)")
        else:
            noter("ÉCHEC", f"{chemin} accessible", f"réponse {statut} : les fichiers ne doivent passer que par l'API")


def controle_taille_envoi(serveur):
    """Un envoi de plus de 20 Mo doit être refusé par nginx, avant Django."""
    taille = 21 * 1024 * 1024
    conn = serveur.connexion(delai=60)
    try:
        conn.putrequest("POST", "/api/documents/")
        conn.putheader("Content-Type", "application/octet-stream")
        conn.putheader("Content-Length", str(taille))
        conn.endheaders()
        morceau = b"\0" * 65536
        try:
            for _ in range(taille // len(morceau)):
                conn.send(morceau)
        except OSError:
            pass  # nginx a refusé et fermé la connexion en cours d'envoi
        reponse = conn.getresponse()
        statut = reponse.status
    except OSError as exc:
        noter("ATTENTION", "Envoi de plus de 20 Mo", f"connexion coupée sans réponse lisible : {exc}")
        return
    finally:
        conn.close()
    if statut == 413:
        noter("OK", "Envoi de plus de 20 Mo refusé par le serveur (413)")
    else:
        noter("ÉCHEC", "Envoi de plus de 20 Mo", f"réponse {statut} au lieu de 413 (client_max_body_size)")


def se_connecter(serveur, identifiant, mot_de_passe):
    statut, _, corps = serveur.requete(
        "POST", "/api/token/",
        corps=json.dumps({"username": identifiant, "password": mot_de_passe}).encode(),
        entetes={"Content-Type": "application/json"},
    )
    if statut != 200:
        return None, statut
    return json.loads(corps)["access"], statut


def controle_telechargement(serveur, jeton, document):
    chemin = f"/api/documents/{document}/telecharger/"
    statut, _, _ = serveur.requete("GET", chemin)
    if statut == 401:
        noter("OK", "Téléchargement sans session refusé (401)")
    else:
        noter("ÉCHEC", "Téléchargement sans session", f"réponse {statut}")
    statut, entetes, corps = serveur.requete("GET", chemin, entetes={"Authorization": f"Bearer {jeton}"})
    disposition = un_seul(entetes, "Content-Disposition") or ""
    type_ = un_seul(entetes, "Content-Type") or ""
    fuite = valeurs(entetes, "X-Accel-Redirect")
    if fuite:
        noter("ÉCHEC", "Téléchargement protégé", "l'en-tête interne X-Accel-Redirect parvient au navigateur")
    elif statut == 200 and type_.startswith("text/html"):
        noter("ÉCHEC", "Téléchargement protégé", "le document est annoncé comme une page web (text/html)")
    elif statut == 200 and corps and "attachment" in disposition:
        noter("OK", "Téléchargement protégé servi par nginx", f"{len(corps)} octets, {type_}")
    else:
        noter("ÉCHEC", "Téléchargement protégé",
              f"réponse {statut}, {len(corps)} octets : vérifier DJANGO_PROTECTED_MEDIA_PREFIX "
              "et le bloc location /protected_media/ de nginx")


def controle_rafale(serveur, nombre=30):
    """
    Rafale de connexions simultanées, avec des identifiants et de faux
    X-Forwarded-For tous différents : la limitation doit freiner quand même
    (nginx d'abord, puis Django par adresse). Bloque ensuite les connexions
    depuis cet ordinateur une minute.
    """
    from concurrent.futures import ThreadPoolExecutor

    def tentative(i):
        try:
            return serveur.requete(
                "POST", "/api/token/",
                corps=json.dumps({"username": f"verif-{secrets.token_hex(6)}", "password": "x"}).encode(),
                entetes={"Content-Type": "application/json", "X-Forwarded-For": f"203.0.113.{i + 1}"},
            )[0]
        except OSError as exc:
            return repr(exc)

    with ThreadPoolExecutor(max_workers=nombre) as groupe:
        statuts = list(groupe.map(tentative, range(nombre)))
    refus = {code: statuts.count(code) for code in (429, 503) if code in statuts}
    autres = sorted({str(s) for s in statuts if s not in (401, 429, 503)})
    if autres:
        noter("ÉCHEC", "Rafale de connexions", f"réponses inattendues : {autres}")
    elif 503 in refus:
        noter("ATTENTION", "Rafale de connexions freinée, mais par une erreur 503",
              f"{refus[503]} refus sur {nombre} : l'interface affichera « Le serveur a rencontré une "
              "erreur » au lieu de « Trop de tentatives » ; ajouter `limit_req_status 429;` à nginx")
    elif refus:
        noter("OK", "Rafale de connexions freinée malgré de faux X-Forwarded-For",
              f"{refus[429]} refus 429 sur {nombre} envois simultanés")
    else:
        noter("ÉCHEC", "Rafale de connexions", f"{nombre} envois simultanés sans aucun refus")


def essayer(libelle, controle, *args):
    """Un contrôle sans réponse (serveur muet, coupure) est un échec, pas un arrêt."""
    try:
        return controle(*args)
    except OSError as exc:
        noter("ÉCHEC", libelle, f"pas de réponse du serveur : {exc!r}")
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--url", required=True, help="adresse HTTPS du site")
    parser.add_argument("--http", help="adresse HTTP correspondante (par défaut, la même en http://)")
    parser.add_argument("--identifiant")
    parser.add_argument("--document", type=int)
    parser.add_argument("--auto-signe", action="store_true")
    parser.add_argument("--sans-rafale", action="store_true")
    args = parser.parse_args()

    url = args.url.rstrip("/")
    if not url.startswith("https://"):
        sys.exit("--url doit commencer par https://")
    serveur = Serveur(url, args.auto_signe)
    print(f"Vérification de {url}\n", flush=True)

    if not controle_tls(serveur):
        sys.exit(1)
    controle_redirection_http(args.http or "http://" + url[len("https://"):], url)
    entetes_accueil = essayer("Interface", controle_interface, serveur)
    if entetes_accueil is not None:
        controle_entetes("pages de l'interface", entetes_accueil, hsts_obligatoire=False)
    essayer("API", controle_api, serveur)
    essayer("Accès fermés", controle_acces_fermes, serveur)
    essayer("Envoi de plus de 20 Mo", controle_taille_envoi, serveur)

    # Jeton fourni par la simulation locale (jamais en ligne de commande),
    # sinon connexion avec un compte de test dont le mot de passe est tapé.
    jeton = os.environ.get("EDT_VERIF_JETON")
    if not jeton and args.identifiant:
        mot_de_passe = getpass.getpass("Mot de passe du compte de test : ")
        debut = time.perf_counter()
        jeton, statut = essayer("Connexion du compte de test", se_connecter, serveur,
                                args.identifiant, mot_de_passe) or (None, "sans réponse")
        duree = time.perf_counter() - debut
        if not jeton:
            noter("ÉCHEC", "Connexion du compte de test", f"réponse {statut}")
        elif duree > 2:
            # Le calcul de vérification du mot de passe domine (point 48).
            noter("ATTENTION", f"Connexion lente : {duree:.1f} s",
                  "à la rentrée, beaucoup de connexions simultanées satureront le processeur")
        else:
            noter("OK", f"Connexion du compte de test en {duree:.1f} s")
    if args.document and jeton:
        essayer("Téléchargement protégé", controle_telechargement, serveur, jeton, args.document)
    else:
        noter("ATTENTION", "Téléchargement protégé non vérifié", "indiquer --identifiant et --document")

    if not args.sans_rafale:
        essayer("Rafale de connexions", controle_rafale, serveur)

    echecs, attentions = resultats.count("ÉCHEC"), resultats.count("ATTENTION")
    print(f"\n{len(resultats)} contrôles : {echecs} échec(s), {attentions} point(s) à examiner.")
    print("À faire aussi à la main, si l'adresse est publique : securityheaders.com et "
          "ssllabs.com/ssltest (note A attendue).")
    sys.exit(1 if echecs else 0)


if __name__ == "__main__":
    main()
