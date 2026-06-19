# tests_complets.py
#
# Couverture :
#   1. Serializers  — matricule, archivage, département, motif suspension
#   2. Vues         — login, conflit séance, report dimanche, planning étudiant, accès responsable
#   3. Actions custom — reporter, conflits, passer_semestre, changer_statut
#
# Lancement :
#   python manage.py test EDT_app.tests_complets --verbosity=2

from datetime import date, time, timedelta

from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from EDT_app.factories import (
    AnneeAcademiqueFactory,
    ClasseFactory,
    DepartementFactory,
    EnseignantFactory,
    EtudiantFactory,
    FaculteFactory,
    FiliereFactory,
    ModuleFactory,
    ParcoursFactory,
    ProfilFactory,
    SeanceFactory,
    Semestre1Factory,
    MatiereFactory,
)
from EDT_app.models import (
    AnneeAcademique,
    Classe,
    Etudiant,
    Profil,
    Seance,
    Semestre,
)
from EDT_app.serializers import (
    AnneeAcademiqueSerializer,
    EtudiantSerializer,
    EnseignantSerializer,
    ProfilSerializer,
    SeanceSerializer,
    SeanceReportSerializer,
    ProfilSuspensionSerializer,
)


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def make_user(username="user", password="pass1234", groups=None):
    """Crée un User Django et retourne (user, password)."""
    user = User.objects.create_user(username=username, password=password)
    if groups:
        for g in groups:
            grp, _ = Group.objects.get_or_create(name=g)
            user.groups.add(grp)
    return user, password


def make_responsable(username="resp"):
    """Crée un utilisateur membre du groupe 'responsable'."""
    user, pwd = make_user(username=username, groups=["responsable"])
    ProfilFactory(user=user)
    return user, pwd


def auth_client(username, password):
    """Retourne un APIClient authentifié via JWT."""
    client = APIClient()
    resp = client.post(
        "/api/token/",
        {"username": username, "password": password},
        format="json",
    )
    assert resp.status_code == 200, f"Login failed: {resp.data}"
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
    return client


# ══════════════════════════════════════════════════════════════════════════════
# 1. TESTS SERIALIZERS
# ══════════════════════════════════════════════════════════════════════════════

class TestEtudiantSerializerMatricule(TestCase):
    """Validation du format matricule ETU-XXXXX dans le serializer."""

    def _base_data(self, matricule):
        annee = AnneeAcademiqueFactory()
        sem = Semestre1Factory(annee=annee)
        parcours = ParcoursFactory()
        filiere = FiliereFactory()
        classe = ClasseFactory(parcours=parcours, filiere=filiere, semestre=sem, annee=annee)
        profil = ProfilFactory()
        return {
            "profil_id": profil.user_id,
            "matricule": matricule,
            "parcours_id": parcours.pk,
            "filiere_id": filiere.pk,
            "classe_id": classe.pk,
        }

    def test_matricule_valide(self):
        data = self._base_data("ETU-00042")
        s = EtudiantSerializer(data=data)
        self.assertTrue(s.is_valid(), s.errors)

    def test_matricule_format_incorrect_prefixe(self):
        data = self._base_data("BAD-00042")
        s = EtudiantSerializer(data=data)
        self.assertFalse(s.is_valid())
        self.assertIn("matricule", s.errors)

    def test_matricule_format_incorrect_longueur(self):
        data = self._base_data("ETU-042")
        s = EtudiantSerializer(data=data)
        self.assertFalse(s.is_valid())
        self.assertIn("matricule", s.errors)

    def test_matricule_format_lettres_dans_numero(self):
        data = self._base_data("ETU-0004A")
        s = EtudiantSerializer(data=data)
        self.assertFalse(s.is_valid())
        self.assertIn("matricule", s.errors)


