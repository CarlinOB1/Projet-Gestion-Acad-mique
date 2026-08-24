from django.test import TestCase
from django.core.exceptions import ValidationError
from EDT_app.factories import (
    EnseignantFactory, ModuleFactory, AffectationModuleFactory
)
from EDT_app.models import AffectationModule

class AffectationModuleTest(TestCase):
    def setUp(self):
        self.module = ModuleFactory(credits=3) # 36h max
        self.enseignant = EnseignantFactory()
        
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
                heure_debut="14:00",
                heure_fin="16:00"
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

