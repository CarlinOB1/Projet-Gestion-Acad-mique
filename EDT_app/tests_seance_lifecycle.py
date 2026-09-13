# tests_seance_lifecycle.py
#
# Complète tests_complets.py / tests_affectation.py sur les zones du cycle de
# vie de Seance qui n'étaient couvertes par aucun test :
#   - création : année archivée, séance mutualisée (seance_liee)
#   - modification (PATCH) : périmètre chef/référent en écriture
#   - report (/reporter/) : asymétrie de permission chef-seul, couplage avec
#     le volume de l'affectation
#   - suppression : aucun test n'existait avant ce fichier
#
# Lancement :
#   python manage.py test EDT_app.tests_seance_lifecycle --verbosity=2

from datetime import time, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from EDT_app.factories import (
    AffectationModuleFactory,
    AnneeAcademiqueFactory,
    ClasseFactory,
    DepartementFactory,
    EnseignantFactory,
    FiliereFactory,
    MatiereFactory,
    ModuleFactory,
    ParcoursFactory,
    ProfilFactory,
    SeanceFactory,
    Semestre1Factory,
)
from EDT_app.models import AnneeAcademique, ReferentClasse, Seance


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def make_enseignant(username, departement):
    """Crée un User + Profil + Enseignant rattaché au département donné."""
    from django.contrib.auth.models import User
    user = User.objects.create_user(username=username, password="pass1234")
    profil = ProfilFactory(user=user)
    return EnseignantFactory(profil=profil, departement=departement)


def make_referent(enseignant, classes):
    """Fait de l'enseignant donné le référent des classes listées."""
    referent = ReferentClasse.objects.create(enseignant=enseignant)
    referent.classes.set(classes)
    return referent


def client_for(enseignant):
    """APIClient authentifié directement comme l'utilisateur de cet enseignant."""
    client = APIClient()
    client.force_authenticate(user=enseignant.profil.user)
    return client


# ══════════════════════════════════════════════════════════════════════════════
# A. CRÉATION — deux trous précis (le reste est déjà couvert ailleurs)
# ══════════════════════════════════════════════════════════════════════════════

class SeanceCreationAnneeArchiveeTest(TestCase):

    def test_creation_refusee_si_annee_archivee(self):
        """valider_annee_non_archivee : seul le sens inverse (archivage
        bloqué par une séance future) était testé jusqu'ici."""
        annee = AnneeAcademiqueFactory()
        sem = Semestre1Factory(annee=annee)
        dept = DepartementFactory()
        filiere = FiliereFactory(departement=dept)
        classe = ClasseFactory(filiere=filiere, semestre=sem, annee=annee)
        matiere = MatiereFactory(departement=dept)
        module = ModuleFactory(
            matiere=matiere, semestre=sem, credits=6, libelle="Module Annee Archivee"
        )
        enseignant = EnseignantFactory(departement=dept)

        AnneeAcademique.objects.filter(pk=annee.pk).update(statut='archivée')
        annee.refresh_from_db()

        with self.assertRaises(ValidationError) as cm:
            SeanceFactory(
                module=module, enseignant=enseignant, classe=classe, annee=annee,
                date_seance=sem.date_debut,
                heure_debut=time(9, 0), heure_fin=time(11, 0),
                type_seance='CM', statut='Confirmée',
            )
        self.assertIn("archivée", str(cm.exception))


