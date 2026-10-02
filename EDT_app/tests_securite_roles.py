# tests_securite_roles.py
#
# Matrice des droits par rôle (plan « solidité et sécurité », 2026-10-01).
#
# Chaque test décrit la règle VOULUE, validée avec l'utilisateur :
#   - un chef de département n'agit que sur son département ;
#   - les réglages communs (facultés, départements et leur chef, années,
#     semestres, parcours) sont réservés à l'admin et à la scolarité
#     (groupe `responsable`) ;
#   - un référent peut publier, dépublier et reporter les séances de ses
#     classes ;
#   - le planning est public entre utilisateurs connectés, mais jamais les
#     coordonnées personnelles (email, téléphone, motif de suspension) ;
#   - un compte suspendu est refusé partout, session déjà ouverte comprise.
#
# Quand l'application ne respecte pas encore la règle, le test porte
# @faille_connue(N) (EDT_app/outils_tests.py) et renvoie au point de CORRECTIONS_A_FAIRE.md qui la
# décrit. Le jour où la faille est corrigée, le test passe en « unexpected
# success » : il suffit alors de retirer le décorateur.
#
# Les tests marqués « contrôle » vérifient ce qui marche déjà, pour qu'un
# futur correctif ne le casse pas.
#
# Lancement :
#   ./.venv/Scripts/python.exe manage.py test EDT_app.tests_securite_roles --verbosity=2

import shutil
import tempfile
from datetime import date, time

from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from EDT_app.factories import (
    AffectationModuleFactory,
    AnneeAcademiqueFactory,
    ClasseFactory,
    DepartementFactory,
    FaculteFactory,
    FiliereFactory,
    MatiereFactory,
    ModuleFactory,
    ParcoursFactory,
    ProfilFactory,
    SeanceFactory,
    Semestre1Factory,
)
from EDT_app.models import DocumentPedagogique, Profil, ReferentClasse, Seance
from EDT_app.outils_tests import faille_connue, refus_manquants
from EDT_app.tests_securite import PDF_MINIMAL, make_enseignant, make_etudiant, make_user

# Toute réponse qui empêche l'action : non connecté, interdit ou introuvable.
REFUS = (401, 403, 404)


def client_de(user):
    """
    Client authentifié avec un utilisateur RELU en base.

    L'objet `user` créé par les helpers garde en mémoire son profil tel qu'il
    était à la création ; après une suspension faite en base, il faut le
    relire pour que la requête voie le nouveau statut.
    """
    client = APIClient()
    client.force_authenticate(user=User.objects.get(pk=user.pk))
    # Une erreur serveur doit devenir une réponse 500 observable, pas une
    # exception qui interrompt le test.
    client.raise_request_exception = False
    return client


def user_de(personne):
    return personne.profil.user


