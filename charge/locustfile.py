"""
locustfile.py — test de charge de l'API EDT (étape 3 du plan « solidité et
sécurité », Phase A : en local, sur le serveur de développement).

Ce que ce test mesure en Phase A : quelles pages ralentissent le plus quand
le nombre d'utilisateurs monte, et si le serveur produit des erreurs (500) ou
des blocages de base. Les temps absolus sont pessimistes (serveur de
développement, DEBUG=True) : ils servent à comparer, pas à promettre un temps
en ligne. La Phase B rejoue le même fichier contre le serveur réel.

Préparation (base jetable edt_charge, jamais la base de développement) :
  1. DB_NAME=edt_charge ./.venv/Scripts/python.exe manage.py migrate
  2. DB_NAME=edt_charge ./.venv/Scripts/python.exe seed.py
  3. DB_NAME=edt_charge ./.venv/Scripts/python.exe charge/generer_sessions.py <tmp>/sessions.json
  4. Serveur sur edt_charge, port 8001 (entrée « django-charge » de .claude/launch.json)

Lancement (paliers de la Phase A : 10, 25 puis 50 utilisateurs) :
  set CHARGE_SESSIONS=<tmp>/sessions.json
  .venv-charge/Scripts/locust -f charge/locustfile.py --host http://127.0.0.1:8001 \
      --headless -u 25 -r 5 -t 3m --csv <tmp>/palier_25 Etudiant Enseignant Chef

Rafale de connexions (vérifie que la limitation tient sans erreur serveur) :
  set SEED_PASSWORD=...   (celui de .env)
  .venv-charge/Scripts/locust -f charge/locustfile.py --host http://127.0.0.1:8001 \
      --headless -u 20 -r 20 -t 1m Connexion

Les catégories d'utilisateurs sont choisies par leur nom en fin de commande :
filtrer par étiquette laisserait des catégories vides que Locust lance quand
même (environ un utilisateur virtuel sur dix perdu).

Supprimer <tmp>/sessions.json après le test : il contient des jetons valides.
"""
import itertools
import json
import os
import random

from locust import HttpUser, between, events, task

with open(os.environ["CHARGE_SESSIONS"], encoding="utf-8") as f:
    SESSIONS = json.load(f)

SEMAINE = SESSIONS["semaine"]
# Les comptes sont distribués à tour de rôle : plus d'utilisateurs virtuels
# que de comptes reviennent à plusieurs onglets ouverts sur un même compte.
_etudiants = itertools.cycle(SESSIONS["etudiants"])
_enseignants = itertools.cycle(SESSIONS["enseignants"])
_chefs = itertools.cycle(SESSIONS["chefs"])
_identifiants = itertools.cycle(SESSIONS["identifiants_connexion"])


class Authentifie(HttpUser):
    abstract = True
    wait_time = between(1, 4)  # un humain lit l'écran entre deux clics

    def entetes(self, jeton):
        return {"Authorization": f"Bearer {jeton}"}

    def get(self, url, nom):
        with self.client.get(url, headers=self.entetes(self.jeton), name=nom, catch_response=True) as r:
            if r.status_code == 429:
                r.failure("limitée (429)")
            elif r.status_code >= 400:
                r.failure(f"{r.status_code}")
            return r


class Etudiant(Authentifie):
    """Rentrée : la plupart des connexions sont des étudiants qui ouvrent leur planning."""
    weight = 6

    def on_start(self):
        self.jeton = next(_etudiants)

    @task(5)
    def planning_de_la_semaine(self):
        self.get(f"/api/etudiants/mon_planning/?semaine={SEMAINE}", "étudiant : planning semaine")

    @task(1)
    def documents(self):
        self.get("/api/documents/", "étudiant : documents")


class Enseignant(Authentifie):
    weight = 2

    def on_start(self):
        self.jeton = next(_enseignants)

    @task(4)
    def planning_de_la_semaine(self):
        self.get(f"/api/enseignants/mon_planning/?semaine={SEMAINE}", "enseignant : planning semaine")

    @task(2)
    def mes_modules(self):
        self.get("/api/modules/mes_modules/", "enseignant : mes modules")

    @task(1)
    def documents(self):
        self.get("/api/documents/", "enseignant : documents")


class Chef(Authentifie):
    """Le planning d'une classe se charge page par page, comme dans l'interface."""
    weight = 1

    def on_start(self):
        session = next(_chefs)
        self.jeton = session["jeton"]
        self.classes = session["classes"]

    @task(4)
    def planning_complet_d_une_classe(self):
        c = random.choice(self.classes)
        url = f"/api/seances/?classe_id={c['classe_id']}&semestre_id={c['semestre_id']}"
        pages = 0
        while url and pages < 30:
            r = self.get(url, "chef : planning classe (une page)")
            if r.status_code != 200:
                return
            url = r.json().get("next")
            pages += 1

    @task(1)
    def detection_des_conflits(self):
        # Plante pour les chefs (CORRECTIONS_A_FAIRE.md point 34) : on la garde
        # pour mesurer l'effet du correctif.
        c = random.choice(self.classes)
        self.get(f"/api/seances/conflits/?semestre_id={c['semestre_id']}", "chef : conflits")

    @task(2)
    def classes(self):
        self.get("/api/classes/", "chef : classes")


class Connexion(HttpUser):
    """Rafale de connexions réelles : la limitation doit répondre 429, jamais 500."""
    weight = 1
    wait_time = between(0.1, 0.5)

    @task
    def se_connecter(self):
        donnees = {"username": next(_identifiants), "password": os.environ.get("SEED_PASSWORD", "")}
        with self.client.post("/api/token/", json=donnees, name="connexion", catch_response=True) as r:
            if r.status_code >= 500:
                r.failure(f"erreur serveur {r.status_code}")
            else:
                r.success()  # 200 ou 429 : comportement attendu


@events.quitting.add_listener
def _bilan(environment, **_kwargs):
    stats = environment.stats.total
    if stats.num_requests and environment.runner.stats.errors:
        erreurs_serveur = sum(
            e.occurrences for e in environment.runner.stats.errors.values() if str(e.error).startswith("5")
        )
        if erreurs_serveur:
            print(f"\n!! {erreurs_serveur} erreurs serveur (5xx) pendant le test")
