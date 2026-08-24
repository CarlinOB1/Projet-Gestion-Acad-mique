# models.py
import re
from datetime import datetime, timedelta, date as date_type
from datetime import time as time_type
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator

# ==========================================
# 1. ORGANISATION ACADÉMIQUE
# ==========================================

class Faculte(models.Model):
    """Représente une faculté de l'université."""
    libelle = models.CharField(max_length=100, blank=False)

    def __str__(self):
        return self.libelle


class Departement(models.Model):
    """
    Rattaché à une faculté. Possède des matières et des enseignants.
    Le champ 'chef' représente le chef de département : un enseignant
    rattaché au même département, qui a des droits de gestion sur son
    département et ses filières associées.
    """
    libelle = models.CharField(max_length=100, blank=False)
    faculte = models.ForeignKey(Faculte, on_delete=models.CASCADE, related_name='departements')
    chef    = models.ForeignKey(
        'Enseignant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='departements_diriges',
    )

    def clean(self):
        if self.pk is not None and self.chef_id is not None:
            chef = self.chef
            if chef and chef.departement_id is not None and chef.departement_id != self.pk:
                raise ValidationError(
                    {"chef": "Le chef de département doit être rattaché au même département."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.libelle


class Filiere(models.Model):
    """Rattachée à un département."""
    libelle = models.CharField(max_length=100, blank=False)
    departement = models.ForeignKey(Departement, on_delete=models.CASCADE, related_name='filieres')
    responsable = models.ForeignKey(
        'Enseignant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='filieres_dirigees',
    )

    def __str__(self):
        return self.libelle


class Parcours(models.Model):
    """
    Niveau d'étude indépendant de toute filière.
    Le libellé est généré automatiquement depuis type_parcours et niveau.
    """
    TYPE_CHOICES = [
        ('Licence', 'Licence'),
        ('Master', 'Master'),
        ('Doctorat', 'Doctorat'),
    ]

    NIVEAUX_MAX = {
        'Licence': 3,
        'Master': 2,
        'Doctorat': 3,
    }

    type_parcours = models.CharField(max_length=20, choices=TYPE_CHOICES, blank=False)
    niveau = models.IntegerField(blank=False)

    @property
    def libelle(self):
        return f"{self.type_parcours} {self.niveau}"

    def clean(self):
        if self.type_parcours and self.niveau is not None:
            if self.niveau < 1:
                raise ValidationError("Le niveau doit être au moins 1.")
            niveau_max = self.NIVEAUX_MAX.get(self.type_parcours)
            if niveau_max and self.niveau > niveau_max:
                raise ValidationError(
                    f"{self.type_parcours} ne peut pas dépasser le niveau {niveau_max}."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.libelle

    class Meta:
        unique_together = ('type_parcours', 'niveau')


class AnneeAcademique(models.Model):
    """
    Année académique au format AAAA-AAAA.
    Une année archivée ne peut plus accueillir de nouvelles séances
    ni de nouvelles inscriptions.
    """
    STATUT_CHOICES = [
        ('active', 'Active'),
        ('archivée', 'Archivée'),
    ]

    libelle = models.CharField(max_length=20, blank=False)
    date_debut = models.DateField(blank=False, null=False)
    date_fin = models.DateField(blank=False, null=False)
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='active'
    )

    def clean(self):
        # Validation du format AAAA-AAAA
        pattern = r'^\d{4}-\d{4}$'
        if not re.match(pattern, self.libelle):
            raise ValidationError("Le format doit être AAAA-AAAA. Ex: 2025-2026.")

        annee_debut_str, annee_fin_str = self.libelle.split('-')
        annee_debut, annee_fin = int(annee_debut_str), int(annee_fin_str)

        if annee_fin != annee_debut + 1:
            raise ValidationError(
                "L'année de fin doit être exactement un an après l'année de début."
            )

        if self.date_debut and self.date_fin:
            if self.date_debut >= self.date_fin:
                raise ValidationError("La date de fin doit être après la date de début.")

            if self.date_debut.year != annee_debut:
                raise ValidationError(f"La date de début doit être en {annee_debut}.")

            if self.date_fin.year != annee_fin:
                raise ValidationError(f"La date de fin doit être en {annee_fin}.")

        # Validation archivage : impossible si séances confirmées dans le futur
        if self.statut == 'archivée' and self.pk:
            from django.utils import timezone
            today = timezone.now().date()
            seances_futures = Seance.objects.filter(
                annee=self,
                statut='Confirmée',
                date_seance__gt=today
            )
            if seances_futures.exists():
                raise ValidationError(
                    f"Impossible d'archiver cette année : elle contient "
                    f"{seances_futures.count()} séance(s) confirmée(s) dans le futur."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.libelle} ({self.statut})"


class Semestre(models.Model):
    SEMESTRE_CHOICES = [
        ('Semestre 1', 'Semestre 1'),
        ('Semestre 2', 'Semestre 2'),
    ]

    libelle = models.CharField(max_length=20, choices=SEMESTRE_CHOICES, blank=False)
    date_debut = models.DateField(blank=False, null=False)
    date_fin = models.DateField(blank=False, null=False)
    annee = models.ForeignKey(AnneeAcademique, on_delete=models.CASCADE, related_name='semestres')

    def clean(self):
        super().clean()
        if self.annee:
            # Vérification par rapport à l'année académique
            if self.date_debut < self.annee.date_debut:
                raise ValidationError({
                    'date_debut': f"Le semestre ne peut pas commencer avant l'année académique ({self.annee.date_debut})."
                })
            if self.date_fin > self.annee.date_fin:
                raise ValidationError({
                    'date_fin': f"Le semestre ne peut pas se terminer après l'année académique ({self.annee.date_fin})."
                })
            # Cohérence chronologique
            if self.date_debut >= self.date_fin:
                raise ValidationError("La date de début doit être antérieure à la date de fin.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.libelle} - {self.annee.libelle}"

    class Meta:
        unique_together = ('libelle', 'annee')


class Classe(models.Model):
    """
    Combinaison unique de parcours + semestre + année, éventuellement associée
    à une filière (L2 et plus) ou identifiée par un code libre (L1 : MIP, BCG, PCG).

    - Classes L2+ : filiere renseignée, code vide.
    - Classes L1  : filiere=None, code = 'MIP' | 'BCG' | 'PCG' (rattachées à la faculté).

    Le libellé est généré automatiquement selon le cas.
    """
    libelle  = models.CharField(max_length=100, editable=False)
    code     = models.CharField(
        max_length=20,
        blank=True,
        help_text="Code libre pour les classes sans filière (ex: MIP, BCG, PCG)."
    )
    parcours = models.ForeignKey(Parcours, on_delete=models.CASCADE)
    filiere  = models.ForeignKey(
        Filiere,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    semestre = models.ForeignKey(Semestre, on_delete=models.CASCADE)
    annee    = models.ForeignKey(AnneeAcademique, on_delete=models.CASCADE, related_name='classes')

    def generer_libelle(self):
        numero_semestre = ''.join(filter(str.isdigit, self.semestre.libelle))
        lettre_parcours = self.parcours.type_parcours[0].upper()
        numero_parcours = str(self.parcours.niveau)
        identifiant     = self.filiere.libelle if self.filiere else (self.code or 'N/A')
        return f"{lettre_parcours}{numero_parcours} S{numero_semestre} {identifiant} {self.annee.libelle}"

    def clean(self):
        # Au moins un identifiant parmi filiere ou code est requis
        if not self.filiere and not self.code:
            raise ValidationError(
                "Une classe doit avoir soit une filière, soit un code (ex: MIP, BCG, PCG)."
            )
        # Cohérence semestre / année
        if self.semestre and self.annee:
            if self.semestre.annee != self.annee:
                raise ValidationError(
                    "Le semestre ne correspond pas à l'année académique de la classe."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        self.libelle = self.generer_libelle()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.libelle

    class Meta:
        # La contrainte d'unicité porte sur l'identifiant réel :
        # soit la filière (L2+), soit le code (L1).
        # On utilise unique_together sur les deux colonnes nullables :
        # Django tolère plusieurs NULL dans une colonne unique.
        constraints = [
            models.UniqueConstraint(
                fields=['parcours', 'filiere', 'semestre', 'annee'],
                condition=models.Q(filiere__isnull=False),
                name='unique_classe_avec_filiere',
            ),
            models.UniqueConstraint(
                fields=['parcours', 'code', 'semestre', 'annee'],
                condition=models.Q(filiere__isnull=True),
                name='unique_classe_sans_filiere',
            ),
        ]


# ==========================================
# 2. LES ACTEURS
# ==========================================

class Profil(models.Model):
    """
    Extension du modèle User Django.
    Un profil suspendu doit obligatoirement avoir un motif renseigné.
    """
    STATUT_CHOICES = [('actif', 'Actif'), ('suspendu', 'Suspendu')]
    GENRE_CHOICES = [('M', 'Masculin'), ('F', 'Féminin')]

    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    genre = models.CharField(max_length=1, choices=GENRE_CHOICES, blank=False)
    telephone = models.CharField(max_length=20, blank=True)
    photo = models.ImageField(upload_to='profils/', blank=True, null=True)
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default='actif')
    motif_suspension = models.TextField(
        blank=True,
        help_text="Obligatoire si le statut est 'Suspendu'. "
                  "Ex: En déplacement, Congé maladie, etc."
    )

    def clean(self):
        """
        Validation 1 : motif obligatoire si statut suspendu.
        Validation 2 : un profil ne peut pas être enseignant et étudiant.
        """
        if self.statut == 'suspendu' and not self.motif_suspension.strip():
            raise ValidationError(
                "Le motif de suspension est obligatoire "
                "lorsque le statut est 'Suspendu'."
            )

        est_enseignant = hasattr(self, 'enseignant')
        est_etudiant = hasattr(self, 'etudiant')
        if est_enseignant and est_etudiant:
            raise ValidationError(
                "Un profil ne peut pas être simultanément enseignant et étudiant."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.last_name} {self.user.first_name}"


class Enseignant(models.Model):
    """
    Enseignant rattaché à un département.
    Son grade et son type de contrat sont définis par des choix fixes.
    S'il est chef de département, il doit rester rattaché au département qu'il dirige.
    """
    GRADE_CHOICES = [
        ('', '----------'),
        ('Ingénieur', 'Ingénieur'),
        ('Docteur', 'Docteur'),
        ('Professeur', 'Professeur'),
    ]

    TYPE_CHOICES = [
        ('Permanent', 'Permanent'),
        ('Vacataire', 'Vacataire'),
    ]

    profil = models.OneToOneField(Profil, on_delete=models.CASCADE, primary_key=True)
    grade = models.CharField(max_length=50, choices=GRADE_CHOICES, blank=True)
    contrat = models.CharField(max_length=20, choices=TYPE_CHOICES, blank=False)
    departement = models.ForeignKey(Departement, on_delete=models.PROTECT)

    def clean(self):
        if self.pk is not None:
            departements_diriges = Departement.objects.filter(chef=self)
            if departements_diriges.exists():
                departement_dirige = departements_diriges.first()
                if self.departement_id is None or self.departement_id != departement_dirige.pk:
                    raise ValidationError(
                        {"departement": "Un enseignant chef de département doit rester rattaché au département qu'il dirige."}
                    )

    def charge_totale(self):
        """
        Somme des heures_prevues sur toutes les affectations de cet enseignant.
        Utile pour un futur contrôle de quota statutaire.
        """
        from django.db.models import Sum
        result = self.affectations.aggregate(total=Sum('heures_prevues'))['total']
        return result or 0

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.profil.user.last_name} {self.profil.user.first_name}"


class Etudiant(models.Model):
    """
    Étudiant dont :
    - Le matricule doit respecter le format ETU-XXXXX
    - La classe doit correspondre au parcours et à la filière
    - L'inscription est impossible dans une année archivée
    """
    MATRICULE_PATTERN = r'^ETU-\d{5}$'

    profil = models.OneToOneField(Profil, on_delete=models.CASCADE, primary_key=True)
    matricule = models.CharField(max_length=20, unique=True, blank=False)
    parcours = models.ForeignKey(Parcours, on_delete=models.PROTECT)
    filiere = models.ForeignKey(Filiere, on_delete=models.PROTECT, null=True, blank=True)
    classe = models.ForeignKey(Classe, on_delete=models.PROTECT)

    def clean(self):
        # Validation 1 : format matricule ETU-XXXXX
        if self.matricule and not re.match(self.MATRICULE_PATTERN, self.matricule):
            raise ValidationError(
                "Le matricule doit respecter le format ETU-XXXXX "
                "(ex: ETU-00123)."
            )

        # Validation 2 : cohérence classe / parcours
        if self.classe and self.parcours:
            if self.classe.parcours != self.parcours:
                raise ValidationError(
                    "La classe ne correspond pas au parcours de l'étudiant."
                )

        # Validation 3 : cohérence classe / filière (seulement si l'étudiant a une filière)
        if self.classe and self.filiere:
            if self.classe.filiere and self.classe.filiere != self.filiere:
                raise ValidationError(
                    "La classe ne correspond pas à la filière de l'étudiant."
                )

        # Validation 4 : année archivée
        if self.classe and self.classe.annee.statut == 'archivée':
            raise ValidationError(
                "Impossible d'inscrire un étudiant dans une classe "
                "appartenant à une année académique archivée."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.matricule} - {self.profil.user.last_name}"


# ==========================================
# 3. CONTENU PÉDAGOGIQUE
# ==========================================

class Matiere(models.Model):
    """
    Matière appartenant à un département.
    Le département est propriétaire du contenu de la matière.
    """
    libelle = models.CharField(max_length=100, blank=False)
    departement = models.ForeignKey(
        Departement,
        on_delete=models.PROTECT,
        related_name='matieres'
    )

    def total_credits_par_classe(self, classe):
        """Total des crédits de cette matière pour une classe donnée."""
        return self.module_set.filter(
            semestre=classe.semestre
        ).aggregate(total=models.Sum('credits'))['total'] or 0

    def total_credits_par_semestre(self, semestre):
        """Total des crédits de cette matière pour un semestre donné."""
        return self.module_set.filter(
            semestre=semestre
        ).aggregate(total=models.Sum('credits'))['total'] or 0

    def __str__(self):
        return f"{self.libelle} ({self.departement.libelle})"

    class Meta:
        unique_together = ('libelle', 'departement')


class Module(models.Model):
    """
    Module appartenant à une matière et rattaché à un semestre.
    1 crédit = 12h de cours effectif maximum.

    Ventilation optionnelle par type de séance :
    - heures_cm / heures_td / heures_tp : volumes horaires déclarés par type.
    - Si renseignés, leur somme ne peut pas dépasser heures_max().
    - Servent de plafond de référence pour les AffectationModule typées.
    - Si non renseignés, le module reste sur un volume total non ventilé.
    """
    libelle = models.CharField(max_length=100, blank=False)
    description = models.TextField(blank=True)
    credits = models.IntegerField(
        validators=[
            MinValueValidator(1, message="Un module doit avoir au moins 1 crédit."),
            MaxValueValidator(6, message="Les crédits ne peuvent pas dépasser 6."),
        ]
    )
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE)
    semestre = models.ForeignKey(Semestre, on_delete=models.CASCADE)
    # CORRECTION : champ présent en base mais absent du modèle — réintégré
    created_at = models.DateTimeField(auto_now_add=True)

    # Ventilation horaire optionnelle par type (Phase 1 — décision Phase 0)
    heures_cm = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0, message="Les heures CM ne peuvent pas être négatives.")],
        help_text="Volume horaire CM prévu. Optionnel.",
    )
    heures_td = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0, message="Les heures TD ne peuvent pas être négatives.")],
        help_text="Volume horaire TD prévu. Optionnel.",
    )
    heures_tp = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0, message="Les heures TP ne peuvent pas être négatives.")],
        help_text="Volume horaire TP prévu. Optionnel.",
    )

    def heures_max(self):
        return self.credits * 12

    def heures_consommees(self, exclure_seance_pk=None):
        seances = self.seance_set.filter(statut__in=['Confirmée', 'Reportée'])
        if exclure_seance_pk:
            seances = seances.exclude(pk=exclure_seance_pk)
            
        total = 0
        for s in seances:
            if s.statut == 'Reportée' and s.heure_debut_report and s.heure_fin_report:
                total += Seance.calculer_duree_effective(s.heure_debut_report, s.heure_fin_report)
            else:
                total += Seance.calculer_duree_effective(s.heure_debut, s.heure_fin)
        return total

    def heures_restantes(self, exclure_seance_pk=None):
        return self.heures_max() - self.heures_consommees(exclure_seance_pk)

    def heures_par_type(self, type_seance):
        """
        Retourne le plafond horaire déclaré pour un type donné (CM/TD/TP),
        ou None si ce type n'est pas ventilé sur ce module.
        """
        mapping = {'CM': self.heures_cm, 'TD': self.heures_td, 'TP': self.heures_tp}
        return mapping.get(type_seance)

    def clean(self):
        super().clean()
        # Validation : la somme des heures ventilées ne dépasse pas heures_max()
        # On valide uniquement les champs renseignés.
        champs = {
            'heures_cm': self.heures_cm,
            'heures_td': self.heures_td,
            'heures_tp': self.heures_tp,
        }
        valeurs_renseignees = {k: v for k, v in champs.items() if v is not None}
        if valeurs_renseignees:
            total_ventile = sum(valeurs_renseignees.values())
            if self.credits and total_ventile > self.heures_max():
                raise ValidationError(
                    f"La somme des heures ventilées (CM+TD+TP = {total_ventile}h) "
                    f"dépasse le volume horaire maximal du module "
                    f"({self.heures_max()}h pour {self.credits} crédit(s))."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.libelle} ({self.semestre.libelle})"

    class Meta:
        unique_together = ('libelle', 'semestre')


