from datetime import date, time, timedelta

from django.test import TestCase
from django.core.exceptions import ValidationError
from EDT_app.factories import (
    AnneeAcademiqueFactory, ClasseFactory, DepartementFactory,
    EnseignantFactory, MatiereFactory, ModuleFactory, AffectationModuleFactory,
    ProfilFactory, Semestre1Factory,
)
from EDT_app.models import AffectationModule, ReferentClasse, Seance

class AffectationModuleTest(TestCase):
    def setUp(self):
        self.module = ModuleFactory(credits=3) # 36h max
        # L'enseignant doit appartenir au departement de la matiere du module :
        # AffectationModule.clean() applique desormais la meme regle que Seance.
        self.enseignant = EnseignantFactory(
            departement=self.module.matiere.departement
        )
        
    def test_affectation_generique_et_typee_interdite_meme_enseignant(self):
        """Un même enseignant ne peut pas avoir une affectation générique ET typée sur le même module."""
        # 1. Création affectation générique
        AffectationModuleFactory(
            module=self.module,
            enseignant=self.enseignant,
            type_seance=None,
            heures_prevues=10
        )
        
        # 2. Tentative création affectation typée -> Doit échouer
        with self.assertRaises(ValidationError) as cm:
            AffectationModuleFactory(
                module=self.module,
                enseignant=self.enseignant,
                type_seance='CM',
                heures_prevues=10
            )
        self.assertIn("déjà une affectation générique", str(cm.exception))

    def test_affectation_typee_puis_generique_interdite_meme_enseignant(self):
        """Un même enseignant ne peut pas avoir une affectation typée PUIS générique."""
        # 1. Création affectation typée
        AffectationModuleFactory(
            module=self.module,
            enseignant=self.enseignant,
            type_seance='CM',
            heures_prevues=10
        )
        
        # 2. Tentative création affectation générique -> Doit échouer
        with self.assertRaises(ValidationError) as cm:
            AffectationModuleFactory(
                module=self.module,
                enseignant=self.enseignant,
                type_seance=None,
                heures_prevues=10
            )
        self.assertIn("déjà une ou plusieurs affectations typées", str(cm.exception))

    def test_coexistence_generique_et_typee_differents_enseignants(self):
        """Deux enseignants différents peuvent avoir des affectations de nature différente sur le même module."""
        enseignant2 = EnseignantFactory(departement=self.enseignant.departement)
        
        # Ens 1: CM
        aff1 = AffectationModuleFactory(
            module=self.module,
            enseignant=self.enseignant,
            type_seance='CM',
            heures_prevues=10
        )
        
        # Ens 2: Générique
        aff2 = AffectationModuleFactory(
            module=self.module,
            enseignant=enseignant2,
            type_seance=None,
            heures_prevues=10
        )
        
        self.assertEqual(AffectationModule.objects.count(), 2)

    def test_depassement_volume_module_non_bloquant(self):
        """Le dépassement du volume max du module n'empêche pas l'enregistrement, mais remonte un warning (via has_volume_warning)."""
        # Module max = 36h
        aff1 = AffectationModuleFactory(
            module=self.module,
            enseignant=self.enseignant,
            type_seance='CM',
            heures_prevues=20
        )
        self.assertFalse(aff1.has_volume_warning())
        
        enseignant2 = EnseignantFactory(departement=self.enseignant.departement)
        aff2 = AffectationModuleFactory(
            module=self.module,
            enseignant=enseignant2,
            type_seance='TD',
            heures_prevues=20  # 20 + 20 = 40 > 36
        )
        self.assertTrue(aff2.has_volume_warning())
        self.assertTrue(aff1.has_volume_warning()) # Les deux affectations voient le dépassement

    def test_module_validation_heures_typees(self):
        """La somme des heures CM/TD/TP sur le module ne doit pas dépasser heures_max()"""
        self.module.heures_cm = 20
        self.module.heures_td = 10
        self.module.heures_tp = 0
        self.module.save() # Ok, 30 <= 36
        
        self.module.heures_tp = 10 # 40 > 36
        with self.assertRaises(ValidationError) as cm:
            self.module.save()
        self.assertIn("dépasse le volume horaire maximal du module", str(cm.exception))