class UniversDeuxDepartements:
    """
    Deux départements A et B, chacun avec sa faculté, sa filière, sa classe,
    sa matière, son module, un enseignant, une séance confirmée et une séance
    en brouillon. Chef A, chef B, un référent de la classe A, un étudiant de
    la classe A, un membre de la scolarité et un admin.

    Des objets « vides » (sans rien qui en dépende) servent aux tests de
    suppression, pour qu'une suppression bloquée par des données liées ne
    soit pas confondue avec un refus de droits.
    """

    def construire_univers(self):
        cache.clear()
        self.annee = AnneeAcademiqueFactory()
        self.sem1 = Semestre1Factory(annee=self.annee)
        self.sem2 = Semestre1Factory(
            annee=self.annee, libelle="Semestre 2",
            date_debut=date(2026, 2, 2), date_fin=date(2026, 6, 30),
        )

        self.fac_a = FaculteFactory(libelle="Faculté Rôles A")
        self.fac_b = FaculteFactory(libelle="Faculté Rôles B")
        self.dept_a = DepartementFactory(libelle="Département Rôles A", faculte=self.fac_a)
        self.dept_b = DepartementFactory(libelle="Département Rôles B", faculte=self.fac_b)
        self.filiere_a = FiliereFactory(libelle="Filière Rôles A", departement=self.dept_a)
        self.filiere_b = FiliereFactory(libelle="Filière Rôles B", departement=self.dept_b)
        self.classe_a = ClasseFactory(filiere=self.filiere_a, semestre=self.sem1, annee=self.annee)
        self.classe_b = ClasseFactory(filiere=self.filiere_b, semestre=self.sem1, annee=self.annee)
        self.matiere_a = MatiereFactory(libelle="Matière Rôles A", departement=self.dept_a)
        self.matiere_b = MatiereFactory(libelle="Matière Rôles B", departement=self.dept_b)
        self.module_a = ModuleFactory(
            libelle="Module Rôles A", matiere=self.matiere_a, semestre=self.sem1, credits=6,
        )
        self.module_b = ModuleFactory(
            libelle="Module Rôles B", matiere=self.matiere_b, semestre=self.sem1, credits=6,
        )

        self.ens_a = make_enseignant("ens_roles_a", self.dept_a)
        self.ens_b = make_enseignant("ens_roles_b", self.dept_b)
        self.email_a, self.tel_a = "ens.a@exemple.test", "0700000019"
        self.email_b, self.tel_b = "ens.b@exemple.test", "0700000029"
        for ens, email, tel in ((self.ens_a, self.email_a, self.tel_a), (self.ens_b, self.email_b, self.tel_b)):
            User.objects.filter(pk=user_de(ens).pk).update(email=email)
            Profil.objects.filter(pk=user_de(ens).pk).update(telephone=tel)

        self.chef_a = make_enseignant("chef_roles_a", self.dept_a)
        self.chef_b = make_enseignant("chef_roles_b", self.dept_b)
        self.dept_a.chef = self.chef_a
        self.dept_a.save()
        self.dept_b.chef = self.chef_b
        self.dept_b.save()

        self.ref_a = make_enseignant("ref_roles_a", self.dept_a)
        ReferentClasse.objects.create(enseignant=self.ref_a).classes.add(self.classe_a)

        self.etu_a = make_etudiant("etu_roles_a", self.classe_a)

        self.resp = make_user("resp_roles")
        self.resp.groups.add(Group.objects.get_or_create(name="responsable")[0])
        ProfilFactory(user=self.resp)
        self.admin = User.objects.create_superuser("admin_roles", password="pass1234")

        def seance(module, ens, classe, debut, fin, statut):
            return SeanceFactory(
                module=module, enseignant=ens, classe=classe, annee=self.annee,
                date_seance=self.sem1.date_debut, type_seance="CM",
                heure_debut=debut, heure_fin=fin, statut=statut,
            )

        self.seance_a = seance(self.module_a, self.ens_a, self.classe_a, time(9, 0), time(11, 0), "Confirmée")
        self.brouillon_a = seance(self.module_a, self.ens_a, self.classe_a, time(14, 15), time(16, 15), "brouillon")
        self.seance_b = seance(self.module_b, self.ens_b, self.classe_b, time(9, 0), time(11, 0), "Confirmée")
        self.brouillon_b = seance(self.module_b, self.ens_b, self.classe_b, time(14, 15), time(16, 15), "brouillon")
        self.aff_b = AffectationModuleFactory(module=self.module_b, enseignant=self.ens_b, heures_prevues=24)

        # Objets supprimables sans dépendances.
        self.fac_vide = FaculteFactory(libelle="Faculté Rôles vide")
        self.dept_vide_b = DepartementFactory(libelle="Département Rôles vide", faculte=self.fac_b)
        self.filiere_vide_b = FiliereFactory(libelle="Filière Rôles vide B", departement=self.dept_b)
        self.matiere_vide_b = MatiereFactory(libelle="Matière Rôles vide B", departement=self.dept_b)
        self.annee_vide = AnneeAcademiqueFactory(
            libelle="2030-2031", date_debut=date(2030, 9, 2), date_fin=date(2031, 6, 30),
        )
        self.sem_vide = Semestre1Factory(
            annee=self.annee_vide, date_debut=date(2030, 9, 2), date_fin=date(2031, 1, 31),
        )
        self.parcours_vide = ParcoursFactory(type_parcours="Doctorat", niveau=3)
        self.ens_vide_b = make_enseignant("ens_roles_vide_b", self.dept_b)

    def assertTousRefuses(self, requetes):
        acceptees = refus_manquants(requetes, REFUS)
        self.assertEqual(acceptees, [], "actions acceptées à tort :\n" + "\n".join(acceptees))

    def assertRefuse(self, resp, msg=None):
        self.assertIn(
            resp.status_code, REFUS,
            msg or f"accepté ({resp.status_code}) : {resp.content[:200]!r}",
        )