class TestAnneeAcademiqueSerializerArchivage(TestCase):
    """Blocage d'archivage si séances confirmées dans le futur."""

    def setUp(self):
        self.annee = AnneeAcademiqueFactory(
            libelle="2025-2026",
            date_debut=date(2025, 9, 1),
            date_fin=date(2026, 6, 30),
        )
        self.sem = Semestre1Factory(
            annee=self.annee,
            date_debut=date(2025, 9, 1),
            date_fin=date(2026, 1, 31),
        )

    def test_archivage_bloque_si_seance_future_confirmee(self):
        """Impossible d'archiver une année avec des séances confirmées dans le futur."""
        future = date.today() + timedelta(days=30)
        Semestre.objects.filter(pk=self.sem.pk).update(date_fin=future + timedelta(days=10))
        self.sem.refresh_from_db()

        SeanceFactory(
            annee=self.annee,
            classe=ClasseFactory(semestre=self.sem, annee=self.annee),
            date_seance=future,
            heure_debut=time(9, 0),
            heure_fin=time(11, 0),
            statut="Confirmée",
        )

        data = {
            "libelle": self.annee.libelle,
            "date_debut": self.annee.date_debut,
            "date_fin": self.annee.date_fin,
            "statut": "archivée",
        }
        s = AnneeAcademiqueSerializer(instance=self.annee, data=data)
        self.assertFalse(s.is_valid())
        self.assertIn("statut", s.errors)

    def test_archivage_autorise_sans_seance_future(self):
        """Archivage possible quand toutes les séances sont passées ou absentes."""
        data = {
            "libelle": self.annee.libelle,
            "date_debut": self.annee.date_debut,
            "date_fin": self.annee.date_fin,
            "statut": "archivée",
        }
        s = AnneeAcademiqueSerializer(instance=self.annee, data=data)
        self.assertTrue(s.is_valid(), s.errors)

    def test_archivage_autorise_si_seances_annulees_futures(self):
        """Les séances annulées ne bloquent pas l'archivage."""
        future = date.today() + timedelta(days=30)
        self.sem.date_fin = future + timedelta(days=10)
        self.sem.save()

        SeanceFactory(
            annee=self.annee,
            classe=ClasseFactory(semestre=self.sem, annee=self.annee),
            date_seance=future,
            heure_debut=time(9, 0),
            heure_fin=time(11, 0),
            statut="Annulée",
        )

        data = {
            "libelle": self.annee.libelle,
            "date_debut": self.annee.date_debut,
            "date_fin": self.annee.date_fin,
            "statut": "archivée",
        }
        s = AnneeAcademiqueSerializer(instance=self.annee, data=data)
        self.assertTrue(s.is_valid(), s.errors)


class TestSeanceSerializerDepartement(TestCase):
    """Cohérence département enseignant ↔ matière du module."""

    def setUp(self):
        self.annee = AnneeAcademiqueFactory()
        self.sem = Semestre1Factory(annee=self.annee)

        self.dept_info = DepartementFactory(libelle="Informatique")
        self.dept_math = DepartementFactory(libelle="Mathématiques")

        filiere = FiliereFactory(departement=self.dept_info)
        parcours = ParcoursFactory()
        self.classe = ClasseFactory(
            parcours=parcours, filiere=filiere,
            semestre=self.sem, annee=self.annee,
        )
        matiere = MatiereFactory(departement=self.dept_info)
        self.module = ModuleFactory(matiere=matiere, semestre=self.sem)
        self.enseignant_math = EnseignantFactory(departement=self.dept_math)
        self.enseignant_info = EnseignantFactory(departement=self.dept_info)

    def _payload(self, enseignant):
        return {
            "date_seance": self.sem.date_debut.isoformat(),
            "heure_debut": "09:00:00",
            "heure_fin": "11:00:00",
            "type_seance": "CM",
            "statut": "Confirmée",
            "module_id": self.module.pk,
            "enseignant_id": enseignant.profil_id,
            "classe_id": self.classe.pk,
            "annee_id": self.annee.pk,
        }

    def test_departement_incoherent_rejette(self):
        s = SeanceSerializer(data=self._payload(self.enseignant_math))
        self.assertFalse(s.is_valid())
        self.assertIn("enseignant_id", s.errors)

    def test_departement_coherent_accepte(self):
        s = SeanceSerializer(data=self._payload(self.enseignant_info))
        self.assertTrue(s.is_valid(), s.errors)


