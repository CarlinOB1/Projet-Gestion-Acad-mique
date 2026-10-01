# tests_securite_jetons.py
#
# Sessions (jetons JWT), limitation des tentatives et configuration de
# production (plan « solidité et sécurité », 2026-10-01).
#
# Même convention que tests_securite_roles.py : chaque test décrit la règle
# voulue ; @faille_connue(N) + renvoi à CORRECTIONS_A_FAIRE.md quand l'app ne
# la respecte pas encore ; « contrôle » = ce qui marche déjà.
#
# La configuration de production est vérifiée dans un processus Python séparé
# lancé avec DJANGO_DEBUG=False : les réglages sont calculés une seule fois,
# au chargement, et ne peuvent pas être rejoués en mode production depuis la
# suite de tests, qui tourne en mode développement.
#
# Lancement :
#   ./.venv/Scripts/python.exe manage.py test EDT_app.tests_securite_jetons --verbosity=2

import base64
import json
import os
import secrets
import subprocess
import sys
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client, SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from EDT_app.factories import ProfilFactory
from EDT_app.outils_tests import faille_connue
from EDT_app.tests_securite import make_user


def _b64(donnees):
    return base64.urlsafe_b64encode(json.dumps(donnees).encode()).rstrip(b"=").decode()


def _decode(segment):
    return json.loads(base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4)))


def client_jeton(jeton):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {jeton}")
    return client


# ══════════════════════════════════════════════════════════════════════════════
# 1. JETONS REFUSÉS
# ══════════════════════════════════════════════════════════════════════════════

class JetonsTest(TestCase):
    """Contrôles : un jeton falsifié, expiré ou orphelin ne donne accès à rien."""

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.user = make_user("porteur_jeton")
        ProfilFactory(user=self.user)
        self.autre = make_user("victime_jeton")
        ProfilFactory(user=self.autre)

    def test_controle_jeton_valide_accepte(self):
        jeton = AccessToken.for_user(self.user)
        self.assertEqual(client_jeton(jeton).get("/api/profils/me/").status_code, 200)

    def test_controle_jeton_modifie_a_la_main_refuse(self):
        # On change l'utilisateur dans le jeton sans pouvoir le re-signer.
        entete, contenu, signature = str(AccessToken.for_user(self.user)).split(".")
        donnees = _decode(contenu)
        donnees["user_id"] = str(self.autre.pk)
        falsifie = f"{entete}.{_b64(donnees)}.{signature}"
        self.assertEqual(client_jeton(falsifie).get("/api/profils/me/").status_code, 401)

    def test_controle_jeton_sans_signature_alg_none_refuse(self):
        donnees = _decode(str(AccessToken.for_user(self.user)).split(".")[1])
        donnees["user_id"] = str(self.autre.pk)
        falsifie = f"{_b64({'alg': 'none', 'typ': 'JWT'})}.{_b64(donnees)}."
        self.assertEqual(client_jeton(falsifie).get("/api/profils/me/").status_code, 401)

    def test_controle_jeton_expire_refuse(self):
        jeton = AccessToken.for_user(self.user)
        jeton.set_exp(from_time=timezone.now() - timedelta(hours=2))
        self.assertEqual(client_jeton(jeton).get("/api/profils/me/").status_code, 401)

    def test_controle_jeton_d_un_compte_supprime_refuse(self):
        jeton = AccessToken.for_user(self.user)
        self.user.delete()
        self.assertEqual(client_jeton(jeton).get("/api/profils/me/").status_code, 401)

    def test_controle_jeton_de_renouvellement_utilisable_une_seule_fois(self):
        jeton = str(RefreshToken.for_user(self.user))
        client = APIClient()
        premiere = client.post("/api/token/refresh/", {"refresh": jeton}, format="json")
        self.assertEqual(premiere.status_code, 200)
        seconde = client.post("/api/token/refresh/", {"refresh": jeton}, format="json")
        self.assertEqual(seconde.status_code, 401, "un jeton déjà renouvelé reste utilisable")

    def test_controle_jeton_de_renouvellement_refuse_comme_jeton_d_acces(self):
        jeton = RefreshToken.for_user(self.user)
        self.assertEqual(client_jeton(jeton).get("/api/profils/me/").status_code, 401)


# ══════════════════════════════════════════════════════════════════════════════
# 2. LIMITATION DES TENTATIVES
# ══════════════════════════════════════════════════════════════════════════════

