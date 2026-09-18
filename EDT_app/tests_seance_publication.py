# tests_seance_publication.py
#
# Tests des actions custom SeanceViewSet.publier / depublier / publier_masse
# (EDT_app/views.py) : le seul mécanisme de publication/dépublication de
# séances en masse de l'application (brouillon <-> Confirmée). Aucune des
# trois actions n'avait de test avant ce fichier — en particulier le
# caractère transactionnel (tout-ou-rien) de publier_masse n'était vérifié
# nulle part.
#
# Dans le style de tests_seance_lifecycle.py : authentification directe via
# force_authenticate (pas de login JWT complet), helpers locaux redéfinis
# plutôt qu'importés d'un autre fichier de test.
#
# Lancement :
#   python manage.py test EDT_app.tests_seance_publication --verbosity=2

from datetime import time

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from EDT_app.factories import (
    AnneeAcademiqueFactory,
    ClasseFactory,
    DepartementFactory,
    EnseignantFactory,
    FiliereFactory,
    MatiereFactory,
    ModuleFactory,
    ProfilFactory,
    SeanceFactory,
    Semestre1Factory,
)
from EDT_app.models import Seance


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def make_enseignant(username, departement):
    """Crée un User + Profil + Enseignant rattaché au département donné."""
    user = User.objects.create_user(username=username, password="pass1234")
    profil = ProfilFactory(user=user)
    return EnseignantFactory(profil=profil, departement=departement)


def client_for(enseignant):
    """APIClient authentifié directement comme l'utilisateur de cet enseignant."""
    client = APIClient()
    client.force_authenticate(user=enseignant.profil.user)
    return client


