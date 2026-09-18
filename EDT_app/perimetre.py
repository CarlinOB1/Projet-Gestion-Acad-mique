"""
EDT_app/perimetre.py

Calcul centralisé du périmètre de classes/modules qu'une personne a le droit
de consulter ou de gérer, selon son rôle :

  - superuser / groupe "responsable" : illimité (None = pas de filtre).
  - chef de département             : classes/modules de son ou ses départements dirigés.
  - référent de classe(s)           : ses classes assignées (ReferentClasse),
                                       et les modules utilisés dedans.
  - enseignant simple                : son propre département uniquement.

Une personne peut cumuler chef de département ET référent (ex : un chef qui
coordonne aussi une classe de première année) : les deux périmètres
s'additionnent, ils ne s'excluent jamais.

Ces deux fonctions reprennent la logique déjà écrite et testée dans
SeanceViewSet._get_classes_autorisees (views.py) et dans le correctif union de
ClasseViewSet/EtudiantViewSet — elles ne créent aucune nouvelle règle métier,
elles lui donnent un seul endroit où vivre, pour que les prochains écrans qui
en ont besoin (Document, Module, Affectation...) n'aient pas à la
réécrire une nouvelle fois à leur façon.
"""
from django.db.models import Q

from EDT_app.models import Classe, Module


def _enseignant_courant(user):
    """Retourne l'Enseignant lié à l'utilisateur connecté, ou None."""
    if not hasattr(user, 'profil') or not hasattr(user.profil, 'enseignant'):
        return None
    return user.profil.enseignant


def classes_autorisees(user):
    """
    Retourne le queryset des Classe sur lesquelles l'utilisateur a autorité,
    ou None si son accès est illimité (superuser / responsable).
    """
    if user.is_superuser or user.groups.filter(name='responsable').exists():
        return None

    enseignant = _enseignant_courant(user)
    if enseignant is None:
        return Classe.objects.none()

    departements_diriges = enseignant.departements_diriges.all()
    est_referent = hasattr(enseignant, 'referent_classes')

    if not departements_diriges.exists() and not est_referent:
        # Enseignant simple : son propre département uniquement.
        return Classe.objects.filter(filiere__departement=enseignant.departement)

    perimetre = Q()
    if departements_diriges.exists():
        perimetre |= Q(filiere__departement__in=departements_diriges)
    if est_referent:
        perimetre |= Q(id__in=enseignant.referent_classes.classes.values_list('id', flat=True))
    return Classe.objects.filter(perimetre)


def modules_autorises(user):
    """
    Retourne le queryset des Module sur lesquels l'utilisateur a autorité,
    ou None si son accès est illimité (superuser / responsable).
    """
    if user.is_superuser or user.groups.filter(name='responsable').exists():
        return None

    enseignant = _enseignant_courant(user)
    if enseignant is None:
        return Module.objects.none()

    departements_diriges = enseignant.departements_diriges.all()
    est_referent = hasattr(enseignant, 'referent_classes')

    if not departements_diriges.exists() and not est_referent:
        # Enseignant simple : modules des matières de son propre département.
        return Module.objects.filter(matiere__departement=enseignant.departement)

    perimetre = Q()
    if departements_diriges.exists():
        perimetre |= Q(matiere__departement__in=departements_diriges)
        # Symétrique de la branche référent ci-dessous : un chef peut créer
        # une AffectationModule hors_departement=True sur une classe qu'il
        # dirige (AffectationModuleSerializer.validate() l'autorise), il doit
        # donc pouvoir la relire/modifier/supprimer ensuite — sans quoi
        # l'objet devient introuvable juste après sa création
        # (CORRECTIONS_A_FAIRE.md, point 2).
        classes_dirigees = Classe.objects.filter(filiere__departement__in=departements_diriges)
        perimetre |= Q(classe__in=classes_dirigees) | Q(seance__classe__in=classes_dirigees)
    if est_referent:
        classes_ref = enseignant.referent_classes.classes.all()
        # Un module peut être rattaché directement à une classe (classe_id),
        # ou seulement utilisé dedans via une séance planifiée — les deux
        # comptent comme "module de mes classes en référence".
        perimetre |= Q(classe__in=classes_ref) | Q(seance__classe__in=classes_ref)
    return Module.objects.filter(perimetre).distinct()
