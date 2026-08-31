# serializers.py
import re
from datetime import time
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError as DRFValidationError

from EDT_app.models import (
    Faculte, Departement, Filiere, Parcours,
    AnneeAcademique, Semestre, Classe,
    Profil, Enseignant, Etudiant,
    Matiere, Module, AffectationModule, Seance, ReferentClasse,
    DocumentPedagogique,
)


# ==========================================
# MIXIN UTILITAIRE
# ==========================================

class ValidateOnSaveMixin:
    """
    Intercepte les ValidationError Django levées par full_clean()
    dans save() et les convertit en erreurs DRF 400 lisibles.

    Tous les modèles appelant full_clean() dans save(), sans ce mixin
    une violation de règle métier remonterait en HTTP 500 au lieu d'un
    400 avec un message clair.
    """

    def _convert_django_error(self, exc):
        if hasattr(exc, 'message_dict'):
            raise DRFValidationError(exc.message_dict)
        raise DRFValidationError({'non_field_errors': exc.messages})

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except DjangoValidationError as exc:
            self._convert_django_error(exc)

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except DjangoValidationError as exc:
            self._convert_django_error(exc)


# ==========================================
# 1. ORGANISATION ACADÉMIQUE
# ==========================================

class FaculteSerializer(ValidateOnSaveMixin, serializers.ModelSerializer):
    class Meta:
        model  = Faculte
        fields = ['id', 'libelle']


