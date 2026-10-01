# tests_solidite.py
#
# Solidité de l'API (plan « solidité et sécurité », 2026-10-01).
#
# Règle générale : aucune saisie, même absurde, ne doit faire planter le
# serveur (erreur 500). Une saisie invalide doit être refusée proprement
# (400) avec un message, et les règles métier (créneaux, doublons, volumes)
# doivent tenir, y compris sous requêtes simultanées.
#
# Même convention que tests_securite_roles.py : chaque test décrit la règle
# voulue ; @faille_connue(N) + renvoi à CORRECTIONS_A_FAIRE.md quand l'app ne
# la respecte pas encore ; « contrôle » = ce qui marche déjà.
#
# Les tests de requêtes simultanées sont marqués @tag('concurrence') et
# exclus du lancement normal (plus lents, dépendants de la machine) :
#   ./.venv/Scripts/python.exe manage.py test EDT_app.tests_solidite --exclude-tag concurrence -v2
#   ./.venv/Scripts/python.exe manage.py test EDT_app.tests_solidite --tag concurrence -v2

import json
import os
import shutil
import tempfile
import threading
from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, connection, connections, transaction
from django.test import TestCase, TransactionTestCase, override_settings, tag
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from EDT_app.factories import (
    AffectationModuleFactory,
    AnneeAcademiqueFactory,
    ClasseFactory,
    DepartementFactory,
    FiliereFactory,
    MatiereFactory,
    ModuleFactory,
    SeanceFactory,
    Semestre1Factory,
)
from EDT_app.models import (
    AffectationModule,
    Classe,
    DocumentPedagogique,
    Etudiant,
    Inscription,
    Seance,
)
from EDT_app.outils_tests import faille_connue
from EDT_app.tests_securite import PDF_MINIMAL, make_enseignant, make_etudiant, make_user

BLOCS = [(time(9, 0), time(11, 0)), (time(11, 15), time(13, 15)), (time(14, 15), time(16, 15))]


def client_de(user):
    client = APIClient()
    client.force_authenticate(user=User.objects.get(pk=user.pk))
    # Une erreur serveur doit devenir une réponse 500 observable, pas une
    # exception qui interrompt le test.
    client.raise_request_exception = False
    return client


def creneaux(depart, nombre):
    """`nombre` créneaux valides à partir de `depart` : 3 par jour, sans dimanche."""
    jour, resultat = depart, []
    while len(resultat) < nombre:
        if jour.weekday() != 6:
            for debut, fin in BLOCS:
                if len(resultat) < nombre:
                    resultat.append((jour, debut, fin))
        jour += timedelta(days=1)
    return resultat


class UniversSimple:
    """Un département, sa filière, une classe, un module, un enseignant, un chef, un étudiant, un admin."""

    def construire_univers(self):
        cache.clear()
        self.annee = AnneeAcademiqueFactory()
        self.sem1 = Semestre1Factory(annee=self.annee)
        self.dept = DepartementFactory(libelle="Département Solidité")
        self.filiere = FiliereFactory(libelle="Filière Solidité", departement=self.dept)
        self.classe = ClasseFactory(filiere=self.filiere, semestre=self.sem1, annee=self.annee)
        self.matiere = MatiereFactory(libelle="Matière Solidité", departement=self.dept)
        self.module = ModuleFactory(
            libelle="Module Solidité", matiere=self.matiere, semestre=self.sem1, credits=6,
        )
        self.ens = make_enseignant("ens_solidite", self.dept)
        self.chef = make_enseignant("chef_solidite", self.dept)
        self.dept.chef = self.chef
        self.dept.save()
        self.etu = make_etudiant("etu_solidite", self.classe)
        self.admin = User.objects.create_superuser("admin_solidite", password="pass1234")

    def seance(self, jour, debut, fin, statut="Confirmée", **kwargs):
        kwargs.setdefault("module", self.module)
        kwargs.setdefault("enseignant", self.ens)
        kwargs.setdefault("classe", self.classe)
        return SeanceFactory(
            annee=self.annee, date_seance=jour, heure_debut=debut, heure_fin=fin,
            type_seance="CM", statut=statut, **kwargs,
        )

    def assertAucunPlantage(self, requetes):
        """requetes : liste de (libellé, fonction). Échoue en listant celles qui plantent."""
        plantages = []
        for libelle, requete in requetes:
            resp = requete()
            if resp.status_code >= 500:
                plantages.append(f"{libelle} → {resp.status_code}")
        self.assertEqual(plantages, [], "erreurs serveur :\n" + "\n".join(plantages))

    def assertPasDePlantage(self, resp, contexte=""):
        self.assertLess(resp.status_code, 500, f"erreur serveur {contexte}: {resp.content[:300]!r}")