# ==========================================
# 3b. AFFECTATION DES MODULES
# ==========================================

class AffectationModule(models.Model):
    """
    Niveau 2 : répartition des charges d'enseignement.
    Lie un enseignant à un module pour un volume d'heures donné,
    avec un type de séance optionnel (CM/TD/TP).

    - type_seance=None  → affectation générique (l'enseignant couvre tout type)
    - type_seance=CM/TD/TP → affectation typée (l'enseignant couvre ce type uniquement)

    Règle de non-ambiguïté : pour un couple (module, enseignant) donné,
    on ne peut pas mélanger affectation générique ET affectations typées.

    Dépassement de volume : si la somme des heures_prevues dépasse heures_max()
    du module, un avertissement est émis (non bloquant — décision Phase 0).
    """
    TYPE_CHOICES = [('CM', 'CM'), ('TD', 'TD'), ('TP', 'TP')]

    module      = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name='affectations',
    )
    enseignant  = models.ForeignKey(
        Enseignant,
        on_delete=models.CASCADE,
        related_name='affectations',
    )
    type_seance = models.CharField(
        max_length=5,
        choices=TYPE_CHOICES,
        null=True,
        blank=True,
        help_text="Laisser vide pour une affectation générique (tous types).",
    )
    heures_prevues = models.FloatField(
        validators=[MinValueValidator(0, message="Le volume prévu ne peut pas être négatif.")],
        help_text="Volume horaire affecté à cet enseignant pour ce module (et ce type).",
    )
    created_at  = models.DateTimeField(auto_now_add=True)

    # ── Contraintes d'intégrité ──────────────────────────────────────────────

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['module', 'enseignant', 'type_seance'],
                name='unique_affectation_module_enseignant_type',
            ),
        ]
        ordering = ['module', 'enseignant', 'type_seance']

    def clean(self):
        super().clean()
        if not self.module_id or not self.enseignant_id:
            return  # FKs pas encore résolues, on laisse passer

        # ── Règle de non-ambiguïté par couple (module, enseignant) ────────────
        autres = AffectationModule.objects.filter(
            module=self.module_id,
            enseignant=self.enseignant_id,
        ).exclude(pk=self.pk)

        if self.type_seance is None:
            # Affectation générique : interdit si le couple a déjà des affectations typées
            if autres.filter(type_seance__isnull=False).exists():
                raise ValidationError(
                    "Impossible de créer une affectation générique : cet enseignant possède "
                    "déjà une ou plusieurs affectations typées (CM/TD/TP) sur ce module. "
                    "Supprimez-les d'abord, ou utilisez une affectation typée."
                )
        else:
            # Affectation typée : interdit si le couple a déjà une affectation générique
            if autres.filter(type_seance__isnull=True).exists():
                raise ValidationError(
                    "Impossible de créer une affectation typée : cet enseignant possède "
                    "déjà une affectation générique sur ce module. "
                    "Supprimez-la d'abord, ou utilisez une affectation générique."
                )

        # ── Avertissement (non bloquant) : dépassement du volume du module ────
        # Le dépassement est détecté ici pour traçabilité, mais n'est pas bloquant.
        # Le serializer exposera l'avertissement dans la réponse API (champ 'warnings').
        # Pas de raise ValidationError ici — décision Phase 0.

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    # ── Méthodes utilitaires ─────────────────────────────────────────────────

    def heures_consommees(self, exclure_seance_pk=None):
        """
        Heures effectives des séances confirmées ou reportées rattachées à cette affectation.
        Si l'affectation est typée, seules les séances du même type sont comptées.
        """
        seances = Seance.objects.filter(
            module=self.module_id,
            enseignant=self.enseignant_id,
            statut__in=['Confirmée', 'Reportée'],
        )
        if self.type_seance:
            seances = seances.filter(type_seance=self.type_seance)
        if exclure_seance_pk:
            seances = seances.exclude(pk=exclure_seance_pk)
            
        total = 0
        for s in seances:
            if s.statut == 'Reportée' and s.heure_debut_report and s.heure_fin_report:
                total += Seance.calculer_duree_effective(s.heure_debut_report, s.heure_fin_report)
            else:
                total += Seance.calculer_duree_effective(s.heure_debut, s.heure_fin)
        return total

    def heures_restantes(self, exclure_seance_pk=None):
        """Volume horaire encore disponible sur cette affectation."""
        return self.heures_prevues - self.heures_consommees(exclure_seance_pk)

    def volume_total_affectations_module(self):
        """
        Somme de toutes les heures_prevues sur le module (tous enseignants).
        Utilisé pour générer l'avertissement de dépassement.
        """
        from django.db.models import Sum
        result = AffectationModule.objects.filter(
            module=self.module_id
        ).exclude(pk=self.pk).aggregate(total=Sum('heures_prevues'))['total'] or 0
        return result + (self.heures_prevues or 0)

    def has_volume_warning(self):
        """Retourne True si la somme des affectations dépasse heures_max() du module."""
        return self.volume_total_affectations_module() > self.module.heures_max()

    def __str__(self):
        type_label = self.type_seance or 'Générique'
        return (
            f"{self.enseignant} → {self.module.libelle} "
            f"({type_label}, {self.heures_prevues}h)"
        )