class DepartementSerializer(ValidateOnSaveMixin, serializers.ModelSerializer):
    faculte    = FaculteSerializer(read_only=True)
    faculte_id = serializers.PrimaryKeyRelatedField(
        queryset=Faculte.objects.all(),
        source='faculte',
        write_only=True,
    )
    # Chef de département : lecture seule (nom complet) + écriture via chef_id
    chef    = serializers.SerializerMethodField(read_only=True)
    chef_id = serializers.PrimaryKeyRelatedField(
        queryset=Enseignant.objects.all(),
        source='chef',
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model  = Departement
        fields = ['id', 'libelle', 'faculte', 'faculte_id', 'chef', 'chef_id']

    def get_chef(self, obj):
        if obj.chef:
            return {
                'id'         : obj.chef.profil.user.pk,
                'nom_complet': f"{obj.chef.profil.user.last_name} {obj.chef.profil.user.first_name}".strip(),
                'grade'      : obj.chef.grade,
            }
        return None


class FiliereSerializer(ValidateOnSaveMixin, serializers.ModelSerializer):
    departement = DepartementSerializer(read_only=True)
    departement_id = serializers.PrimaryKeyRelatedField(
        queryset=Departement.objects.all(),
        source='departement',
        write_only=True,
    )
    # Responsable de filière : dérivé du chef du département pour éviter la confusion.
    responsable = serializers.SerializerMethodField(read_only=True)
    responsable_id = serializers.PrimaryKeyRelatedField(
        queryset=Enseignant.objects.all(),
        source='responsable',
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model  = Filiere
        fields = ['id', 'libelle', 'departement', 'departement_id', 'responsable', 'responsable_id']

    def get_responsable(self, obj):
        chef = obj.departement.chef if obj.departement_id else None
        if chef and hasattr(chef, 'profil'):
            return {
                'id'         : chef.profil.user.pk,
                'nom_complet': f"{chef.profil.user.last_name} {chef.profil.user.first_name}".strip(),
            }
        if obj.responsable and hasattr(obj.responsable, 'profil'):
            return {
                'id'         : obj.responsable.profil.user.pk,
                'nom_complet': f"{obj.responsable.profil.user.last_name} {obj.responsable.profil.user.first_name}".strip(),
            }
        return None


class ParcoursSerializer(ValidateOnSaveMixin, serializers.ModelSerializer):
    # libelle est une @property → jamais écrit en base, toujours calculé.
    libelle = serializers.SerializerMethodField()

    class Meta:
        model  = Parcours
        fields = ['id', 'type_parcours', 'niveau', 'libelle']

    def get_libelle(self, obj):
        return obj.libelle

    def validate(self, data):
        type_parcours = data.get('type_parcours')
        niveau        = data.get('niveau')
        niveaux_max   = {'Licence': 3, 'Master': 2, 'Doctorat': 3}

        if type_parcours and niveau is not None:
            if niveau < 1:
                raise serializers.ValidationError(
                    {'niveau': "Le niveau doit être au moins 1."}
                )
            max_n = niveaux_max.get(type_parcours)
            if max_n and niveau > max_n:
                raise serializers.ValidationError(
                    {'niveau': f"{type_parcours} ne peut pas dépasser le niveau {max_n}."}
                )
        return data


class AnneeAcademiqueSerializer(ValidateOnSaveMixin, serializers.ModelSerializer):
    class Meta:
        model  = AnneeAcademique
        fields = ['id', 'libelle', 'date_debut', 'date_fin', 'statut']

    def validate_libelle(self, value):
        if not re.match(r'^\d{4}-\d{4}$', value):
            raise serializers.ValidationError(
                "Le format doit être AAAA-AAAA. Ex : 2025-2026."
            )
        debut, fin = int(value[:4]), int(value[5:])
        if fin != debut + 1:
            raise serializers.ValidationError(
                "L'année de fin doit être exactement un an après l'année de début."
            )
        return value

    def validate(self, data):
        libelle    = data.get('libelle', '')
        date_debut = data.get('date_debut')
        date_fin   = data.get('date_fin')
        statut     = data.get('statut', 'active')

        if date_debut and date_fin:
            if date_debut >= date_fin:
                raise serializers.ValidationError(
                    {'date_fin': "La date de fin doit être après la date de début."}
                )
            if re.match(r'^\d{4}-\d{4}$', libelle):
                annee_debut = int(libelle[:4])
                annee_fin   = int(libelle[5:])
                if date_debut.year != annee_debut:
                    raise serializers.ValidationError(
                        {'date_debut': f"La date de début doit être en {annee_debut}."}
                    )
                if date_fin.year != annee_fin:
                    raise serializers.ValidationError(
                        {'date_fin': f"La date de fin doit être en {annee_fin}."}
                    )

        # Blocage archivage si séances confirmées futures
        if statut == 'archivée' and self.instance and self.instance.pk:
            today         = timezone.now().date()
            seances_futur = Seance.objects.filter(
                annee=self.instance,
                statut='Confirmée',
                date_seance__gt=today,
            )
            if seances_futur.exists():
                raise serializers.ValidationError(
                    {
                        'statut': (
                            f"Impossible d'archiver : {seances_futur.count()} "
                            f"séance(s) confirmée(s) dans le futur."
                        )
                    }
                )
        return data


class SemestreSerializer(ValidateOnSaveMixin, serializers.ModelSerializer):
    annee    = AnneeAcademiqueSerializer(read_only=True)
    annee_id = serializers.PrimaryKeyRelatedField(
        queryset=AnneeAcademique.objects.all(),
        source='annee',
        write_only=True,
    )

    class Meta:
        model  = Semestre
        fields = ['id', 'libelle', 'date_debut', 'date_fin', 'annee', 'annee_id']

    def validate(self, data):
        """
        Aligné sur le Semestre.clean() mis à jour :
        - date_debut < date_fin
        - Les dates restent dans les bornes de l'année académique.
        """
        date_debut = data.get('date_debut')
        date_fin   = data.get('date_fin')
        annee      = data.get('annee')

        if date_debut and date_fin:
            if date_debut >= date_fin:
                raise serializers.ValidationError(
                    {'date_fin': "La date de fin doit être après la date de début."}
                )
            if annee:
                if date_debut < annee.date_debut:
                    raise serializers.ValidationError(
                        {
                            'date_debut': (
                                f"Le semestre ne peut pas commencer avant "
                                f"l'année académique ({annee.date_debut})."
                            )
                        }
                    )
                if date_fin > annee.date_fin:
                    raise serializers.ValidationError(
                        {
                            'date_fin': (
                                f"Le semestre ne peut pas se terminer après "
                                f"l'année académique ({annee.date_fin})."
                            )
                        }
                    )
        return data


class ClasseSerializer(ValidateOnSaveMixin, serializers.ModelSerializer):
    libelle     = serializers.CharField(read_only=True)
    parcours    = ParcoursSerializer(read_only=True)
    filiere     = FiliereSerializer(read_only=True)
    semestre    = SemestreSerializer(read_only=True)
    annee       = AnneeAcademiqueSerializer(read_only=True)
    parcours_id = serializers.PrimaryKeyRelatedField(
        queryset=Parcours.objects.all(), source='parcours', write_only=True,
    )
    # filiere_id est optionnel : null pour les classes L1 (MIP, BCG, PCG)
    filiere_id  = serializers.PrimaryKeyRelatedField(
        queryset=Filiere.objects.all(),
        source='filiere',
        write_only=True,
        required=False,
        allow_null=True,
    )
    semestre_id = serializers.PrimaryKeyRelatedField(
        queryset=Semestre.objects.all(), source='semestre', write_only=True,
    )
    annee_id    = serializers.PrimaryKeyRelatedField(
        queryset=AnneeAcademique.objects.all(), source='annee', write_only=True,
    )
    # Champ code pour les classes L1 sans filière
    code = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Code libre (MIP, BCG, PCG) pour les classes sans filière."
    )

    nombre_etudiants = serializers.SerializerMethodField()

    class Meta:
        model  = Classe
        fields = [
            'id', 'libelle', 'code',
            'parcours', 'parcours_id',
            'filiere',  'filiere_id',
            'semestre', 'semestre_id',
            'annee',    'annee_id',
            'nombre_etudiants',
        ]

    def get_nombre_etudiants(self, obj):
        return obj.etudiant_set.count()

    def validate(self, data):
        semestre = data.get('semestre')
        annee    = data.get('annee')
        filiere  = data.get('filiere')
        code     = data.get('code', '').strip()

        # Cohérence semestre / année
        if semestre and annee and semestre.annee != annee:
            raise serializers.ValidationError(
                {
                    'semestre_id': (
                        "Le semestre ne correspond pas à l'année académique "
                        "sélectionnée."
                    )
                }
            )
        # Au moins un identifiant requis
        if not filiere and not code:
            raise serializers.ValidationError(
                {'code': "Une classe L1 doit avoir un code (ex : MIP, BCG, PCG)."}
            )
        return data


# ==========================================
# 2. LES ACTEURS
# ==========================================

class UserSerializer(serializers.ModelSerializer):
    """Lecture seule — la création d'un User se fait séparément."""
    class Meta:
        model            = User
        fields           = ['id', 'username', 'first_name', 'last_name', 'email']
        read_only_fields = fields


class ProfilSerializer(ValidateOnSaveMixin, serializers.ModelSerializer):
    user    = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='user',
        write_only=True,
    )

    photo   = serializers.SerializerMethodField()

    def get_photo(self, obj):
        if obj.photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.photo.url)
            return obj.photo.url
        return None

    class Meta:
        model  = Profil
        fields = [
            'user_id', 'user',
            'genre', 'telephone', 'photo', 'statut', 'motif_suspension',
        ]

    def validate(self, data):
        statut           = data.get('statut', 'actif')
        motif_suspension = data.get('motif_suspension', '').strip()

        if statut == 'suspendu' and not motif_suspension:
            raise serializers.ValidationError(
                {
                    'motif_suspension': (
                        "Le motif est obligatoire lorsque le statut est 'suspendu'."
                    )
                }
            )
        if statut == 'actif':
            data['motif_suspension'] = ''
        return data


