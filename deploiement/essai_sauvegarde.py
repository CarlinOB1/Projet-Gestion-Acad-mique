"""
Essai de sauvegarde ET de restauration de la base (Phase B) : une sauvegarde
n'a de valeur que si on sait la restaurer.

    python deploiement/essai_sauvegarde.py [--base edt_charge] [--garder-fichier <dossier>]

Déroulé :
  1. sauvegarde de la base avec mysqldump (lecture seule, sans bloquer
     l'application : --single-transaction) ;
  2. restauration dans une base neuve `<base>_restauration`, créée avec le
     même jeu de caractères ;
  3. comparaison du nombre de lignes de chaque table ;
  4. suppression de la base restaurée (et du fichier de sauvegarde, sauf
     --garder-fichier).

Les identifiants MySQL sont ceux de l'application (.env, via les réglages
Django) : passés à mysqldump par un fichier d'options temporaire, jamais
affichés ni passés en ligne de commande. Sur le serveur, lancer avec le
.env de production ; mysqldump et mysql doivent être installés (paquet
mysql-client sous Linux).

Les fichiers déposés (DJANGO_MEDIA_ROOT) se sauvegardent à part, avec la
base : voir DEPLOIEMENT.md § 5.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)


def outil(nom):
    for candidat in (shutil.which(nom), rf"C:\Program Files\MySQL\MySQL Server 8.0\bin\{nom}.exe"):
        if candidat and os.path.exists(candidat):
            return candidat
    sys.exit(f"{nom} introuvable : installer le client MySQL.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="edt_charge")
    parser.add_argument("--garder-fichier", help="dossier où conserver le fichier de sauvegarde")
    args = parser.parse_args()

    os.environ["DB_NAME"] = args.base
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Gestion_edt.settings")
    import django
    django.setup()
    from django.conf import settings

    reglages = settings.DATABASES["default"]
    cible = f"{args.base}_restauration"
    mysqldump, mysql = outil("mysqldump"), outil("mysql")
    travail = tempfile.mkdtemp(prefix="edt-sauvegarde-")
    options = os.path.join(travail, "client.cnf")
    with open(options, "w", encoding="utf-8") as f:
        f.write(f"[client]\nuser={reglages['USER']}\npassword={reglages['PASSWORD']}\n"
                f"host={reglages['HOST'] or 'localhost'}\nport={reglages['PORT'] or 3306}\n")
    os.chmod(options, 0o600)
    connexion = [f"--defaults-extra-file={options}"]

    def requete(sql, base=None):
        commande = [mysql, *connexion, "-N", "-B", "-e", sql] + ([base] if base else [])
        return subprocess.run(commande, capture_output=True, text=True, check=True).stdout.split("\n")

    cree = False
    try:
        existe = requete(f"SELECT COUNT(*) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='{cible}'")
        if existe[0] != "0":
            sys.exit(f"La base {cible} existe déjà : la supprimer d'abord (essai précédent interrompu).")
        jeu, collation = requete(
            "SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME FROM information_schema.SCHEMATA "
            f"WHERE SCHEMA_NAME='{args.base}'"
        )[0].split("\t")

        fichier = os.path.join(travail, f"{args.base}.sql")
        debut = time.time()
        with open(fichier, "wb") as sortie:
            subprocess.run([mysqldump, *connexion, "--single-transaction", "--routines", "--triggers",
                            "--default-character-set=utf8mb4", "--no-tablespaces", args.base],
                           stdout=sortie, check=True)
        print(f"1. Sauvegarde : {os.path.getsize(fichier) / 1e6:.1f} Mo en {time.time() - debut:.0f} s", flush=True)

        requete(f"CREATE DATABASE `{cible}` CHARACTER SET {jeu} COLLATE {collation}")
        cree = True
        debut = time.time()
        with open(fichier, "rb") as entree:
            subprocess.run([mysql, *connexion, "--default-character-set=utf8mb4", cible], stdin=entree, check=True)
        print(f"2. Restauration dans {cible} : {time.time() - debut:.0f} s", flush=True)

        tables = [t for t in requete(
            f"SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA='{args.base}' "
            "AND TABLE_TYPE='BASE TABLE' ORDER BY TABLE_NAME") if t]

        def comptes(base):
            sql = " UNION ALL ".join(f"SELECT '{t}', COUNT(*) FROM `{base}`.`{t}`" for t in tables)
            return dict(ligne.split("\t") for ligne in requete(sql) if ligne)

        avant, apres = comptes(args.base), comptes(cible)
        ecarts = [f"{t} : {avant[t]} → {apres.get(t)}" for t in tables if avant[t] != apres.get(t)]
        total = sum(int(n) for n in avant.values())
        if ecarts:
            print("3. ÉCHEC : la base restaurée diffère de l'originale :\n   " + "\n   ".join(ecarts))
        else:
            print(f"3. OK : {len(tables)} tables, {total} lignes, identiques après restauration.")
        if args.garder_fichier:
            os.makedirs(args.garder_fichier, exist_ok=True)
            shutil.copy(fichier, args.garder_fichier)
            print(f"   Fichier de sauvegarde gardé dans {args.garder_fichier}")
        sys.exit(1 if ecarts else 0)
    finally:
        if cree:
            requete(f"DROP DATABASE `{cible}`")
            print(f"4. Base {cible} supprimée.")
        shutil.rmtree(travail, ignore_errors=True)


if __name__ == "__main__":
    main()