class SeanceAffectationIntegrationTest(TestCase):
    def setUp(self):
        from EDT_app.factories import ClasseFactory, SeanceFactory
        from datetime import time, date, timedelta
        
        self.module = ModuleFactory(credits=3) # max 36h
        self.enseignant = EnseignantFactory(departement=self.module.matiere.departement)
        self.classe = ClasseFactory(semestre=self.module.semestre, annee=self.module.semestre.annee)
        self.date_seance = self.module.semestre.date_debut
        
    def test_seance_sans_aucune_affectation_module(self):
        """Dégradation gracieuse : si le module n'a AUCUNE affectation, la séance est acceptée normalement."""
        from EDT_app.factories import SeanceFactory
        
        # On ne crée aucune AffectationModule
        
        # Création séance
        seance = SeanceFactory(
            module=self.module,
            enseignant=self.enseignant,
            classe=self.classe,
            type_seance='CM',
            date_seance=self.date_seance
        )
        # Ne doit pas lever d'exception
        self.assertIsNotNone(seance.pk)

    def test_seance_avec_affectation_manquante_enseignant(self):
        """Si le module a des affectations, mais pas pour cet enseignant -> erreur."""
        from EDT_app.factories import SeanceFactory
        
        enseignant_autre = EnseignantFactory(departement=self.module.matiere.departement)
        AffectationModuleFactory(module=self.module, enseignant=enseignant_autre, type_seance='CM')
        
        # Création séance avec self.enseignant (non affecté)
        with self.assertRaises(ValidationError) as cm:
            SeanceFactory(
                module=self.module,
                enseignant=self.enseignant,
                classe=self.classe,
                type_seance='CM',
                date_seance=self.date_seance
            )
        self.assertIn("Cet enseignant n'est pas affecté sur ce module", str(cm.exception))

    def test_seance_avec_affectation_valide_generique(self):
        """Une affectation générique autorise la séance et déduit les heures."""
        from EDT_app.factories import SeanceFactory
        
        affectation = AffectationModuleFactory(
            module=self.module,
            enseignant=self.enseignant,
            type_seance=None,
            heures_prevues=4
        )
        
        seance = SeanceFactory(
            module=self.module,
            enseignant=self.enseignant,
            classe=self.classe,
            type_seance='CM', # Séance typée CM
            date_seance=self.date_seance,
            heure_debut="09:00",
            heure_fin="11:00" # 2h
        )
        self.assertEqual(affectation.heures_consommees(), 2)

    def test_seance_avec_affectation_valide_typee(self):
        """Une affectation typée autorise la séance correspondante."""
        from EDT_app.factories import SeanceFactory
        
        affectation = AffectationModuleFactory(
            module=self.module,
            enseignant=self.enseignant,
            type_seance='TD',
            heures_prevues=4
        )
        
        # Test séance TD: OK
        seance = SeanceFactory(
            module=self.module,
            enseignant=self.enseignant,
            classe=self.classe,
            type_seance='TD',
            date_seance=self.date_seance
        )
        self.assertIsNotNone(seance.pk)
        
        # Test séance CM: Erreur, car l'enseignant n'a qu'une affectation TD
        with self.assertRaises(ValidationError) as cm:
            SeanceFactory(
                module=self.module,
                enseignant=self.enseignant,
                classe=self.classe,
                type_seance='CM',
                date_seance=self.date_seance,
                heure_debut="14:15",
                heure_fin="16:15"
            )
        self.assertIn("Cet enseignant n'est pas affecté sur ce module", str(cm.exception))

    def test_seance_depassement_volume_affectation(self):
        """Dépassement du volume de l'affectation individuelle lève une erreur spécifique."""
        from EDT_app.factories import SeanceFactory
        
        affectation = AffectationModuleFactory(
            module=self.module,
            enseignant=self.enseignant,
            type_seance='TD',
            heures_prevues=2 # Seulement 2h prévues
        )
        
        with self.assertRaises(ValidationError) as cm:
            SeanceFactory(
                module=self.module,
                enseignant=self.enseignant,
                classe=self.classe,
                type_seance='TD',
                date_seance=self.date_seance,
                heure_debut="09:00",
                heure_fin="12:00" # 3h > 2h
            )
        self.assertIn("dépasse le volume horaire restant sur l'affectation", str(cm.exception))



class AffectationDepartementTest(TestCase):
    """
    AffectationModule.clean() applique la meme regle de departement que Seance :
    sans elle, un chef pouvait affecter a un enseignant un module relevant d'un
    autre departement, et la fiche de l'enseignant listait des modules
    etrangers a sa discipline.
    """

    def test_affectation_hors_departement_rejetee(self):
        module = ModuleFactory(credits=3)
        etranger = EnseignantFactory()   # departement distinct de la matiere

        self.assertNotEqual(
            etranger.departement_id, module.matiere.departement_id
        )
        with self.assertRaises(ValidationError) as cm:
            AffectationModuleFactory(
                module=module, enseignant=etranger,
                type_seance='CM', heures_prevues=10,
            )
        self.assertIn("pas du même département", str(cm.exception))

    def test_affectation_meme_departement_acceptee(self):
        module = ModuleFactory(credits=3)
        collegue = EnseignantFactory(departement=module.matiere.departement)

        affectation = AffectationModuleFactory(
            module=module, enseignant=collegue,
            type_seance='CM', heures_prevues=10,
        )
        self.assertIsNotNone(affectation.pk)