class EnseignantSerializer(ValidateOnSaveMixin, serializers.ModelSerializer):
    profil         = ProfilSerializer(read_only=True)
    profil_id      = serializers.PrimaryKeyRelatedField(
        queryset=Profil.objects.all(), source='profil', write_only=True,
    )
    departement    = DepartementSerializer(read_only=True)
    departement_id = serializers.PrimaryKeyRelatedField(
        queryset=Departement.objects.all(), source='departement', write_only=True,
    )
    nom_complet = serializers.SerializerMethodField()

    class Meta:
        model  = Enseignant
        fields = [
            'profil_id', 'profil', 'nom_complet',
            'grade', 'contrat',
            'departement', 'departement_id',
        ]

    def get_nom_complet(self, obj):
        return f"{obj.profil.user.last_name} {obj.profil.user.first_name}".strip()

    def validate(self, data):
        profil = data.get('profil')
        if profil and hasattr(profil, 'etudiant'):
            raise serializers.ValidationError(
                {'profil_id': "Ce profil est déjà enregistré comme étudiant."}
            )
        return data


class EtudiantSerializer(ValidateOnSaveMixin, serializers.ModelSerializer):
    profil      = ProfilSerializer(read_only=True)
    profil_id   = serializers.PrimaryKeyRelatedField(
        queryset=Profil.objects.all(), source='profil', write_only=True,
    )
    parcours    = ParcoursSerializer(read_only=True)
    parcours_id = serializers.PrimaryKeyRelatedField(
        queryset=Parcours.objects.all(), source='parcours', write_only=True,
    )
    filiere     = FiliereSerializer(read_only=True)
    filiere_id  = serializers.PrimaryKeyRelatedField(
        queryset=Filiere.objects.all(), source='filiere', write_only=True,
    )
    classe      = ClasseSerializer(read_only=True)
    classe_id   = serializers.PrimaryKeyRelatedField(
        queryset=Classe.objects.all(), source='classe', write_only=True,
    )

    class Meta:
        model  = Etudiant
        fields = [
            'profil_id', 'profil', 'matricule',
            'parcours', 'parcours_id',
            'filiere',  'filiere_id',
            'classe',   'classe_id',
        ]

    def validate_matricule(self, value):
        if not re.match(r'^ETU-\d{5}$', value):
            raise serializers.ValidationError(
                "Le format attendu est ETU-XXXXX (ex : ETU-00123)."
            )
        return value

    def validate(self, data):
        profil   = data.get('profil')
        classe   = data.get('classe')
        parcours = data.get('parcours')
        filiere  = data.get('filiere')

        if profil and hasattr(profil, 'enseignant'):
            raise serializers.ValidationError(
                {'profil_id': "Ce profil est déjà enregistré comme enseignant."}
            )
        if classe and parcours and classe.parcours != parcours:
            raise serializers.ValidationError(
                {'classe_id': "La classe ne correspond pas au parcours sélectionné."}
            )
        # Vérification filière seulement si la classe en a une
        if classe and filiere and classe.filiere and classe.filiere != filiere:
            raise serializers.ValidationError(
                {'classe_id': "La classe ne correspond pas à la filière sélectionnée."}
            )
        if classe and classe.annee.statut == 'archivée':
            raise serializers.ValidationError(
                {
                    'classe_id': (
                        "Impossible d'inscrire dans une classe d'une année archivée."
                    )
                }
            )
        return data