# ══════════════════════════════════════════════════════════════════════════════
# 1. VISITEUR NON CONNECTÉ
# ══════════════════════════════════════════════════════════════════════════════

class AccesAnonymeTest(TestCase):
    """Contrôle : aucune route de l'API ne répond sans session."""

    ROUTES = [
        "facultes", "departements", "filieres", "parcours", "annees", "semestres",
        "classes", "profils", "enseignants", "etudiants", "inscriptions",
        "matieres", "modules", "seances", "affectations", "documents",
        "profils/me", "enseignants/mon_planning", "etudiants/mon_planning",
        "modules/mes_modules", "seances/conflits",
    ]

    def test_toutes_les_listes_refusent_un_visiteur(self):
        client = APIClient()
        for route in self.ROUTES:
            with self.subTest(route=route):
                self.assertEqual(client.get(f"/api/{route}/").status_code, 401)


# ══════════════════════════════════════════════════════════════════════════════
# 2. COMPTE SUSPENDU — CORRECTIONS_A_FAIRE.md point 17
# ══════════════════════════════════════════════════════════════════════════════

class CompteSuspenduTest(UniversDeuxDepartements, TestCase):
    """
    Le chef A est suspendu alors que sa session est encore ouverte. Il doit
    être refusé partout, renouvellement de session compris
    (CORRECTIONS_A_FAIRE.md point 17, corrigé le 2026-10-01).
    """

    def setUp(self):
        self.construire_univers()
        Profil.objects.filter(pk=user_de(self.chef_a).pk).update(
            statut="suspendu", motif_suspension="Test de suspension",
        )
        self.client_chef = client_de(user_de(self.chef_a))

    def test_controle_liste_des_seances_refusee(self):
        self.assertEqual(self.client_chef.get("/api/seances/").status_code, 403)

    def test_le_refus_dit_que_le_compte_est_suspendu(self):
        # Champ `code` lu par l'interface pour ramener la personne à la
        # connexion avec ce message (CORRECTIONS_A_FAIRE.md point 41).
        resp = self.client_chef.get("/api/seances/")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.data.get("code"), "profil_suspendu")
        self.assertIn("suspendu", str(resp.data.get("detail")))

    def test_archiver_une_annee_refuse(self):
        self.assertRefuse(self.client_chef.post(f"/api/annees/{self.annee.pk}/archiver/"))

    def test_passer_au_semestre_suivant_refuse(self):
        resp = self.client_chef.post(
            f"/api/classes/{self.classe_a.pk}/passer_semestre/",
            {"semestre_cible_id": self.sem2.pk}, format="json",
        )
        self.assertRefuse(resp)

    def test_controle_se_reactiver_soi_meme_refuse(self):
        resp = self.client_chef.patch(
            f"/api/profils/{user_de(self.chef_a).pk}/changer_statut/",
            {"statut": "actif"}, format="json",
        )
        self.assertRefuse(resp)
        self.assertEqual(Profil.objects.get(pk=user_de(self.chef_a).pk).statut, "suspendu")

    def test_reporter_refuse(self):
        resp = self.client_chef.patch(
            f"/api/seances/{self.seance_a.pk}/reporter/",
            {"date_report": "2025-09-02", "heure_debut_report": "09:00", "heure_fin_report": "11:00"},
            format="json",
        )
        self.assertRefuse(resp)

    def test_controle_publier_refuse(self):
        self.assertRefuse(self.client_chef.post(f"/api/seances/{self.brouillon_a.pk}/publier/"))

    def test_controle_depublier_refuse(self):
        self.assertRefuse(self.client_chef.post(f"/api/seances/{self.seance_a.pk}/depublier/"))

    def test_controle_publier_en_masse_refuse(self):
        resp = self.client_chef.post(
            "/api/seances/publier_masse/", {"seance_ids": [self.brouillon_a.pk]}, format="json",
        )
        self.assertRefuse(resp)

    def test_detecter_les_conflits_refuse(self):
        self.assertRefuse(self.client_chef.get(f"/api/seances/conflits/?semestre_id={self.sem1.pk}"))

    def test_renouveler_sa_session_refuse(self):
        jeton = RefreshToken.for_user(user_de(self.chef_a))
        resp = APIClient().post("/api/token/refresh/", {"refresh": str(jeton)}, format="json")
        self.assertEqual(resp.status_code, 401, "un compte suspendu obtient encore une nouvelle session")
        self.assertEqual(resp.data.get("code"), "profil_suspendu")


