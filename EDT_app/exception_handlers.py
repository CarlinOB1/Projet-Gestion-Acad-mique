# EDT_app/exception_handlers.py
#
# Handler d'exception DRF global : convertit toute django.core.exceptions.
# ValidationError non interceptée en réponse 400 DRF, au lieu de laisser
# DRF la traiter comme une erreur serveur non gérée (500).
#
# Pourquoi ce fichier existe : ValidateOnSaveMixin (EDT_app/serializers.py)
# fait déjà cette conversion, mais uniquement pour les serializers qui
# l'utilisent, et uniquement dans leurs méthodes create()/update(). Trois
# points d'entrée appellent model.full_clean()/save() en dehors de ce
# chemin et laissaient donc filtrer une ValidationError Django brute :
#   - SeanceReportSerializer.save()      (serializers.py)
#   - ProfilSuspensionSerializer.save()  (serializers.py)
#   - SeanceViewSet.publier()            (views.py)
# Voir CORRECTIONS_A_FAIRE.md, points 1 et 6, pour l'historique de ces deux
# bugs — corrigés ici à la source plutôt que site par site, pour fermer
# toute la catégorie (y compris un futur appel direct à full_clean() qu'on
# n'a pas encore repéré).
#
# Câblé via REST_FRAMEWORK['EXCEPTION_HANDLER'] dans Gestion_edt/settings.py.
# N'affecte que les requêtes passant par DRF (pas l'admin Django, ni les
# commandes de gestion, qui ont leurs propres mécanismes de restitution
# d'erreur).

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import ProtectedError, RestrictedError
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc, context):
    # Suppression d'un élément encore utilisé (département qui a des
    # enseignants, classe qui a des étudiants...) : refus expliqué au lieu
    # d'une erreur 500 (CORRECTIONS_A_FAIRE.md point 28). Rien n'a été
    # effacé : Django vérifie les protections avant toute suppression.
    if isinstance(exc, (ProtectedError, RestrictedError)):
        objets = exc.protected_objects if isinstance(exc, ProtectedError) else exc.restricted_objects
        exemples = sorted({str(o._meta.verbose_name_plural) for o in list(objets)[:50]})
        return Response(
            {
                'detail': (
                    "Suppression impossible : cet élément est encore utilisé ("
                    + ", ".join(exemples)
                    + "). Supprimez ou déplacez d'abord ces éléments."
                ),
            },
            status=status.HTTP_409_CONFLICT,
        )
    if isinstance(exc, DjangoValidationError):
        detail = exc.message_dict if hasattr(exc, 'message_dict') else {
            'non_field_errors': exc.messages
        }
        exc = DRFValidationError(detail)
    return drf_exception_handler(exc, context)