# ==========================================
# 3. CONTENU PÉDAGOGIQUE
# ==========================================

class MatiereSerializer(ValidateOnSaveMixin, serializers.ModelSerializer):
    departement    = DepartementSerializer(read_only=True)
    departement_id = serializers.PrimaryKeyRelatedField(
        queryset=Departement.objects.all(), source='departement', write_only=True,
    )

    class Meta:
        model  = Matiere
        fields = ['id', 'libelle', 'departement', 'departement_id']


class ModuleSerializer(ValidateOnSaveMixin, serializers.ModelSerializer):
    matiere     = MatiereSerializer(read_only=True)
    matiere_id  = serializers.PrimaryKeyRelatedField(
        queryset=Matiere.objects.all(), source='matiere', write_only=True,
    )
    semestre    = SemestreSerializer(read_only=True)
    semestre_id = serializers.PrimaryKeyRelatedField(
        queryset=Semestre.objects.all(), source='semestre', write_only=True,
    )
    classe_id = serializers.PrimaryKeyRelatedField(
        queryset=Classe.objects.all(), source='classe', write_only=True, allow_null=True, required=False,
    )
    heures_max        = serializers.SerializerMethodField()
    heures_consommees = serializers.SerializerMethodField()
    heures_restantes  = serializers.SerializerMethodField()

    class Meta:
        model  = Module
        fields = [
            'id', 'libelle', 'description', 'credits', 'created_at',
            'matiere',  'matiere_id',
            'semestre', 'semestre_id',
            'classe_id',
            'heures_max', 'heures_consommees', 'heures_restantes',
        ]
        read_only_fields = ['created_at']

    def get_heures_max(self, obj):
        return obj.heures_max()

    def get_heures_consommees(self, obj):
        return round(obj.heures_consommees(), 2)

    def get_heures_restantes(self, obj):
        return round(obj.heures_restantes(), 2)