class AffectationInterDepartementAPITest(TestCase):
    """
    Couvre la branche d'autorisation "chef de departement" de
    AffectationModuleSerializer.validate() (flag hors_departement) : ce
    n'est testable qu'via un appel API authentifie, ce n'est pas exprimable
    au niveau du modele (AffectationModule.clean() ne connait pas *qui*
    affecte, seulement la coherence enseignant <-> matiere).

    Cas reel : le departement Mathematiques dispense "Algebre lineaire"
    dans une classe du departement Informatique. Le chef Informatique
    dirige la classe mais pas les Mathematiques.
    """

    def setUp(self):
        from rest_framework.test import APIClient
        from EDT_app.factories import DepartementFactory, FiliereFactory, ClasseFactory, MatiereFactory

        self.dept_info = DepartementFactory(libelle='Département Informatique')
        self.dept_math = DepartementFactory(libelle='Département Mathématiques')

        self.chef_info = EnseignantFactory(departement=self.dept_info)
        self.dept_info.chef = self.chef_info
        self.dept_info.save()

        self.filiere_info = FiliereFactory(departement=self.dept_info)
        self.classe_info = ClasseFactory(filiere=self.filiere_info)

        self.matiere_math = MatiereFactory(departement=self.dept_math, libelle='Algèbre')
        self.module_algebre = ModuleFactory(
            libelle='Algèbre linéaire', matiere=self.matiere_math,
            classe=self.classe_info, credits=3,
        )
        self.enseignant_math = EnseignantFactory(departement=self.dept_math)

        self.client = APIClient()
        self.client.force_authenticate(user=self.chef_info.profil.user)

    def _payload(self, **overrides):
        payload = {
            'module_id': self.module_algebre.pk,
            'enseignant_id': self.enseignant_math.profil_id,
            'type_seance': 'CM',
            'heures_prevues': 10,
        }
        payload.update(overrides)
        return payload

    def test_hors_departement_sans_flag_refusee(self):
        """Meme si c'est bien sa classe, sans cocher le flag, l'affectation est refusee."""
        reponse = self.client.post('/api/affectations/', self._payload())
        self.assertEqual(reponse.status_code, 400)
        self.assertIn('module_id', reponse.data)

    def test_hors_departement_avec_flag_et_classe_geree_acceptee(self):
        """Flag coche + classe geree par le chef -> affectation autorisee."""
        reponse = self.client.post(
            '/api/affectations/', self._payload(hors_departement=True)
        )
        self.assertEqual(reponse.status_code, 201, reponse.data)
        self.assertTrue(reponse.data['hors_departement'])

    def test_hors_departement_avec_flag_mais_classe_non_geree_refusee(self):
        """Le flag seul ne suffit pas : si ce n'est pas une de ses classes, refus."""
        from EDT_app.factories import FiliereFactory, ClasseFactory

        filiere_math = FiliereFactory(departement=self.dept_math)
        classe_math = ClasseFactory(filiere=filiere_math)
        module_hors_classe = ModuleFactory(
            libelle='Analyse', matiere=self.matiere_math,
            classe=classe_math, credits=3,
        )
        reponse = self.client.post(
            '/api/affectations/',
            self._payload(module_id=module_hors_classe.pk, hors_departement=True),
        )
        self.assertEqual(reponse.status_code, 400)
        self.assertIn('module_id', reponse.data)

    def test_propre_departement_flag_absent_non_regression(self):
        """Cas normal (module de son propre departement) : toujours accepte, sans flag."""
        from EDT_app.factories import MatiereFactory

        matiere_info = MatiereFactory(departement=self.dept_info, libelle='Bases de données')
        module_info = ModuleFactory(
            libelle='Bases de données avancées', matiere=matiere_info,
            classe=self.classe_info, credits=3,
        )
        enseignant_info = EnseignantFactory(departement=self.dept_info)

        reponse = self.client.post(
            '/api/affectations/',
            self._payload(module_id=module_info.pk, enseignant_id=enseignant_info.profil_id),
        )
        self.assertEqual(reponse.status_code, 201, reponse.data)
        self.assertFalse(reponse.data['hors_departement'])

    def test_hors_departement_classe_l1_sans_filiere_refusee_proprement(self):
        """
        Une classe de L1 (filiere=None) ne doit jamais faire planter la regle
        (classe.filiere.departement_id sur filiere=None) : elle est simplement
        traitee comme hors perimetre du chef, jamais une erreur 500.
        """
        from EDT_app.factories import ClasseFactory, ParcoursFactory

        classe_l1 = ClasseFactory(
            filiere=None, code='MIP', parcours=ParcoursFactory(niveau=1),
        )
        module_l1 = ModuleFactory(
            libelle='Algèbre linéaire L1', matiere=self.matiere_math,
            classe=classe_l1, credits=3,
        )
        reponse = self.client.post(
            '/api/affectations/',
            self._payload(module_id=module_l1.pk, hors_departement=True),
        )
        self.assertEqual(reponse.status_code, 400)
        self.assertIn('module_id', reponse.data)

    def test_liste_enseignants_scopee_par_defaut_au_departement_du_chef(self):
        """
        Non-regression : sans parametre explicite, /api/enseignants/ reste
        scope au(x) departement(s) diriges par le chef (comportement existant
        des pages de gestion des enseignants).
        """
        reponse = self.client.get('/api/enseignants/')
        self.assertEqual(reponse.status_code, 200)
        resultats = reponse.data.get('results', reponse.data)
        departements_vus = {r['departement']['id'] for r in resultats if r.get('departement')}
        self.assertEqual(departements_vus, {self.dept_info.pk})

    def test_liste_enseignants_tous_departements_debloque_le_choix_hors_departement(self):
        """
        Avec ?tous_departements=1 (envoye par le formulaire quand la case est
        cochee), le chef doit pouvoir voir des enseignants d'un autre
        departement -- sinon le formulaire d'affectation inter-departements
        ne peut jamais proposer le bon enseignant.
        """
        reponse = self.client.get('/api/enseignants/', {'tous_departements': 1})
        self.assertEqual(reponse.status_code, 200)
        resultats = reponse.data.get('results', reponse.data)
        profils_vus = {r['profil_id'] for r in resultats}
        self.assertIn(self.enseignant_math.profil_id, profils_vus)