class LimitationTentativesTest(TestCase):

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def test_controle_renouvellement_de_session_limite(self):
        # Limite globale des visiteurs : 60 requêtes par minute et par adresse.
        client = APIClient()
        codes = [
            client.post("/api/token/refresh/", {"refresh": "faux"}, format="json").status_code
            for _ in range(61)
        ]
        self.assertIn(429, codes, "aucune limite sur le renouvellement de session")

    @faille_connue(25)
    def test_connexion_a_l_administration_limitee(self):
        User.objects.create_superuser("admin_force_brute", password="Bon-mot-de-passe-42")
        client = Client()
        url = "/admin/login/?next=/admin/"
        for _ in range(10):
            client.post(url, {"username": "admin_force_brute", "password": "mauvais"})
        resp = client.post(url, {"username": "admin_force_brute", "password": "Bon-mot-de-passe-42"})
        self.assertNotEqual(
            resp.status_code, 302,
            "après 10 essais ratés, la page d'administration accepte encore une connexion",
        )


# ══════════════════════════════════════════════════════════════════════════════
# 3. EN-TÊTES DE SÉCURITÉ (valables aussi en développement)
# ══════════════════════════════════════════════════════════════════════════════

class EntetesSecuriteTest(TestCase):

    def test_controle_entetes_poses_par_django(self):
        user = make_user("lecteur_entetes")
        ProfilFactory(user=user)
        client = APIClient()
        client.force_authenticate(user=user)
        resp = client.get("/api/facultes/")
        self.assertEqual(resp.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(resp.headers.get("Referrer-Policy"), "same-origin")
        self.assertEqual(resp.headers.get("X-Frame-Options"), "DENY")


# ══════════════════════════════════════════════════════════════════════════════
# 4. CONFIGURATION DE PRODUCTION
# ══════════════════════════════════════════════════════════════════════════════

# Lancé dans un processus séparé avec les variables de production.
SONDE_PRODUCTION = """
import json, os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_edt.settings')
django.setup()
from django.conf import settings
from django.core import checks
from django.urls import Resolver404, resolve
try:
    resolve('/media/documents/cours.pdf')
    media_servi = True
except Resolver404:
    media_servi = False
avertissements = sorted(
    m.id for m in checks.run_checks(include_deployment_checks=True)
    if m.level >= checks.WARNING
)
print('SONDE=' + json.dumps({
    'debug': settings.DEBUG,
    'media_servi': media_servi,
    'avertissements': avertissements,
    'ssl_redirect': settings.SECURE_SSL_REDIRECT,
    'cookies_securises': settings.SESSION_COOKIE_SECURE and settings.CSRF_COOKIE_SECURE,
    'cors_identifiants': settings.CORS_ALLOW_CREDENTIALS,
    'api_navigable': 'rest_framework.renderers.BrowsableAPIRenderer'
        in settings.REST_FRAMEWORK.get('DEFAULT_RENDERER_CLASSES', []),
}))
"""

# Avertissements volontaires : HSTS démarre sans sous-domaines ni
# préchargement, puis monte une fois HTTPS stable (DEPLOIEMENT.md).
AVERTISSEMENTS_ACCEPTES = {"security.W005", "security.W021"}
# Contrainte conditionnelle d'unicité des classes ignorée par MySQL : voir
# tests_solidite.py, pas un réglage de production.
AVERTISSEMENTS_HORS_SUJET = {"models.W036"}


class ConfigurationProductionTest(SimpleTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = dict(os.environ)
        env.update({
            "DJANGO_DEBUG": "False",
            "DJANGO_SECRET_KEY": secrets.token_urlsafe(50),
            "DJANGO_ALLOWED_HOSTS": "edt.exemple.test",
        })
        env.pop("DJANGO_HTTPS", None)
        sortie = subprocess.run(
            [sys.executable, "-c", SONDE_PRODUCTION],
            cwd=settings.BASE_DIR, env=env, capture_output=True, text=True, timeout=120,
        )
        lignes = [l for l in sortie.stdout.splitlines() if l.startswith("SONDE=")]
        if not lignes:
            raise AssertionError(f"la sonde de production a échoué :\n{sortie.stderr[-2000:]}")
        cls.prod = json.loads(lignes[-1][len("SONDE="):])

    def test_controle_debug_desactive(self):
        self.assertFalse(self.prod["debug"])

    def test_controle_aucun_avertissement_de_deploiement_inattendu(self):
        inattendus = set(self.prod["avertissements"]) - AVERTISSEMENTS_ACCEPTES - AVERTISSEMENTS_HORS_SUJET
        self.assertEqual(inattendus, set())

    def test_controle_fichiers_media_non_servis_par_django(self):
        self.assertFalse(self.prod["media_servi"])

    def test_controle_https_impose(self):
        self.assertTrue(self.prod["ssl_redirect"])
        self.assertTrue(self.prod["cookies_securises"])

    def test_controle_api_navigable_desactivee(self):
        self.assertFalse(self.prod["api_navigable"])

    def test_cors_n_autorise_pas_l_envoi_d_identifiants(self):
        # Le jeton voyage dans l'en-tête Authorization : aucun cookie n'a besoin
        # de traverser les origines.
        self.assertFalse(self.prod["cors_identifiants"])