# ==========================================
# 4. PLANIFICATION
# ==========================================

class AffectationModuleSerializer(ValidateOnSaveMixin, serializers.ModelSerializer):
    module_id = serializers.PrimaryKeyRelatedField(
        queryset=Module.objects.all(), source='module', write_only=True
    )
    module = ModuleSerializer(read_only=True)
    enseignant_id = serializers.PrimaryKeyRelatedField(
        queryset=Enseignant.objects.all(), source='enseignant', write_only=True
    )
    enseignant = EnseignantSerializer(read_only=True)
    heures_consommees = serializers.SerializerMethodField()
    heures_restantes = serializers.SerializerMethodField()

    class Meta:
        model = AffectationModule
        fields = [
            'id', 'module', 'module_id', 'enseignant', 'enseignant_id',
            'type_seance', 'heures_prevues', 'created_at',
            'heures_consommees', 'heures_restantes'
        ]
        read_only_fields = ['created_at']

    def get_heures_consommees(self, obj):
        return round(obj.heures_consommees(), 2)

    def get_heures_restantes(self, obj):
        return round(obj.heures_restantes(), 2)


class SeanceSerializer(ValidateOnSaveMixin, serializers.ModelSerializer):
    """
    Règles métier réimplémentées (en plus du full_clean() du modèle) :
      - heure_debut >= 09h00
      - heure_fin   <= 16h20
      - Pas de séance un dimanche
      - Cohérence département enseignant ↔ matière du module
      - Conflit enseignant sur le même créneau (levé entre séances liées)
      - Conflit classe sur le même créneau
      - Volume horaire journalier de la classe <= MAX_HEURES_JOUR
      - Volume horaire du module non dépassé
      - Date dans les bornes du semestre
      - Champs de report obligatoires si statut == 'Reportée'
    """
    module        = ModuleSerializer(read_only=True)
    module_id     = serializers.PrimaryKeyRelatedField(
        queryset=Module.objects.all(), source='module', write_only=True,
    )
    enseignant    = EnseignantSerializer(read_only=True)
    enseignant_id = serializers.PrimaryKeyRelatedField(
        queryset=Enseignant.objects.all(), source='enseignant', write_only=True,
    )
    classe      = ClasseSerializer(read_only=True)
    classe_id   = serializers.PrimaryKeyRelatedField(
        queryset=Classe.objects.all(), source='classe', write_only=True,
    )
    annee       = AnneeAcademiqueSerializer(read_only=True)
    annee_id    = serializers.PrimaryKeyRelatedField(
        queryset=AnneeAcademique.objects.all(), source='annee', write_only=True,
    )
    # Séance jumelle pour cours mutualisé
    seance_liee_id = serializers.PrimaryKeyRelatedField(
        queryset=Seance.objects.all(),
        source='seance_liee',
        write_only=True,
        required=False,
        allow_null=True,
    )
    # Champ calculé : indique si la séance est mutualisée
    is_mutualise    = serializers.SerializerMethodField()
    duree_effective = serializers.SerializerMethodField()

    class Meta:
        model  = Seance
        fields = [
            'id', 'libelle',
            'date_seance', 'heure_debut', 'heure_fin', 'duree_effective',
            'type_seance', 'statut',
            'date_report', 'heure_debut_report', 'heure_fin_report',
            'module',      'module_id',
            'enseignant',  'enseignant_id',
            'classe',      'classe_id',
            'annee',       'annee_id',
            'seance_liee_id', 'is_mutualise',
        ]

    def get_duree_effective(self, obj):
        if obj.heure_debut and obj.heure_fin:
            return round(
                Seance.calculer_duree_effective(obj.heure_debut, obj.heure_fin), 2
            )
        return None

    def get_is_mutualise(self, obj):
        """Vrai si la séance est liée à une autre (cours mutualisé)."""
        return obj.seance_liee_id is not None or obj.seances_associees.exists()

    @staticmethod
    def _to_drf_error(field, exc):
        """
        Convertit une django.core.exceptions.ValidationError
        en erreur DRF 400 ciblée sur le champ JSON `field`.
        """
        from django.core.exceptions import ValidationError as DjangoVE
        if isinstance(exc, DjangoVE):
            raise serializers.ValidationError({field: exc.messages})
        raise exc

    # ── Validations champ par champ ──────────────────────────────────────────────

    def validate_heure_debut(self, value):
        """
        Délègue à validation_seance.valider_horaires (partiel — heure_debut seule).
        La validation complète (ordre debut/fin) se fait dans validate().
        """
        from EDT_app.validation_seance import MIN_HEURE_DEBUT
        if value < MIN_HEURE_DEBUT:
            raise serializers.ValidationError(
                f"Les séances ne peuvent pas commencer avant "
                f"{MIN_HEURE_DEBUT.strftime('%Hh:%M')}."
            )
        return value

    def validate_heure_fin(self, value):
        from EDT_app.validation_seance import HEURE_FIN_MAX
        if value > HEURE_FIN_MAX:
            raise serializers.ValidationError(
                f"L'heure de fin ne peut pas dépasser "
                f"{HEURE_FIN_MAX.strftime('%Hh:%M')}."
            )
        return value

    def validate_date_seance(self, value):
        from EDT_app.validation_seance import valider_dimanche
        try:
            valider_dimanche(value)
        except Exception as exc:
            self._to_drf_error('date_seance', exc)
        return value

    # ── Validations croisées ─────────────────────────────────────────────────────

    def validate(self, data):
        """
        Délègue toutes les validations croisées aux fonctions pures
        de EDT_app.validation_seance (source unique de vérité partagée
        avec Seance.clean() du modèle).
        """
        from EDT_app.validation_seance import (
            valider_horaires,
            valider_annee_non_archivee,
            valider_departement,
            valider_coherence_module_semestre,
            valider_bornes_semestre,
            valider_conflit_enseignant,
            valider_conflit_classe,
            valider_volume_module,
            valider_affectation,
            valider_volume_journalier,
            MAX_HEURES_JOUR,
        )
        from EDT_app.validation_seance import _calculer_duree_effective

        heure_debut = data.get('heure_debut')
        heure_fin   = data.get('heure_fin')
        date_seance = data.get('date_seance')
        module      = data.get('module')
        enseignant  = data.get('enseignant')
        classe      = data.get('classe')
        annee       = data.get('annee')
        statut      = data.get('statut', 'Confirmée')
        seance_liee = data.get('seance_liee')
        pk          = self.instance.pk if self.instance else None

        # 1. Ordre heure_debut / heure_fin
        try:
            valider_horaires(heure_debut, heure_fin)
        except Exception as exc:
            self._to_drf_error('heure_fin', exc)

        # 2. Année archivée
        try:
            valider_annee_non_archivee(annee)
        except Exception as exc:
            self._to_drf_error('annee_id', exc)

        if heure_debut and heure_fin:
            duree = _calculer_duree_effective(heure_debut, heure_fin)

            # 3. Durée effective max par séance
            if duree > MAX_HEURES_JOUR:
                raise serializers.ValidationError(
                    {
                        'heure_fin': (
                            f"La durée effective dépasse {MAX_HEURES_JOUR}h "
                            f"(durée calculée : {duree:.2f}h)."
                        )
                    }
                )

            # 4. Volume horaire du module non dépassé
            if module:
                try:
                    valider_volume_module(module, duree, pk)
                except Exception as exc:
                    self._to_drf_error('module_id', exc)

            # 5. Affectation de l'enseignant + volume restant
            if module and enseignant and data.get('type_seance'):
                try:
                    valider_affectation(
                        module, enseignant, data.get('type_seance'), duree, pk
                    )
                except Exception as exc:
                    self._to_drf_error('enseignant_id', exc)

            # 6. Volume journalier de la classe
            try:
                valider_volume_journalier(classe, date_seance, heure_debut, heure_fin, pk)
            except Exception as exc:
                self._to_drf_error('date_seance', exc)

        # 7. Cohérence module / semestre de la classe
        if module and classe:
            try:
                valider_coherence_module_semestre(module, classe)
            except Exception as exc:
                self._to_drf_error('module_id', exc)

        # 8. Date dans les bornes du semestre
        if date_seance and classe:
            try:
                valider_bornes_semestre(date_seance, classe)
            except Exception as exc:
                self._to_drf_error('date_seance', exc)

        # 9. Cohérence département enseignant ↔ matière du module
        if enseignant and module:
            try:
                valider_departement(enseignant, module)
            except Exception as exc:
                self._to_drf_error('enseignant_id', exc)

        # 10. Conflit enseignant (levé si séance liée / mutualisée)
        try:
            valider_conflit_enseignant(
                enseignant, date_seance, heure_debut, heure_fin, pk,
                seance_liee_pk=seance_liee.pk if seance_liee else None,
            )
        except Exception as exc:
            self._to_drf_error('enseignant_id', exc)

        # 11. Conflit classe
        try:
            valider_conflit_classe(classe, date_seance, heure_debut, heure_fin, pk)
        except Exception as exc:
            self._to_drf_error('classe_id', exc)

        # 12. Champs de report obligatoires si statut == 'Reportée'
        if statut == 'Reportée':
            data = self._validate_report(data, pk)

        return data


    def _validate_report(self, data, pk):
        """
        Délègue à validation_seance.valider_creneau_report().
        Aligné automatiquement sur Seance._valider_creneau_report() du modèle.
        """
        from EDT_app.validation_seance import valider_creneau_report
        try:
            valider_creneau_report(
                enseignant=data.get('enseignant'),
                classe=data.get('classe'),
                annee=data.get('annee'),
                date_report=data.get('date_report'),
                heure_debut_report=data.get('heure_debut_report'),
                heure_fin_report=data.get('heure_fin_report'),
                pk=pk,
            )
        except Exception as exc:
            self._to_drf_error('date_report', exc)
        return data