# ══════════════════════════════════════════════════════════════════════════════
# 3. RÉGLAGES COMMUNS — CORRECTIONS_A_FAIRE.md point 18
# ══════════════════════════════════════════════════════════════════════════════

class ReglagesCommunsTest(UniversDeuxDepartements, TestCase):
    """
    Facultés, départements (et leur chef), années, semestres, parcours :
    réservés à l'admin et à la scolarité. Un chef ne fait que les lire.
    """

    def setUp(self):
        self.construire_univers()
        self.client_chef = client_de(user_de(self.chef_a))

    def _verifier_refus(self, requetes):
        self.assertTousRefuses(requetes)

    def test_controle_scolarite_et_admin_gerent_les_reglages(self):
        for user in (self.resp, self.admin):
            with self.subTest(user=user.username):
                resp = client_de(user).patch(
                    f"/api/facultes/{self.fac_b.pk}/", {"libelle": f"Renommée {user.pk}"}, format="json",
                )
                self.assertEqual(resp.status_code, 200)

    def test_controle_enseignant_referent_et_etudiant_ne_gerent_pas_les_reglages(self):
        for user in (user_de(self.ens_a), user_de(self.etu_a), user_de(self.ref_a)):
            with self.subTest(user=user.username):
                resp = client_de(user).patch(
                    f"/api/facultes/{self.fac_b.pk}/", {"libelle": "Pirate"}, format="json",
                )
                self.assertEqual(resp.status_code, 403)

    def test_controle_un_chef_lit_les_reglages(self):
        for route in ("facultes", "departements", "annees", "semestres", "parcours"):
            with self.subTest(route=route):
                self.assertEqual(self.client_chef.get(f"/api/{route}/").status_code, 200)

    def test_chef_ne_gere_pas_les_facultes(self):
        c = self.client_chef
        self._verifier_refus([
            ("créer", lambda: c.post("/api/facultes/", {"libelle": "Faculté pirate"}, format="json")),
            ("modifier", lambda: c.patch(f"/api/facultes/{self.fac_b.pk}/", {"libelle": "Pirate"}, format="json")),
            ("supprimer", lambda: c.delete(f"/api/facultes/{self.fac_vide.pk}/")),
        ])

    def test_chef_ne_gere_pas_les_departements(self):
        c = self.client_chef
        self._verifier_refus([
            ("créer", lambda: c.post(
                "/api/departements/", {"libelle": "Département pirate", "faculte_id": self.fac_a.pk},
                format="json")),
            ("modifier un autre", lambda: c.patch(
                f"/api/departements/{self.dept_b.pk}/", {"libelle": "Pirate"}, format="json")),
            ("changer le chef du sien", lambda: c.patch(
                f"/api/departements/{self.dept_a.pk}/", {"chef_id": self.ens_a.pk}, format="json")),
            ("supprimer", lambda: c.delete(f"/api/departements/{self.dept_vide_b.pk}/")),
        ])

    def test_chef_ne_gere_pas_les_annees(self):
        c = self.client_chef
        self._verifier_refus([
            ("créer", lambda: c.post(
                "/api/annees/",
                {"libelle": "2031-2032", "date_debut": "2031-09-01", "date_fin": "2032-06-30"},
                format="json")),
            ("modifier", lambda: c.patch(
                f"/api/annees/{self.annee_vide.pk}/", {"date_fin": "2031-06-29"}, format="json")),
            ("archiver", lambda: c.post(f"/api/annees/{self.annee_vide.pk}/archiver/")),
            ("supprimer", lambda: c.delete(f"/api/annees/{self.annee_vide.pk}/")),
        ])

    def test_chef_ne_gere_pas_les_semestres(self):
        c = self.client_chef
        self._verifier_refus([
            ("modifier", lambda: c.patch(
                f"/api/semestres/{self.sem_vide.pk}/", {"date_fin": "2031-01-30"}, format="json")),
            ("supprimer", lambda: c.delete(f"/api/semestres/{self.sem_vide.pk}/")),
        ])

    def test_chef_ne_gere_pas_les_parcours(self):
        c = self.client_chef
        self._verifier_refus([
            ("créer", lambda: c.post("/api/parcours/", {"type_parcours": "Master", "niveau": 2}, format="json")),
            ("supprimer", lambda: c.delete(f"/api/parcours/{self.parcours_vide.pk}/")),
        ])