# ══════════════════════════════════════════════════════════════════════════════
# 1. SAISIES MALFORMÉES — CORRECTIONS_A_FAIRE.md point 27
# ══════════════════════════════════════════════════════════════════════════════

class SaisiesMalformeesTest(UniversSimple, TestCase):

    # Paramètres de filtre de chaque liste (lus dans les get_queryset de views.py).
    FILTRES = {
        "seances": ["classe_id", "enseignant_id", "semestre_id", "annee_id"],
        "classes": ["annee_id", "semestre_id", "filiere_id"],
        "etudiants": ["classe_id", "filiere_id", "parcours_id"],
        "enseignants": ["departement_id"],
        "modules": ["semestre_id", "matiere_id", "classe_id"],
        "affectations": ["module_id", "enseignant_id", "annee_id", "semestre_id"],
        "documents": ["module_id"],
        "filieres": ["departement_id"],
        "departements": ["faculte_id"],
        "semestres": ["annee_id"],
        "matieres": ["departement_id"],
    }
    VALEURS = ["abc", "1.5", "-1", "99999999999999999999", "1' OR '1'='1"]

    def setUp(self):
        self.construire_univers()
        self.client_admin = client_de(self.admin)

    def test_controle_dates_invalides_refusees_proprement(self):
        resp = self.client_admin.get("/api/seances/?date_debut=pas-une-date")
        self.assertEqual(resp.status_code, 400)

    def test_aucun_filtre_de_liste_ne_fait_planter_le_serveur(self):
        plantages = []
        for route, parametres in self.FILTRES.items():
            for parametre in parametres:
                for valeur in self.VALEURS:
                    resp = self.client_admin.get(f"/api/{route}/", {parametre: valeur})
                    if resp.status_code >= 500:
                        plantages.append(f"/api/{route}/?{parametre}={valeur}")
        self.assertEqual(plantages, [], f"{len(plantages)} combinaisons font planter le serveur")

    def test_conflits_avec_un_semestre_non_numerique(self):
        self.assertPasDePlantage(self.client_admin.get("/api/seances/conflits/?semestre_id=abc"))

    def test_planning_etudiant_avec_une_semaine_extreme(self):
        client = client_de(self.etu.profil.user)
        self.assertAucunPlantage([
            (semaine, lambda semaine=semaine: client.get(f"/api/etudiants/mon_planning/?semaine={semaine}"))
            for semaine in ("9999-12-31", "0001-01-01")
        ])

    def test_planning_enseignant_avec_une_semaine_extreme(self):
        client = client_de(self.ens.profil.user)
        self.assertPasDePlantage(client.get("/api/enseignants/mon_planning/?semaine=9999-12-31"))

    def test_planning_avec_un_semestre_non_numerique(self):
        self.assertAucunPlantage([
            (route, lambda user=user, route=route: client_de(user).get(f"/api/{route}/mon_planning/?semestre_id=x"))
            for user, route in ((self.etu.profil.user, "etudiants"), (self.ens.profil.user, "enseignants"))
        ])

    def test_publier_en_masse_avec_un_corps_malforme(self):
        brouillon = self.seance(self.sem1.date_debut, *BLOCS[0], statut="brouillon")
        corps = {
            "nombre seul": {"seance_ids": brouillon.pk},
            "texte": {"seance_ids": f"{brouillon.pk},{brouillon.pk}"},
            "liste nue": [brouillon.pk],
            "objet": {"seance_ids": {"a": 1}},
        }
        self.assertAucunPlantage([
            (libelle, lambda donnees=donnees: self.client_admin.post(
                "/api/seances/publier_masse/", json.dumps(donnees), content_type="application/json"))
            for libelle, donnees in corps.items()
        ])

    def test_controle_publier_en_masse_avec_dix_mille_identifiants(self):
        resp = self.client_admin.post(
            "/api/seances/publier_masse/", {"seance_ids": list(range(1, 10001))}, format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_passer_au_semestre_suivant_avec_un_semestre_non_numerique(self):
        resp = self.client_admin.post(
            f"/api/classes/{self.classe.pk}/passer_semestre/", {"semestre_cible_id": "abc"}, format="json",
        )
        self.assertPasDePlantage(resp)

    def test_controle_corps_de_requete_trop_volumineux(self):
        # Au-delà de 2,5 Mo (limite Django par défaut), refus propre attendu.
        resp = self.client_admin.post(
            "/api/facultes/", json.dumps({"libelle": "x" * (3 * 1024 * 1024)}),
            content_type="application/json",
        )
        self.assertPasDePlantage(resp)
        self.assertNotEqual(resp.status_code, 201)


# ══════════════════════════════════════════════════════════════════════════════
# 2. SUPPRESSIONS BLOQUÉES ET CAS LIMITES — CORRECTIONS_A_FAIRE.md point 28
# ══════════════════════════════════════════════════════════════════════════════

class SuppressionsEtCasLimitesTest(UniversSimple, TestCase):

    def setUp(self):
        self.construire_univers()
        self.client_admin = client_de(self.admin)

    def test_supprimer_un_departement_qui_a_des_enseignants(self):
        resp = self.client_admin.delete(f"/api/departements/{self.dept.pk}/")
        self.assertPasDePlantage(resp)
        self.assertIn(resp.status_code, (400, 409))

    def test_supprimer_une_classe_qui_a_des_etudiants(self):
        resp = self.client_admin.delete(f"/api/classes/{self.classe.pk}/")
        self.assertPasDePlantage(resp)
        self.assertIn(resp.status_code, (400, 409))

    def test_admin_sans_profil_consulte_son_profil(self):
        self.assertPasDePlantage(self.client_admin.get("/api/profils/me/"))

    def test_admin_sans_profil_depose_un_document(self):
        resp = self.client_admin.post("/api/documents/", {
            "titre": "Cours", "module_id": self.module.pk,
            "fichier": SimpleUploadedFile("cours.pdf", PDF_MINIMAL, content_type="application/pdf"),
        }, format="multipart")
        self.assertPasDePlantage(resp)

    def test_telecharger_un_document_dont_le_fichier_a_disparu(self):
        media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media, ignore_errors=True)
        with override_settings(MEDIA_ROOT=media):
            doc = DocumentPedagogique.objects.create(
                titre="Cours", module=self.module, enseignant=self.ens,
                fichier=SimpleUploadedFile("cours.pdf", PDF_MINIMAL, content_type="application/pdf"),
            )
            os.remove(doc.fichier.path)
            resp = self.client_admin.get(f"/api/documents/{doc.pk}/telecharger/")
        self.assertPasDePlantage(resp)
        self.assertEqual(resp.status_code, 404)

    def test_supprimer_un_module_efface_aussi_ses_fichiers(self):
        media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media, ignore_errors=True)
        with override_settings(MEDIA_ROOT=media):
            doc = DocumentPedagogique.objects.create(
                titre="Cours", module=self.module, enseignant=self.ens,
                fichier=SimpleUploadedFile("cours.pdf", PDF_MINIMAL, content_type="application/pdf"),
            )
            chemin = doc.fichier.path
            self.assertEqual(self.client_admin.delete(f"/api/modules/{self.module.pk}/").status_code, 204)
            self.assertFalse(os.path.exists(chemin), "fichier orphelin resté sur le disque")

    def test_supprimer_une_annee_qui_a_des_etudiants(self):
        resp = self.client_admin.delete(f"/api/annees/{self.annee.pk}/")
        self.assertPasDePlantage(resp)
        self.assertTrue(Etudiant.objects.filter(pk=self.etu.pk).exists())