# ==========================================
# 5. SERIALIZERS SPÉCIAUX
# ==========================================

class SeanceReportSerializer(serializers.Serializer):
    """
    Dédié à l'action PATCH /seances/{id}/reporter/.
    N'expose que les trois champs de report et bascule le statut automatiquement.
    """
    date_report        = serializers.DateField()
    heure_debut_report = serializers.TimeField()
    heure_fin_report   = serializers.TimeField()

    def validate_date_report(self, value):
        from EDT_app.validation_seance import valider_dimanche
        try:
            valider_dimanche(value)
        except Exception as exc:
            raise serializers.ValidationError(str(exc)) from exc
        return value

    def validate_heure_debut_report(self, value):
        from EDT_app.validation_seance import MIN_HEURE_DEBUT
        if value < MIN_HEURE_DEBUT:
            raise serializers.ValidationError(
                f"Le créneau de report ne peut pas commencer avant "
                f"{MIN_HEURE_DEBUT.strftime('%Hh%M')}."
            )
        return value

    def validate_heure_fin_report(self, value):
        from EDT_app.validation_seance import HEURE_FIN_MAX
        if value > HEURE_FIN_MAX:
            raise serializers.ValidationError(
                f"L'heure de fin du report ne peut pas dépasser "
                f"{HEURE_FIN_MAX.strftime('%Hh%M')}."
            )
        return value

    def validate(self, data):
        """
        Délègue à validation_seance.valider_creneau_report().
        La séance existante est récupérée depuis le contexte.
        """
        from EDT_app.validation_seance import valider_creneau_report
        from django.core.exceptions import ValidationError as DjangoVE

        seance = self.context['seance']
        try:
            valider_creneau_report(
                enseignant=seance.enseignant,
                classe=seance.classe,
                annee=seance.annee,
                date_report=data['date_report'],
                heure_debut_report=data['heure_debut_report'],
                heure_fin_report=data['heure_fin_report'],
                pk=seance.pk,
            )
        except DjangoVE as exc:
            raise serializers.ValidationError({'date_report': exc.messages}) from exc

        return data

    def save(self):
        seance = self.context['seance']
        seance.date_report        = self.validated_data['date_report']
        seance.heure_debut_report = self.validated_data['heure_debut_report']
        seance.heure_fin_report   = self.validated_data['heure_fin_report']
        seance.statut             = 'Reportée'
        seance.save()
        return seance