# ══════════════════════════════════════════════════════════════════════════════
# 4. ORGANISATION D'UN AUTRE DÉPARTEMENT — CORRECTIONS_A_FAIRE.md point 19
# ══════════════════════════════════════════════════════════════════════════════

class OrganisationAutreDepartementTest(UniversDeuxDepartements, TestCase):
    """Le chef A ne touche ni aux filières, ni aux matières, ni aux classes de B."""

    def setUp(self):
        self.construire_univers()
        self.client_chef = client_de(user_de(self.chef_a))

    def test_controle_chef_modifie_une_filiere_de_son_departement(self):
        resp = self.client_chef.patch(
            f"/api/filieres/{self.filiere_a.pk}/", {"libelle": "Filière Rôles A bis"}, format="json",
        )
        self.assertEqual(resp.status_code, 200)

    def test_controle_filiere_autre_departement_introuvable_sans_parametre(self):
        resp = self.client_chef.patch(
            f"/api/filieres/{self.filiere_b.pk}/", {"libelle": "Pirate"}, format="json",
        )
        self.assertEqual(resp.status_code, 404)

    def test_filiere_autre_departement_via_parametre_departement_id(self):
        c = self.client_chef
        dept = f"?departement_id={self.dept_b.pk}"
        self.assertTousRefuses([
            ("modifier", lambda: c.patch(
                f"/api/filieres/{self.filiere_b.pk}/{dept}", {"libelle": "Pirate"}, format="json")),
            ("supprimer", lambda: c.delete(f"/api/filieres/{self.filiere_vide_b.pk}/{dept}")),
        ])

    def test_matiere_autre_departement(self):
        c = self.client_chef
        self.assertTousRefuses([
            ("modifier", lambda: c.patch(
                f"/api/matieres/{self.matiere_b.pk}/", {"libelle": "Pirate"}, format="json")),
            ("supprimer", lambda: c.delete(f"/api/matieres/{self.matiere_vide_b.pk}/")),
        ])

    def test_creer_une_classe_dans_un_autre_departement(self):
        parcours = ParcoursFactory(type_parcours="Licence", niveau=2)
        resp = self.client_chef.post("/api/classes/", {
            "parcours_id": parcours.pk, "filiere_id": self.filiere_b.pk,
            "semestre_id": self.sem1.pk, "annee_id": self.annee.pk, "code": "",
        }, format="json")
        self.assertRefuse(resp)

    def test_controle_classe_autre_departement_introuvable(self):
        resp = self.client_chef.patch(f"/api/classes/{self.classe_b.pk}/", {"code": "X"}, format="json")
        self.assertEqual(resp.status_code, 404)

    def test_controle_module_autre_departement_refuse(self):
        resp = self.client_chef.patch(f"/api/modules/{self.module_b.pk}/", {"libelle": "Pirate"}, format="json")
        self.assertIn(resp.status_code, (400,) + REFUS)

    def test_lire_une_affectation_d_un_autre_departement_par_son_numero(self):
        # La liste est filtrée ; la lecture par numéro doit l'être aussi.
        self.assertRefuse(self.client_chef.get(f"/api/affectations/{self.aff_b.pk}/"))


