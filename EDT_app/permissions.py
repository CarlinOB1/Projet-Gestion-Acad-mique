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


class IsResponsable(BasePermission):
    """
    Autorise uniquement les membres du groupe 'responsable'.
    Utilisé pour les opérations de création, modification, suppression.
    """
    message = "Accès réservé au responsable pédagogique."

    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        return request.user.groups.filter(name='responsable').exists()


class IsResponsableOrReadOnly(BasePermission):
    """
    Lecture libre pour tout utilisateur authentifié et actif.
    Écriture réservée au responsable (ou superuser).
    """
    message = "Modification réservée au responsable pédagogique."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if request.user.is_superuser:
            return True
        return request.user.groups.filter(name='responsable').exists()


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


class IsOwnerOrResponsable(BasePermission):
    """
    Autorise l'accès si l'objet appartient à l'utilisateur connecté,
    ou si l'utilisateur est responsable/superuser.
    Utilisé au niveau objet (has_object_permission).
    """
    message = "Vous n'avez pas accès à cette ressource."

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        if request.user.groups.filter(name='responsable').exists():
            return True
        # Vérifie si l'objet appartient à l'utilisateur courant
        if hasattr(obj, 'profil'):
            return obj.profil.user == request.user
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return False