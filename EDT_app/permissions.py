# permissions.py
from rest_framework.permissions import BasePermission, SAFE_METHODS


class ProfilActifPermission(BasePermission):
    """
    Bloque toute requête d'un utilisateur dont le profil est suspendu.
    S'applique en plus de IsAuthenticated sur tous les ViewSets.
    Les superusers (admin Django) ne sont pas concernés.
    """
    message = "Votre profil est suspendu. Contactez le responsable pédagogique."

    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        if not hasattr(request.user, 'profil'):
            return True  # Pas encore de profil — laissé passer, géré ailleurs
        return request.user.profil.statut == 'actif'


class IsChefDepartementOrReadOnly(BasePermission):
    """
    Lecture libre pour tout utilisateur authentifié et actif.
    Écriture réservée au chef de département (ou superuser).
    """
    message = "Modification réservée au chef de département."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if request.user.is_superuser:
            return True
        return (
            hasattr(request.user, 'profil')
            and hasattr(request.user.profil, 'enseignant')
            and request.user.profil.enseignant.departements_diriges.exists()
        )


class IsEnseignant(BasePermission):
    """
    Vérifie que l'utilisateur authentifié est bien un enseignant.
    Utilisé pour les actions propres à l'enseignant (mon_planning, etc.).
    """
    message = "Accès réservé aux enseignants."

    def has_permission(self, request, view):
        return (
            hasattr(request.user, 'profil')
            and hasattr(request.user.profil, 'enseignant')
        )


class IsEtudiant(BasePermission):
    """
    Vérifie que l'utilisateur authentifié est bien un étudiant.
    Utilisé pour les actions propres à l'étudiant (mon_planning, etc.).
    """
    message = "Accès réservé aux étudiants."

    def has_permission(self, request, view):
        return (
            hasattr(request.user, 'profil')
            and hasattr(request.user.profil, 'etudiant')
        )


class IsChefDepartement(BasePermission):
    """
    Vérifie que l'utilisateur est chef d'au moins un département.
    Il a des droits d'écriture globaux en tant qu'administrateur de l'application.
    """
    message = "Accès réservé aux chefs de département."

    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        return (
            hasattr(request.user, 'profil')
            and hasattr(request.user.profil, 'enseignant')
            and request.user.profil.enseignant.departements_diriges.exists()
        )


class IsReferentClasse(BasePermission):
    """
    Vérifie que l'utilisateur est référent d'au moins une classe.
    Cas d'usage principal : coordinateur L1 (MIP, BCG, PCG).
    Il peut créer/modifier des séances uniquement pour ses classes assignées.
    """
    message = "Accès réservé aux référents de classes."

    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        return (
            hasattr(request.user, 'profil')
            and hasattr(request.user.profil, 'enseignant')
            and hasattr(request.user.profil.enseignant, 'referent_classes')
        )


class IsChefOrReferentOrReadOnly(BasePermission):
    """
    Lecture libre pour tout utilisateur authentifié.
    Écriture autorisée pour :
      - superuser
      - responsable (groupe Django)
      - chef de département (sur les séances de son département)
      - référent de classe (sur ses classes assignées)
    Cette permission est une porte d'entrée générale ; le filtrage
    fin par département/classe se fait dans les ViewSets.
    """
    message = "Modification réservée aux gestionnaires d'emplois du temps."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if request.user.is_superuser:
            return True
        if not hasattr(request.user, 'profil'):
            return False
        profil = request.user.profil
        if not hasattr(profil, 'enseignant'):
            return False
        enseignant = profil.enseignant
        return (
            enseignant.departements_diriges.exists()
            or hasattr(enseignant, 'referent_classes')
        )


class IsOwnerOrChefDepartement(BasePermission):
    """
    Autorise l'accès si l'objet appartient à l'utilisateur connecté,
    ou si l'utilisateur est chef de département/superuser.
    Utilisé au niveau objet (has_object_permission).
    """
    message = "Vous n'avez pas accès à cette ressource."

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        
        # Check if user is chef_departement
        if (hasattr(request.user, 'profil') and
            hasattr(request.user.profil, 'enseignant') and
            request.user.profil.enseignant.departements_diriges.exists()):
            return True

        # Vérifie si l'objet appartient à l'utilisateur courant
        if hasattr(obj, 'profil'):
            return obj.profil.user == request.user
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return False


class IsDocumentOwnerOrReadOnly(BasePermission):
    """
    Lecture libre pour tout utilisateur authentifié actif.
    Création : enseignants uniquement.
    Modification / Suppression : uniquement l'enseignant propriétaire du document.
    """
    message = "Seul l'enseignant propriétaire peut modifier ou supprimer ce document."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if request.user.is_superuser:
            return True
        # Création/modification : enseignants uniquement
        return (
            hasattr(request.user, 'profil')
            and hasattr(request.user.profil, 'enseignant')
        )

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if request.user.is_superuser:
            return True
        # Seul le propriétaire peut modifier/supprimer
        return (
            hasattr(request.user, 'profil')
            and hasattr(request.user.profil, 'enseignant')
            and obj.enseignant == request.user.profil.enseignant
        )