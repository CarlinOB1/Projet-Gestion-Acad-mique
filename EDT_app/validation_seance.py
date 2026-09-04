# validation_seance.py
"""
Source unique de vérité pour les règles métier de validation des séances.

Toutes les fonctions de ce module :
  - Sont des fonctions **pures** (pas d'état, pas de `self`).
  - Lèvent `django.core.exceptions.ValidationError`.
  - Peuvent être appelées depuis n'importe quel contexte :
      Seance.clean() (modèle), SeanceSerializer.validate() (API REST),
      tests unitaires, shell Django, etc.

Le sérialiseur est responsable de convertir ces ValidationError Django
en erreurs DRF 400 avec le bon champ JSON (via _to_drf_error()).
"""
from datetime import datetime, date as date_type
from datetime import time as time_type

from django.core.exceptions import ValidationError


# ── Constantes extraites de Seance ──────────────────────────────────────────
# Ces valeurs sont des copies intentionnelles de Seance.{constante}. Si elles
# changent dans le modèle, elles doivent être mises à jour ici aussi — mais
# ce module est leur unique point de définition pour la logique de validation.

MIN_HEURE_DEBUT = time_type(9, 0)
HEURE_FIN_MAX   = time_type(16, 20)
MAX_HEURES_JOUR = 6
PAUSE_DEBUT     = time_type(11, 0)
PAUSE_FIN       = time_type(11, 15)


# ── Utilitaire interne ───────────────────────────────────────────────────────

def _calculer_duree_effective(heure_debut, heure_fin):
    """
    Calcule la durée effective en heures en soustrayant la pause méridienne
    (11h00–11h15) si la séance la chevauche.
    Identique à Seance.calculer_duree_effective() — synchronisez-les ensemble.
    """
    debut = datetime.combine(date_type.today(), heure_debut)
    fin   = datetime.combine(date_type.today(), heure_fin)
    duree_totale = fin - debut

    pause_debut = datetime.combine(date_type.today(), PAUSE_DEBUT)
    pause_fin   = datetime.combine(date_type.today(), PAUSE_FIN)

    if debut < pause_fin and fin > pause_debut:
        overlap_start = max(debut, pause_debut)
        overlap_end   = min(fin, pause_fin)
        duree_effective = duree_totale - (overlap_end - overlap_start)
    else:
        duree_effective = duree_totale

    return duree_effective.total_seconds() / 3600


# ── Règles atomiques ─────────────────────────────────────────────────────────

def valider_horaires(heure_debut, heure_fin):
    """
    Vérifie :
      - heure_debut et heure_fin sont présentes.
      - heure_debut >= MIN_HEURE_DEBUT (09h00).
      - heure_fin   <= HEURE_FIN_MAX  (16h20).
      - heure_debut < heure_fin.
    """
    if not heure_debut or not heure_fin:
        raise ValidationError("Horaires obligatoires.")

    if heure_debut < MIN_HEURE_DEBUT:
        raise ValidationError(
            f"Les séances ne peuvent pas commencer avant "
            f"{MIN_HEURE_DEBUT.strftime('%Hh%M')}."
        )

    if heure_fin > HEURE_FIN_MAX:
        raise ValidationError(
            f"L'heure de fin max est {HEURE_FIN_MAX.strftime('%Hh%M')}."
        )

    if heure_debut >= heure_fin:
        raise ValidationError("L'heure de début doit être avant la fin.")


def valider_dimanche(date_seance):
    """Interdit les séances le dimanche (weekday == 6)."""
    if date_seance and date_seance.weekday() == 6:
        raise ValidationError("Impossible de planifier une séance un dimanche.")


def valider_departement(enseignant, module):
    """
    L'enseignant doit appartenir au même département que la matière du module.
    """
    if enseignant.departement != module.matiere.departement:
        raise ValidationError(
            f"L'enseignant ({enseignant.departement}) n'est pas du même "
            f"département que la matière ({module.matiere.departement})."
        )


def valider_annee_non_archivee(annee):
    """Interdit de créer/modifier une séance sur une année académique archivée."""
    if annee and annee.statut == 'archivée':
        raise ValidationError(
            "Impossible de créer une séance sur une année archivée."
        )