class SeanceMutualiseeTest(TestCase):
    """
    seance_liee relie deux séances d'un même cours mutualisé (même enseignant,
    même créneau, classes différentes). L'exemption ne joue QUE sur le conflit
    enseignant (valider_conflit_enseignant) : le conflit classe
    (valider_conflit_classe) n'a aucune notion de séance liée.
    """

    def setUp(self):
        self.annee = AnneeAcademiqueFactory()
        self.sem = Semestre1Factory(annee=self.annee)
        self.dept = DepartementFactory()
        self.filiere = FiliereFactory(departement=self.dept)
        self.classe_a = ClasseFactory(filiere=self.filiere, semestre=self.sem, annee=self.annee)
        self.classe_b = ClasseFactory(
            filiere=self.filiere, semestre=self.sem, annee=self.annee,
            parcours=ParcoursFactory(type_parcours='Licence', niveau=2),
        )
        self.matiere = MatiereFactory(departement=self.dept)
        self.module = ModuleFactory(
            matiere=self.matiere, semestre=self.sem, credits=6, libelle="Module Mutualise"
        )
        self.enseignant = EnseignantFactory(departement=self.dept)

    def test_seance_liee_exempte_le_conflit_enseignant(self):
        seance1 = SeanceFactory(
            module=self.module, enseignant=self.enseignant, classe=self.classe_a,
            annee=self.annee, date_seance=self.sem.date_debut,
            heure_debut=time(9, 0), heure_fin=time(11, 0),
            type_seance='CM', statut='Confirmée',
        )
        seance2 = SeanceFactory(
            module=self.module, enseignant=self.enseignant, classe=self.classe_b,
            annee=self.annee, date_seance=self.sem.date_debut,
            heure_debut=time(9, 0), heure_fin=time(11, 0),
            type_seance='CM', statut='Confirmée', seance_liee=seance1,
        )
        self.assertIsNotNone(seance2.pk)
        self.assertEqual(seance2.seance_liee_id, seance1.pk)

    def test_conflit_classe_reste_bloquant_malgre_le_lien(self):
        seance1 = SeanceFactory(
            module=self.module, enseignant=self.enseignant, classe=self.classe_b,
            annee=self.annee, date_seance=self.sem.date_debut,
            heure_debut=time(9, 0), heure_fin=time(11, 0),
            type_seance='CM', statut='Confirmée',
        )
        autre_enseignant = EnseignantFactory(departement=self.dept)
        with self.assertRaises(ValidationError) as cm:
            SeanceFactory(
                module=self.module, enseignant=autre_enseignant, classe=self.classe_b,
                annee=self.annee, date_seance=self.sem.date_debut,
                heure_debut=time(9, 0), heure_fin=time(11, 0),
                type_seance='TD', statut='Confirmée', seance_liee=seance1,
            )
        self.assertIn("classe a déjà une séance", str(cm.exception))


# ══════════════════════════════════════════════════════════════════════════════
# B. MODIFICATION (PATCH)
# ══════════════════════════════════════════════════════════════════════════════

class SeanceModificationTest(TestCase):

    def setUp(self):
        self.annee = AnneeAcademiqueFactory()
        self.sem = Semestre1Factory(annee=self.annee)
        self.dept_a = DepartementFactory(libelle="Département Modif A")
        self.dept_b = DepartementFactory(libelle="Département Modif B")
        self.filiere_a = FiliereFactory(departement=self.dept_a)
        self.filiere_b = FiliereFactory(departement=self.dept_b)
        self.classe_a = ClasseFactory(filiere=self.filiere_a, semestre=self.sem, annee=self.annee)
        self.classe_b = ClasseFactory(
            filiere=self.filiere_b, semestre=self.sem, annee=self.annee,
            parcours=ParcoursFactory(type_parcours='Licence', niveau=2),
        )
        self.matiere_a = MatiereFactory(departement=self.dept_a)
        self.module_a = ModuleFactory(
            matiere=self.matiere_a, semestre=self.sem, credits=6, libelle="Module Modif A"
        )
        self.enseignant_a = EnseignantFactory(departement=self.dept_a)

        self.seance = SeanceFactory(
            module=self.module_a, enseignant=self.enseignant_a, classe=self.classe_a,
            annee=self.annee, date_seance=self.sem.date_debut,
            heure_debut=time(9, 0), heure_fin=time(11, 0),
            type_seance='CM', statut='Confirmée',
        )

        self.chef_a = make_enseignant("chef_modif_a", self.dept_a)
        self.dept_a.chef = self.chef_a
        self.dept_a.save()

        self.chef_b = make_enseignant("chef_modif_b", self.dept_b)
        self.dept_b.chef = self.chef_b
        self.dept_b.save()

    def _patch(self, enseignant):
        client = client_for(enseignant)
        return client.patch(
            f"/api/seances/{self.seance.pk}/",
            {"heure_debut": "14:15:00", "heure_fin": "16:15:00"},
            format="json",
        )

    def test_patch_partiel_reussit(self):
        resp = self._patch(self.chef_a)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.seance.refresh_from_db()
        self.assertEqual(self.seance.heure_debut, time(14, 15))

    def test_chef_hors_departement_refuse(self):
        """
        Chef d'un autre département : la permission globale passe (il est
        bien chef), mais get_queryset() filtre déjà les séances par
        _get_classes_autorisees() pour tout chef (pas pour un référent) —
        l'objet est donc introuvable avant même perform_update, d'où un 404
        et non le 403 qu'on pourrait attendre par analogie avec le référent.
        """
        resp = self._patch(self.chef_b)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.seance.refresh_from_db()
        self.assertEqual(self.seance.heure_debut, time(9, 0))

    def test_referent_modifie_sa_classe_reussit(self):
        referent_ens = make_enseignant("referent_modif", self.dept_b)
        make_referent(referent_ens, [self.classe_a])
        resp = self._patch(referent_ens)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)

    def test_referent_hors_de_ses_classes_refuse(self):
        referent_ens = make_enseignant("referent_modif_hors", self.dept_b)
        make_referent(referent_ens, [self.classe_b])
        resp = self._patch(referent_ens)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_enseignant_simple_refuse(self):
        """Ni chef ni référent : bloqué dès la permission globale (403),
        avant même d'atteindre le contrôle de périmètre par classe."""
        simple = make_enseignant("simple_modif", self.dept_a)
        resp = self._patch(simple)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ══════════════════════════════════════════════════════════════════════════════