class TestProfilSerializerSuspension(TestCase):
    """Motif obligatoire si statut suspendu."""

    def test_suspension_sans_motif_rejette(self):
        user = User.objects.create_user(username="u1", password="x")
        data = {
            "user_id": user.pk,
            "genre": "M",
            "statut": "suspendu",
            "motif_suspension": "",
        }
        s = ProfilSerializer(data=data)
        self.assertFalse(s.is_valid())
        self.assertIn("motif_suspension", s.errors)

    def test_suspension_avec_motif_accepte(self):
        user = User.objects.create_user(username="u2", password="x")
        data = {
            "user_id": user.pk,
            "genre": "M",
            "statut": "suspendu",
            "motif_suspension": "Congé maladie",
        }
        s = ProfilSerializer(data=data)
        self.assertTrue(s.is_valid(), s.errors)

    def test_reactiver_efface_motif(self):
        user = User.objects.create_user(username="u3", password="x")
        profil = ProfilFactory(
            user=user,
            statut="suspendu",
            motif_suspension="Congé",
        )
        data = {
            "user_id": user.pk,
            "genre": profil.genre,
            "statut": "actif",
            "motif_suspension": "Congé",
        }
        s = ProfilSerializer(instance=profil, data=data)
        self.assertTrue(s.is_valid(), s.errors)
        self.assertEqual(s.validated_data["motif_suspension"], "")


# ══════════════════════════════════════════════════════════════════════════════
# 2. TESTS VUES (API)
# ══════════════════════════════════════════════════════════════════════════════

