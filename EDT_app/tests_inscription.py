# tests_inscription.py
#
# Tests unitaires dédiés à Etudiant.reinscrire() (EDT_app/models.py), point
# d'entrée unique de l'application de scolarité pour faire progresser un
# étudiant d'une classe à l'autre.
#
# La méthode fait quatre choses dans une même transaction : déduire le type
# (Inscription / Réinscription) de l'historique, clôturer les inscriptions
# actives, créer la nouvelle ligne via get_or_create(), et repointer
# Etudiant.classe. Seuls le chemin nominal (InscriptionTest, dans
# tests_affectation.py) et la cohérence année/classe sont couverts : ni
# l'idempotence du get_or_create, ni l'atomicité, ni le sort des inscriptions
# non actives ne sont vérifiés.
#
# Comme tests_perimetre.py et tests_module_quota.py, ce fichier appelle
# directement les méthodes du modèle, sans HTTP ni sérialiseur.
#
# Lancement :
#   python manage.py test EDT_app.tests_inscription --verbosity=2

from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase

from EDT_app.factories import (
    AnneeAcademiqueFactory,
    ClasseFactory,
    EtudiantFactory,
    FiliereFactory,
    ParcoursFactory,
    Semestre1Factory,
)
from EDT_app.models import AnneeAcademique, Inscription


