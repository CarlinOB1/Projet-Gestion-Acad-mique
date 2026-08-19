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
    Matiere, Module, Seance, ReferentClasse,
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
    heures_max        = serializers.SerializerMethodField()
    heures_consommees = serializers.SerializerMethodField()
    heures_restantes  = serializers.SerializerMethodField()

    class Meta:
        model  = Module
        fields = [
            'id', 'libelle', 'description', 'credits', 'created_at',
            'matiere',  'matiere_id',
            'semestre', 'semestre_id',
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

    # ── Validations champ par champ ──────────────────────────────────────────

    def validate_heure_debut(self, value):
        """
        Aligné sur Seance.MIN_HEURE_DEBUT :
        avant 09h00 est interdit, mais n'importe quelle heure >= 09h00 est valide.
        """
        if value < Seance.MIN_HEURE_DEBUT:
            raise serializers.ValidationError(
                f"Les séances ne peuvent pas commencer avant "
                f"{Seance.MIN_HEURE_DEBUT.strftime('%Hh:%M')}."
            )
        return value

    def validate_heure_fin(self, value):
        if value > Seance.HEURE_FIN_MAX:
            raise serializers.ValidationError(
                f"L'heure de fin ne peut pas dépasser "
                f"{Seance.HEURE_FIN_MAX.strftime('%Hh:%M')}."
            )
        return value

    def validate_date_seance(self, value):
        if value.weekday() == 6:
            raise serializers.ValidationError(
                "Impossible de planifier une séance un dimanche."
            )
        return value

    # ── Validations croisées ─────────────────────────────────────────────────

    def validate(self, data):
        heure_debut = data.get('heure_debut')
        heure_fin   = data.get('heure_fin')
        date_seance = data.get('date_seance')
        module      = data.get('module')
        enseignant  = data.get('enseignant')
        classe      = data.get('classe')
        annee       = data.get('annee')
        statut      = data.get('statut', 'Confirmée')
        pk          = self.instance.pk if self.instance else None

        # 1. Ordre heure_debut / heure_fin
        if heure_debut and heure_fin and heure_debut >= heure_fin:
            raise serializers.ValidationError(
                {'heure_fin': "L'heure de fin doit être après l'heure de début."}
            )

        # 2. Année archivée
        if annee and annee.statut == 'archivée':
            raise serializers.ValidationError(
                {'annee_id': "Impossible de créer une séance sur une année archivée."}
            )

        if heure_debut and heure_fin:
            duree = Seance.calculer_duree_effective(heure_debut, heure_fin)

            # 3. Durée effective max par séance
            if duree > Seance.MAX_HEURES_JOUR:
                raise serializers.ValidationError(
                    {
                        'heure_fin': (
                            f"La durée effective dépasse {Seance.MAX_HEURES_JOUR}h "
                            f"(durée calculée : {duree:.2f}h)."
                        )
                    }
                )

            # 4. Volume horaire du module non dépassé
            if module:
                heures_consommees = module.heures_consommees(exclure_seance_pk=pk)
                heures_max        = module.heures_max()
                if heures_consommees + duree > heures_max:
                    restant = heures_max - heures_consommees
                    raise serializers.ValidationError(
                        {
                            'module_id': (
                                f"Volume horaire de '{module.libelle}' dépassé. "
                                f"Restant : {restant:.2f}h, "
                                f"durée demandée : {duree:.2f}h."
                            )
                        }
                    )

        # 5. Cohérence module / semestre de la classe
        if module and classe and module.semestre != classe.semestre:
            raise serializers.ValidationError(
                {
                    'module_id': (
                        f"Le module appartient au semestre '{module.semestre}' "
                        f"mais la classe est en '{classe.semestre}'."
                    )
                }
            )

        # 6. Date dans les bornes du semestre
        if date_seance and classe:
            sem = classe.semestre
            if not (sem.date_debut <= date_seance <= sem.date_fin):
                raise serializers.ValidationError(
                    {
                        'date_seance': (
                            f"La date est hors du semestre "
                            f"({sem.date_debut} → {sem.date_fin})."
                        )
                    }
                )

        # 7. Cohérence département enseignant ↔ matière du module
        if enseignant and module:
            if enseignant.departement != module.matiere.departement:
                raise serializers.ValidationError(
                    {
                        'enseignant_id': (
                            f"L'enseignant est du département "
                            f"'{enseignant.departement}', "
                            f"la matière appartient au département "
                            f"'{module.matiere.departement}'."
                        )
                    }
                )

        # 8. Conflit enseignant sur le même créneau
        # Levé si la séance conflictuelle est la séance liée (mutualisée)
        seance_liee = data.get('seance_liee')
        if enseignant and date_seance and heure_debut and heure_fin:
            conflit_ens_qs = Seance.objects.filter(
                enseignant=enseignant,
                date_seance=date_seance,
                heure_debut__lt=heure_fin,
                heure_fin__gt=heure_debut,
            ).exclude(pk=pk)
            if seance_liee:
                conflit_ens_qs = conflit_ens_qs.exclude(pk=seance_liee.pk)
            if conflit_ens_qs.exists():
                raise serializers.ValidationError(
                    {
                        'enseignant_id': (
                            f"L'enseignant a déjà une séance le "
                            f"{date_seance} sur ce créneau."
                        )
                    }
                )

        # 9. Conflit classe sur le même créneau
        if classe and date_seance and heure_debut and heure_fin:
            if Seance.objects.filter(
                classe=classe,
                date_seance=date_seance,
                heure_debut__lt=heure_fin,
                heure_fin__gt=heure_debut,
            ).exclude(pk=pk).exists():
                raise serializers.ValidationError(
                    {
                        'classe_id': (
                            f"La classe a déjà une séance le "
                            f"{date_seance} sur ce créneau."
                        )
                    }
                )

        # 10. Volume horaire journalier de la classe
        if classe and date_seance and heure_debut and heure_fin:
            seances_jour = Seance.objects.filter(
                classe=classe,
                date_seance=date_seance,
                statut='Confirmée',
            ).exclude(pk=pk)
            total_jour = sum(
                Seance.calculer_duree_effective(s.heure_debut, s.heure_fin)
                for s in seances_jour
            ) + Seance.calculer_duree_effective(heure_debut, heure_fin)

            if total_jour > Seance.MAX_HEURES_JOUR:
                raise serializers.ValidationError(
                    {
                        'date_seance': (
                            f"Le volume journalier de la classe dépasse "
                            f"{Seance.MAX_HEURES_JOUR}h "
                            f"(total : {total_jour:.2f}h)."
                        )
                    }
                )

        # 11. Champs de report obligatoires si statut == 'Reportée'
        if statut == 'Reportée':
            data = self._validate_report(data, pk)

        return data

    def _validate_report(self, data, pk):
        """
        Valide le créneau de report.
        Aligné sur Seance._valider_creneau_report() du modèle mis à jour.
        """
        date_report        = data.get('date_report')
        heure_debut_report = data.get('heure_debut_report')
        heure_fin_report   = data.get('heure_fin_report')
        classe             = data.get('classe')
        annee              = data.get('annee')
        enseignant         = data.get('enseignant')

        if not date_report or not heure_debut_report or not heure_fin_report:
            raise serializers.ValidationError(
                {
                    'date_report': (
                        "La date et les horaires de report sont obligatoires "
                        "lorsque le statut est 'Reportée'."
                    )
                }
            )

        if date_report.weekday() == 6:
            raise serializers.ValidationError(
                {'date_report': "Impossible de reporter une séance un dimanche."}
            )

        # Aligné sur MIN_HEURE_DEBUT : avant 09h00 interdit
        if heure_debut_report < Seance.MIN_HEURE_DEBUT:
            raise serializers.ValidationError(
                {
                    'heure_debut_report': (
                        f"Le créneau de report ne peut pas commencer avant "
                        f"{Seance.MIN_HEURE_DEBUT.strftime('%Hh:%M')}."
                    )
                }
            )

        if heure_fin_report > Seance.HEURE_FIN_MAX:
            raise serializers.ValidationError(
                {
                    'heure_fin_report': (
                        f"L'heure de fin du report ne peut pas dépasser "
                        f"{Seance.HEURE_FIN_MAX.strftime('%Hh:%M')}."
                    )
                }
            )

        if classe:
            sem = classe.semestre
            if not (sem.date_debut <= date_report <= sem.date_fin):
                raise serializers.ValidationError(
                    {'date_report': "La date de report est hors du semestre."}
                )

        if annee:
            if not (annee.date_debut <= date_report <= annee.date_fin):
                raise serializers.ValidationError(
                    {
                        'date_report': (
                            "La date de report est hors de l'année académique."
                        )
                    }
                )

        if enseignant and heure_debut_report and heure_fin_report:
            if Seance.objects.filter(
                enseignant=enseignant,
                date_seance=date_report,
                heure_debut__lt=heure_fin_report,
                heure_fin__gt=heure_debut_report,
            ).exclude(pk=pk).exists():
                raise serializers.ValidationError(
                    {
                        'date_report': (
                            "L'enseignant a déjà une séance sur le créneau de report."
                        )
                    }
                )

        if classe and heure_debut_report and heure_fin_report:
            if Seance.objects.filter(
                classe=classe,
                date_seance=date_report,
                heure_debut__lt=heure_fin_report,
                heure_fin__gt=heure_debut_report,
            ).exclude(pk=pk).exists():
                raise serializers.ValidationError(
                    {
                        'date_report': (
                            "La classe a déjà une séance sur le créneau de report."
                        )
                    }
                )

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
        if value.weekday() == 6:
            raise serializers.ValidationError(
                "Impossible de reporter une séance un dimanche."
            )
        return value

    def validate_heure_debut_report(self, value):
        if value < Seance.MIN_HEURE_DEBUT:
            raise serializers.ValidationError(
                f"Le créneau de report ne peut pas commencer avant "
                f"{Seance.MIN_HEURE_DEBUT.strftime('%Hh%M')}."
            )
        return value

    def validate_heure_fin_report(self, value):
        if value > Seance.HEURE_FIN_MAX:
            raise serializers.ValidationError(
                f"L'heure de fin du report ne peut pas dépasser "
                f"{Seance.HEURE_FIN_MAX.strftime('%Hh%M')}."
            )
        return value

    def validate(self, data):
        seance             = self.context['seance']
        date_report        = data['date_report']
        heure_debut_report = data['heure_debut_report']
        heure_fin_report   = data['heure_fin_report']

        sem = seance.classe.semestre
        if not (sem.date_debut <= date_report <= sem.date_fin):
            raise serializers.ValidationError(
                {'date_report': "La date de report est hors du semestre."}
            )

        if not (seance.annee.date_debut <= date_report <= seance.annee.date_fin):
            raise serializers.ValidationError(
                {'date_report': "La date de report est hors de l'année académique."}
            )

        if Seance.objects.filter(
            enseignant=seance.enseignant,
            date_seance=date_report,
            heure_debut__lt=heure_fin_report,
            heure_fin__gt=heure_debut_report,
        ).exclude(pk=seance.pk).exists():
            raise serializers.ValidationError(
                {'date_report': "L'enseignant est déjà occupé sur ce créneau."}
            )

        if Seance.objects.filter(
            classe=seance.classe,
            date_seance=date_report,
            heure_debut__lt=heure_fin_report,
            heure_fin__gt=heure_debut_report,
        ).exclude(pk=seance.pk).exists():
            raise serializers.ValidationError(
                {'date_report': "La classe a déjà une séance sur ce créneau."}
            )

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