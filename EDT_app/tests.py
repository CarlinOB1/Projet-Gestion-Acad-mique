from django.test import TestCase
from django.core.exceptions import ValidationError
from datetime import date, time
from .factories import (
    SeanceFactory, EtudiantFactory, Semestre1Factory,
    AnneeAcademiqueFactory, ClasseFactory, ModuleFactory
)
from .models import Seance


class GestionEDTTests(TestCase):

    # 1 & 3. SOLUTION : Utilisation de assertRaises pour les validations attendues
    def test_semestre_hors_dates_annee(self):
        """Vérifie qu'un semestre ne peut pas sortir des dates de l'année."""
        annee = AnneeAcademiqueFactory(
            date_debut=date(2025, 9, 1),
            date_fin=date(2026, 6, 30)
        )
        with self.assertRaises(ValidationError):
            Semestre1Factory.create(
                annee=annee,
                date_debut=date(2025, 8, 1)  # AVANT l'année
            )

    def test_matricule_etudiant_invalide(self):
        """Vérifie le format ETU-XXXXX."""
        # On s'attend à ce que la factory lève une ValidationError
        with self.assertRaises(ValidationError):
            EtudiantFactory.create(matricule="BAD-12345")

    # 2. SOLUTION : Cohérence département pour le conflit enseignant
    def test_conflit_enseignant(self):
        """Un enseignant ne peut pas avoir deux séances en même temps."""
        s1 = SeanceFactory.create(
            date_seance=date(2025, 10, 10),
            heure_debut=time(9, 0),
            heure_fin=time(11, 0)
        )

        # On réutilise le MEME module et le MEME enseignant
        # pour éviter l'erreur de département différent
        with self.assertRaises(ValidationError):
            SeanceFactory.create(
                enseignant=s1.enseignant,
                module=s1.module,
                classe=s1.classe,
                date_seance=date(2025, 10, 10),
                heure_debut=time(10, 0),  # Chevauchement
                heure_fin=time(12, 0)
            )

    # 4. MODIFICATION DU TEST : Nouvelle règle heure_debut >= 09h00
    def test_heure_debut_valide_et_invalide(self):
        """Vérifie que 09h00 est accepté mais 08h00 est rejeté."""
        # Cas valide (09h00)
        s_valide = SeanceFactory.create(heure_debut=time(9, 0))
        self.assertIsNotNone(s_valide.pk)

        # Cas invalide (08h00) - car inférieur au MIN_HEURE_DEBUT (09h00)
        with self.assertRaises(ValidationError):
            SeanceFactory.create(heure_debut=time(8, 0))

    # 5. VÉRIFICATION : Même instance de classe pour le plafond journalier
    def test_plafond_journalier_classe(self):
        """Une classe ne peut pas dépasser 6h de cours par jour."""
        # On crée une classe unique
        ma_classe = ClasseFactory.create()

        # Séance 1 : 09h00 - 13h00
        # (Durée brute 4h, moins 15min de pause = 3.75h effectives)
        SeanceFactory.create(
            classe=ma_classe,
            date_seance=date(2025, 10, 10),
            heure_debut=time(9, 0),
            heure_fin=time(13, 0)
        )

        # Séance 2 : 14h00 - 18h00 (4h effectives, pas de pause l'après-midi)
        # TOTAL : 3.75h + 4h = 7.75h -> Doit impérativement lever une ValidationError
        with self.assertRaises(ValidationError):
            s2 = SeanceFactory.build(
                classe=ma_classe,
                date_seance=date(2025, 10, 10),
                heure_debut=time(14, 0),
                heure_fin=time(18, 0)
            )
            s2.full_clean()  # Force la validation des contraintes clean()
            s2.save()

    def test_calcul_duree_avec_pause(self):
        """Vérifie que la pause de 11h00-11h15 est déduite."""
        # Créneau 09h00 - 12h00 = 3h00
        # Pause 11h00 - 11h15 = 15min (0.25h)
        # Durée attendue = 2.75h
        seance = SeanceFactory.create(
            heure_debut=time(9, 0),
            heure_fin=time(12, 0)
        )
        duree = seance.calculer_duree_effective(seance.heure_debut, seance.heure_fin)
        self.assertEqual(duree, 2.75)