def valider_coherence_annee_classe(annee, classe):
    """
    L'année académique de la séance doit correspondre à celle de sa classe.
    `Seance.annee` et `Seance.classe.annee` sont deux FK indépendantes vers
    AnneeAcademique : cette règle empêche leur désynchronisation.
    """
    if annee and classe and classe.annee_id and annee.pk != classe.annee_id:
        raise ValidationError(
            f"L'année de la séance ({annee}) ne correspond pas à "
            f"l'année académique de la classe ({classe.annee})."
        )


def valider_bornes_semestre(date_seance, classe):
    """
    La date de la séance doit être dans les bornes du semestre de la classe.
    """
    sem = classe.semestre
    if not (sem.date_debut <= date_seance <= sem.date_fin):
        raise ValidationError(
            f"La date de séance est hors des limites du semestre "
            f"({sem.date_debut} → {sem.date_fin})."
        )


def valider_coherence_module_semestre(module, classe):
    """Le module doit appartenir au même semestre que la classe."""
    if module.semestre != classe.semestre:
        raise ValidationError(
            f"Le module appartient au semestre '{module.semestre}' "
            f"mais la classe est en '{classe.semestre}'."
        )


def valider_conflit_enseignant(enseignant, date_seance, heure_debut, heure_fin,
                                pk, seance_liee_pk=None):
    """
    Détecte un conflit horaire pour l'enseignant sur le créneau demandé.
    La séance liée (cours mutualisé, seance_liee_pk) est exclue du conflit.
    """
    from EDT_app.models import Seance  # import local pour éviter la circularité

    if not (enseignant and date_seance and heure_debut and heure_fin):
        return

    qs = Seance.objects.filter(
        enseignant=enseignant,
        date_seance=date_seance,
        heure_debut__lt=heure_fin,
        heure_fin__gt=heure_debut,
        statut__in=['Confirmée', 'Reportée'],
    ).exclude(pk=pk)

    if seance_liee_pk:
        qs = qs.exclude(pk=seance_liee_pk)

    if qs.exists():
        raise ValidationError(
            f"L'enseignant a déjà une séance le {date_seance} sur ce créneau."
        )


def valider_conflit_classe(classe, date_seance, heure_debut, heure_fin, pk):
    """Détecte un conflit horaire pour la classe sur le créneau demandé."""
    from EDT_app.models import Seance

    if not (classe and date_seance and heure_debut and heure_fin):
        return

    if Seance.objects.filter(
        classe=classe,
        date_seance=date_seance,
        heure_debut__lt=heure_fin,
        heure_fin__gt=heure_debut,
        statut__in=['Confirmée', 'Reportée'],
    ).exclude(pk=pk).exists():
        raise ValidationError(
            f"La classe a déjà une séance le {date_seance} sur ce créneau."
        )


def valider_volume_module(module, duree, pk):
    """
    Le volume horaire du module ne doit pas être dépassé.
    `duree` est la durée effective de la séance à valider (en heures).
    """
    heures_restantes = module.heures_restantes(exclure_seance_pk=pk)
    if duree > heures_restantes:
        raise ValidationError(
            f"Cette séance ({duree}h) dépasse le volume horaire restant du module "
            f"'{module.libelle}' "
            f"({heures_restantes}h restantes sur {module.heures_max()}h max)."
        )


def valider_affectation(module, enseignant, type_seance, duree, pk):
    """
    Vérifie que l'enseignant est bien affecté sur ce module (règle de
    résolution de l'affectation) et que son volume horaire restant
    est suffisant.

    Algorithme (identique à Seance._resoudre_affectation) :
      1. Cherche une affectation typée (même type_seance).
      2. Sinon, cherche une affectation générique (type_seance=None).
      3. Si aucune et que le module a d'autres affectations → erreur.
      4. Si affectation trouvée → vérifie le volume restant.
    """
    from EDT_app.models import AffectationModule

    if not (module and enseignant and type_seance):
        return

    affectations = AffectationModule.objects.filter(
        module=module,
        enseignant=enseignant,
    )

    affectation = (
        affectations.filter(type_seance=type_seance).first()
        or affectations.filter(type_seance__isnull=True).first()
    )

    if not affectation:
        module_has_affectations = AffectationModule.objects.filter(
            module=module
        ).exists()
        if module_has_affectations:
            raise ValidationError(
                "Cet enseignant n'est pas affecté sur ce module (ni pour ce "
                "type de séance, ni de manière générique)."
            )
        return  # module sans affectations déclarées → dégradation gracieuse

    heures_restantes = affectation.heures_restantes(exclure_seance_pk=pk)
    if duree > heures_restantes:
        type_label = affectation.type_seance or 'Générique'
        raise ValidationError(
            f"Cette séance ({duree}h) dépasse le volume horaire restant sur "
            f"l'affectation de cet enseignant "
            f"({type_label} : {heures_restantes}h restantes sur "
            f"{affectation.heures_prevues}h max)."
        )


