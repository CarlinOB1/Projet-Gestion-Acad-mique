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
import hashlib

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
