# authentication.py
#
# Ce fichier personalise le comportement JWT de simplejwt :
#   1. Bloque les profils suspendus dès la demande de token
#   2. Enrichit le token avec le rôle et les infos du profil
#   3. Expose une vue de login qui retourne aussi les infos utilisateur
#
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework import serializers

from EDT_app.throttles import LoginCompteRateThrottle, LoginIPRateThrottle


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Étend le serializer JWT par défaut pour :
      - Vérifier que l'utilisateur a un profil actif avant de délivrer un token
      - Injecter le rôle, le nom et le statut dans le payload du token

    Payload JWT enrichi :
      {
        "user_id"    : int,
        "username"   : str,
        "role"       : "responsable" | "chef_departement" | "enseignant" | "etudiant" | "admin",
        "nom_complet": str,
        "statut"     : "actif" | "suspendu"
      }
    """

    def validate(self, attrs):
        # 1. Validation standard (username + password)
        data = super().validate(attrs)
        user = self.user

        # 2. Vérifie l'existence et le statut du profil
        if not user.is_superuser:
            if not hasattr(user, 'profil'):
                raise serializers.ValidationError(
                    "Aucun profil associé à ce compte. "
                    "Contactez l'administrateur."
                )
            if user.profil.statut == 'suspendu':
                raise serializers.ValidationError(
                    f"Votre profil est suspendu. "
                    f"Motif : {user.profil.motif_suspension or 'Non précisé'}. "
                    f"Contactez le responsable pédagogique."
                )

        # 3. Détermine le rôle
        role = self._get_role(user)

        # 4. Ajoute les infos utilisateur dans la réponse (pas dans le token)
        photo_url = None
        if hasattr(user, 'profil') and user.profil.photo:
            request = self.context.get('request')
            if request:
                photo_url = request.build_absolute_uri(user.profil.photo.url)
            else:
                photo_url = user.profil.photo.url

        data['user'] = {
            'id'            : user.pk,
            'username'      : user.username,
            'nom_complet'   : self._get_nom_complet(user),
            'role'          : role,
            'statut'        : user.profil.statut if hasattr(user, 'profil') else 'actif',
            'photo'         : photo_url,
            'departement_id': self._get_departement_id(user),
        }

        return data

    @classmethod
    def get_token(cls, user):
        """Injecte le rôle et le nom directement dans le payload du JWT."""
        token = super().get_token(user)
        token['role']        = cls._get_role(user)
        token['nom_complet'] = cls._get_nom_complet(user)
        token['username']    = user.username
        return token

    @staticmethod
    def _get_role(user):
        if user.is_superuser:
            return 'admin'
        if hasattr(user, 'profil'):
            if hasattr(user.profil, 'enseignant'):
                enseignant = user.profil.enseignant
                # Chef de département : dirige un département
                if enseignant.departements_diriges.exists():
                    return 'chef_departement'
                # Référent de classe : enseignant assigné à des classes L1
                if hasattr(enseignant, 'referent_classes'):
                    return 'referent_l1'
                return 'enseignant'
            if hasattr(user.profil, 'etudiant'):
                return 'etudiant'
        return 'inconnu'

    @staticmethod
    def _get_departement_id(user):
        """Retourne l'id du département dirigé par l'utilisateur, ou None."""
        if hasattr(user, 'profil') and hasattr(user.profil, 'enseignant'):
            dept = user.profil.enseignant.departements_diriges.first()
            return dept.pk if dept else None
        return None

    @staticmethod
    def _get_nom_complet(user):
        nom = f"{user.last_name} {user.first_name}".strip()
        return nom if nom else user.username


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Vue de login personnalisée.
    Utilise CustomTokenObtainPairSerializer pour enrichir la réponse.

    POST /api/token/
    Corps : { "username": "...", "password": "..." }

    Réponse :
    {
      "access" : "<jwt>",
      "refresh": "<jwt>",
      "user"   : {
        "id"         : 1,
        "username"   : "mbemba",
        "nom_complet": "Mbemba Jean",
        "role"       : "enseignant",
        "statut"     : "actif"
      }
    }
    """
    serializer_class = CustomTokenObtainPairSerializer
    # Remplace les limites globales : voir EDT_app/throttles.py.
    throttle_classes = [LoginCompteRateThrottle, LoginIPRateThrottle]


class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    """
    Renouvellement de session refusé à un profil suspendu ou absent, comme
    la connexion. Sans ce contrôle, un compte suspendu pendant sa session
    la prolongeait indéfiniment (CORRECTIONS_A_FAIRE.md point 17).
    """

    def validate(self, attrs):
        refresh = self.token_class(attrs['refresh'])
        user_id = refresh.payload.get(api_settings.USER_ID_CLAIM)
        user = get_user_model().objects.filter(
            **{api_settings.USER_ID_FIELD: user_id}
        ).first()
        if user is not None and not user.is_superuser:
            if not hasattr(user, 'profil') or user.profil.statut != 'actif':
                raise AuthenticationFailed(
                    "Votre profil est suspendu. Contactez le responsable pédagogique.",
                    'profil_suspendu',
                )
        return super().validate(attrs)


class CustomTokenRefreshView(TokenRefreshView):
    """POST /api/token/refresh/ — refuse les profils suspendus."""
    serializer_class = CustomTokenRefreshSerializer