def valider_volume_journalier(classe, date_seance, heure_debut, heure_fin, pk):
    """
    La somme des durées effectives des séances de la classe dans la journée
    (séances 'Confirmée', hors la séance en cours) ne doit pas dépasser
    MAX_HEURES_JOUR.
    """
    from EDT_app.models import Seance

    if not (classe and date_seance and heure_debut and heure_fin):
        return

    seances_jour = Seance.objects.filter(
        classe=classe,
        date_seance=date_seance,
        statut__in=['Confirmée', 'Reportée'],
    ).exclude(pk=pk)

    total_jour = sum(
        _calculer_duree_effective(s.heure_debut, s.heure_fin)
        for s in seances_jour
    ) + _calculer_duree_effective(heure_debut, heure_fin)

    if total_jour > MAX_HEURES_JOUR:
        raise ValidationError(
            f"Le volume journalier de la classe dépasse {MAX_HEURES_JOUR}h "
            f"(total calculé : {total_jour:.2f}h)."
        )


# ── Règles de report ─────────────────────────────────────────────────────────

def valider_creneau_report(enseignant, classe, annee, date_report,
                            heure_debut_report, heure_fin_report, pk):
    """
    Valide le créneau de report d'une séance :
      - Données complètes.
      - Pas un dimanche.
      - heure_debut_report >= MIN_HEURE_DEBUT.
      - heure_fin_report   <= HEURE_FIN_MAX.
      - Dans les bornes du semestre.
      - Dans les bornes de l'année académique.
      - Pas de conflit enseignant sur le créneau de report.
      - Pas de conflit classe sur le créneau de report.
    """
    from EDT_app.models import Seance

    if not date_report or not heure_debut_report or not heure_fin_report:
        raise ValidationError("Les données de report sont incomplètes.")

    if date_report.weekday() == 6:
        raise ValidationError(
            "Impossible de reporter une séance un dimanche."
        )

    if heure_debut_report < MIN_HEURE_DEBUT:
        raise ValidationError(
            f"Le report ne peut pas commencer avant "
            f"{MIN_HEURE_DEBUT.strftime('%Hh%M')}."
        )

    if heure_fin_report > HEURE_FIN_MAX:
        raise ValidationError(
            f"Le report ne peut pas finir après "
            f"{HEURE_FIN_MAX.strftime('%Hh%M')}."
        )

    if classe:
        sem = classe.semestre
        if not (sem.date_debut <= date_report <= sem.date_fin):
            raise ValidationError(
                "La date de report est hors des limites du semestre."
            )

    if annee:
        if not (annee.date_debut <= date_report <= annee.date_fin):
            raise ValidationError(
                "La date de report est hors de l'année académique."
            )

    if enseignant and heure_debut_report and heure_fin_report:
        if Seance.objects.filter(
            enseignant=enseignant,
            date_seance=date_report,
            heure_debut__lt=heure_fin_report,
            heure_fin__gt=heure_debut_report,
            statut__in=['Confirmée', 'Reportée'],
        ).exclude(pk=pk).exists():
            raise ValidationError(
                "Conflit d'horaire pour l'enseignant sur le créneau de report."
            )

    if classe and heure_debut_report and heure_fin_report:
        if Seance.objects.filter(
            classe=classe,
            date_seance=date_report,
            heure_debut__lt=heure_fin_report,
            heure_fin__gt=heure_debut_report,
            statut__in=['Confirmée', 'Reportée'],
        ).exclude(pk=pk).exists():
            raise ValidationError(
                "La classe a déjà une séance sur le créneau de report."
            )
