# tests_module_quota.py
#
# Tests unitaires dédiés aux méthodes de quota horaire de Module
# (EDT_app/models.py) : heures_max(), heures_consommees(), heures_effectuees(),
# heures_restantes() et heures_par_type().
#
# Ces méthodes sont le socle de valider_volume_module()
# (EDT_app/validation_seance.py), l'une des rares règles *bloquantes* de
# l'application : une séance est refusée dès que sa durée dépasse
# module.heures_restantes(). Jusqu'ici elles n'étaient exercées
# qu'indirectement, à travers des tests d'intégration séance <-> affectation
# qui passent par l'API et ne disent pas quelle couche a produit le chiffre.
#
# Le pendant côté affectation existe déjà (AffectationModuleQuotaMethodesTest,
# dans tests_affectation.py) ; ce fichier est son symétrique côté module. Dans
# le style de tests_perimetre.py, on appelle directement les méthodes sur des
# objets construits en base de test, sans HTTP, sans authentification et sans
# sérialiseur — ces couches sont couvertes ailleurs.
#
# Lancement :
#   python manage.py test EDT_app.tests_module_quota --verbosity=2

from datetime import date, time, timedelta

from django.test import TestCase

from EDT_app.factories import (
    AffectationModuleFactory,
    AnneeAcademiqueFactory,
    ClasseFactory,
    EnseignantFactory,
    ModuleFactory,
    SeanceFactory,
    Semestre1Factory,
)
from EDT_app.models import Module, Seance