# C. REPORT (/api/seances/{id}/reporter/)
# ══════════════════════════════════════════════════════════════════════════════

class SeanceReportTest(TestCase):

    def setUp(self):
        self.annee = AnneeAcademiqueFactory()
        self.sem = Semestre1Factory(annee=self.annee)
        self.dept = DepartementFactory()
        self.filiere = FiliereFactory(departement=self.dept)
        self.classe = ClasseFactory(filiere=self.filiere, semestre=self.sem, annee=self.annee)
        self.matiere = MatiereFactory(departement=self.dept)
        self.module = ModuleFactory(
            matiere=self.matiere, semestre=self.sem, credits=6, libelle="Module Report"
        )
        self.enseignant = EnseignantFactory(departement=self.dept)
        self.seance = SeanceFactory(
            module=self.module, enseignant=self.enseignant, classe=self.classe,
            annee=self.annee, date_seance=self.sem.date_debut,
            heure_debut=time(9, 0), heure_fin=time(11, 0),
            type_seance='CM', statut='Confirmée',
        )
        self.chef = make_enseignant("chef_report", self.dept)
        self.dept.chef = self.chef
        self.dept.save()

    def _date_libre(self):
        d = self.sem.date_debut + timedelta(days=2)
        while d.weekday() == 6:
            d += timedelta(days=1)
        return d

    def test_referent_reporter_refuse(self):
        """
        /reporter/ exige IsChefDepartement seul : contrairement à
        create/update/destroy, le référent — pourtant gestionnaire légitime
        de cette classe — en est exclu.
        """
        referent_ens = make_enseignant("referent_report", self.dept)
        make_referent(referent_ens, [self.classe])
        client = client_for(referent_ens)
        resp = client.patch(
            f"/api/seances/{self.seance.pk}/reporter/",
            {
                "date_report": self._date_libre().isoformat(),
                "heure_debut_report": "14:15:00",
                "heure_fin_report": "16:15:00",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_report_echoue_si_volume_affectation_reduit_entre_temps(self):
        """
        Le chef affecte 2h à l'enseignant, exactement consommées par la
        séance existante (9h-11h). Il réduit ensuite ce volume à 1h : la
        baisse elle-même n'est pas bloquée (AffectationModule.clean() ne
        vérifie pas la consommation déjà engagée). La prochaine sauvegarde
        de la séance — ici son report — rejoue valider_affectation() avec
        la durée du créneau ORIGINAL (9h-11h, inchangé par le report) et
        échoue désormais.

        Point notable : ce rejet se produit dans Seance.save() (appelé par
        SeanceReportSerializer.save(), après que serializer.is_valid() a
        déjà réussi), donc comme une django.core.exceptions.ValidationError
        brute, pas une réponse 400 propre : aucun exception_handler DRF
        personnalisé ne l'intercepte sur ce chemin précis.
        """
        affectation = AffectationModuleFactory(
            module=self.module, enseignant=self.enseignant,
            type_seance='CM', heures_prevues=2,
        )
        affectation.heures_prevues = 1
        affectation.save()

        client = client_for(self.chef)
        with self.assertRaises(ValidationError):
            client.patch(
                f"/api/seances/{self.seance.pk}/reporter/",
                {
                    "date_report": self._date_libre().isoformat(),
                    "heure_debut_report": "14:15:00",
                    "heure_fin_report": "16:15:00",
                },
                format="json",
            )

    def test_referent_reporte_via_patch_normal_sans_passer_par_laction_reporter(self):
        """
        Asymétrie observée : /reporter/ est réservé au chef, mais rien
        n'empêche un référent, autorisé à modifier une séance de sa classe,
        d'obtenir le même effet via un PUT standard avec statut='Reportée'
        (le serveur rejoue alors valider_creneau_report() depuis
        SeanceSerializer.validate(), pas SeanceReportSerializer).
        """
        referent_ens = make_enseignant("referent_report_patch", self.dept)
        make_referent(referent_ens, [self.classe])
        client = client_for(referent_ens)

        date_r = self._date_libre()
        payload = {
            "date_seance": self.seance.date_seance.isoformat(),
            "heure_debut": self.seance.heure_debut.isoformat(),
            "heure_fin": self.seance.heure_fin.isoformat(),
            "type_seance": self.seance.type_seance,
            "statut": "Reportée",
            "module_id": self.module.pk,
            "enseignant_id": self.enseignant.profil_id,
            "classe_id": self.classe.pk,
            "annee_id": self.annee.pk,
            "date_report": date_r.isoformat(),
            "heure_debut_report": "14:15:00",
            "heure_fin_report": "16:15:00",
        }
        resp = client.put(f"/api/seances/{self.seance.pk}/", payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["statut"], "Reportée")


# ══════════════════════════════════════════════════════════════════════════════
# D. SUPPRESSION — aucun test n'existait avant ce fichier
# ══════════════════════════════════════════════════════════════════════════════

class SeanceSuppressionTest(TestCase):

    def setUp(self):
        self.annee = AnneeAcademiqueFactory()
        self.sem = Semestre1Factory(annee=self.annee)
        self.dept_a = DepartementFactory(libelle="Département Suppr A")
        self.dept_b = DepartementFactory(libelle="Département Suppr B")
        self.filiere_a = FiliereFactory(departement=self.dept_a)
        self.classe_a = ClasseFactory(filiere=self.filiere_a, semestre=self.sem, annee=self.annee)
        self.classe_a2 = ClasseFactory(
            filiere=self.filiere_a, semestre=self.sem, annee=self.annee,
            parcours=ParcoursFactory(type_parcours='Licence', niveau=2),
        )
        self.matiere_a = MatiereFactory(departement=self.dept_a)
        self.module_a = ModuleFactory(
            matiere=self.matiere_a, semestre=self.sem, credits=6, libelle="Module Suppr A"
        )
        self.enseignant_a = EnseignantFactory(departement=self.dept_a)

        self.chef_a = make_enseignant("chef_suppr_a", self.dept_a)
        self.dept_a.chef = self.chef_a
        self.dept_a.save()

        self.chef_b = make_enseignant("chef_suppr_b", self.dept_b)
        self.dept_b.chef = self.chef_b
        self.dept_b.save()

    def _creer_seance(self, classe, enseignant=None, heure_debut=time(9, 0),
                       heure_fin=time(11, 0), seance_liee=None):
        return SeanceFactory(
            module=self.module_a, enseignant=enseignant or self.enseignant_a, classe=classe,
            annee=self.annee, date_seance=self.sem.date_debut,
            heure_debut=heure_debut, heure_fin=heure_fin,
            type_seance='CM', statut='Confirmée', seance_liee=seance_liee,
        )

    def test_chef_supprime_succes(self):
        seance = self._creer_seance(self.classe_a)
        client = client_for(self.chef_a)
        resp = client.delete(f"/api/seances/{seance.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Seance.objects.filter(pk=seance.pk).exists())

    def test_referent_supprime_sa_classe_succes(self):
        seance = self._creer_seance(self.classe_a)
        referent_ens = make_enseignant("referent_suppr", self.dept_b)
        make_referent(referent_ens, [self.classe_a])
        client = client_for(referent_ens)
        resp = client.delete(f"/api/seances/{seance.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Seance.objects.filter(pk=seance.pk).exists())

    def test_chef_hors_perimetre_refuse(self):
        """
        Comme pour la modification : get_queryset() filtre déjà les séances
        par département pour un chef, donc l'objet est introuvable (404)
        avant même d'atteindre perform_destroy — pas un 403.
        """
        seance = self._creer_seance(self.classe_a)
        client = client_for(self.chef_b)
        resp = client.delete(f"/api/seances/{seance.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Seance.objects.filter(pk=seance.pk).exists())

    def test_enseignant_simple_refuse(self):
        seance = self._creer_seance(self.classe_a)
        simple = make_enseignant("simple_suppr", self.dept_a)
        client = client_for(simple)
        resp = client.delete(f"/api/seances/{seance.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Seance.objects.filter(pk=seance.pk).exists())

    def test_suppression_dune_seance_mutualisee_ne_supprime_pas_la_jumelle(self):
        """
        Pas de FK directe entre les deux séances liées : supprimer l'une ne
        cascade pas sur l'autre. Son champ seance_liee repasse simplement à
        null (on_delete=SET_NULL) sans lever d'erreur.
        """
        seance1 = self._creer_seance(self.classe_a)
        seance2 = self._creer_seance(self.classe_a2, seance_liee=seance1)

        client = client_for(self.chef_a)
        resp = client.delete(f"/api/seances/{seance1.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

        seance2.refresh_from_db()
        self.assertIsNone(seance2.seance_liee_id)


# ══════════════════════════════════════════════════════════════════════════════
# E. REMPLACEMENT DU MODULE OU DE L'ENSEIGNANT D'UNE SÉANCE EXISTANTE
# ══════════════════════════════════════════════════════════════════════════════
#
# SeanceModificationTest (section B) ne couvre la modification que sous
# l'angle du périmètre, via un simple changement d'horaire en PATCH partiel.
# Remplacer le module ou l'enseignant par un AUTRE réactive potentiellement
# toutes les validations croisées de EDT_app.validation_seance (département,
# semestre, conflit, volume module, volume d'affectation) — jamais testé.
#
# Ces tests utilisent un PUT avec la représentation complète (pas un PATCH
# partiel) : SeanceSerializer.validate() ne lit que data.get(...), donc un
# champ absent du corps de la requête désactive silencieusement les
# contrôles qui en dépendent (déjà observé avec le PATCH d'horaire de la
# section B).

class SeanceRemplacementModuleEnseignantTest(TestCase):

    def setUp(self):
        self.annee = AnneeAcademiqueFactory()
        self.sem = Semestre1Factory(annee=self.annee)
        self.dept_a = DepartementFactory(libelle="Département Remplacement A")
        self.dept_b = DepartementFactory(libelle="Département Remplacement B")
        self.filiere_a = FiliereFactory(departement=self.dept_a, libelle="Filiere Remplacement A")
        self.classe = ClasseFactory(filiere=self.filiere_a, semestre=self.sem, annee=self.annee)
        self.matiere_a = MatiereFactory(departement=self.dept_a, libelle="Matière Remplacement A")
        self.matiere_b = MatiereFactory(departement=self.dept_b, libelle="Matière Remplacement B")
        self.module_a = ModuleFactory(
            matiere=self.matiere_a, semestre=self.sem, credits=6,
            libelle="Module Remplacement Initial",
        )
        self.enseignant_a = EnseignantFactory(departement=self.dept_a)

        self.seance = SeanceFactory(
            module=self.module_a, enseignant=self.enseignant_a, classe=self.classe,
            annee=self.annee, date_seance=self.sem.date_debut,
            heure_debut=time(9, 0), heure_fin=time(11, 0),
            type_seance='CM', statut='Confirmée',
        )

        self.chef_a = make_enseignant("chef_remplacement_a", self.dept_a)
        self.dept_a.chef = self.chef_a
        self.dept_a.save()

    def _payload(self, **overrides):
        payload = {
            "date_seance": self.seance.date_seance.isoformat(),
            "heure_debut": self.seance.heure_debut.isoformat(),
            "heure_fin": self.seance.heure_fin.isoformat(),
            "type_seance": self.seance.type_seance,
            "statut": self.seance.statut,
            "module_id": self.module_a.pk,
            "enseignant_id": self.enseignant_a.profil_id,
            "classe_id": self.classe.pk,
            "annee_id": self.annee.pk,
        }
        payload.update(overrides)
        return payload

    def _put(self, **overrides):
        return client_for(self.chef_a).put(
            f"/api/seances/{self.seance.pk}/", self._payload(**overrides), format="json",
        )

    def _nouvelle_classe(self, suffix):
        """Une classe supplémentaire de dept_a, pour des séances de
        remplissage ou de conflit qui ne doivent pas se marcher dessus."""
        filiere = FiliereFactory(departement=self.dept_a, libelle=f"Filiere {suffix}")
        return ClasseFactory(filiere=filiere, semestre=self.sem, annee=self.annee)

    def _remplir_module(self, module, nb):
        """
        Sature (une partie du) volume de `module` via `nb` séances de 4h
        effectives (9h-13h15 : chevauche la courte pause de 11h-11h15,
        déduite du calcul, mais pas la pause méridienne de 13h15-14h15),
        chacune sur sa propre classe et son propre enseignant pour ne
        déclencher ni plafond journalier par classe, ni conflit enseignant.
        """
        for i in range(nb):
            classe = self._nouvelle_classe(f"Remplissage {module.pk}-{i}")
            enseignant = EnseignantFactory(departement=self.dept_a)
            SeanceFactory(
                module=module, enseignant=enseignant, classe=classe,
                annee=self.annee, date_seance=self.sem.date_debut,
                heure_debut=time(9, 0), heure_fin=time(13, 15),
                type_seance='CM', statut='Confirmée',
            )

    # ── Remplacement du module ────────────────────────────────────────────

    def test_remplacement_module_valide_reussit(self):
        module_a2 = ModuleFactory(
            matiere=self.matiere_a, semestre=self.sem, credits=6, libelle="Module A2"
        )
        resp = self._put(module_id=module_a2.pk)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["module"]["id"], module_a2.pk)

    def test_remplacement_module_departement_different_refuse(self):
        module_b = ModuleFactory(
            matiere=self.matiere_b, semestre=self.sem, credits=6,
            libelle="Module B Departement Different",
        )
        resp = self._put(module_id=module_b.pk)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("enseignant_id", resp.data)

    def test_remplacement_module_semestre_different_refuse(self):
        autre_sem = Semestre1Factory(
            annee=self.annee, libelle="Semestre 2",
            date_debut=self.annee.date_debut, date_fin=self.annee.date_fin,
        )
        module_autre_sem = ModuleFactory(
            matiere=self.matiere_a, semestre=autre_sem, credits=6,
            libelle="Module Autre Semestre",
        )
        resp = self._put(module_id=module_autre_sem.pk)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("module_id", resp.data)

    def test_remplacement_module_volume_sature_refuse(self):
        module_sature = ModuleFactory(
            matiere=self.matiere_a, semestre=self.sem, credits=1,  # 12h max
            libelle="Module Sature",
        )
        self._remplir_module(module_sature, 3)  # 3 x 4h = 12h : plus rien de libre
        resp = self._put(module_id=module_sature.pk)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("module_id", resp.data)

    def test_remplacement_module_avec_affectation_pour_autre_enseignant_refuse(self):
        module_aff_autre = ModuleFactory(
            matiere=self.matiere_a, semestre=self.sem, credits=6,
            libelle="Module Affectation Autre Enseignant",
        )
        autre_enseignant = EnseignantFactory(departement=self.dept_a)
        AffectationModuleFactory(
            module=module_aff_autre, enseignant=autre_enseignant,
            type_seance='CM', heures_prevues=10,
        )
        resp = self._put(module_id=module_aff_autre.pk)  # enseignant_a inchangé, non affecté ici
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("enseignant_id", resp.data)

    def test_remplacement_module_avec_affectation_volume_insuffisant_refuse(self):
        module_aff_insuff = ModuleFactory(
            matiere=self.matiere_a, semestre=self.sem, credits=6,
            libelle="Module Affectation Volume Insuffisant",
        )
        AffectationModuleFactory(
            module=module_aff_insuff, enseignant=self.enseignant_a,
            type_seance='CM', heures_prevues=1,  # < 2h, la durée de la séance
        )
        resp = self._put(module_id=module_aff_insuff.pk)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("enseignant_id", resp.data)

    def test_remplacement_par_le_meme_module_reussit(self):
        """Non-régression : renvoyer le module inchangé ne casse rien."""
        resp = self._put()
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)

    # ── Remplacement de l'enseignant ──────────────────────────────────────

    def test_remplacement_enseignant_valide_reussit(self):
        enseignant_a2 = EnseignantFactory(departement=self.dept_a)
        resp = self._put(enseignant_id=enseignant_a2.profil_id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["enseignant"]["profil_id"], enseignant_a2.profil_id)

    def test_remplacement_enseignant_departement_different_refuse(self):
        enseignant_b = EnseignantFactory(departement=self.dept_b)
        resp = self._put(enseignant_id=enseignant_b.profil_id)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("enseignant_id", resp.data)

    def test_remplacement_enseignant_conflit_horaire_refuse(self):
        enseignant_c = EnseignantFactory(departement=self.dept_a)
        autre_classe = self._nouvelle_classe("Conflit Enseignant")
        SeanceFactory(
            module=self.module_a, enseignant=enseignant_c, classe=autre_classe,
            annee=self.annee, date_seance=self.sem.date_debut,
            heure_debut=time(9, 0), heure_fin=time(11, 0),
            type_seance='CM', statut='Confirmée',
        )
        resp = self._put(enseignant_id=enseignant_c.profil_id)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("enseignant_id", resp.data)

    def test_remplacement_enseignant_non_affecte_refuse(self):
        enseignant_affecte = EnseignantFactory(departement=self.dept_a)
        AffectationModuleFactory(
            module=self.module_a, enseignant=enseignant_affecte,
            type_seance='CM', heures_prevues=10,
        )
        enseignant_non_affecte = EnseignantFactory(departement=self.dept_a)
        resp = self._put(enseignant_id=enseignant_non_affecte.profil_id)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("enseignant_id", resp.data)

    def test_remplacement_enseignant_volume_affectation_insuffisant_refuse(self):
        enseignant_limite = EnseignantFactory(departement=self.dept_a)
        AffectationModuleFactory(
            module=self.module_a, enseignant=enseignant_limite,
            type_seance='CM', heures_prevues=1,  # < 2h
        )
        resp = self._put(enseignant_id=enseignant_limite.profil_id)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("enseignant_id", resp.data)

    def test_remplacement_par_le_meme_enseignant_reussit(self):
        """Non-régression : renvoyer l'enseignant inchangé ne casse rien."""
        resp = self._put()
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)

    # ── Remplacement combiné ──────────────────────────────────────────────

    def test_remplacement_module_et_enseignant_paire_coherente_reussit(self):
        module_combo = ModuleFactory(
            matiere=self.matiere_a, semestre=self.sem, credits=6,
            libelle="Module Combo Coherent",
        )
        enseignant_combo = EnseignantFactory(departement=self.dept_a)
        resp = self._put(module_id=module_combo.pk, enseignant_id=enseignant_combo.profil_id)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)

    def test_remplacement_module_et_enseignant_paire_incoherente_refuse(self):
        """Nouveau module d'un département, nouvel enseignant d'un AUTRE
        département : ni l'un ni l'autre ne se correspond."""
        dept_c = DepartementFactory(libelle="Département Remplacement C")
        matiere_c = MatiereFactory(departement=dept_c, libelle="Matière Remplacement C")
        module_combo = ModuleFactory(
            matiere=matiere_c, semestre=self.sem, credits=6,
            libelle="Module Combo Incoherent",
        )
        enseignant_b = EnseignantFactory(departement=self.dept_b)
        resp = self._put(module_id=module_combo.pk, enseignant_id=enseignant_b.profil_id)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("enseignant_id", resp.data)


class SeanceRemplacementEnseignantMutualiseeTest(TestCase):
    """
    L'exemption de conflit enseignant sur seance_liee (cf. section A,
    SeanceMutualiseeTest) doit tenir aussi bien à la MODIFICATION qu'à la
    création — et ne couvrir que le couple lié spécifique, pas n'importe
    quel conflit du nouvel enseignant.

    Point technique : seance_liee_id est un champ non requis. S'il est omis
    du corps de la requête, SeanceSerializer.validate() le lit comme None
    (data.get('seance_liee') ne "hérite" pas de la valeur déjà en base), et
    l'exemption ne s'applique donc pas. Il faut le renvoyer explicitement à
    chaque PUT pour préserver le lien.
    """

    def setUp(self):
        self.annee = AnneeAcademiqueFactory()
        self.sem = Semestre1Factory(annee=self.annee)
        self.dept = DepartementFactory(libelle="Département Mutualise Remplacement")
        self.filiere = FiliereFactory(departement=self.dept, libelle="Filiere Mutualise Remplacement")
        self.classe_a = ClasseFactory(filiere=self.filiere, semestre=self.sem, annee=self.annee)
        self.classe_b = ClasseFactory(
            filiere=self.filiere, semestre=self.sem, annee=self.annee,
            parcours=ParcoursFactory(type_parcours='Licence', niveau=2),
        )
        self.matiere = MatiereFactory(departement=self.dept, libelle="Matière Mutualise Remplacement")
        self.module = ModuleFactory(
            matiere=self.matiere, semestre=self.sem, credits=6, libelle="Module Mutualise Remplacement"
        )
        self.ens_a = EnseignantFactory(departement=self.dept)
        self.ens_b = EnseignantFactory(departement=self.dept)

        self.seance1 = SeanceFactory(
            module=self.module, enseignant=self.ens_a, classe=self.classe_a,
            annee=self.annee, date_seance=self.sem.date_debut,
            heure_debut=time(9, 0), heure_fin=time(11, 0),
            type_seance='CM', statut='Confirmée',
        )
        self.seance2 = SeanceFactory(
            module=self.module, enseignant=self.ens_b, classe=self.classe_b,
            annee=self.annee, date_seance=self.sem.date_debut,
            heure_debut=time(9, 0), heure_fin=time(11, 0),
            type_seance='CM', statut='Confirmée', seance_liee=self.seance1,
        )

        self.chef = make_enseignant("chef_mutualise_remplacement", self.dept)
        self.dept.chef = self.chef
        self.dept.save()

    def _payload_seance2(self, enseignant_id):
        return {
            "date_seance": self.seance2.date_seance.isoformat(),
            "heure_debut": self.seance2.heure_debut.isoformat(),
            "heure_fin": self.seance2.heure_fin.isoformat(),
            "type_seance": self.seance2.type_seance,
            "statut": self.seance2.statut,
            "module_id": self.module.pk,
            "enseignant_id": enseignant_id,
            "classe_id": self.classe_b.pk,
            "annee_id": self.annee.pk,
            "seance_liee_id": self.seance1.pk,
        }

    def test_remplacement_vers_lenseignant_de_la_seance_liee_reussit(self):
        """Les deux séances mutualisées partagent maintenant le même
        enseignant sur le même créneau : l'exemption sur seance_liee tient
        à la modification, pas seulement à la création."""
        client = client_for(self.chef)
        resp = client.put(
            f"/api/seances/{self.seance2.pk}/",
            self._payload_seance2(self.ens_a.profil_id),
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)

    def test_remplacement_vers_un_tiers_en_conflit_ailleurs_refuse(self):
        """L'exemption ne couvre que le couple lié (seance1<->seance2) : un
        troisième enseignant, en conflit avec une séance SANS RAPPORT, reste
        bloqué malgré le lien conservé."""
        classe_c = self._nouvelle_classe_dept("Tiers")
        ens_c = EnseignantFactory(departement=self.dept)
        SeanceFactory(
            module=self.module, enseignant=ens_c, classe=classe_c,
            annee=self.annee, date_seance=self.sem.date_debut,
            heure_debut=time(9, 0), heure_fin=time(11, 0),
            type_seance='CM', statut='Confirmée',
        )

        client = client_for(self.chef)
        resp = client.put(
            f"/api/seances/{self.seance2.pk}/",
            self._payload_seance2(ens_c.profil_id),
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("enseignant_id", resp.data)

    def _nouvelle_classe_dept(self, suffix):
        filiere = FiliereFactory(departement=self.dept, libelle=f"Filiere {suffix}")
        return ClasseFactory(filiere=filiere, semestre=self.sem, annee=self.annee)