class PauseMeridienneTest(TestCase):
    """
    La pause meridienne (13h15-14h15) est une ligne non enseignable de la
    grille. Une seance qui la chevauche s'affichait dans la case 'Pause' de
    l'emploi du temps : elle est desormais refusee a la source.
    """

    def setUp(self):
        from EDT_app.factories import ClasseFactory
        self.module = ModuleFactory(credits=6)
        self.enseignant = EnseignantFactory(
            departement=self.module.matiere.departement
        )
        self.classe = ClasseFactory(
            semestre=self.module.semestre, annee=self.module.semestre.annee
        )
        self.date_seance = self.module.semestre.date_debut

    def _creer(self, heure_debut, heure_fin):
        from EDT_app.factories import SeanceFactory
        return SeanceFactory(
            module=self.module, enseignant=self.enseignant, classe=self.classe,
            type_seance='CM', date_seance=self.date_seance,
            heure_debut=heure_debut, heure_fin=heure_fin,
        )

    def test_seance_sur_la_pause_rejetee(self):
        with self.assertRaises(ValidationError) as cm:
            self._creer("14:00", "16:00")
        self.assertIn("pause méridienne", str(cm.exception))

    def test_seance_a_cheval_sur_la_pause_rejetee(self):
        with self.assertRaises(ValidationError):
            self._creer("13:00", "15:00")

    def test_blocs_de_la_grille_acceptes(self):
        from EDT_app.validation_seance import BLOCS_JOURNEE
        from datetime import timedelta

        for index, (heure_debut, heure_fin) in enumerate(BLOCS_JOURNEE):
            seance = self._creer(heure_debut, heure_fin)
            self.assertIsNotNone(seance.pk)


class InscriptionTest(TestCase):
    """
    Le parcours d'un etudiant est historise par Inscription : Etudiant.classe
    ne designe que la classe courante et perdait tout le passe a chaque
    changement de semestre ou de niveau.
    """

    def setUp(self):
        from EDT_app.factories import ClasseFactory, EtudiantFactory, ParcoursFactory
        self.classe_l1 = ClasseFactory(parcours=ParcoursFactory(
            type_parcours='Licence', niveau=1))
        self.classe_l2 = ClasseFactory(
            parcours=ParcoursFactory(type_parcours='Licence', niveau=2),
            semestre=self.classe_l1.semestre,
        )
        self.etudiant = EtudiantFactory(classe=self.classe_l1)

    def test_premiere_inscription_puis_reinscription(self):
        from EDT_app.models import Inscription

        premiere = self.etudiant.reinscrire(self.classe_l1)
        self.assertEqual(premiere.type_inscription, Inscription.TYPE_INSCRIPTION)
        self.assertEqual(premiere.statut, 'active')

        seconde = self.etudiant.reinscrire(self.classe_l2)
        self.assertEqual(seconde.type_inscription, Inscription.TYPE_REINSCRIPTION)

        premiere.refresh_from_db()
        self.etudiant.refresh_from_db()
        self.assertEqual(premiere.statut, 'terminée')
        self.assertEqual(self.etudiant.classe_id, self.classe_l2.pk)
        self.assertEqual(self.etudiant.inscriptions.count(), 2)

    def test_annee_incoherente_rejetee(self):
        from EDT_app.models import Inscription
        from EDT_app.factories import AnneeAcademiqueFactory

        autre_annee = AnneeAcademiqueFactory(
            libelle='2030-2031',
            date_debut=date(2030, 9, 1), date_fin=date(2031, 6, 30),
        )
        with self.assertRaises(ValidationError):
            Inscription.objects.create(
                etudiant=self.etudiant, classe=self.classe_l1,
                annee=autre_annee,
                type_inscription=Inscription.TYPE_INSCRIPTION,
                date_inscription=date(2030, 9, 15),
            )