# ══════════════════════════════════════════════════════════════════════════════
# 5. PERSONNES — CORRECTIONS_A_FAIRE.md points 20 et 21
# ══════════════════════════════════════════════════════════════════════════════

class PersonnesTest(UniversDeuxDepartements, TestCase):

    def setUp(self):
        self.construire_univers()
        self.client_chef = client_de(user_de(self.chef_a))

    def _suspendre(self, cible):
        return self.client_chef.patch(
            f"/api/profils/{user_de(cible).pk}/changer_statut/",
            {"statut": "suspendu", "motif_suspension": "Test"}, format="json",
        )

    def test_controle_chef_suspend_un_enseignant_de_son_departement(self):
        self.assertEqual(self._suspendre(self.ens_a).status_code, 200)

    def test_chef_ne_suspend_pas_un_enseignant_d_un_autre_departement(self):
        self.assertRefuse(self._suspendre(self.ens_b))
        self.assertEqual(Profil.objects.get(pk=user_de(self.ens_b).pk).statut, "actif")

    def test_chef_ne_suspend_pas_un_autre_chef(self):
        self.assertRefuse(self._suspendre(self.chef_b))
        self.assertEqual(Profil.objects.get(pk=user_de(self.chef_b).pk).statut, "actif")

    def test_chef_ne_lit_pas_le_profil_complet_d_un_autre_departement(self):
        self.assertRefuse(self.client_chef.get(f"/api/profils/{user_de(self.ens_b).pk}/"))

    def test_un_profil_ne_change_pas_de_compte(self):
        autre = make_user("compte_sans_profil")
        resp = self.client_chef.patch(
            f"/api/profils/{user_de(self.ens_a).pk}/", {"user_id": autre.pk}, format="json",
        )
        self.assertIn(resp.status_code, (400,) + REFUS)
        self.assertFalse(Profil.objects.filter(pk=autre.pk).exists())

    def test_controle_enseignant_autre_departement_introuvable_sans_parametre(self):
        resp = self.client_chef.patch(f"/api/enseignants/{self.ens_b.pk}/", {"grade": "Professeur"}, format="json")
        self.assertEqual(resp.status_code, 404)

    def test_chef_ne_modifie_pas_un_enseignant_d_un_autre_departement(self):
        c, tous = self.client_chef, "?tous_departements=1"
        self.assertTousRefuses([
            ("modifier", lambda: c.patch(
                f"/api/enseignants/{self.ens_b.pk}/{tous}", {"grade": "Professeur"}, format="json")),
            ("supprimer", lambda: c.delete(f"/api/enseignants/{self.ens_vide_b.pk}/{tous}")),
        ])

    def test_fiche_reduite_pour_les_enseignants_d_un_autre_departement(self):
        resp = self.client_chef.get("/api/enseignants/?tous_departements=1")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(self.ens_b.pk, [e["profil_id"] for e in resp.data["results"]])
        contenu = resp.content.decode()
        self.assertNotIn(self.email_b, contenu, "email visible hors département")
        self.assertNotIn(self.tel_b, contenu, "téléphone visible hors département")

    def test_chef_n_inscrit_pas_un_etudiant_dans_une_classe_d_un_autre_departement(self):
        profil = ProfilFactory(user=make_user("nouvel_etudiant"))
        resp = self.client_chef.post("/api/etudiants/", {
            "profil_id": profil.pk, "matricule": "ETU-99999", "classe_id": self.classe_b.pk,
        }, format="json")
        self.assertRefuse(resp)

    def test_chef_ne_deplace_pas_un_etudiant_vers_un_autre_departement(self):
        resp = self.client_chef.patch(
            f"/api/etudiants/{self.etu_a.pk}/", {"classe_id": self.classe_b.pk}, format="json",
        )
        self.assertRefuse(resp)