# ══════════════════════════════════════════════════════════════════════════════
# 2 bis. SUPPRIMER UN ENSEIGNANT — CORRECTIONS_A_FAIRE.md point 36
# ══════════════════════════════════════════════════════════════════════════════

class SuppressionEnseignantTest(UniversSimple, TestCase):
    """
    Supprimer un enseignant effaçait en cascade ses séances (y compris celles
    déjà faites), ses affectations et ses documents. Règle validée le
    2026-10-01 : à terme, suppression permise en gardant les séances
    effectuées à son nom ; en attendant, refus avec proposition de suspension.
    """

    def setUp(self):
        media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=media)
        override.enable()
        self.addCleanup(override.disable)

        self.construire_univers()
        self.seance_faite = self.seance(self.sem1.date_debut, *BLOCS[0])
        AffectationModuleFactory(module=self.module, enseignant=self.ens)
        self.doc = DocumentPedagogique.objects.create(
            titre="Cours", module=self.module, enseignant=self.ens,
            fichier=SimpleUploadedFile("cours.pdf", PDF_MINIMAL, content_type="application/pdf"),
        )

    def test_supprimer_un_enseignant_qui_a_des_seances_est_refuse(self):
        resp = client_de(self.admin).delete(f"/api/enseignants/{self.ens.pk}/")
        self.assertIn(resp.status_code, (400, 409), resp.content[:300])
        self.assertIn("Suspendez", str(resp.data))
        self.assertTrue(Seance.objects.filter(pk=self.seance_faite.pk).exists(), "séance effacée")

    def test_controle_supprimer_un_enseignant_sans_activite(self):
        sans_activite = make_enseignant("ens_sans_activite", self.dept)
        resp = client_de(self.admin).delete(f"/api/enseignants/{sans_activite.pk}/")
        self.assertEqual(resp.status_code, 204)