class EtudiantReinscriptionTest(TestCase):
    """
    Contrat de Etudiant.reinscrire() sur les chemins non nominaux.
    """

    def setUp(self):
        # ParcoursFactory plafonne `niveau` selon `type_parcours`
        # (Licence -> 3) : on reste dans L1/L2 pour obtenir deux classes
        # distinctes, sans chercher à forcer un niveau arbitraire.
        # classe_l2 est sur l'année académique qui suit directement celle de
        # classe_l1 : depuis CORRECTIONS_A_FAIRE.md point 15, un passage vers
        # un niveau supérieur du même cycle n'est accepté par
        # Etudiant.reinscrire() que si l'année suit directement la
        # précédente (pas de saut d'année).
        self.classe_l1 = ClasseFactory(
            parcours=ParcoursFactory(type_parcours="Licence", niveau=1)
        )
        annee_suivante = AnneeAcademiqueFactory(
            libelle="2026-2027",
            date_debut=date(2026, 9, 1),
            date_fin=date(2027, 6, 30),
        )
        self.classe_l2 = ClasseFactory(
            parcours=ParcoursFactory(type_parcours="Licence", niveau=2),
            semestre=Semestre1Factory(
                annee=annee_suivante,
                date_debut=date(2026, 9, 1),
                date_fin=date(2027, 1, 31),
            ),
        )
        self.etudiant = EtudiantFactory(classe=self.classe_l1)

    # ──────────────────────────────────────────────────────────────────────────
    # IDEMPOTENCE DU get_or_create
    # ──────────────────────────────────────────────────────────────────────────

    def test_reinscrire_sur_la_meme_classe_est_idempotent(self):
        """
        get_or_create() n'applique ses `defaults` qu'à la création : réinscrire
        un étudiant sur la classe où il est déjà inscrit renvoie la ligne
        existante telle quelle. Ni le type, ni la date, ni la référence externe
        ne sont réécrits — la seconde tentative est sans effet, elle ne crée pas
        un doublon et ne requalifie pas l'inscription en réinscription.
        """
        premiere = self.etudiant.reinscrire(self.classe_l1)

        rejouee = self.etudiant.reinscrire(
            self.classe_l1,
            date_inscription=date(2020, 1, 1),
            reference_externe="SCOL-999",
        )

        self.assertEqual(rejouee.pk, premiere.pk)
        self.assertEqual(self.etudiant.inscriptions.count(), 1)
        self.assertEqual(rejouee.type_inscription, Inscription.TYPE_INSCRIPTION)
        self.assertEqual(rejouee.statut, "active")
        # Les `defaults` du second appel sont ignorés : la ligne garde les
        # valeurs posées lors de la première inscription.
        self.assertEqual(rejouee.date_inscription, date.today())
        self.assertEqual(rejouee.reference_externe, "")

    def test_date_du_jour_par_defaut_et_reference_externe_transmise(self):
        """
        `date_inscription` vaut le jour courant quand elle n'est pas fournie, et
        `reference_externe` — le point de raccrochage vers l'application de
        scolarité — est bien porté par la ligne créée.
        """
        sans_date = self.etudiant.reinscrire(self.classe_l1)
        self.assertEqual(sans_date.date_inscription, date.today())

        avec_reference = self.etudiant.reinscrire(
            self.classe_l2,
            date_inscription=date(2025, 10, 3),
            reference_externe="SCOL-2025-4821",
        )
        self.assertEqual(avec_reference.date_inscription, date(2025, 10, 3))
        self.assertEqual(avec_reference.reference_externe, "SCOL-2025-4821")

    # ──────────────────────────────────────────────────────────────────────────
    # PORTÉE DE LA CLÔTURE
    # ──────────────────────────────────────────────────────────────────────────

    def test_seules_les_inscriptions_actives_sont_cloturees(self):
        """
        La clôture filtre sur statut='active' : une inscription abandonnée garde
        son statut, qui porte une information métier distincte de « terminée ».
        """
        abandonnee = self.etudiant.reinscrire(self.classe_l1)
        Inscription.objects.filter(pk=abandonnee.pk).update(statut="abandonnée")

        self.etudiant.reinscrire(self.classe_l2)

        abandonnee.refresh_from_db()
        self.assertEqual(abandonnee.statut, "abandonnée")

    def test_reinscrire_ne_touche_pas_aux_inscriptions_des_autres_etudiants(self):
        """
        La clôture passe par self.inscriptions : un camarade inscrit dans la
        même classe n'est pas emporté au passage.
        """
        camarade = EtudiantFactory(classe=self.classe_l1)
        inscription_camarade = camarade.reinscrire(self.classe_l1)

        self.etudiant.reinscrire(self.classe_l1)
        self.etudiant.reinscrire(self.classe_l2)

        inscription_camarade.refresh_from_db()
        camarade.refresh_from_db()
        self.assertEqual(inscription_camarade.statut, "active")
        self.assertEqual(camarade.classe_id, self.classe_l1.pk)

    # ──────────────────────────────────────────────────────────────────────────
    # ATOMICITÉ
    # ──────────────────────────────────────────────────────────────────────────

    def test_echec_sur_annee_archivee_ne_laisse_pas_letudiant_sans_inscription(self):
        """
        reinscrire() clôture l'inscription courante *avant* de créer la nouvelle.
        Si la création échoue — ici parce que Inscription.clean() refuse une
        inscription active sur une année archivée — le transaction.atomic() doit
        ramener l'étudiant à son état d'origine, sinon il se retrouverait sans
        aucune inscription active et sans nouvelle classe.
        """
        # Niveau et année choisis pour que seul le statut « archivée » fasse
        # échouer l'appel : niveau immédiatement supérieur à classe_l1 (1 -> 2)
        # et année qui la suit directement (2025-2026 -> 2026-2027), sinon
        # c'est _valider_progression() qui refuserait en premier, pour une
        # tout autre raison que celle visée par ce test. Création directe
        # (pas via AnneeAcademiqueFactory) : le libellé "2026-2027" existe
        # déjà, actif, pour classe_l2 (créé dans setUp) — la fabrique, qui
        # fait un get_or_create sur le libellé, renverrait cette même ligne
        # active au lieu d'une ligne archivée distincte.
        annee_archivee = AnneeAcademique.objects.create(
            libelle="2026-2027",
            date_debut=date(2026, 9, 1),
            date_fin=date(2027, 6, 30),
            statut="archivée",
        )
        classe_archivee = ClasseFactory(
            parcours=ParcoursFactory(type_parcours="Licence", niveau=2),
            filiere=FiliereFactory(libelle="Filiere Archivee"),
            semestre=Semestre1Factory(
                annee=annee_archivee,
                date_debut=date(2026, 9, 1),
                date_fin=date(2027, 1, 31),
            ),
            annee=annee_archivee,
        )

        active = self.etudiant.reinscrire(self.classe_l1)

        with self.assertRaises(ValidationError):
            self.etudiant.reinscrire(classe_archivee)

        active.refresh_from_db()
        self.etudiant.refresh_from_db()
        self.assertEqual(active.statut, "active")
        self.assertEqual(self.etudiant.classe_id, self.classe_l1.pk)
        self.assertEqual(self.etudiant.inscriptions.count(), 1)

    # ──────────────────────────────────────────────────────────────────────────
    # RETOUR EN ARRIÈRE
    # ──────────────────────────────────────────────────────────────────────────

    def test_retour_sur_une_classe_deja_quittee_reactive_linscription(self):
        """
        Correction d'une erreur de saisie : on ramène l'étudiant sur une classe
        qu'il a déjà quittée. get_or_create() retrouve la ligne historique
        (statut='terminée') ; reinscrire() la rouvre désormais explicitement
        au lieu de la laisser telle quelle — CORRECTIONS_A_FAIRE.md, point 4,
        corrigé : l'étudiant ne doit jamais se retrouver rattaché à une classe
        pour laquelle il n'a aucune inscription active.
        """
        inscription_l1 = self.etudiant.reinscrire(self.classe_l1)
        self.etudiant.reinscrire(self.classe_l2)

        # Un retour en arrière n'est pas une « progression » au sens de
        # _valider_progression() : il reste volontairement hors de son
        # périmètre (niveau <= niveau actuel), pour ne pas bloquer ce
        # scénario de correction manuelle — CORRECTIONS_A_FAIRE.md, point 15.
        retour = self.etudiant.reinscrire(self.classe_l1)

        self.assertEqual(retour.pk, inscription_l1.pk)  # même ligne, pas un doublon
        self.assertEqual(retour.statut, "active")
        self.assertEqual(retour.type_inscription, Inscription.TYPE_REINSCRIPTION)
        self.etudiant.refresh_from_db()
        self.assertEqual(self.etudiant.classe_id, self.classe_l1.pk)
        self.assertEqual(self.etudiant.inscriptions.filter(statut="active").count(), 1)

    # ──────────────────────────────────────────────────────────────────────────
    # PROGRESSION DE NIVEAU (CORRECTIONS_A_FAIRE.md, point 15)
    # ──────────────────────────────────────────────────────────────────────────

    def test_premiere_inscription_libre_de_toute_contrainte_de_progression(self):
        """
        Un étudiant sans historique (première inscription) peut arriver sur
        n'importe quelle classe : la règle de continuité ne s'applique
        qu'aux réinscriptions (un étudiant qui a déjà un historique).
        """
        nouvel_etudiant = EtudiantFactory(classe=self.classe_l1)

        inscription = nouvel_etudiant.reinscrire(self.classe_l2)

        self.assertEqual(inscription.classe_id, self.classe_l2.pk)

    def test_passage_de_niveau_normal_accepte(self):
        """
        Cas nominal : année qui suit directement, niveau immédiatement
        supérieur, même cycle. Doit toujours passer.
        """
        self.etudiant.reinscrire(self.classe_l1)

        inscription = self.etudiant.reinscrire(self.classe_l2)

        self.assertEqual(inscription.classe_id, self.classe_l2.pk)

    def test_saut_de_niveau_refuse(self):
        """
        Depuis L1, sauter directement en L3 (même cycle) est refusé : seul
        le niveau immédiatement supérieur est accessible.
        """
        classe_l3 = ClasseFactory(
            parcours=ParcoursFactory(type_parcours="Licence", niveau=3),
            semestre=Semestre1Factory(
                annee=AnneeAcademiqueFactory(
                    libelle="2026-2027",
                    date_debut=date(2026, 9, 1), date_fin=date(2027, 6, 30),
                ),
                date_debut=date(2026, 9, 1), date_fin=date(2027, 1, 31),
            ),
        )
        self.etudiant.reinscrire(self.classe_l1)

        with self.assertRaises(ValidationError):
            self.etudiant.reinscrire(classe_l3)

    def test_saut_d_annee_refuse(self):
        """
        Depuis L1 (2025-2026), passer en L2 mais sur une année qui n'est pas
        directement la suivante est refusé, même si le niveau, lui, est
        correct.
        """
        classe_l2_annee_lointaine = ClasseFactory(
            parcours=ParcoursFactory(type_parcours="Licence", niveau=2),
            semestre=Semestre1Factory(
                annee=AnneeAcademiqueFactory(
                    libelle="2028-2029",
                    date_debut=date(2028, 9, 1), date_fin=date(2029, 6, 30),
                ),
                date_debut=date(2028, 9, 1), date_fin=date(2029, 1, 31),
            ),
        )
        self.etudiant.reinscrire(self.classe_l1)

        with self.assertRaises(ValidationError):
            self.etudiant.reinscrire(classe_l2_annee_lointaine)

    def test_changement_de_cycle_non_couvert_par_la_regle(self):
        """
        Le passage d'un cycle à l'autre (ex. Licence -> Master) n'est pas une
        « progression de niveau » au sens de cette règle : _valider_progression()
        ne s'en mêle pas (ni validation, ni refus) — traité comme hors
        périmètre, à couvrir plus tard par un autre mécanisme (nouvelle
        admission) si besoin.
        """
        classe_m1 = ClasseFactory(
            parcours=ParcoursFactory(type_parcours="Master", niveau=1),
            semestre=Semestre1Factory(
                annee=AnneeAcademiqueFactory(
                    libelle="2030-2031",
                    date_debut=date(2030, 9, 1), date_fin=date(2031, 6, 30),
                ),
                date_debut=date(2030, 9, 1), date_fin=date(2031, 1, 31),
            ),
        )
        self.etudiant.reinscrire(self.classe_l1)

        inscription = self.etudiant.reinscrire(classe_m1)

        self.assertEqual(inscription.classe_id, classe_m1.pk)