class TestLoginSuspension(TestCase):
    """Login bloqué si le profil est suspendu."""

    def test_login_profil_suspendu_rejette(self):
        user, pwd = make_user(username="suspendu", password="pass1234")
        ProfilFactory(user=user, statut="suspendu", motif_suspension="Test")

        client = APIClient()
        resp = client.post(
            "/api/token/",
            {"username": "suspendu", "password": "pass1234"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_profil_actif_accepte(self):
        user, pwd = make_user(username="actif", password="pass1234")
        ProfilFactory(user=user, statut="actif")

        client = APIClient()
        resp = client.post(
            "/api/token/",
            {"username": "actif", "password": "pass1234"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", resp.data)
        self.assertIn("user", resp.data)
        self.assertEqual(resp.data["user"]["statut"], "actif")

    def test_login_sans_profil_rejette(self):
        """Un user sans profil ne peut pas obtenir de token."""
        User.objects.create_user(username="sansprofil", password="pass1234")
        client = APIClient()
        resp = client.post(
            "/api/token/",
            {"username": "sansprofil", "password": "pass1234"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class TestSeanceCreationConflits(TestCase):
    """Création de séance : conflits → 400."""

    def setUp(self):
        self.resp_user, self.pwd = make_responsable("resp_conflit")
        self.client = auth_client("resp_conflit", self.pwd)

        self.annee = AnneeAcademiqueFactory()
        self.sem = Semestre1Factory(annee=self.annee)
        dept = DepartementFactory()
        filiere = FiliereFactory(departement=dept)
        parcours = ParcoursFactory()
        self.classe = ClasseFactory(
            parcours=parcours, filiere=filiere,
            semestre=self.sem, annee=self.annee,
        )
        matiere = MatiereFactory(departement=dept)
        self.module = ModuleFactory(matiere=matiere, semestre=self.sem, credits=6)
        self.enseignant = EnseignantFactory(departement=dept)

        self.seance_ref = SeanceFactory(
            module=self.module,
            enseignant=self.enseignant,
            classe=self.classe,
            annee=self.annee,
            date_seance=self.sem.date_debut,
            heure_debut=time(9, 0),
            heure_fin=time(11, 0),
            statut="Confirmée",
        )

    def _payload(self, heure_debut="10:00:00", heure_fin="12:00:00"):
        return {
            "date_seance": self.sem.date_debut.isoformat(),
            "heure_debut": heure_debut,
            "heure_fin": heure_fin,
            "type_seance": "TD",
            "statut": "Confirmée",
            "module_id": self.module.pk,
            "enseignant_id": self.enseignant.profil_id,
            "classe_id": self.classe.pk,
            "annee_id": self.annee.pk,
        }

    def test_conflit_enseignant_retourne_400(self):
        resp = self.client.post("/api/seances/", self._payload(), format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("enseignant_id", resp.data)

    def test_conflit_classe_meme_creneau_400(self):
        """Même classe, même créneau, enseignant différent → conflit classe."""
        autre_enseignant = EnseignantFactory(departement=self.enseignant.departement)
        payload = self._payload()
        payload["enseignant_id"] = autre_enseignant.profil_id
        resp = self.client.post("/api/seances/", payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("classe_id", resp.data)

    def test_seance_sans_conflit_cree_201(self):
        """Créneau différent (après-midi) → succès."""
        payload = self._payload(heure_debut="13:00:00", heure_fin="15:00:00")
        resp = self.client.post("/api/seances/", payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)


class TestSeanceReportDimanche(TestCase):
    """Report d'une séance vers un dimanche → 400."""

    def setUp(self):
        self.resp_user, self.pwd = make_responsable("resp_report")
        self.client = auth_client("resp_report", self.pwd)

        self.annee = AnneeAcademiqueFactory()
        self.sem = Semestre1Factory(annee=self.annee)
        dept = DepartementFactory()
        filiere = FiliereFactory(departement=dept)
        parcours = ParcoursFactory()
        classe = ClasseFactory(
            parcours=parcours, filiere=filiere,
            semestre=self.sem, annee=self.annee,
        )
        matiere = MatiereFactory(departement=dept)
        module = ModuleFactory(matiere=matiere, semestre=self.sem, credits=6)
        enseignant = EnseignantFactory(departement=dept)

        self.seance = SeanceFactory(
            module=module,
            enseignant=enseignant,
            classe=classe,
            annee=self.annee,
            date_seance=self.sem.date_debut,
            heure_debut=time(9, 0),
            heure_fin=time(11, 0),
            statut="Confirmée",
        )

    def _prochain_dimanche(self):
        d = self.sem.date_debut
        while d.weekday() != 6:
            d += timedelta(days=1)
        return d

    def _prochain_lundi(self):
        d = self.sem.date_debut + timedelta(days=1)
        while d.weekday() != 0:
            d += timedelta(days=1)
        if d > self.sem.date_fin:
            d = self.sem.date_debut + timedelta(days=1)
        return d

    def test_report_dimanche_retourne_400(self):
        dimanche = self._prochain_dimanche()
        resp = self.client.patch(
            f"/api/seances/{self.seance.pk}/reporter/",
            {
                "date_report": dimanche.isoformat(),
                "heure_debut_report": "09:00:00",
                "heure_fin_report": "11:00:00",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("date_report", resp.data)

    def test_report_jour_valide_retourne_200(self):
        lundi = self._prochain_lundi()
        resp = self.client.patch(
            f"/api/seances/{self.seance.pk}/reporter/",
            {
                "date_report": lundi.isoformat(),
                "heure_debut_report": "09:00:00",
                "heure_fin_report": "11:00:00",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["statut"], "Reportée")


class TestPlanningEtudiant(TestCase):
    """Un étudiant ne voit que les séances de sa propre classe."""

    def setUp(self):
        self.annee = AnneeAcademiqueFactory()
        self.sem = Semestre1Factory(annee=self.annee)
        dept = DepartementFactory()
        filiere = FiliereFactory(departement=dept)
        parcours = ParcoursFactory()

        self.classe_a = ClasseFactory(
            parcours=parcours, filiere=filiere,
            semestre=self.sem, annee=self.annee,
        )
        parcours_b = ParcoursFactory(type_parcours="Master", niveau=1)
        self.classe_b = ClasseFactory(
            parcours=parcours_b, filiere=filiere,
            semestre=self.sem, annee=self.annee,
        )

        matiere = MatiereFactory(departement=dept)
        module = ModuleFactory(matiere=matiere, semestre=self.sem, credits=6)
        enseignant = EnseignantFactory(departement=dept)

        self.seance_a = SeanceFactory(
            module=module, enseignant=enseignant,
            classe=self.classe_a, annee=self.annee,
            date_seance=self.sem.date_debut,
            heure_debut=time(9, 0), heure_fin=time(11, 0),
        )
        enseignant_b = EnseignantFactory(departement=dept)
        self.seance_b = SeanceFactory(
            module=module, enseignant=enseignant_b,
            classe=self.classe_b, annee=self.annee,
            date_seance=self.sem.date_debut,
            heure_debut=time(9, 0), heure_fin=time(11, 0),
        )

        etu_user, self.etu_pwd = make_user("etudiant_a", "pass1234")
        etu_profil = ProfilFactory(user=etu_user)
        self.etudiant = EtudiantFactory(
            profil=etu_profil,
            parcours=parcours,
            filiere=filiere,
            classe=self.classe_a,
        )

    def test_etudiant_ne_voit_que_sa_classe(self):
        client = auth_client("etudiant_a", "pass1234")
        resp = client.get("/api/etudiants/mon_planning/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = [s["id"] for s in resp.data]
        self.assertIn(self.seance_a.pk, ids)
        self.assertNotIn(self.seance_b.pk, ids)

    def test_enseignant_ne_peut_pas_acceder_planning_etudiant(self):
        """Un enseignant accédant à /etudiants/mon_planning/ → 403."""
        ens_user, ens_pwd = make_user("enseignant_test", "pass1234")
        ens_profil = ProfilFactory(user=ens_user)
        EnseignantFactory(profil=ens_profil)
        client = auth_client("enseignant_test", "pass1234")
        resp = client.get("/api/etudiants/mon_planning/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class TestAccesResponsable(TestCase):
    """Le responsable accède à toutes les ressources en lecture et écriture."""

    def setUp(self):
        self.resp_user, self.pwd = make_responsable("resp_acces")
        self.client = auth_client("resp_acces", self.pwd)

        etu_user, self.etu_pwd = make_user("etu_acces", "pass1234")
        ProfilFactory(user=etu_user)

    def test_responsable_peut_lister_profils(self):
        resp = self.client.get("/api/profils/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_etudiant_ne_peut_pas_lister_profils(self):
        client = auth_client("etu_acces", "pass1234")
        resp = client.get("/api/profils/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_responsable_peut_creer_faculte(self):
        resp = self.client.post("/api/facultes/", {"libelle": "Faculté Test"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_lecture_seule_pour_non_responsable(self):
        """Un simple utilisateur authentifié peut lire mais pas écrire."""
        client = auth_client("etu_acces", "pass1234")
        resp = client.get("/api/facultes/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        resp2 = client.post("/api/facultes/", {"libelle": "Test"}, format="json")
        self.assertEqual(resp2.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_authentifie_retourne_401(self):
        client = APIClient()
        resp = client.get("/api/facultes/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


# ══════════════════════════════════════════════════════════════════════════════
# 3. TESTS ACTIONS CUSTOM
# ══════════════════════════════════════════════════════════════════════════════

class TestActionReporter(TestCase):
    """PATCH /seances/{id}/reporter/ — action custom."""

    def setUp(self):
        self.resp_user, self.pwd = make_responsable("resp_reporter")
        self.client = auth_client("resp_reporter", self.pwd)

        self.annee = AnneeAcademiqueFactory()
        self.sem = Semestre1Factory(annee=self.annee)
        dept = DepartementFactory()
        filiere = FiliereFactory(departement=dept)
        parcours = ParcoursFactory()
        self.classe = ClasseFactory(
            parcours=parcours, filiere=filiere,
            semestre=self.sem, annee=self.annee,
        )
        matiere = MatiereFactory(departement=dept)
        module = ModuleFactory(matiere=matiere, semestre=self.sem, credits=6)
        self.enseignant = EnseignantFactory(departement=dept)

        self.seance = SeanceFactory(
            module=module, enseignant=self.enseignant,
            classe=self.classe, annee=self.annee,
            date_seance=self.sem.date_debut,
            heure_debut=time(9, 0), heure_fin=time(11, 0),
            statut="Confirmée",
        )

    def _date_libre(self):
        """Trouve un jour dans le semestre sans séance, non dimanche."""
        d = self.sem.date_debut + timedelta(days=2)
        while d.weekday() == 6:
            d += timedelta(days=1)
        return d

    def test_reporter_succes(self):
        date_r = self._date_libre()
        resp = self.client.patch(
            f"/api/seances/{self.seance.pk}/reporter/",
            {
                "date_report": date_r.isoformat(),
                "heure_debut_report": "14:00:00",
                "heure_fin_report": "16:00:00",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["statut"], "Reportée")
        self.assertEqual(resp.data["date_report"], date_r.isoformat())

    def test_reporter_heure_avant_9h_retourne_400(self):
        date_r = self._date_libre()
        resp = self.client.patch(
            f"/api/seances/{self.seance.pk}/reporter/",
            {
                "date_report": date_r.isoformat(),
                "heure_debut_report": "08:00:00",
                "heure_fin_report": "10:00:00",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("heure_debut_report", resp.data)

    def test_reporter_hors_semestre_retourne_400(self):
        hors_sem = self.sem.date_fin + timedelta(days=10)
        resp = self.client.patch(
            f"/api/seances/{self.seance.pk}/reporter/",
            {
                "date_report": hors_sem.isoformat(),
                "heure_debut_report": "09:00:00",
                "heure_fin_report": "11:00:00",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("date_report", resp.data)

    def test_reporter_conflit_enseignant_retourne_400(self):
        """Report vers un créneau où l'enseignant est déjà occupé."""
        date_r = self._date_libre()
        SeanceFactory(
            enseignant=self.enseignant,
            classe=self.classe,
            annee=self.annee,
            date_seance=date_r,
            heure_debut=time(9, 0),
            heure_fin=time(11, 0),
            module=self.seance.module,
        )
        resp = self.client.patch(
            f"/api/seances/{self.seance.pk}/reporter/",
            {
                "date_report": date_r.isoformat(),
                "heure_debut_report": "09:00:00",
                "heure_fin_report": "11:00:00",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reporter_non_responsable_retourne_403(self):
        etu_user, pwd = make_user("etu_reporter", "pass1234")
        ProfilFactory(user=etu_user)
        client = auth_client("etu_reporter", "pass1234")
        resp = client.patch(
            f"/api/seances/{self.seance.pk}/reporter/",
            {
                "date_report": self._date_libre().isoformat(),
                "heure_debut_report": "09:00:00",
                "heure_fin_report": "11:00:00",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class TestActionConflits(TestCase):
    """GET /seances/conflits/ — détection de conflits."""

    def setUp(self):
        self.resp_user, self.pwd = make_responsable("resp_conflits")
        self.client = auth_client("resp_conflits", self.pwd)

        self.annee = AnneeAcademiqueFactory()
        self.sem = Semestre1Factory(annee=self.annee)
        dept = DepartementFactory()
        filiere = FiliereFactory(departement=dept)
        parcours = ParcoursFactory()
        self.classe = ClasseFactory(
            parcours=parcours, filiere=filiere,
            semestre=self.sem, annee=self.annee,
        )
        matiere = MatiereFactory(departement=dept)
        self.module = ModuleFactory(matiere=matiere, semestre=self.sem, credits=6)
        self.enseignant = EnseignantFactory(departement=dept)

    def test_conflits_sans_parametre_retourne_400(self):
        resp = self.client.get("/api/seances/conflits/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_conflits_vide_quand_pas_de_conflit(self):
        SeanceFactory(
            module=self.module, enseignant=self.enseignant,
            classe=self.classe, annee=self.annee,
            date_seance=self.sem.date_debut,
            heure_debut=time(9, 0), heure_fin=time(11, 0),
            statut="Confirmée",
        )
        resp = self.client.get(f"/api/seances/conflits/?semestre_id={self.sem.pk}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 0)

    # CORRECTION 2 : suppression du paramètre `filiere_obj` avec valeur vide,
    # et remplacement des walrus operators par des assignations locales simples.
    def test_conflits_detecte_chevauchement_enseignant(self):
        """
        Deux séances confirmées avec le même enseignant qui se chevauchent
        doivent être détectées comme conflit.
        On contourne la validation en forçant l'insertion via bulk_create().
        """
        SeanceFactory(
            module=self.module, enseignant=self.enseignant,
            classe=self.classe, annee=self.annee,
            date_seance=self.sem.date_debut,
            heure_debut=time(9, 0), heure_fin=time(11, 0),
            statut="Confirmée",
        )
        # Crée une autre classe pour contourner la validation clean()
        parcours2 = ParcoursFactory(type_parcours="Master", niveau=1)
        dept2 = DepartementFactory()
        filiere2 = FiliereFactory(departement=dept2)
        classe2 = ClasseFactory(
            parcours=parcours2, filiere=filiere2,
            semestre=self.sem, annee=self.annee,
        )
        # Force l'insertion sans validation pour simuler un conflit déjà en base
        # Force l'insertion sans validation pour simuler un conflit déjà en base
        s2 = Seance(
            module=self.module,
            enseignant=self.enseignant,
            classe=classe2,
            annee=self.annee,
            date_seance=self.sem.date_debut,
            heure_debut=time(10, 0),
            heure_fin=time(12, 0),
            type_seance="TD",
            statut="Confirmée",
        )
        Seance.objects.bulk_create([s2])  # bypasse full_clean()

        resp = self.client.get(f"/api/seances/conflits/?semestre_id={self.sem.pk}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(resp.data["count"], 1)

    def test_conflits_non_responsable_retourne_403(self):
        etu_user, pwd = make_user("etu_conflits", "pass1234")
        ProfilFactory(user=etu_user)
        client = auth_client("etu_conflits", "pass1234")
        resp = client.get(f"/api/seances/conflits/?semestre_id={self.sem.pk}")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class TestActionPasserSemestre(TestCase):
    """POST /classes/{id}/passer_semestre/ — transfert d'étudiants."""

    def setUp(self):
        self.resp_user, self.pwd = make_responsable("resp_passer")
        self.client = auth_client("resp_passer", self.pwd)

        self.annee = AnneeAcademiqueFactory()
        self.sem1 = Semestre1Factory(annee=self.annee)
        sem2 = Semestre(
            libelle='Semestre 2',
            date_debut=date(2026, 2, 1),
            date_fin=date(2026, 6, 30),
            annee=self.annee,
        )
        Semestre.objects.bulk_create([sem2])
        self.sem2 = Semestre.objects.get(libelle='Semestre 2', annee=self.annee)

        filiere = FiliereFactory()
        parcours = ParcoursFactory()
        self.classe_s1 = ClasseFactory(
            parcours=parcours, filiere=filiere,
            semestre=self.sem1, annee=self.annee,
        )
        etu1_user, _ = make_user("etu_passer1", "x")
        etu1_profil = ProfilFactory(user=etu1_user, statut="actif")
        self.etudiant_actif = EtudiantFactory(
            profil=etu1_profil, parcours=parcours,
            filiere=filiere, classe=self.classe_s1,
        )
        etu2_user, _ = make_user("etu_passer2", "x")
        etu2_profil = ProfilFactory(
            user=etu2_user, statut="suspendu", motif_suspension="Retard"
        )
        self.etudiant_suspendu = EtudiantFactory(
            profil=etu2_profil, parcours=parcours,
            filiere=filiere, classe=self.classe_s1,
        )

    def test_passer_semestre_succes(self):
        resp = self.client.post(
            f"/api/classes/{self.classe_s1.pk}/passer_semestre/",
            {"semestre_cible_id": self.sem2.pk},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["total_passes"], 1)
        self.assertEqual(resp.data["total_bloques"], 1)

        self.etudiant_actif.refresh_from_db()
        self.assertEqual(self.etudiant_actif.classe.semestre, self.sem2)

    def test_passer_semestre_sans_parametre_retourne_400(self):
        resp = self.client.post(
            f"/api/classes/{self.classe_s1.pk}/passer_semestre/",
            {},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_passer_semestre_semestre_inexistant_retourne_404(self):
        resp = self.client.post(
            f"/api/classes/{self.classe_s1.pk}/passer_semestre/",
            {"semestre_cible_id": 99999},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_passer_semestre_non_responsable_retourne_403(self):
        etu_user, pwd = make_user("etu_passer3", "pass1234")
        ProfilFactory(user=etu_user)
        client = auth_client("etu_passer3", "pass1234")
        resp = client.post(
            f"/api/classes/{self.classe_s1.pk}/passer_semestre/",
            {"semestre_cible_id": self.sem2.pk},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_passer_semestre_cree_classe_cible_si_inexistante(self):
        """La classe cible est créée à la volée si elle n'existe pas encore."""
        resp = self.client.post(
            f"/api/classes/{self.classe_s1.pk}/passer_semestre/",
            {"semestre_cible_id": self.sem2.pk},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["classe_cible_creee"])


class TestActionChangerStatut(TestCase):
    """PATCH /profils/{id}/changer_statut/ — suspension et réactivation."""

    def setUp(self):
        self.resp_user, self.pwd = make_responsable("resp_statut")
        self.client = auth_client("resp_statut", self.pwd)

        cible_user, _ = make_user("cible_statut", "x")
        self.profil_cible = ProfilFactory(user=cible_user, statut="actif")

    def test_suspendre_avec_motif_succes(self):
        resp = self.client.patch(
            f"/api/profils/{self.profil_cible.user_id}/changer_statut/",
            {"statut": "suspendu", "motif_suspension": "Comportement inacceptable"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.profil_cible.refresh_from_db()
        self.assertEqual(self.profil_cible.statut, "suspendu")
        self.assertNotEqual(self.profil_cible.motif_suspension, "")

    def test_suspendre_sans_motif_retourne_400(self):
        resp = self.client.patch(
            f"/api/profils/{self.profil_cible.user_id}/changer_statut/",
            {"statut": "suspendu", "motif_suspension": ""},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("motif_suspension", resp.data)

    def test_reactiver_efface_motif(self):
        self.profil_cible.statut = "suspendu"
        self.profil_cible.motif_suspension = "Raison initiale"
        self.profil_cible.save()

        resp = self.client.patch(
            f"/api/profils/{self.profil_cible.user_id}/changer_statut/",
            {"statut": "actif"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.profil_cible.refresh_from_db()
        self.assertEqual(self.profil_cible.statut, "actif")
        self.assertEqual(self.profil_cible.motif_suspension, "")

    def test_changer_statut_non_responsable_retourne_403(self):
        etu_user, pwd = make_user("etu_statut", "pass1234")
        ProfilFactory(user=etu_user)
        client = auth_client("etu_statut", "pass1234")
        resp = client.patch(
            f"/api/profils/{self.profil_cible.user_id}/changer_statut/",
            {"statut": "suspendu", "motif_suspension": "Hack"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ══════════════════════════════════════════════════════════════════════════════
# 4. TESTS MODÈLES (règles métier internes)
# ══════════════════════════════════════════════════════════════════════════════

class TestSeanceModeleRegles(TestCase):
    """Règles métier directement testées sur le modèle."""

    def setUp(self):
        self.annee = AnneeAcademiqueFactory()
        self.sem = Semestre1Factory(annee=self.annee)
        dept = DepartementFactory()
        filiere = FiliereFactory(departement=dept)
        parcours = ParcoursFactory()
        self.classe = ClasseFactory(
            parcours=parcours, filiere=filiere,
            semestre=self.sem, annee=self.annee,
        )
        matiere = MatiereFactory(departement=dept)
        self.module = ModuleFactory(matiere=matiere, semestre=self.sem, credits=6)
        self.enseignant = EnseignantFactory(departement=dept)

    def test_heure_debut_avant_9h_rejette(self):
        with self.assertRaises(ValidationError):
            SeanceFactory(
                module=self.module, enseignant=self.enseignant,
                classe=self.classe, annee=self.annee,
                date_seance=self.sem.date_debut,
                heure_debut=time(8, 0), heure_fin=time(10, 0),
            )

    def test_calcul_duree_avec_pause_11h(self):
        seance = SeanceFactory(
            module=self.module, enseignant=self.enseignant,
            classe=self.classe, annee=self.annee,
            date_seance=self.sem.date_debut,
            heure_debut=time(9, 0), heure_fin=time(12, 0),
        )
        # 3h brutes − 15min de pause = 2.75h
        self.assertEqual(
            Seance.calculer_duree_effective(seance.heure_debut, seance.heure_fin),
            2.75,
        )

    def test_plafond_volume_module(self):
        module_1cr = ModuleFactory(
            matiere=self.module.matiere,
            semestre=self.sem,
            credits=1,
            libelle="Module 1 crédit",
        )

        # 1. Créer les séances en base (nécessaire pour que l'agrégation fonctionne)
        SeanceFactory(
            module=module_1cr, enseignant=self.enseignant,
            classe=self.classe, annee=self.annee,
            date_seance=self.sem.date_debut,
            heure_debut=time(9, 0), heure_fin=time(15, 15),  # 6h
        )
        SeanceFactory(
            module=module_1cr, enseignant=self.enseignant,
            classe=self.classe, annee=self.annee,
            date_seance=self.sem.date_debut + timedelta(days=1),
            heure_debut=time(9, 0), heure_fin=time(15, 15),  # + 6h = 12h
        )

        # 2. Préparer la séance qui dépasse
        s_depasse = SeanceFactory.build(
            module=module_1cr, enseignant=self.enseignant,
            classe=self.classe, annee=self.annee,
            date_seance=self.sem.date_debut + timedelta(days=2),
            heure_debut=time(9, 0), heure_fin=time(11, 0),  # + 2h = 14h
        )

        # 3. Vérifier que la validation échoue
        with self.assertRaises(ValidationError):
            s_depasse.full_clean()

    def test_date_hors_semestre_rejette(self):
        hors = self.sem.date_fin + timedelta(days=5)
        with self.assertRaises(ValidationError):
            SeanceFactory(
                module=self.module, enseignant=self.enseignant,
                classe=self.classe, annee=self.annee,
                date_seance=hors,
                heure_debut=time(9, 0), heure_fin=time(11, 0),
            )