# ══════════════════════════════════════════════════════════════════════════════
# 2 ter. TEXTES TRÈS LONGS — CORRECTIONS_A_FAIRE.md point 37
# ══════════════════════════════════════════════════════════════════════════════

class TextesTresLongsTest(UniversSimple, TestCase):
    """
    Un texte d'un million de caractères (sous la limite de 2,5 Mo par
    requête) doit être refusé proprement, pas planter ni être tronqué en
    silence par la base.
    """

    UN_MILLION = "x" * 1_000_000

    def setUp(self):
        self.construire_univers()
        self.client_admin = client_de(self.admin)

    @faille_connue(37)
    def test_description_de_module_d_un_million_de_caracteres(self):
        resp = self.client_admin.patch(
            f"/api/modules/{self.module.pk}/", {"description": self.UN_MILLION}, format="json",
        )
        self.assertEqual(resp.status_code, 400, resp.content[:200])

    def test_controle_motif_de_suspension_limite_par_changer_statut(self):
        resp = self.client_admin.patch(
            f"/api/profils/{self.ens.pk}/changer_statut/",
            {"statut": "suspendu", "motif_suspension": self.UN_MILLION}, format="json",
        )
        self.assertEqual(resp.status_code, 400, resp.content[:200])

    @faille_connue(37)
    def test_motif_de_suspension_d_un_million_de_caracteres_par_la_fiche(self):
        # Le même motif passe par une simple modification de la fiche profil
        # (voir aussi le point 20 : statut et motif y sont modifiables).
        resp = self.client_admin.patch(
            f"/api/profils/{self.ens.pk}/",
            {"statut": "suspendu", "motif_suspension": self.UN_MILLION}, format="json",
        )
        self.assertEqual(resp.status_code, 400, resp.content[:200])


# ══════════════════════════════════════════════════════════════════════════════
# 3. SÉANCES : SAISIES PARTIELLES ET VALEURS LIMITES — CORRECTIONS_A_FAIRE.md point 29
# ══════════════════════════════════════════════════════════════════════════════