class IdentifiantActeursTest(TestCase):
    """
    `Enseignant` et `Etudiant` ont `profil` pour cle primaire : aucun champ `id`
    ne prend le relais. Si `profil_id` repasse en `write_only`, l'API renvoie des
    acteurs sans identifiant et tout filtrage cote client redevient impossible —
    c'est ce qui vidait la page "Mes enseignants" du profil etudiant.
    """

    def setUp(self):
        from EDT_app.factories import ClasseFactory, EtudiantFactory

        self.module = ModuleFactory(credits=3)
        self.enseignant = EnseignantFactory(
            departement=self.module.matiere.departement
        )
        self.classe = ClasseFactory(
            semestre=self.module.semestre, annee=self.module.semestre.annee
        )
        self.etudiant = EtudiantFactory(classe=self.classe)

    def test_enseignant_serialise_expose_profil_id(self):
        from EDT_app.serializers import EnseignantSerializer

        data = EnseignantSerializer(self.enseignant).data
        self.assertIn('profil_id', data)
        self.assertEqual(data['profil_id'], self.enseignant.profil_id)
        self.assertEqual(data['profil_id'], data['profil']['user']['id'])

    def test_etudiant_serialise_expose_profil_id(self):
        from EDT_app.serializers import EtudiantSerializer

        data = EtudiantSerializer(self.etudiant).data
        self.assertIn('profil_id', data)
        self.assertEqual(data['profil_id'], self.etudiant.profil_id)
        self.assertEqual(data['profil_id'], data['profil']['user']['id'])

    def test_profil_id_reste_requis_en_ecriture(self):
        from EDT_app.serializers import EtudiantSerializer

        serializer = EtudiantSerializer(data={
            'matricule': 'ETU-90001',
            'classe_id': self.classe.pk,
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn('profil_id', serializer.errors)

    def test_enseignant_imbrique_dans_une_seance_porte_profil_id(self):
        """
        C'est la donnee dont depend buildTrombinoscope() : sans elle, chaque
        seance est ignoree et la liste "Mes enseignants" reste vide.
        """
        from EDT_app.factories import SeanceFactory
        from EDT_app.serializers import SeanceSerializer

        seance = SeanceFactory(
            module=self.module, enseignant=self.enseignant, classe=self.classe,
            type_seance='CM', date_seance=self.module.semestre.date_debut,
        )
        data = SeanceSerializer(seance).data
        self.assertEqual(data['enseignant']['profil_id'], self.enseignant.profil_id)

    def test_filtre_affectations_par_enseignant(self):
        """
        Garde-fou pour la fiche enseignant : sans identifiant exploitable,
        `enseignant_id` etait `undefined` et l'API renvoyait les affectations
        de tous les enseignants sur chaque fiche.
        """
        from rest_framework.test import APIClient

        collegue = EnseignantFactory(departement=self.module.matiere.departement)
        AffectationModuleFactory(
            module=self.module, enseignant=self.enseignant,
            type_seance='CM', heures_prevues=10,
        )
        AffectationModuleFactory(
            module=self.module, enseignant=collegue,
            type_seance='TD', heures_prevues=10,
        )

        client = APIClient()
        client.force_authenticate(user=self.enseignant.profil.user)
        reponse = client.get(
            '/api/affectations/', {'enseignant_id': self.enseignant.profil_id}
        )
        self.assertEqual(reponse.status_code, 200)
        donnees = reponse.data
        resultats = donnees.get('results', donnees) if isinstance(donnees, dict) else donnees

        self.assertEqual(AffectationModule.objects.count(), 2)
        self.assertEqual(len(resultats), 1)
        self.assertEqual(
            resultats[0]['enseignant']['profil_id'], self.enseignant.profil_id
        )


# ══════════════════════════════════════════════════════════════════════════════
# MODIFICATION D'AFFECTATION — aucun test n'existait avant ce lot
# ══════════════════════════════════════════════════════════════════════════════

def _make_enseignant_avec_compte(username, departement):
    """Crée un User + Profil + Enseignant, pour authentifier un client API."""
    from django.contrib.auth.models import User
    user = User.objects.create_user(username=username, password="pass1234")
    profil = ProfilFactory(user=user)
    return EnseignantFactory(profil=profil, departement=departement)


def _client_pour(enseignant):
    from rest_framework.test import APIClient
    client = APIClient()
    client.force_authenticate(user=enseignant.profil.user)
    return client


class AffectationModuleModificationTest(TestCase):
    """PATCH /api/affectations/{id}/ — jamais testé jusqu'ici."""

    def setUp(self):
        self.dept = DepartementFactory(libelle="Département Modif Aff")
        self.matiere = MatiereFactory(departement=self.dept)
        self.module = ModuleFactory(matiere=self.matiere, credits=3, libelle="Module Modif Aff")
        self.enseignant = EnseignantFactory(departement=self.dept)
        self.chef = _make_enseignant_avec_compte("chef_modif_aff", self.dept)
        self.dept.chef = self.chef
        self.dept.save()
        self.affectation = AffectationModuleFactory(
            module=self.module, enseignant=self.enseignant,
            type_seance='CM', heures_prevues=10,
        )

    def test_chef_modifie_heures_prevues_succes(self):
        resp = _client_pour(self.chef).patch(
            f"/api/affectations/{self.affectation.pk}/",
            {"heures_prevues": 15}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data["heures_prevues"], 15)
        self.assertEqual(resp.data["heures_restantes"], 15)

    def test_modification_en_collision_avec_la_contrainte_dunicite_refusee(self):
        """
        (module, enseignant, type_seance) doit rester unique : faire glisser
        une deuxième affectation typée du même enseignant vers un type déjà
        pris est refusé, pas seulement bloqué à la création.
        """
        autre = AffectationModuleFactory(
            module=self.module, enseignant=self.enseignant,
            type_seance='TD', heures_prevues=5,
        )
        resp = _client_pour(self.chef).patch(
            f"/api/affectations/{autre.pk}/", {"type_seance": "CM"}, format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_referent_seul_ne_peut_pas_modifier(self):
        """
        IsChefDepartementOrReadOnly n'accepte que le chef en écriture : le
        référent, pourtant autorisé à gérer les séances de sa classe, ne
        l'est pas ici — distinction jamais vérifiée jusqu'ici.
        """
        referent_ens = _make_enseignant_avec_compte("referent_modif_aff", self.dept)
        ReferentClasse.objects.create(enseignant=referent_ens)
        resp = _client_pour(referent_ens).patch(
            f"/api/affectations/{self.affectation.pk}/",
            {"heures_prevues": 20}, format="json",
        )
        self.assertEqual(resp.status_code, 403)


class AffectationInterDepartementModificationAPITest(TestCase):
    """
    Le flag hors_departement d'AffectationModuleSerializer.validate() est
    revalidé à CHAQUE modification, pas seulement à la création (complète
    AffectationInterDepartementAPITest, qui ne couvre que le POST).
    """

    def setUp(self):
        from rest_framework.test import APIClient
        from EDT_app.factories import FiliereFactory

        self.dept_info = DepartementFactory(libelle='Département Info Modif')
        self.dept_math = DepartementFactory(libelle='Département Math Modif')
        self.chef_info = EnseignantFactory(departement=self.dept_info)
        self.dept_info.chef = self.chef_info
        self.dept_info.save()

        filiere_info = FiliereFactory(departement=self.dept_info)
        classe_info = ClasseFactory(filiere=filiere_info)
        matiere_math = MatiereFactory(departement=self.dept_math, libelle='Algèbre Modif')
        self.module_algebre = ModuleFactory(
            libelle='Algèbre linéaire Modif', matiere=matiere_math,
            classe=classe_info, credits=3,
        )
        self.enseignant_math = EnseignantFactory(departement=self.dept_math)

        self.client = APIClient()
        self.client.force_authenticate(user=self.chef_info.profil.user)

        creation = self.client.post('/api/affectations/', {
            'module_id': self.module_algebre.pk,
            'enseignant_id': self.enseignant_math.profil_id,
            'type_seance': 'CM',
            'heures_prevues': 10,
            'hors_departement': True,
        })
        assert creation.status_code == 201, creation.data
        self.affectation_id = creation.data['id']

    def test_affectation_hors_departement_creee_reste_accessible(self):
        """
        CORRECTIONS_A_FAIRE.md, point 2, corrigé : perimetre.modules_autorises()
        prolonge désormais aux chefs la même règle qu'aux référents (inclure
        les modules des classes qu'ils dirigent, même hors de leur propre
        département). Le chef peut donc relire ET modifier l'affectation
        hors_departement qu'il vient de créer, plutôt que de la voir
        disparaître (404) juste après sa création.

        Le PATCH porte sur `heures_prevues`, pas sur `hors_departement` :
        remettre `hors_departement` à False resterait refusé par
        AffectationModuleSerializer.validate() (le module reste d'un autre
        département) — une règle distincte, toujours en vigueur, qu'on ne
        veut pas mélanger avec le périmètre testé ici.
        """
        resp_get = self.client.get(f'/api/affectations/{self.affectation_id}/')
        self.assertEqual(resp_get.status_code, 200)

        resp_patch = self.client.patch(
            f'/api/affectations/{self.affectation_id}/',
            {'heures_prevues': 15}, format='json',
        )
        self.assertEqual(resp_patch.status_code, 200, resp_patch.data)
        self.assertEqual(resp_patch.data['heures_prevues'], 15)


# ══════════════════════════════════════════════════════════════════════════════
# SUPPRESSION D'AFFECTATION — aucun test n'existait avant ce lot
# ══════════════════════════════════════════════════════════════════════════════

class AffectationModuleSuppressionTest(TestCase):

    def setUp(self):
        from EDT_app.factories import FiliereFactory

        self.dept_a = DepartementFactory(libelle="Département Suppr Aff A")
        self.dept_b = DepartementFactory(libelle="Département Suppr Aff B")
        self.filiere_a = FiliereFactory(departement=self.dept_a)
        self.matiere_a = MatiereFactory(departement=self.dept_a)
        self.module_a = ModuleFactory(
            matiere=self.matiere_a, credits=3, libelle="Module Suppr Aff A"
        )
        self.enseignant_a = EnseignantFactory(departement=self.dept_a)

        self.chef_a = _make_enseignant_avec_compte("chef_suppr_aff_a", self.dept_a)
        self.dept_a.chef = self.chef_a
        self.dept_a.save()

        self.chef_b = _make_enseignant_avec_compte("chef_suppr_aff_b", self.dept_b)
        self.dept_b.chef = self.chef_b
        self.dept_b.save()

    def test_chef_supprime_sa_propre_affectation_succes(self):
        affectation = AffectationModuleFactory(
            module=self.module_a, enseignant=self.enseignant_a,
            type_seance='CM', heures_prevues=10,
        )
        resp = _client_pour(self.chef_a).delete(f"/api/affectations/{affectation.pk}/")
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(AffectationModule.objects.filter(pk=affectation.pk).exists())

    def test_chef_dun_autre_departement_recoit_403(self):
        """
        CORRECTIONS_A_FAIRE.md, point 3, corrigé : AffectationModuleViewSet a
        désormais son propre contrôle dédié (perform_destroy), symétrique de
        celui de ModuleViewSet, qui s'exécute maintenant que get_queryset()
        ne filtre plus les routes de détail par périmètre.
        """
        affectation = AffectationModuleFactory(
            module=self.module_a, enseignant=self.enseignant_a,
            type_seance='CM', heures_prevues=10,
        )
        resp = _client_pour(self.chef_b).delete(f"/api/affectations/{affectation.pk}/")
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(AffectationModule.objects.filter(pk=affectation.pk).exists())

    def test_referent_seul_refuse(self):
        """IsChefDepartementOrReadOnly n'accepte que le chef : le référent,
        pourtant autorisé sur les séances, ne l'est pas ici."""
        affectation = AffectationModuleFactory(
            module=self.module_a, enseignant=self.enseignant_a,
            type_seance='CM', heures_prevues=10,
        )
        referent_ens = _make_enseignant_avec_compte("referent_suppr_aff", self.dept_b)
        ReferentClasse.objects.create(enseignant=referent_ens)
        resp = _client_pour(referent_ens).delete(f"/api/affectations/{affectation.pk}/")
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(AffectationModule.objects.filter(pk=affectation.pk).exists())

    def test_suppression_naffecte_pas_la_seance_existante_mais_bloque_sa_prochaine_modification(self):
        """
        Pas de FK Seance -> AffectationModule : supprimer une affectation ne
        supprime ni n'invalide en cascade une séance déjà créée avec elle.
        Mais valider_affectation() est rejouée à CHAQUE sauvegarde de la
        séance : la prochaine modification échoue si le module a encore
        d'autres affectations (pour un autre enseignant) mais plus aucune
        pour celui de la séance — couplage différé entre les deux modèles.
        """
        from EDT_app.factories import SeanceFactory

        affectation_x = AffectationModuleFactory(
            module=self.module_a, enseignant=self.enseignant_a,
            type_seance='CM', heures_prevues=10,
        )
        autre_enseignant = EnseignantFactory(departement=self.dept_a)
        AffectationModuleFactory(
            module=self.module_a, enseignant=autre_enseignant,
            type_seance='TD', heures_prevues=5,
        )
        classe = ClasseFactory(
            filiere=self.filiere_a,
            semestre=self.module_a.semestre, annee=self.module_a.semestre.annee,
        )
        seance = SeanceFactory(
            module=self.module_a, enseignant=self.enseignant_a, classe=classe,
            annee=self.module_a.semestre.annee,
            date_seance=self.module_a.semestre.date_debut,
            heure_debut=time(9, 0), heure_fin=time(11, 0),
            type_seance='CM', statut='Confirmée',
        )

        del_resp = _client_pour(self.chef_a).delete(f"/api/affectations/{affectation_x.pk}/")
        self.assertEqual(del_resp.status_code, 204)
        self.assertFalse(AffectationModule.objects.filter(pk=affectation_x.pk).exists())
        self.assertTrue(Seance.objects.filter(pk=seance.pk).exists())

        payload = {
            "date_seance": seance.date_seance.isoformat(),
            "heure_debut": "09:00:00",
            "heure_fin": "11:00:00",
            "type_seance": "CM",
            "statut": "Confirmée",
            "module_id": self.module_a.pk,
            "enseignant_id": self.enseignant_a.profil_id,
            "classe_id": classe.pk,
            "annee_id": self.module_a.semestre.annee_id,
        }
        resp = _client_pour(self.chef_a).put(
            f"/api/seances/{seance.pk}/", payload, format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("enseignant_id", resp.data)


# ══════════════════════════════════════════════════════════════════════════════
# MÉTHODES DE QUOTA — tests unitaires directs, sans API
# ══════════════════════════════════════════════════════════════════════════════

class AffectationModuleQuotaMethodesTest(TestCase):
    """
    heures_consommees / heures_restantes / heures_effectuees /
    volume_total_affectations_module / has_volume_warning / charge_totale
    ne sont exercées jusqu'ici qu'indirectement à travers les tests
    d'intégration séance <-> affectation. On les vérifie ici pour
    elles-mêmes, dans le style de tests_perimetre.py (appel direct, sans API).
    """

    def setUp(self):
        self.today = date.today()
        # AnneeAcademique.clean() exige libelle="AAAA-AAAA" ET que
        # date_debut/date_fin tombent respectivement dans ces deux années
        # civiles : on encadre largement `today` par une "année" du 1er
        # janvier au 31 décembre de l'année suivante, pour être sûr d'avoir
        # de la marge des deux côtés (séance passée / séance future) sans
        # dépendre de la position de `today` dans l'année civile.
        annee_debut = self.today.year
        self.annee = AnneeAcademiqueFactory(
            libelle=f"{annee_debut}-{annee_debut + 1}",
            date_debut=date(annee_debut, 1, 1),
            date_fin=date(annee_debut + 1, 12, 31),
        )
        self.sem = Semestre1Factory(
            annee=self.annee,
            date_debut=date(annee_debut, 1, 1),
            date_fin=date(annee_debut + 1, 12, 31),
        )
        self.module = ModuleFactory(credits=3, semestre=self.sem, libelle="Module Quota")  # 36h max
        self.enseignant = EnseignantFactory(departement=self.module.matiere.departement)
        self.classe = ClasseFactory(semestre=self.sem, annee=self.annee)

    def _date_non_dimanche(self, delta_jours):
        d = self.today + timedelta(days=delta_jours)
        while d.weekday() == 6:
            d += timedelta(days=1)
        return d

    def _creer_seance(self, delta_jours, heure_debut, heure_fin, **kwargs):
        from EDT_app.factories import SeanceFactory
        return SeanceFactory(
            module=self.module, enseignant=self.enseignant, classe=self.classe,
            annee=self.annee, date_seance=self._date_non_dimanche(delta_jours),
            heure_debut=heure_debut, heure_fin=heure_fin,
            type_seance='CM', statut='Confirmée', **kwargs
        )

    def test_heures_consommees_ignore_les_seances_annulees(self):
        affectation = AffectationModuleFactory(
            module=self.module, enseignant=self.enseignant,
            type_seance='CM', heures_prevues=10,
        )
        self._creer_seance(-10, time(9, 0), time(11, 0))               # 2h comptées
        annulee = self._creer_seance(-5, time(14, 15), time(16, 15))   # 2h, puis annulée
        Seance.objects.filter(pk=annulee.pk).update(statut='Annulée')

        self.assertEqual(affectation.heures_consommees(), 2)
        self.assertEqual(affectation.heures_restantes(), 8)

    def test_heures_effectuees_ne_compte_que_le_passe(self):
        affectation = AffectationModuleFactory(
            module=self.module, enseignant=self.enseignant,
            type_seance='CM', heures_prevues=10,
        )
        self._creer_seance(-10, time(9, 0), time(11, 0))    # passée : 2h
        self._creer_seance(10, time(14, 15), time(16, 15))  # future : pas encore effectuée

        self.assertEqual(affectation.heures_effectuees(), 2)
        self.assertEqual(affectation.heures_consommees(), 4)  # passée + future confondues

    def test_volume_total_et_warning_restent_non_bloquants(self):
        aff1 = AffectationModuleFactory(
            module=self.module, enseignant=self.enseignant,
            type_seance='CM', heures_prevues=20,
        )
        autre_enseignant = EnseignantFactory(departement=self.enseignant.departement)
        AffectationModuleFactory(
            module=self.module, enseignant=autre_enseignant,
            type_seance='TD', heures_prevues=20,
        )
        # 20 + 20 = 40h > 36h max du module (credits=3) : dépassement détecté,
        # mais AffectationModuleFactory() n'a pas levé d'exception plus haut.
        self.assertEqual(aff1.volume_total_affectations_module(), 40)
        self.assertTrue(aff1.has_volume_warning())

    def test_charge_totale_somme_toutes_les_affectations_de_lenseignant(self):
        autre_module = ModuleFactory(
            matiere=MatiereFactory(departement=self.enseignant.departement),
            semestre=self.sem, credits=3, libelle="Module Quota Bis",
        )
        AffectationModuleFactory(
            module=self.module, enseignant=self.enseignant,
            type_seance='CM', heures_prevues=10,
        )
        AffectationModuleFactory(
            module=autre_module, enseignant=self.enseignant,
            type_seance='TD', heures_prevues=5,
        )
        self.assertEqual(self.enseignant.charge_totale(), 15)