# ══════════════════════════════════════════════════════════════════════════════
# 6. COORDONNÉES PERSONNELLES — CORRECTIONS_A_FAIRE.md point 21
# ══════════════════════════════════════════════════════════════════════════════

class CoordonneesPersonnellesTest(UniversDeuxDepartements, TestCase):
    """Planning public, mais jamais l'email ni le téléphone d'un enseignant."""

    def setUp(self):
        self.construire_univers()
        self.client_etu = client_de(user_de(self.etu_a))

    def _sans_coordonnees(self, resp):
        self.assertEqual(resp.status_code, 200)
        contenu = resp.content.decode()
        self.assertNotIn(self.email_a, contenu, "email de l'enseignant visible")
        self.assertNotIn(self.tel_a, contenu, "téléphone de l'enseignant visible")

    def test_controle_planning_public(self):
        # Règle validée : un étudiant peut consulter la séance d'une autre classe.
        self.assertEqual(self.client_etu.get(f"/api/seances/{self.seance_b.pk}/").status_code, 200)

    def test_etudiant_ne_recoit_pas_les_coordonnees_via_les_seances(self):
        self._sans_coordonnees(self.client_etu.get(f"/api/seances/?classe_id={self.classe_a.pk}"))

    def test_etudiant_ne_recoit_pas_les_coordonnees_via_son_planning(self):
        self._sans_coordonnees(
            self.client_etu.get(f"/api/etudiants/mon_planning/?semaine={self.sem1.date_debut}")
        )


# ══════════════════════════════════════════════════════════════════════════════
# 7. ACTIONS SUR LES SÉANCES — CORRECTIONS_A_FAIRE.md points 22, 23 et 34
# ══════════════════════════════════════════════════════════════════════════════