class SeancesSaisiesTest(UniversSimple, TestCase):

    def setUp(self):
        self.construire_univers()
        self.client_chef = client_de(self.chef.profil.user)

    def _payload(self, **surcharges):
        donnees = {
            "module_id": self.module.pk, "enseignant_id": self.ens.pk,
            "classe_id": self.classe.pk, "annee_id": self.annee.pk,
            "date_seance": str(self.sem1.date_debut + timedelta(days=1)),
            "heure_debut": "09:00", "heure_fin": "11:00",
            "type_seance": "CM", "statut": "Confirmée",
        }
        donnees.update(surcharges)
        return donnees

    def test_controle_creation_valide(self):
        self.assertEqual(self.client_chef.post("/api/seances/", self._payload(), format="json").status_code, 201)

    def test_controle_valeurs_absurdes_refusees(self):
        cas = {
            "fin avant début": {"heure_debut": "11:00", "heure_fin": "09:00"},
            "dimanche": {"date_seance": "2025-09-07"},
            "année 9999": {"date_seance": "9999-12-31"},
            "année 0001": {"date_seance": "0001-01-01"},
            "heure impossible": {"heure_debut": "25:00"},
            "type inconnu": {"type_seance": "XX"},
            "module inexistant": {"module_id": 99999999},
        }
        for libelle, surcharge in cas.items():
            with self.subTest(cas=libelle):
                resp = self.client_chef.post("/api/seances/", self._payload(**surcharge), format="json")
                self.assertEqual(resp.status_code, 400, resp.content[:300])

    def test_annuler_une_seance_par_modification_partielle(self):
        seance = self.seance(self.sem1.date_debut, *BLOCS[0])
        resp = self.client_chef.patch(f"/api/seances/{seance.pk}/", {"statut": "Annulée"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content[:300])
        self.assertEqual(Seance.objects.get(pk=seance.pk).statut, "Annulée")


# ══════════════════════════════════════════════════════════════════════════════
# 4. PASSAGE AU SEMESTRE SUIVANT — CORRECTIONS_A_FAIRE.md point 30
# ══════════════════════════════════════════════════════════════════════════════

class PasserSemestreTest(UniversSimple, TestCase):

    def setUp(self):
        self.construire_univers()
        self.client_chef = client_de(self.chef.profil.user)
        self.sem2 = Semestre1Factory(
            annee=self.annee, libelle="Semestre 2",
            date_debut=date(2026, 2, 2), date_fin=date(2026, 6, 30),
        )

    def test_controle_les_etudiants_changent_de_classe(self):
        resp = self.client_chef.post(
            f"/api/classes/{self.classe.pk}/passer_semestre/", {"semestre_cible_id": self.sem2.pk}, format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Etudiant.objects.get(pk=self.etu.pk).classe.semestre_id, self.sem2.pk)

    def test_le_passage_ouvre_une_inscription_dans_la_nouvelle_classe(self):
        self.client_chef.post(
            f"/api/classes/{self.classe.pk}/passer_semestre/", {"semestre_cible_id": self.sem2.pk}, format="json",
        )
        nouvelle = Etudiant.objects.get(pk=self.etu.pk).classe
        self.assertTrue(
            Inscription.objects.filter(etudiant=self.etu, classe=nouvelle, statut="active").exists(),
            "étudiant déplacé sans inscription active dans sa nouvelle classe",
        )

    def test_une_classe_l1_passe_dans_la_classe_de_meme_code(self):
        # Avec MIP et BCG en S1 et en S2, la classe cible se choisit par son code.
        sources = {}
        for code in ("MIP", "BCG"):
            sources[code] = Classe.objects.create(filiere=None, code=code, parcours=self.classe.parcours,
                                                  semestre=self.sem1, annee=self.annee)
            Classe.objects.create(filiere=None, code=code, parcours=self.classe.parcours,
                                  semestre=self.sem2, annee=self.annee)
        etu_l1 = make_etudiant("etu_l1_mip", classe=sources["MIP"])
        # Les classes de L1 dépendent de la faculté : c'est la scolarité qui les gère.
        resp = client_de(self.admin).post(
            f"/api/classes/{sources['MIP'].pk}/passer_semestre/", {"semestre_cible_id": self.sem2.pk}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content[:300])
        nouvelle = Etudiant.objects.get(pk=etu_l1.pk).classe
        self.assertEqual((nouvelle.code, nouvelle.semestre_id), ("MIP", self.sem2.pk))

    def test_semestre_cible_d_une_autre_annee_refuse(self):
        autre_annee = AnneeAcademiqueFactory(
            libelle="2026-2027", date_debut=date(2026, 9, 1), date_fin=date(2027, 6, 30),
        )
        sem_autre = Semestre1Factory(
            annee=autre_annee, date_debut=date(2026, 9, 1), date_fin=date(2027, 1, 31),
        )
        resp = self.client_chef.post(
            f"/api/classes/{self.classe.pk}/passer_semestre/", {"semestre_cible_id": sem_autre.pk}, format="json",
        )
        self.assertEqual(resp.status_code, 400)


# ══════════════════════════════════════════════════════════════════════════════
# 5. DOUBLONS — CORRECTIONS_A_FAIRE.md point 31
# ══════════════════════════════════════════════════════════════════════════════

class DoublonsTest(UniversSimple, TestCase):

    def setUp(self):
        self.construire_univers()
        self.client_admin = client_de(self.admin)

    def test_deux_annees_academiques_du_meme_nom(self):
        resp = self.client_admin.post("/api/annees/", {
            "libelle": self.annee.libelle, "date_debut": "2025-09-02", "date_fin": "2026-06-29",
        }, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_deux_affectations_generiques_identiques(self):
        donnees = {"module_id": self.module.pk, "enseignant_id": self.ens.pk, "heures_prevues": 12}
        self.assertEqual(self.client_admin.post("/api/affectations/", donnees, format="json").status_code, 201)
        resp = self.client_admin.post("/api/affectations/", donnees, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(AffectationModule.objects.filter(module=self.module, enseignant=self.ens).count(), 1)

    def test_controle_deux_classes_identiques_refusees_par_l_api(self):
        donnees = {
            "parcours_id": self.classe.parcours_id, "filiere_id": self.filiere.pk,
            "semestre_id": self.sem1.pk, "annee_id": self.annee.pk, "code": "",
        }
        resp = self.client_admin.post("/api/classes/", donnees, format="json")
        self.assertEqual(resp.status_code, 400, resp.content[:300])
        self.assertNotIn("code", resp.data, "refus dû au champ code, pas au doublon")

    def _doublon_refuse_par_la_base(self, objet):
        # bulk_create contourne toutes les vérifications Python : seule la
        # base peut refuser (cas de deux enregistrements simultanés).
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                type(objet).objects.bulk_create([objet])

    def test_la_base_interdit_elle_meme_les_classes_en_double(self):
        # MySQL ignore les contraintes d'unicité conditionnelles : les
        # contraintes de Classe sont écrites pour s'en passer.
        self._doublon_refuse_par_la_base(Classe(
            libelle="doublon", code=self.classe.code, parcours=self.classe.parcours,
            filiere=self.filiere, semestre=self.sem1, annee=self.annee,
        ))

    def test_la_base_interdit_elle_meme_les_classes_l1_en_double(self):
        l1 = Classe.objects.create(filiere=None, code="MIP", parcours=self.classe.parcours,
                                   semestre=self.sem1, annee=self.annee)
        self._doublon_refuse_par_la_base(Classe(
            libelle="doublon", code="MIP", parcours=l1.parcours, filiere=None,
            semestre=self.sem1, annee=self.annee,
        ))

    def test_controle_deux_classes_l1_de_codes_differents_acceptees(self):
        for code in ("MIP", "BCG"):
            Classe.objects.create(filiere=None, code=code, parcours=self.classe.parcours,
                                  semestre=self.sem1, annee=self.annee)
        self.assertEqual(Classe.objects.filter(filiere=None, semestre=self.sem1).count(), 2)

    def test_la_base_interdit_elle_meme_les_affectations_generiques_en_double(self):
        AffectationModule.objects.bulk_create([
            AffectationModule(module=self.module, enseignant=self.ens, heures_prevues=12),
        ])
        self._doublon_refuse_par_la_base(
            AffectationModule(module=self.module, enseignant=self.ens, heures_prevues=12),
        )


# ══════════════════════════════════════════════════════════════════════════════
# 6. SÉANCES REPORTÉES ET CRÉNEAUX — CORRECTIONS_A_FAIRE.md point 32
# ══════════════════════════════════════════════════════════════════════════════

class CreneauxSeancesReporteesTest(UniversSimple, TestCase):
    """
    Une séance reportée occupe son NOUVEAU créneau et libère l'ancien.
    Un autre cours ne doit donc pas pouvoir être placé sur le nouveau créneau
    avec le même enseignant, mais doit pouvoir l'être sur l'ancien.
    """

    def setUp(self):
        self.construire_univers()
        self.lundi = self.sem1.date_debut
        self.mardi = self.lundi + timedelta(days=1)
        self.reportee = self.seance(self.lundi, *BLOCS[0])
        resp = client_de(self.chef.profil.user).patch(
            f"/api/seances/{self.reportee.pk}/reporter/",
            {"date_report": str(self.mardi), "heure_debut_report": "09:00", "heure_fin_report": "11:00"},
            format="json",
        )
        assert resp.status_code == 200, resp.content
        self.autre_classe = ClasseFactory(
            filiere=FiliereFactory(libelle="Filière Solidité 2", departement=self.dept),
            semestre=self.sem1, annee=self.annee,
        )

    def _nouvelle(self, jour):
        return Seance(
            module=self.module, enseignant=self.ens, classe=self.autre_classe, annee=self.annee,
            date_seance=jour, heure_debut=BLOCS[0][0], heure_fin=BLOCS[0][1],
            type_seance="CM", statut="Confirmée",
        )

    def test_le_nouveau_creneau_est_bloque_pour_l_enseignant(self):
        with self.assertRaises(ValidationError):
            self._nouvelle(self.mardi).full_clean()

    def test_l_ancien_creneau_est_libere(self):
        self._nouvelle(self.lundi).full_clean()

    def test_la_detection_des_conflits_voit_les_seances_reportees(self):
        self._nouvelle(self.mardi).save_base(raw=True)  # contourne la validation
        resp = client_de(self.admin).get(f"/api/seances/conflits/?semestre_id={self.sem1.pk}")
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(resp.data["count"], 2)

    def test_controle_seances_mutualisees_pas_en_conflit(self):
        # Même enseignant, même créneau réel, deux classes : c'est voulu
        # quand les deux séances sont liées (cours mutualisé).
        jumelle = self._nouvelle(self.mardi)
        jumelle.seance_liee = self.reportee
        jumelle.save_base(raw=True)
        resp = client_de(self.admin).get(f"/api/seances/conflits/?semestre_id={self.sem1.pk}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 0)

    def test_controle_taille_de_page_demandee(self):
        # V5 : l'interface demande une semaine entière en une page ; une
        # valeur absurde retombe sur 20, une valeur énorme est plafonnée.
        client = client_de(self.admin)
        for valeur in ("abc", "-1", "0", "100000"):
            with self.subTest(page_size=valeur):
                self.assertEqual(client.get(f"/api/seances/?page_size={valeur}").status_code, 200)
        self.assertEqual(len(client.get("/api/seances/?page_size=1").data["results"]), 1)


# ══════════════════════════════════════════════════════════════════════════════
# 7. NOMBRE DE REQUÊTES PAR PAGE — CORRECTIONS_A_FAIRE.md point 33
# ══════════════════════════════════════════════════════════════════════════════

class NombreDeRequetesTest(UniversSimple, TestCase):
    """
    Passer de 5 à 15 lignes ne doit presque rien ajouter : une requête de
    plus par ligne est le signe d'une lenteur qui grandira avec les données
    (planning du chef : 21 s mesurées le 2026-09-23).
    """

    TOLERANCE = 3  # requêtes supplémentaires admises pour 10 lignes de plus

    def setUp(self):
        self.construire_univers()
        self.etapes = creneaux(self.sem1.date_debut, 15)

    def _compter(self, client, url):
        with CaptureQueriesContext(connection) as requetes:
            resp = client.get(url)
        self.assertEqual(resp.status_code, 200, resp.content[:300])
        return len(requetes)

    def _mesurer(self, client, url):
        for jour, debut, fin in self.etapes[:5]:
            self.seance(jour, debut, fin)
        avant = self._compter(client, url)
        for jour, debut, fin in self.etapes[5:]:
            self.seance(jour, debut, fin)
        apres = self._compter(client, url)
        self.assertLessEqual(
            apres - avant, self.TOLERANCE,
            f"{url} : {avant} requêtes pour 5 lignes, {apres} pour 15",
        )

    def test_liste_des_seances(self):
        self._mesurer(client_de(self.admin), f"/api/seances/?classe_id={self.classe.pk}")

    def test_planning_etudiant(self):
        self._mesurer(client_de(self.etu.profil.user), "/api/etudiants/mon_planning/")

    def test_planning_enseignant(self):
        self._mesurer(client_de(self.ens.profil.user), "/api/enseignants/mon_planning/")

    def test_controle_detection_des_conflits(self):
        self._mesurer(client_de(self.admin), f"/api/seances/conflits/?semestre_id={self.sem1.pk}")

    def test_liste_des_modules(self):
        client = client_de(self.admin)
        url = f"/api/modules/?semestre_id={self.sem1.pk}"

        def ajouter(debut, fin):
            for i in range(debut, fin):
                module = ModuleFactory(libelle=f"Module requêtes {i}", matiere=self.matiere, semestre=self.sem1)
                AffectationModuleFactory(module=module, enseignant=self.ens)

        ajouter(0, 5)
        avant = self._compter(client, url)
        ajouter(5, 15)
        apres = self._compter(client, url)
        self.assertLessEqual(apres - avant, self.TOLERANCE, f"{avant} requêtes pour 5 modules, {apres} pour 15")

    def test_liste_des_affectations(self):
        client = client_de(self.admin)
        url = f"/api/affectations/?enseignant_id={self.ens.pk}"

        def ajouter(debut, fin):
            for i in range(debut, fin):
                module = ModuleFactory(libelle=f"Module affectation {i}", matiere=self.matiere, semestre=self.sem1)
                AffectationModuleFactory(module=module, enseignant=self.ens)

        ajouter(0, 5)
        avant = self._compter(client, url)
        ajouter(5, 15)
        apres = self._compter(client, url)
        self.assertLessEqual(apres - avant, self.TOLERANCE, f"{avant} requêtes pour 5 affectations, {apres} pour 15")


# ══════════════════════════════════════════════════════════════════════════════
# 8. REQUÊTES SIMULTANÉES — CORRECTIONS_A_FAIRE.md point 9
# ══════════════════════════════════════════════════════════════════════════════

@tag("concurrence")
class RequetesSimultaneesTest(UniversSimple, TransactionTestCase):
    """
    Deux gestionnaires valident en même temps (deux onglets, deux bureaux).
    Les deux fils démarrent ensemble grâce à une barrière, 20 fois de suite.
    """

    REPETITIONS = 20

    @staticmethod
    def _vider_tables_application():
        # Django vide la base entre deux TransactionTestCase, mais sous Windows
        # MySQL renvoie les noms de tables en minuscules (« edt_app_seance »)
        # et Django ne reconnaît plus les siennes (« EDT_app_seance ») : les
        # données de l'application restaient d'un test (et d'un lancement
        # --keepdb) à l'autre. On les vide donc nous-mêmes.
        from django.apps import apps
        with connection.cursor() as curseur:
            curseur.execute("SET FOREIGN_KEY_CHECKS = 0")
            try:
                for modele in apps.get_app_config("EDT_app").get_models(include_auto_created=True):
                    curseur.execute(f"DELETE FROM {connection.ops.quote_name(modele._meta.db_table)}")
            finally:
                curseur.execute("SET FOREIGN_KEY_CHECKS = 1")

    def setUp(self):
        self._vider_tables_application()
        self.addCleanup(self._vider_tables_application)
        self.construire_univers()
        self.autre_classe = ClasseFactory(
            filiere=FiliereFactory(libelle="Filière Solidité 3", departement=self.dept),
            semestre=self.sem1, annee=self.annee,
        )

    def _en_parallele(self, *fonctions):
        barriere = threading.Barrier(len(fonctions))
        resultats = [None] * len(fonctions)

        def lancer(i, fonction):
            try:
                barriere.wait()
                resultats[i] = fonction()
            except Exception as exc:  # noqa: BLE001 — on veut tout remonter
                resultats[i] = exc
            finally:
                connections.close_all()

        fils = [threading.Thread(target=lancer, args=(i, f)) for i, f in enumerate(fonctions)]
        for f in fils:
            f.start()
        for f in fils:
            f.join(timeout=60)
        return resultats

    def test_controle_meme_enseignant_meme_creneau_une_seule_seance(self):
        etapes = creneaux(self.sem1.date_debut, self.REPETITIONS)
        doublons, plantages = [], []
        for jour, debut, fin in etapes:
            def creer(classe):
                def appel():
                    client = client_de(self.chef.profil.user)
                    return client.post("/api/seances/", {
                        "module_id": self.module.pk, "enseignant_id": self.ens.pk,
                        "classe_id": classe.pk, "annee_id": self.annee.pk,
                        "date_seance": str(jour), "heure_debut": debut.strftime("%H:%M"),
                        "heure_fin": fin.strftime("%H:%M"), "type_seance": "CM", "statut": "Confirmée",
                    }, format="json").status_code
                return appel

            codes = self._en_parallele(creer(self.classe), creer(self.autre_classe))
            if any(isinstance(c, Exception) or c >= 500 for c in codes):
                plantages.append((str(jour), codes))
            n = Seance.objects.filter(enseignant=self.ens, date_seance=jour, heure_debut=debut).count()
            if n > 1:
                doublons.append(str(jour))
        self.assertEqual(plantages, [], "erreurs serveur sous requêtes simultanées")
        self.assertEqual(doublons, [], "enseignant réservé deux fois sur le même créneau")

    def test_controle_publications_croisees_sans_blocage(self):
        # Deux gestionnaires publient en masse les mêmes séances, listées dans
        # l'ordre inverse : risque d'interblocage MySQL (erreur 1213).
        ens2 = make_enseignant("ens_solidite_2", self.dept)
        # Un module par enseignant : 20 répétitions de 2 h tiennent dans le
        # volume de chacun (72 h).
        module2 = ModuleFactory(
            libelle="Module Solidité 2", matiere=self.matiere, semestre=self.sem1, credits=6,
        )
        plantages = []
        for jour, debut, fin in creneaux(self.sem1.date_debut, self.REPETITIONS):
            s1 = self.seance(jour, debut, fin, statut="brouillon")
            s2 = self.seance(
                jour, debut, fin, statut="brouillon", module=module2, enseignant=ens2, classe=self.autre_classe,
            )

            def publier(ids):
                def appel():
                    return client_de(self.admin).post(
                        "/api/seances/publier_masse/", {"seance_ids": ids}, format="json",
                    ).status_code
                return appel

            codes = self._en_parallele(publier([s1.pk, s2.pk]), publier([s2.pk, s1.pk]))
            if any(isinstance(c, Exception) or c >= 500 for c in codes):
                plantages.append((str(jour), [repr(c) for c in codes]))
        self.assertEqual(plantages, [], "interblocage ou erreur serveur")

    @faille_connue(38)
    def test_reinscriptions_simultanees_une_seule_inscription_active(self):
        # Deux réinscriptions du même étudiant vers deux classes différentes,
        # au même instant (double clic, deux onglets, import en parallèle).
        parcours = self.classe.parcours
        classe2 = ClasseFactory(
            parcours=parcours, filiere=FiliereFactory(libelle="Filière Réinscription 2", departement=self.dept),
            semestre=self.sem1, annee=self.annee,
        )
        classe3 = ClasseFactory(
            parcours=parcours, filiere=FiliereFactory(libelle="Filière Réinscription 3", departement=self.dept),
            semestre=self.sem1, annee=self.annee,
        )
        doubles, plantages = [], []
        for i in range(self.REPETITIONS):
            etu = make_etudiant(f"etu_reinscription_{i}", self.classe)

            def reinscrire(classe, pk=etu.pk):
                return lambda: Etudiant.objects.get(pk=pk).reinscrire(classe)

            resultats = self._en_parallele(reinscrire(classe2), reinscrire(classe3))
            plantages += [repr(r) for r in resultats if isinstance(r, Exception)]
            actives = Inscription.objects.filter(etudiant_id=etu.pk, statut="active").count()
            if actives > 1:
                doubles.append(f"étudiant {i} : {actives} inscriptions actives")
        self.assertEqual(
            (plantages, doubles), ([], []),
            f"{len(plantages)} erreurs (dont interblocages MySQL 1213) et {len(doubles)} étudiants "
            f"inscrits deux fois, sur {self.REPETITIONS} répétitions",
        )
