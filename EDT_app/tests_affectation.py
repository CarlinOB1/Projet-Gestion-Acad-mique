from datetime import date

from django.test import TestCase
from django.core.exceptions import ValidationError
from EDT_app.factories import (
    EnseignantFactory, ModuleFactory, AffectationModuleFactory
)
from EDT_app.models import AffectationModule

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