class ActionsSeancesTest(UniversDeuxDepartements, TestCase):

    REPORT = {"date_report": "2025-09-02", "heure_debut_report": "09:00", "heure_fin_report": "11:00"}

    def setUp(self):
        self.construire_univers()
        self.client_chef_b = client_de(user_de(self.chef_b))
        self.client_ref = client_de(user_de(self.ref_a))

    def test_controle_chef_publie_dans_son_departement(self):
        resp = client_de(user_de(self.chef_a)).post(f"/api/seances/{self.brouillon_a.pk}/publier/")
        self.assertEqual(resp.status_code, 200)

    # ── Chef d'un autre département ─────────────────────────────────────────

    def test_chef_ne_publie_pas_dans_un_autre_departement(self):
        self.assertRefuse(self.client_chef_b.post(f"/api/seances/{self.brouillon_a.pk}/publier/"))
        self.assertEqual(Seance.objects.get(pk=self.brouillon_a.pk).statut, "brouillon")

    def test_chef_ne_depublie_pas_dans_un_autre_departement(self):
        self.assertRefuse(self.client_chef_b.post(f"/api/seances/{self.seance_a.pk}/depublier/"))
        self.assertEqual(Seance.objects.get(pk=self.seance_a.pk).statut, "Confirmée")

    def test_chef_ne_reporte_pas_dans_un_autre_departement(self):
        self.assertRefuse(self.client_chef_b.patch(
            f"/api/seances/{self.seance_a.pk}/reporter/", self.REPORT, format="json"))

    def test_chef_ne_publie_pas_en_masse_dans_un_autre_departement(self):
        resp = self.client_chef_b.post(
            "/api/seances/publier_masse/", {"seance_ids": [self.brouillon_a.pk]}, format="json",
        )
        self.assertIn(resp.status_code, (400,) + REFUS)
        self.assertEqual(Seance.objects.get(pk=self.brouillon_a.pk).statut, "brouillon")

    # ── Référent de la classe A ─────────────────────────────────────────────

    def test_controle_referent_publie_dans_sa_classe(self):
        resp = self.client_ref.post(f"/api/seances/{self.brouillon_a.pk}/publier/")
        self.assertEqual(resp.status_code, 200)

    def test_controle_referent_depublie_dans_sa_classe(self):
        resp = self.client_ref.post(f"/api/seances/{self.seance_a.pk}/depublier/")
        self.assertEqual(resp.status_code, 200)

    def test_referent_reporte_dans_sa_classe(self):
        resp = self.client_ref.patch(f"/api/seances/{self.seance_a.pk}/reporter/", self.REPORT, format="json")
        self.assertEqual(resp.status_code, 200)

    def test_referent_ne_publie_ni_ne_depublie_hors_de_ses_classes(self):
        c = self.client_ref
        self.assertTousRefuses([
            ("publier", lambda: c.post(f"/api/seances/{self.brouillon_b.pk}/publier/")),
            ("dépublier", lambda: c.post(f"/api/seances/{self.seance_b.pk}/depublier/")),
            ("publier en masse", lambda: c.post(
                "/api/seances/publier_masse/", {"seance_ids": [self.brouillon_b.pk]}, format="json")),
        ])

    # ── Détection des conflits ──────────────────────────────────────────────

    def test_un_chef_detecte_les_conflits_de_son_semestre(self):
        # Les tests existants passent par la scolarité, qui saute le contrôle
        # de département : pour un chef, la requête plante (erreur 500).
        client = client_de(user_de(self.chef_a))
        resp = client.get(f"/api/seances/conflits/?semestre_id={self.sem1.pk}")
        self.assertEqual(resp.status_code, 200, resp.content[:200])


# ══════════════════════════════════════════════════════════════════════════════
# 8. DOCUMENTS — CORRECTIONS_A_FAIRE.md point 24
# ══════════════════════════════════════════════════════════════════════════════

class DocumentsSansRoleTest(UniversDeuxDepartements, TestCase):

    def setUp(self):
        media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=media)
        override.enable()
        self.addCleanup(override.disable)

        self.construire_univers()
        DocumentPedagogique.objects.create(
            titre="Cours A", module=self.module_a, enseignant=self.ens_a,
            fichier=SimpleUploadedFile("cours.pdf", PDF_MINIMAL, content_type="application/pdf"),
        )

    def test_controle_compte_sans_profil_ne_voit_rien(self):
        resp = client_de(make_user("sans_profil")).get("/api/documents/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 0)

    def test_profil_ni_etudiant_ni_enseignant_ne_voit_rien(self):
        user = make_user("profil_sans_role")
        ProfilFactory(user=user)
        resp = client_de(user).get("/api/documents/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 0)
