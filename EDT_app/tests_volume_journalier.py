# tests_volume_journalier.py
#
# Tests unitaires dédiés à validation_seance.valider_volume_journalier() :
# le plafond de MAX_HEURES_JOUR (6h) de cours par classe et par jour.
#
# Cette fonction est appelée sans condition depuis Seance.clean() dès que
# heure_debut/heure_fin sont renseignés, mais n'avait jusqu'ici qu'une
# couverture indirecte : test_plafond_journalier_classe (EDT_app/tests.py)
# passe par le cycle de vie complet d'une Seance et ne vérifie qu'un seul
# scénario de dépassement.
#
# Comme tests_perimetre.py et tests_module_quota.py, ce fichier appelle la
# fonction directement, sans passer par Seance.clean() ni par l'API — ce qui
# isole cette règle de toutes les autres validations qu'un full_clean()
# complet déclencherait en même temps, et permet de tester des créneaux
# candidats qui n'ont pas besoin d'exister comme Seance réelle.
#
# Lancement :
#   python manage.py test EDT_app.tests_volume_journalier --verbosity=2

from datetime import date, time, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase

from EDT_app.factories import (
    AnneeAcademiqueFactory,
    ClasseFactory,
    EnseignantFactory,
    ModuleFactory,
    SeanceFactory,
    Semestre1Factory,
)
from EDT_app.models import Seance
from EDT_app.validation_seance import valider_volume_journalier