# ==========================================
# 4. PLANIFICATION
# ==========================================

class Seance(models.Model):
    MIN_HEURE_DEBUT   = time_type(9, 0)
    PAUSE_DEBUT       = time_type(11, 0)
    PAUSE_FIN         = time_type(11, 15)
    HEURE_FIN_MAX     = time_type(16, 20)
    MAX_HEURES_JOUR   = 6
    HEURES_PAR_CREDIT = 12

    TYPE_CHOICES   = [('CM', 'CM'), ('TD', 'TD'), ('TP', 'TP')]
    STATUT_CHOICES = [('Confirmée', 'Confirmée'), ('Annulée', 'Annulée'), ('Reportée', 'Reportée')]

    libelle     = models.CharField(max_length=100, blank=True)
    date_seance = models.DateField(null=False)
    heure_debut = models.TimeField(null=False)
    heure_fin   = models.TimeField(null=False)
    type_seance = models.CharField(max_length=5, choices=TYPE_CHOICES)
    statut      = models.CharField(max_length=20, choices=STATUT_CHOICES, default='Confirmée')

    date_report        = models.DateField(blank=True, null=True)
    heure_debut_report = models.TimeField(blank=True, null=True)
    heure_fin_report   = models.TimeField(blank=True, null=True)

    module     = models.ForeignKey(Module, on_delete=models.CASCADE)
    enseignant = models.ForeignKey(Enseignant, on_delete=models.CASCADE)
    classe     = models.ForeignKey(Classe, on_delete=models.CASCADE)
    annee      = models.ForeignKey(AnneeAcademique, on_delete=models.CASCADE)

    # Liaison entre séances mutualisées (même cours, classes différentes).
    # Quand deux séances sont liées, la contrainte de conflit horaire
    # de l'enseignant est levée entre elles.
    seance_liee = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='seances_associees',
        help_text="Séance jumelle pour un cours mutualisé (même créneau, classe différente)."
    )

    @staticmethod
    def calculer_duree_effective(heure_debut, heure_fin):
        debut = datetime.combine(date_type.today(), heure_debut)
        fin = datetime.combine(date_type.today(), heure_fin)
        duree_totale = fin - debut
        pause_debut = datetime.combine(date_type.today(), time_type(11, 0))
        pause_fin = datetime.combine(date_type.today(), time_type(11, 15))

        if debut < pause_fin and fin > pause_debut:
            overlap_start = max(debut, pause_debut)
            overlap_end = min(fin, pause_fin)
            duree_effective = duree_totale - (overlap_end - overlap_start)
        else:
            duree_effective = duree_totale
        return duree_effective.total_seconds() / 3600

    def _valider_creneau_report(self):
        """Délègue à validation_seance.valider_creneau_report()."""
        from EDT_app.validation_seance import valider_creneau_report
        valider_creneau_report(
            enseignant=self.enseignant,
            classe=self.classe if self.classe_id else None,
            annee=self.annee if self.annee_id else None,
            date_report=self.date_report,
            heure_debut_report=self.heure_debut_report,
            heure_fin_report=self.heure_fin_report,
            pk=self.pk,
        )

    def clean(self):
        """
        Délègue toutes les validations métier à EDT_app.validation_seance.
        Source unique de vérité partagée avec SeanceSerializer.validate().
        """
        super().clean()
        from EDT_app.validation_seance import (
            valider_horaires,
            valider_dimanche,
            valider_annee_non_archivee,
            valider_departement,
            valider_coherence_module_semestre,
            valider_bornes_semestre,
            valider_conflit_enseignant,
            valider_conflit_classe,
            valider_volume_module,
            valider_affectation,
            valider_volume_journalier,
        )

        valider_horaires(self.heure_debut, self.heure_fin)

        if self.date_seance:
            valider_dimanche(self.date_seance)

        if self.annee_id:
            valider_annee_non_archivee(self.annee)

        if self.enseignant_id and self.module_id:
            valider_departement(self.enseignant, self.module)

        if self.module_id and self.classe_id:
            valider_coherence_module_semestre(self.module, self.classe)

        if self.date_seance and self.classe_id:
            valider_bornes_semestre(self.date_seance, self.classe)

        # Conflit enseignant : levé si la séance conflictuelle est la séance liée (mutualisée)
        valider_conflit_enseignant(
            self.enseignant,
            self.date_seance,
            self.heure_debut,
            self.heure_fin,
            self.pk,
            seance_liee_pk=self.seance_liee_id,
        )

        valider_conflit_classe(
            self.classe if self.classe_id else None,
            self.date_seance,
            self.heure_debut,
            self.heure_fin,
            self.pk,
        )

        if self.heure_debut and self.heure_fin:
            duree = self.calculer_duree_effective(self.heure_debut, self.heure_fin)

            if self.module_id:
                valider_volume_module(self.module, duree, self.pk)

            if self.module_id and self.enseignant_id and self.type_seance:
                valider_affectation(
                    self.module, self.enseignant, self.type_seance, duree, self.pk
                )

            valider_volume_journalier(
                self.classe if self.classe_id else None,
                self.date_seance,
                self.heure_debut,
                self.heure_fin,
                self.pk,
            )

        if self.statut == 'Reportée':
            self._valider_creneau_report()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.module.libelle} - {self.date_seance}"