class ModuleQuotaMethodesTest(TestCase):
    """
    Contrat de calcul du volume horaire d'un module.

    Deux particularités distinguent Module.heures_consommees() de son homonyme
    sur AffectationModule, et aucune n'était documentée par un test : côté
    module, le total agrège *tous* les enseignants et *tous* les types de
    séance, sans aucun filtre.
    """

    def setUp(self):
        self.today = date.today()
        # Même montage que AffectationModuleQuotaMethodesTest :
        # AnneeAcademique.clean() exige libelle="AAAA-AAAA" ET que
        # date_debut/date_fin tombent dans ces deux années civiles. On encadre
        # largement `today` par une "année" du 1er janvier au 31 décembre de
        # l'année suivante, pour avoir de la marge des deux côtés (séance
        # passée / séance future) sans dépendre de la position de `today` dans
        # l'année civile.
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
        # Libellé explicite obligatoire : ModuleFactory fait un get_or_create
        # sur (libelle, semestre) avec un Iterator de 2 valeurs seulement, dont
        # l'état est partagé entre tests.
        self.module = ModuleFactory(
            credits=3, semestre=self.sem, libelle="Module Volume"
        )  # 3 crédits x 12h = 36h de plafond
        self.enseignant = EnseignantFactory(
            departement=self.module.matiere.departement
        )
        self.classe = ClasseFactory(semestre=self.sem, annee=self.annee)
        # Aucune AffectationModule n'est créée ici : valider_affectation()
        # dégrade gracieusement quand le module n'en déclare aucune, ce qui
        # isole le calcul du module de celui de l'affectation.

    # ──────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────────────────────

    def _date_non_dimanche(self, delta_jours):
        d = self.today + timedelta(days=delta_jours)
        while d.weekday() == 6:
            d += timedelta(days=1)
        return d

    def _creer_seance(self, delta_jours, heure_debut, heure_fin, **kwargs):
        """
        Chaque appel doit viser un jour différent : sur un même jour, les
        séances se heurteraient à valider_conflit_classe,
        valider_conflit_enseignant ou au plafond de 6h/jour.
        """
        kwargs.setdefault("enseignant", self.enseignant)
        return SeanceFactory(
            module=self.module,
            classe=self.classe,
            annee=self.annee,
            date_seance=self._date_non_dimanche(delta_jours),
            heure_debut=heure_debut,
            heure_fin=heure_fin,
            type_seance="CM",
            statut="Confirmée",
            **kwargs,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # TESTS
    # ──────────────────────────────────────────────────────────────────────────

    def test_heures_max_et_restantes_derivent_des_credits(self):
        """1 crédit = 12h : sans aucune séance, tout le plafond reste disponible."""
        self.assertEqual(self.module.heures_max(), 36)
        self.assertEqual(self.module.heures_consommees(), 0)
        self.assertEqual(self.module.heures_restantes(), 36)

    def test_seuls_les_statuts_confirmee_et_reportee_sont_comptes(self):
        """Un brouillon ou une séance annulée ne consomme pas de volume."""
        self._creer_seance(-12, time(9, 0), time(11, 0))               # 2h comptées
        brouillon = self._creer_seance(-10, time(9, 0), time(11, 0))   # 2h, puis brouillon
        annulee = self._creer_seance(-8, time(9, 0), time(11, 0))      # 2h, puis annulée
        # .update() contourne full_clean() : on fabrique ici un état, pas une
        # transition métier (celles-ci sont testées dans tests_seance_lifecycle).
        Seance.objects.filter(pk=brouillon.pk).update(statut="brouillon")
        Seance.objects.filter(pk=annulee.pk).update(statut="Annulée")

        self.assertEqual(self.module.heures_consommees(), 2)
        self.assertEqual(self.module.heures_restantes(), 34)

    def test_heures_consommees_agrege_tous_les_enseignants_du_module(self):
        """
        Côté module, le total ne fait aucun tri : il additionne les séances de
        tous les enseignants et de tous les types. C'est précisément ce qui le
        distingue de AffectationModule.heures_consommees(), qui reste cantonné
        au couple (module, enseignant) — et au type quand l'affectation est
        typée.
        """
        autre_enseignant = EnseignantFactory(
            departement=self.module.matiere.departement
        )
        self._creer_seance(-12, time(9, 0), time(11, 0))  # 2h — enseignant 1
        self._creer_seance(
            -10, time(9, 0), time(11, 0), enseignant=autre_enseignant
        )  # 2h — enseignant 2

        affectation = AffectationModuleFactory(
            module=self.module,
            enseignant=self.enseignant,
            type_seance="CM",
            heures_prevues=10,
        )

        self.assertEqual(self.module.heures_consommees(), 4)
        self.assertEqual(affectation.heures_consommees(), 2)

    def test_cours_mutualise_ne_compte_quune_fois(self):
        """
        Un cours mutualisé entre deux classes (deux Seance liées par
        seance_liee, même module/enseignant/créneau) ne doit être compté
        qu'une fois — pas deux — sur le volume du module.
        CORRECTIONS_A_FAIRE.md, point 16 : avant dédoublonnage, un cours de
        2h mutualisé entre deux classes comptait pour 4h.
        """
        autre_classe = ClasseFactory(semestre=self.sem, annee=self.annee)

        pivot = self._creer_seance(-10, time(9, 0), time(11, 0))  # 2h, classe 1
        SeanceFactory(
            module=self.module, classe=autre_classe, annee=self.annee,
            enseignant=self.enseignant, date_seance=pivot.date_seance,
            heure_debut=pivot.heure_debut, heure_fin=pivot.heure_fin,
            type_seance="CM", statut="Confirmée", seance_liee=pivot,
        )  # même créneau, classe 2 — jumelle mutualisée

        self.assertEqual(self.module.heures_consommees(), 2)
        self.assertEqual(self.module.heures_restantes(), 34)

    def test_pause_courte_deduite_puis_creneau_de_report_prioritaire(self):
        """
        Deux propriétés en une, sur la même séance :
        - la pause de 11h00-11h15 est retranchée de la durée facturée ;
        - dès que la séance est reportée, c'est le créneau de report qui
          compte, plus celui d'origine.
        """
        # 09:00-13:15 = 4h15 au mur, moins les 15 min de pause = 4h effectives.
        # Le créneau s'arrête pile à 13:15, donc il ne mord pas sur la pause
        # méridienne et passe bien valider_horaires().
        seance = self._creer_seance(-10, time(9, 0), time(13, 15))
        self.assertEqual(self.module.heures_consommees(), 4.0)

        Seance.objects.filter(pk=seance.pk).update(
            statut="Reportée",
            date_report=self._date_non_dimanche(-5),
            heure_debut_report=time(14, 15),
            heure_fin_report=time(16, 15),
        )

        # Le report vaut 2h : c'est lui qui est compté, pas les 4h d'origine.
        self.assertEqual(self.module.heures_consommees(), 2.0)
        self.assertEqual(self.module.heures_restantes(), 34.0)

    def test_heures_effectuees_suit_la_date_de_report_pas_la_date_initiale(self):
        """
        heures_consommees() compte le planifié, heures_effectuees() le réalisé.
        Une séance passée mais reportée dans le futur départage les deux : elle
        occupe toujours du volume, mais elle n'a pas encore eu lieu.
        """
        seance = self._creer_seance(-10, time(9, 0), time(11, 0))
        self.assertEqual(self.module.heures_effectuees(), 2)

        Seance.objects.filter(pk=seance.pk).update(
            statut="Reportée",
            date_report=self._date_non_dimanche(10),
            heure_debut_report=time(9, 0),
            heure_fin_report=time(11, 0),
        )

        self.assertEqual(self.module.heures_consommees(), 2)
        self.assertEqual(self.module.heures_effectuees(), 0)

    def test_exclure_seance_pk_neutralise_la_seance_en_cours_de_modification(self):
        """
        Contrat dont dépend valider_volume_module() : sans cette exclusion, une
        séance ré-enregistrée se compterait elle-même et serait refusée par son
        propre volume.
        """
        seance = self._creer_seance(-12, time(9, 0), time(11, 0))
        self._creer_seance(-10, time(9, 0), time(11, 0))

        self.assertEqual(self.module.heures_consommees(), 4)
        self.assertEqual(self.module.heures_restantes(), 32)

        self.assertEqual(self.module.heures_consommees(exclure_seance_pk=seance.pk), 2)
        self.assertEqual(self.module.heures_restantes(exclure_seance_pk=seance.pk), 34)

    def test_heures_restantes_devient_negative_si_les_credits_sont_reduits(self):
        """
        heures_restantes() ne borne pas à zéro. C'est l'état de base à
        l'origine du point 1 de CORRECTIONS_A_FAIRE.md : un volume réduit
        *après* que des séances l'ont déjà consommé laisse un solde négatif.
        """
        for delta in (-16, -14, -12, -10):
            self._creer_seance(delta, time(9, 0), time(13, 15))  # 4h chacune

        self.assertEqual(self.module.heures_consommees(), 16.0)
        self.assertEqual(self.module.heures_restantes(), 20.0)

        # .update() contourne full_clean() : on fabrique ici l'état d'un module
        # dégradé après coup, pas une modification passée par l'API.
        Module.objects.filter(pk=self.module.pk).update(credits=1)
        self.module.refresh_from_db()

        self.assertEqual(self.module.heures_max(), 12)
        self.assertEqual(self.module.heures_restantes(), -4.0)

    def test_heures_par_type_retourne_le_plafond_declare_ou_none(self):
        """
        La ventilation par type est optionnelle : un type non renseigné vaut
        None (pas 0), ce qui signifie « non ventilé », et non « aucune heure ».
        """
        module = ModuleFactory(
            credits=3,
            semestre=self.sem,
            libelle="Module Ventile",
            heures_cm=20,
        )

        self.assertEqual(module.heures_par_type("CM"), 20)
        self.assertIsNone(module.heures_par_type("TD"))
        self.assertIsNone(module.heures_par_type("TP"))
        self.assertIsNone(module.heures_par_type("XX"))