class VolumeJournalierTest(TestCase):
    """
    Contrat du plafond de 6h de cours par classe et par jour.
    """

    def setUp(self):
        self.today = date.today()
        # Même montage que ModuleQuotaMethodesTest : AnneeAcademique.clean()
        # exige libelle="AAAA-AAAA" ET que date_debut/date_fin tombent dans
        # ces deux années civiles. On encadre largement `today` pour avoir de
        # la marge des deux côtés sans dépendre de la position de `today`
        # dans l'année civile.
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
        self.classe = ClasseFactory(semestre=self.sem, annee=self.annee)
        # Libellé explicite obligatoire : ModuleFactory fait un get_or_create
        # sur (libelle, semestre) avec un Iterator de 2 valeurs seulement,
        # dont l'état est partagé entre tests.
        self.module = ModuleFactory(
            credits=3, semestre=self.sem, libelle="Module Volume Journalier"
        )
        self.enseignant = EnseignantFactory(
            departement=self.module.matiere.departement
        )

    # ──────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────────────────────

    def _date_non_dimanche(self, delta_jours):
        d = self.today + timedelta(days=delta_jours)
        while d.weekday() == 6:
            d += timedelta(days=1)
        return d

    def _creer_seance(self, date_seance, heure_debut, heure_fin, **kwargs):
        """
        Contrairement à tests_module_quota.py, plusieurs séances sont ici
        volontairement placées sur le même jour : c'est le sujet même de la
        règle testée.
        """
        kwargs.setdefault("classe", self.classe)
        kwargs.setdefault("module", self.module)
        kwargs.setdefault("enseignant", self.enseignant)
        return SeanceFactory(
            date_seance=date_seance,
            heure_debut=heure_debut,
            heure_fin=heure_fin,
            type_seance="CM",
            statut="Confirmée",
            annee=self.annee,
            **kwargs,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # TESTS
    # ──────────────────────────────────────────────────────────────────────────

    def test_le_plafond_exact_de_six_heures_est_accepte(self):
        """
        Le test est `>` strict : un total qui tombe exactement sur le plafond
        doit passer. On utilise les 3 blocs réels de BLOCS_JOURNEE
        (09:00-11:00, 11:15-13:15, 14:15-16:15), 2h chacun.
        """
        jour = self._date_non_dimanche(-10)
        self._creer_seance(jour, time(9, 0), time(11, 0))
        self._creer_seance(jour, time(11, 15), time(13, 15))

        # Ne doit pas lever : 4h existantes + 2h de candidat = 6h pile.
        valider_volume_journalier(self.classe, jour, time(14, 15), time(16, 15), pk=None)

    def test_depassement_leve_une_erreur_avec_le_total_dans_le_message(self):
        """Un dépassement, même léger, doit être refusé avec le total calculé."""
        jour = self._date_non_dimanche(-10)
        self._creer_seance(jour, time(9, 0), time(11, 0))
        self._creer_seance(jour, time(11, 15), time(13, 15))

        with self.assertRaises(ValidationError) as ctx:
            valider_volume_journalier(
                self.classe, jour, time(14, 15), time(16, 30), pk=None
            )  # 4h + 2h15 = 6h25

        message = str(ctx.exception)
        self.assertIn("6.25", message)

    def test_brouillon_et_annulee_ne_comptent_pas(self):
        """
        Seules les séances Confirmée/Reportée entrent dans le total : un
        brouillon ou une séance annulée ne doivent pas compter, même si tout
        le monde partage le même jour.
        """
        jour = self._date_non_dimanche(-10)
        self._creer_seance(jour, time(9, 0), time(11, 0))  # 2h comptées

        brouillon = self._creer_seance(jour, time(11, 15), time(13, 15))  # 2h, puis brouillon
        annulee = self._creer_seance(jour, time(14, 15), time(16, 15))  # 2h, puis annulée
        # .update() contourne full_clean() : on fabrique ici un état, pas une
        # transition métier (déjà couvertes par tests_seance_lifecycle.py).
        Seance.objects.filter(pk=brouillon.pk).update(statut="brouillon")
        Seance.objects.filter(pk=annulee.pk).update(statut="Annulée")

        # Si brouillon/annulée comptaient, 2+2+2+4=10h aurait été refusé.
        valider_volume_journalier(
            self.classe, jour, time(16, 15), time(20, 15), pk=None
        )  # candidat de 4h, hors grille réelle mais la fonction ne valide pas les bornes horaires

    def test_isolation_par_classe_et_par_jour(self):
        """
        Le total ne doit mélanger ni les classes, ni les jours : une séance
        d'une autre classe le même jour, et une séance de la même classe un
        autre jour, ne doivent apparaître dans aucun des deux calculs.
        """
        jour_cible = self._date_non_dimanche(-10)
        autre_jour = self._date_non_dimanche(-5)
        autre_classe = ClasseFactory(semestre=self.sem, annee=self.annee)

        self._creer_seance(
            jour_cible, time(9, 0), time(13, 15), classe=autre_classe,
        )  # 4h, autre classe, même jour
        self._creer_seance(autre_jour, time(9, 0), time(13, 15))  # 4h, même classe, autre jour

        # Aucune des deux séances ci-dessus ne doit compter ici : 4h de
        # candidat doit passer sans dépassement fantôme.
        valider_volume_journalier(
            self.classe, jour_cible, time(9, 0), time(13, 15), pk=None
        )

    def test_exclusion_du_pk_evite_lauto_double_comptage(self):
        """
        Contrat dont dépend Seance.clean() en passant self.pk : sans cette
        exclusion, une séance ré-enregistrée se compterait elle-même en plus
        de son propre candidat.
        """
        jour = self._date_non_dimanche(-10)
        premier_bloc = self._creer_seance(jour, time(9, 0), time(11, 0))
        self._creer_seance(jour, time(11, 15), time(13, 15))
        self._creer_seance(jour, time(14, 15), time(16, 15))
        # 3 blocs réels = 6h, déjà à la limite exacte (acceptée à la création).

        # Revalider le premier bloc sans exclure son propre pk : il est compté
        # une fois comme séance existante ET une fois comme candidat -> 8h.
        with self.assertRaises(ValidationError):
            valider_volume_journalier(
                self.classe, jour, time(9, 0), time(11, 0), pk=None
            )

        # En excluant son pk, on retombe sur 4h (les 2 autres blocs) + 2h
        # (le candidat, qui reprend ses propres horaires) = 6h pile.
        valider_volume_journalier(
            self.classe, jour, time(9, 0), time(11, 0), pk=premier_bloc.pk
        )

    def test_seance_reportee_compte_sur_son_nouveau_jour_pas_sur_lancien(self):
        """
        CORRECTIONS_A_FAIRE.md, point 5, corrigé : valider_volume_journalier
        bascule désormais sur Seance.creneau_effectif(), comme
        Module.heures_consommees(). Une séance reportée ne pèse plus sur le
        quota de son ANCIEN jour (qu'elle n'occupe plus) mais bien sur celui
        de son NOUVEAU jour (qu'elle occupe réellement).
        """
        ancien_jour = self._date_non_dimanche(-10)
        nouveau_jour = self._date_non_dimanche(-3)

        seance = self._creer_seance(ancien_jour, time(9, 0), time(11, 0))  # 2h
        Seance.objects.filter(pk=seance.pk).update(
            statut="Reportée",
            date_report=nouveau_jour,
            heure_debut_report=time(14, 15),
            heure_fin_report=time(16, 15),
        )

        # L'ancien jour est libéré : un candidat de 4h15 y passe désormais
        # sans les 2h fantômes de la séance qui ne s'y déroule plus.
        valider_volume_journalier(
            self.classe, ancien_jour, time(14, 0), time(18, 15), pk=None
        )  # 4h15 seules

        # Le nouveau jour tient maintenant compte des 2h réellement
        # dispensées ce jour-là (le report) : un candidat de 4h15 EFFECTIVES
        # y dépasse le plafond (4h15 + 2h = 6h15). Le créneau 9h00-13h30
        # (et non 9h00-13h15) est nécessaire ici pour obtenir 4h15
        # effectives : il chevauche la pause courte (11h-11h15), contrairement
        # au candidat 14h00-18h15 utilisé plus haut pour l'ancien jour, qui
        # ne la chevauche pas.
        with self.assertRaises(ValidationError):
            valider_volume_journalier(
                self.classe, nouveau_jour, time(9, 0), time(13, 30), pk=None
            )

    def test_parametres_manquants_ne_leve_rien(self):
        """
        Garde d'entrée : Seance.clean() peut appeler cette fonction avant que
        toutes les FK ne soient résolues (classe absente, dates non encore
        renseignées) — la fonction doit alors se taire plutôt que planter.
        """
        jour = self._date_non_dimanche(-10)
        valider_volume_journalier(None, jour, time(9, 0), time(11, 0), pk=None)
        valider_volume_journalier(self.classe, None, time(9, 0), time(11, 0), pk=None)
        valider_volume_journalier(self.classe, jour, None, time(11, 0), pk=None)
        valider_volume_journalier(self.classe, jour, time(9, 0), None, pk=None)