# ==========================================
# 5. RÉFÉRENTS DE CLASSES
# ==========================================

class ReferentClasse(models.Model):
    """
    Désigne un enseignant comme référent d'un ensemble de classes.
    Cas d'usage principal : coordinateur L1 (MIP, BCG, PCG).

    Le référent peut créer et modifier des séances pour les classes
    qui lui sont assignées, sans pour autant être chef de département.
    """
    enseignant = models.OneToOneField(
        Enseignant,
        on_delete=models.CASCADE,
        related_name='referent_classes',
    )
    classes = models.ManyToManyField(
        Classe,
        blank=True,
        related_name='referents',
        help_text="Classes dont cet enseignant peut gérer l'emploi du temps.",
    )

    def __str__(self):
        return f"Référent : {self.enseignant} ({self.classes.count()} classe(s))"


# ==========================================
# 6. DOCUMENTS PÉDAGOGIQUES
# ==========================================

def validate_extension_fichier(value):
    """Autorise uniquement certaines extensions."""
    import os
    from django.core.exceptions import ValidationError
    EXTENSIONS_AUTORISEES = {
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt'
    }
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in EXTENSIONS_AUTORISEES:
        raise ValidationError(
            f"Les fichiers de type '{ext}' ne sont pas autorisés. Formats acceptés : PDF, DOC, XLS, PPT, TXT."
        )


class DocumentPedagogique(models.Model):
    """
    Document pédagogique uploadé par un enseignant et rattaché à un module.
    Accessible en lecture à tous les utilisateurs authentifiés actifs.
    Modifiable / supprimable uniquement par l'enseignant propriétaire.
    """
    TYPE_CHOICES = [
        ('cours',  'Cours'),
        ('td',     'TD'),
        ('tp',     'TP'),
        ('autre',  'Autre'),
    ]

    titre      = models.CharField(max_length=200, blank=False)
    fichier    = models.FileField(
        upload_to='documents/%Y/%m/',
        validators=[validate_extension_fichier],
    )
    type_doc   = models.CharField(max_length=20, choices=TYPE_CHOICES, default='cours')
    module     = models.ForeignKey(
        Module, on_delete=models.CASCADE, related_name='documents'
    )
    enseignant = models.ForeignKey(
        Enseignant, on_delete=models.CASCADE, related_name='documents'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.titre} ({self.module.libelle})"

    class Meta:
        ordering = ['-created_at']