class SeancePublicationTest(TestCase):

    def setUp(self):
        self.annee = AnneeAcademiqueFactory()
        self.sem = Semestre1Factory(annee=self.annee)
        self.dept = DepartementFactory(libelle="Département Publication")
        self.filiere = FiliereFactory(departement=self.dept)
        self.classe = ClasseFactory(filiere=self.filiere, semestre=self.sem, annee=self.annee)
        self.matiere = MatiereFactory(departement=self.dept)
        self.module = ModuleFactory(
            matiere=self.matiere, semestre=self.sem, credits=6, libelle="Module Publication"
        )  # 72h de plafond : large marge pour toutes les séances de ce fichier
        self.enseignant = EnseignantFactory(departement=self.dept)

        self.chef = make_enseignant("chef_publication", self.dept)
        self.dept.chef = self.chef
        self.dept.save()

        self.simple = make_enseignant("simple_publication", self.dept)  # ni chef, ni référent

    def _creer_brouillon(self, heure_debut, heure_fin, **kwargs):
        kwargs.setdefault("module", self.module)
        kwargs.setdefault("enseignant", self.enseignant)
        kwargs.setdefault("classe", self.classe)
        kwargs.setdefault("annee", self.annee)
        kwargs.setdefault("date_seance", self.sem.date_debut)
        kwargs.setdefault("type_seance", "CM")
        return SeanceFactory(
            heure_debut=heure_debut, heure_fin=heure_fin, statut="brouillon", **kwargs
        )

    # ──────────────────────────────────────────────────────────────────────────
    # publier
    # ──────────────────────────────────────────────────────────────────────────

    def test_publier_un_brouillon_le_passe_en_confirmee(self):
        seance = self._creer_brouillon(time(9, 0), time(11, 0))
        resp = client_for(self.chef).post(f"/api/seances/{seance.pk}/publier/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["statut"], "Confirmée")
        seance.refresh_from_db()
        self.assertEqual(seance.statut, "Confirmée")

    def test_publier_une_seance_deja_confirmee_refuse_400(self):
        seance = self._creer_brouillon(time(9, 0), time(11, 0))
        Seance.objects.filter(pk=seance.pk).update(statut="Confirmée")

        resp = client_for(self.chef).post(f"/api/seances/{seance.pk}/publier/")

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_publier_revalide_les_conflits(self):
        """
        full_clean() est bien rejoué à la publication (views.py:921) : deux
        brouillons créés sur des créneaux non chevauchants (donc acceptés à
        la création) peuvent malgré tout entrer en conflit au moment de la
        publication si leurs horaires ont changé entre-temps — la
        revalidation elle-même fonctionne.

        `publier()` (contrairement à `publier_masse()`, qui enveloppe son
        propre `full_clean()`) n'a aucune protection locale : c'est
        EDT_app.exception_handlers.exception_handler (câblé globalement via
        REST_FRAMEWORK['EXCEPTION_HANDLER']) qui convertit désormais la
        django.core.exceptions.ValidationError levée par full_clean() en
        réponse 400 DRF. Avant ce handler, elle remontait en 500
        (CORRECTIONS_A_FAIRE.md, point 14).
        """
        premiere = self._creer_brouillon(time(9, 0), time(11, 0))
        seconde = self._creer_brouillon(time(14, 15), time(16, 15))
        # Forcé après coup pour chevaucher `premiere`, en contournant
        # full_clean() — on ne teste pas la création ici, seulement ce que
        # publier() revalide.
        Seance.objects.filter(pk=seconde.pk).update(
            heure_debut=time(9, 0), heure_fin=time(11, 0)
        )

        resp_premiere = client_for(self.chef).post(f"/api/seances/{premiere.pk}/publier/")
        self.assertEqual(resp_premiere.status_code, status.HTTP_200_OK)

        resp_seconde = client_for(self.chef).post(f"/api/seances/{seconde.pk}/publier/")
        self.assertEqual(resp_seconde.status_code, status.HTTP_400_BAD_REQUEST)

        seconde.refresh_from_db()
        self.assertEqual(seconde.statut, "brouillon")  # publication refusée, statut inchangé

    def test_publier_non_chef_refuse_403(self):
        seance = self._creer_brouillon(time(9, 0), time(11, 0))
        resp = client_for(self.simple).post(f"/api/seances/{seance.pk}/publier/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # ──────────────────────────────────────────────────────────────────────────
    # depublier
    # ──────────────────────────────────────────────────────────────────────────

    def test_depublier_une_seance_confirmee_revient_en_brouillon(self):
        seance = self._creer_brouillon(time(9, 0), time(11, 0))
        Seance.objects.filter(pk=seance.pk).update(statut="Confirmée")

        resp = client_for(self.chef).post(f"/api/seances/{seance.pk}/depublier/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["statut"], "brouillon")
        seance.refresh_from_db()
        self.assertEqual(seance.statut, "brouillon")

    def test_depublier_un_brouillon_refuse_400(self):
        seance = self._creer_brouillon(time(9, 0), time(11, 0))
        resp = client_for(self.chef).post(f"/api/seances/{seance.pk}/depublier/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_depublier_non_chef_refuse_403(self):
        seance = self._creer_brouillon(time(9, 0), time(11, 0))
        Seance.objects.filter(pk=seance.pk).update(statut="Confirmée")

        resp = client_for(self.simple).post(f"/api/seances/{seance.pk}/depublier/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # ──────────────────────────────────────────────────────────────────────────
    # publier_masse
    # ──────────────────────────────────────────────────────────────────────────

    def test_publier_masse_succes_sur_plusieurs_brouillons(self):
        a = self._creer_brouillon(time(9, 0), time(11, 0))
        b = self._creer_brouillon(time(11, 15), time(13, 15))
        c = self._creer_brouillon(time(14, 15), time(16, 15))

        resp = client_for(self.chef).post(
            "/api/seances/publier_masse/",
            {"seance_ids": [a.pk, b.pk, c.pk]},
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for seance in (a, b, c):
            seance.refresh_from_db()
            self.assertEqual(seance.statut, "Confirmée")

    def test_publier_masse_sans_seance_ids_retourne_400(self):
        resp = client_for(self.chef).post(
            "/api/seances/publier_masse/", {"seance_ids": []}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_publier_masse_avec_id_introuvable_ou_non_brouillon_retourne_400(self):
        valide = self._creer_brouillon(time(9, 0), time(11, 0))

        # Cas 1 : un id qui n'existe pas dans la liste.
        resp = client_for(self.chef).post(
            "/api/seances/publier_masse/",
            {"seance_ids": [valide.pk, 999999]},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        valide.refresh_from_db()
        self.assertEqual(valide.statut, "brouillon")  # rien n'a été publié

        # Cas 2 : un id déjà Confirmée mélangé à un brouillon valide — le
        # contrôle de comptage (`len(seances) != len(seance_ids)`) précède
        # toute publication, donc `valide` ne doit pas non plus être publiée.
        deja_confirmee = self._creer_brouillon(time(11, 15), time(13, 15))
        Seance.objects.filter(pk=deja_confirmee.pk).update(statut="Confirmée")

        resp2 = client_for(self.chef).post(
            "/api/seances/publier_masse/",
            {"seance_ids": [valide.pk, deja_confirmee.pk]},
            format="json",
        )
        self.assertEqual(resp2.status_code, status.HTTP_400_BAD_REQUEST)
        valide.refresh_from_db()
        self.assertEqual(valide.statut, "brouillon")

    def test_publier_masse_rollback_si_une_seule_seance_echoue(self):
        """
        Le test le plus important du lot : preuve du tout-ou-rien de
        transaction.atomic() (views.py:964-978). `a` et `b` réussiraient
        individuellement, mais `c` échoue une fois son créneau forcé en
        conflit avec `a` — la transaction entière doit être annulée, y
        compris les statuts de `a` et `b` déjà écrits plus tôt dans la boucle.
        """
        a = self._creer_brouillon(time(9, 0), time(11, 0))
        b = self._creer_brouillon(time(11, 15), time(13, 15))
        c = self._creer_brouillon(time(14, 15), time(16, 15))
        # Forcé après coup pour chevaucher `a`, tout en restant trié après
        # `a` dans get_queryset() (order_by date_seance, heure_debut) afin
        # que `a` soit bien publiée la première dans la boucle.
        Seance.objects.filter(pk=c.pk).update(heure_debut=time(9, 30), heure_fin=time(10, 30))

        resp = client_for(self.chef).post(
            "/api/seances/publier_masse/",
            {"seance_ids": [a.pk, b.pk, c.pk]},
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("erreurs", resp.data)

        for seance in (a, b, c):
            seance.refresh_from_db()
            self.assertEqual(
                seance.statut, "brouillon",
                f"la séance {seance.pk} n'a pas été correctement annulée par le rollback",
            )

    def test_publier_masse_non_chef_refuse_403(self):
        a = self._creer_brouillon(time(9, 0), time(11, 0))
        resp = client_for(self.simple).post(
            "/api/seances/publier_masse/", {"seance_ids": [a.pk]}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
