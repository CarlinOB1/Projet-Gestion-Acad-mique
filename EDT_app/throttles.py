# EDT_app/throttles.py
#
# Limitation du nombre de tentatives de connexion (POST /api/token/).
#
# Deux compteurs indépendants, tous deux consultés à chaque tentative :
#
#   - LoginCompteRateThrottle : par couple (adresse IP, identifiant saisi).
#     Freine quelqu'un qui essaie des mots de passe sur UN compte, sans gêner
#     les autres personnes qui partagent la même adresse (le réseau de
#     l'université sort souvent par une seule IP publique : une limite par IP
#     seule bloquerait toute une salle de TP).
#
#   - LoginIPRateThrottle : par adresse IP seule, plafond large. Freine
#     l'essai d'un même mot de passe sur beaucoup de comptes différents.
#
# Les débits sont définis dans REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']
# (Gestion_edt/settings.py), scopes 'login' et 'login_ip'.
#
# Les mêmes limites s'appliquent à la page de connexion de l'administration
# Django (limiter_connexion_admin, branchée dans EDT_app/admin.py), avec des
# compteurs séparés (CORRECTIONS_A_FAIRE.md point 25).
import hashlib
from functools import wraps

from django.http import HttpResponse
from rest_framework.throttling import SimpleRateThrottle


class LoginCompteRateThrottle(SimpleRateThrottle):
    scope = 'login'

    def get_cache_key(self, request, view):
        data = request.data
        identifiant = ''
        if hasattr(data, 'get'):
            identifiant = str(data.get('username', '')).strip().lower()
        # Condensé : borne la longueur de la clé de cache et évite qu'un
        # identifiant exotique n'y injecte des caractères problématiques.
        empreinte = hashlib.sha256(identifiant.encode('utf-8')).hexdigest()[:32]
        return self.cache_format % {
            'scope': self.scope,
            'ident': f'{self.get_ident(request)}:{empreinte}',
        }


class LoginIPRateThrottle(SimpleRateThrottle):
    scope = 'login_ip'

    def get_cache_key(self, request, view):
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request),
        }


# ── Administration Django (/admin/login/) ─────────────────────────────────────

class AdminCompteRateThrottle(LoginCompteRateThrottle):
    """Même règle que LoginCompteRateThrottle, sur le formulaire de /admin/."""

    def get_cache_key(self, request, view):
        identifiant = request.POST.get('username', '').strip().lower()
        empreinte = hashlib.sha256(identifiant.encode('utf-8')).hexdigest()[:32]
        return self.cache_format % {
            'scope': self.scope,
            'ident': f'admin:{self.get_ident(request)}:{empreinte}',
        }


class AdminIPRateThrottle(LoginIPRateThrottle):
    def get_cache_key(self, request, view):
        return self.cache_format % {
            'scope': self.scope,
            'ident': f'admin:{self.get_ident(request)}',
        }


def limiter_connexion_admin(vue_connexion):
    """
    Enveloppe la vue de connexion de l'administration : au-delà de la limite,
    chaque envoi du formulaire est refusé (429) sans même vérifier le mot de
    passe. L'affichage de la page reste libre.
    """
    @wraps(vue_connexion)
    def vue(request, *args, **kwargs):
        if request.method == 'POST':
            for limite in (AdminCompteRateThrottle(), AdminIPRateThrottle()):
                if not limite.allow_request(request, None):
                    return HttpResponse(
                        "Trop de tentatives de connexion. Réessayez dans une minute.",
                        status=429,
                        content_type='text/plain; charset=utf-8',
                    )
        return vue_connexion(request, *args, **kwargs)
    return vue