class ProfilSuspensionSerializer(serializers.Serializer):
    """
    Dédié à l'action PATCH /profils/{id}/suspendre/ et /reactiver/.
    Force la présence du motif si statut → 'suspendu'.
    Efface automatiquement le motif si statut → 'actif'.
    """
    statut           = serializers.ChoiceField(choices=['actif', 'suspendu'])
    motif_suspension = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255,
    )

    def validate(self, data):
        statut           = data.get('statut')
        motif_suspension = data.get('motif_suspension', '').strip()

        if statut == 'suspendu' and not motif_suspension:
            raise serializers.ValidationError(
                {
                    'motif_suspension': (
                        "Le motif est obligatoire pour suspendre un profil."
                    )
                }
            )
        if statut == 'actif':
            data['motif_suspension'] = ''
        return data

    def save(self):
        profil = self.context['profil']
        profil.statut           = self.validated_data['statut']
        profil.motif_suspension = self.validated_data.get('motif_suspension', '')
        profil.save()
        return profil


# ==========================================
# 6. DOCUMENTS PÉDAGOGIQUES
# ==========================================

class DocumentPedagogiqueSerializer(serializers.ModelSerializer):
    """
    Serializer pour les documents pédagogiques.
    - `fichier_url` : URL absolue pour téléchargement.
    - `enseignant` : lecture seule, injecté depuis request.user à la création.
    - `module_id`  : clé étrangère en écriture.
    """
    fichier_url  = serializers.SerializerMethodField(read_only=True)
    enseignant   = EnseignantSerializer(read_only=True)
    module       = ModuleSerializer(read_only=True)
    module_id    = serializers.PrimaryKeyRelatedField(
        queryset=Module.objects.all(), source='module', write_only=True
    )
    nom_fichier  = serializers.SerializerMethodField(read_only=True)
    taille       = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model  = DocumentPedagogique
        fields = [
            'id', 'titre', 'fichier', 'fichier_url', 'nom_fichier', 'taille',
            'type_doc', 'module', 'module_id', 'enseignant', 'created_at',
        ]
        read_only_fields = ['enseignant', 'created_at', 'fichier_url', 'nom_fichier', 'taille']

    def get_fichier_url(self, obj):
        if obj.fichier:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.fichier.url)
            return obj.fichier.url
        return None

    def get_nom_fichier(self, obj):
        """Retourne juste le nom du fichier sans son chemin complet."""
        if obj.fichier:
            import os
            return os.path.basename(obj.fichier.name)
        return None

    def get_taille(self, obj):
        """Retourne la taille du fichier en octets, None si introuvable."""
        try:
            return obj.fichier.size
        except Exception:
            return None

    def validate_fichier(self, value):
        """Validation de l'extension côté serializer (doublée du validateur modèle)."""
        import os
        EXTENSIONS_AUTORISEES = {
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt'
        }
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in EXTENSIONS_AUTORISEES:
            raise serializers.ValidationError(
                f"Les fichiers '{ext}' ne sont pas autorisés. Formats acceptés : PDF, DOC, XLS, PPT, TXT."
            )
        return value