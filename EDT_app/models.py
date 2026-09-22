# models.py
import re
from datetime import datetime, timedelta, date as date_type
from datetime import time as time_type
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator

from EDT_app.fichiers import chemin_televerse, valider_fichier_televerse


# Fonctions `upload_to` : au niveau du module, car les migrations les
# référencent par leur nom.
def chemin_photo(instance, filename):
    return chemin_televerse('profils', filename)


def chemin_document(instance, filename):
    return chemin_televerse('documents/%Y/%m', filename)


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
    - Classes L1  : filiere=None, code = 'MIP' | 'BGC' | 'PCG' (rattachées à la faculté).

    Le libellé est généré automatiquement selon le cas.
    """
    libelle  = models.CharField(max_length=100, editable=False)
    code     = models.CharField(
        max_length=20,
        blank=True,
        help_text="Code libre pour les classes sans filière (ex: MIP, BGC, PCG)."
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
    photo = models.ImageField(upload_to=chemin_photo, max_length=255, blank=True, null=True)
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
    - L'inscription est impossible dans une année archivée

    Le parcours et la filière ne sont pas stockés sur l'étudiant : ils sont
    toujours ceux de sa classe (parcours/filiere/classe sont décidés ensemble
    à l'inscription — cf. Classe). Les exposer en doublon ici ne ferait que
    créer une source de désynchronisation.
    """
    MATRICULE_PATTERN = r'^ETU-\d{5}$'

    profil = models.OneToOneField(Profil, on_delete=models.CASCADE, primary_key=True)
    matricule = models.CharField(max_length=20, unique=True, blank=False)
    classe = models.ForeignKey(Classe, on_delete=models.PROTECT)

    @property
    def parcours(self):
        return self.classe.parcours

    @property
    def filiere(self):
        return self.classe.filiere

    def clean(self):
        # Validation 1 : format matricule ETU-XXXXX
        if self.matricule and not re.match(self.MATRICULE_PATTERN, self.matricule):
            raise ValidationError(
                "Le matricule doit respecter le format ETU-XXXXX "
                "(ex: ETU-00123)."
            )

        # Validation 2 : année archivée
        if self.classe and self.classe.annee.statut == 'archivée':
            raise ValidationError(
                "Impossible d'inscrire un étudiant dans une classe "
                "appartenant à une année académique archivée."
            )

    def reinscrire(self, nouvelle_classe, date_inscription=None,
                   reference_externe=''):
        """
        Fait passer l'étudiant sur `nouvelle_classe` :
        clôt l'inscription active en cours, en crée une nouvelle et met à jour
        le pointeur `classe`.

        Point d'entrée unique pour l'application de scolarité : le type
        (Inscription / Réinscription) est déduit de l'historique, jamais fourni.
        """
        from django.db import transaction

        date_inscription = date_inscription or date_type.today()

        with transaction.atomic():
            deja_inscrit = self.inscriptions.exists()
            self.inscriptions.filter(statut='active').exclude(
                classe=nouvelle_classe
            ).update(statut='terminée')

            inscription, cree = Inscription.objects.get_or_create(
                etudiant=self,
                classe=nouvelle_classe,
                defaults={
                    'annee': nouvelle_classe.annee,
                    'type_inscription': (
                        Inscription.TYPE_REINSCRIPTION if deja_inscrit
                        else Inscription.TYPE_INSCRIPTION
                    ),
                    'date_inscription': date_inscription,
                    'statut': 'active',
                    'reference_externe': reference_externe,
                },
            )

            # get_or_create() n'applique ses `defaults` qu'à la création :
            # si l'étudiant revient sur une classe déjà quittée, la ligne
            # historique existe déjà (statut != 'active') et resterait sinon
            # inchangée — l'étudiant se retrouverait rattaché à une classe
            # sans aucune inscription active (CORRECTIONS_A_FAIRE.md, point 4).
            # On la rouvre explicitement dans ce cas, sans toucher à une ligne
            # déjà active (idempotence : rejouer sur la classe courante ne
            # doit rien réécrire).
            if not cree and inscription.statut != 'active':
                inscription.type_inscription = Inscription.TYPE_REINSCRIPTION
                inscription.statut = 'active'
                inscription.date_inscription = date_inscription
                if reference_externe:
                    inscription.reference_externe = reference_externe
                inscription.save()

            self.classe = nouvelle_classe
            self.save()

        return inscription

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.matricule} - {self.profil.user.last_name}"


class Inscription(models.Model):
    """
    Trace historisée du rattachement d'un étudiant à une classe.

    Une `Classe` étant datée (parcours + semestre + année), un étudiant qui
    progresse de S1 vers S2 puis de L1 vers L2 change de classe : `Etudiant.classe`
    ne conserve que la classe *courante*. Ce modèle conserve le parcours complet
    et distingue la première inscription de la réinscription annuelle.

    Périmètre volontairement **pédagogique** : les frais, paiements et quittances
    sont gérés par l'application de scolarité. `reference_externe` sert de point
    de raccrochement vers l'enregistrement correspondant de cette application.
    """
    TYPE_INSCRIPTION = 'Inscription'
    TYPE_REINSCRIPTION = 'Réinscription'
    TYPE_CHOICES = [
        (TYPE_INSCRIPTION, 'Inscription'),
        (TYPE_REINSCRIPTION, 'Réinscription'),
    ]
    STATUT_CHOICES = [
        ('active', 'Active'),
        ('terminée', 'Terminée'),
        ('abandonnée', 'Abandonnée'),
    ]

    etudiant = models.ForeignKey(
        Etudiant,
        on_delete=models.CASCADE,
        related_name='inscriptions',
    )
    classe = models.ForeignKey(
        Classe,
        on_delete=models.PROTECT,
        related_name='inscriptions',
    )
    annee = models.ForeignKey(
        AnneeAcademique,
        on_delete=models.PROTECT,
        related_name='inscriptions',
    )
    type_inscription = models.CharField(max_length=15, choices=TYPE_CHOICES)
    date_inscription = models.DateField()
    statut = models.CharField(max_length=12, choices=STATUT_CHOICES, default='active')
    reference_externe = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
        help_text="Identifiant de l'inscription dans l'application de scolarité.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['etudiant', 'classe'],
                name='unique_inscription_etudiant_classe',
            ),
        ]
        ordering = ['-annee__date_debut', 'classe']

    def clean(self):
        super().clean()

        # Cohérence année / classe : la classe porte déjà son année académique.
        if self.classe_id and self.annee_id and self.classe.annee_id != self.annee_id:
            raise ValidationError(
                "L'année de l'inscription ne correspond pas à l'année "
                "académique de la classe."
            )

        # Une inscription *active* sur une année archivée n'a pas de sens ;
        # les lignes historiques ('terminée'/'abandonnée') restent créables.
        if self.statut == 'active' and self.annee_id and self.annee.statut == 'archivée':
            raise ValidationError(
                "Impossible d'ouvrir une inscription active sur une année "
                "académique archivée."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.etudiant.matricule} → {self.classe} ({self.type_inscription})"


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
    classe = models.ForeignKey(Classe, on_delete=models.CASCADE, null=True, blank=True, related_name='modules')
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

    def nb_seances_liees(self):
        return self.seance_set.count()

    def nb_affectations_liees(self):
        return self.affectations.count()

    def deja_utilise(self):
        """
        True si ce module a déjà des séances programmées et/ou des
        enseignants affectés — sert à avertir avant une modification qui
        pourrait rendre ces éléments incohérents (aucun contrôle ne les
        revalide automatiquement après coup).
        """
        return self.nb_seances_liees() > 0 or self.nb_affectations_liees() > 0

    def heures_consommees(self, exclure_seance_pk=None):
        seances = self.seance_set.filter(statut__in=['Confirmée', 'Reportée'])
        if exclure_seance_pk:
            seances = seances.exclude(pk=exclure_seance_pk)

        total = 0
        for s in seances:
            _, debut, fin = s.creneau_effectif()
            total += Seance.calculer_duree_effective(debut, fin)
        return total

    def heures_effectuees(self):
        """
        Heures réellement dispensées, c'est-à-dire celles des séances déjà
        passées.

        `heures_consommees()` compte tout ce qui est *planifié* — c'est ce que
        doit vérifier le contrôle de volume, sans quoi on pourrait planifier
        deux fois le quota. Mais un indicateur de progression a besoin de ce
        qui a effectivement eu lieu : sinon un module planifié sur tout le
        semestre affiche 100 % dès la première semaine.
        """
        return self._heures(self.seance_set.all(), passees_seulement=True)

    @staticmethod
    def _heures(seances, passees_seulement=False):
        aujourdhui = date_type.today()
        total = 0
        for s in seances.filter(statut__in=['Confirmée', 'Reportée']):
            jour, debut, fin = s.creneau_effectif()
            if passees_seulement and jour and jour > aujourdhui:
                continue
            total += Seance.calculer_duree_effective(debut, fin)
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
        # La classe fait partie de l'identite du module : deux classes d'un
        # meme semestre peuvent porter un module homonyme (tronc commun,
        # modules mutualises entre filieres).
        unique_together = ('libelle', 'semestre', 'classe')


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
    hors_departement = models.BooleanField(
        default=False,
        blank=True,
        help_text=(
            "Coché quand ce module est affecté par un chef qui ne dirige pas le "
            "département propriétaire de la matière (intervention inter-départements, "
            "ex : un module de Mathématiques enseigné dans une classe d'Informatique)."
        ),
    )

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

        # ── Cohérence de département ─────────────────────────────────────────
        # Même règle que pour une séance (validation_seance.valider_departement) :
        # un enseignant ne peut porter que des modules de son propre département.
        # Sans ce verrou, un chef pouvait affecter un module d'un autre
        # département — incohérence rendue visible sur les fiches enseignant.
        from EDT_app.validation_seance import valider_departement
        valider_departement(self.enseignant, self.module)

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
            _, debut, fin = s.creneau_effectif()
            total += Seance.calculer_duree_effective(debut, fin)
        return total

    def heures_effectuees(self):
        """Heures deja dispensees par cet enseignant sur cette affectation."""
        seances = Seance.objects.filter(
            module=self.module_id,
            enseignant=self.enseignant_id,
        )
        if self.type_seance:
            seances = seances.filter(type_seance=self.type_seance)
        return Module._heures(seances, passees_seulement=True)

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
    STATUT_CHOICES = [
        ('brouillon', 'Brouillon'),
        ('Confirmée', 'Confirmée'),
        ('Annulée', 'Annulée'),
        ('Reportée', 'Reportée'),
    ]

    libelle     = models.CharField(max_length=100, blank=True)
    date_seance = models.DateField(null=False)
    heure_debut = models.TimeField(null=False)
    heure_fin   = models.TimeField(null=False)
    type_seance = models.CharField(max_length=5, choices=TYPE_CHOICES)
    statut      = models.CharField(max_length=20, choices=STATUT_CHOICES, default='brouillon')

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

    def creneau_effectif(self):
        """
        Retourne (jour, heure_debut, heure_fin) réellement occupés par cette
        séance : le créneau de report si elle est 'Reportée' et que le
        report est complet, sinon son créneau d'origine.

        Centralise une règle jusqu'ici dupliquée trois fois à l'identique
        (Module.heures_consommees, Module._heures, AffectationModule.
        heures_consommees) — et absente de valider_volume_journalier
        (EDT_app/validation_seance.py), à l'origine de
        CORRECTIONS_A_FAIRE.md point 5 : une séance reportée continuait d'y
        peser sur le quota de son ancien jour, jamais sur celui du nouveau.
        """
        if self.statut == 'Reportée' and self.heure_debut_report and self.heure_fin_report:
            return self.date_report, self.heure_debut_report, self.heure_fin_report
        return self.date_seance, self.heure_debut, self.heure_fin

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
            valider_coherence_annee_classe,
            valider_departement,
            valider_coherence_module_semestre,
            valider_bornes_semestre,
            valider_conflit_enseignant,
            valider_conflit_classe,
            valider_volume_module,
            valider_affectation,
            valider_volume_journalier,
            valider_module_seance_liee,
        )

        valider_horaires(self.heure_debut, self.heure_fin)

        if self.date_seance:
            valider_dimanche(self.date_seance)

        if self.annee_id:
            valider_annee_non_archivee(self.annee)

        if self.annee_id and self.classe_id:
            valider_coherence_annee_classe(self.annee, self.classe)

        if self.enseignant_id and self.module_id:
            valider_departement(self.enseignant, self.module)

        if self.module_id and self.classe_id:
            valider_coherence_module_semestre(self.module, self.classe)

        if self.date_seance and self.classe_id:
            valider_bornes_semestre(self.date_seance, self.classe)

        if self.module_id:
            valider_module_seance_liee(
                self.module_id,
                self.seance_liee if self.seance_liee_id else None,
                self.seances_associees.all() if self.pk else Seance.objects.none(),
            )

        # Créneau réellement occupé par la séance : celui du report si elle
        # est 'Reportée' et que le report est complet, sinon l'original.
        # Les contrôles de conflit et de volume ci-dessous portent tous sur
        # ce créneau effectif (CORRECTIONS_A_FAIRE.md, point 5) — avant ce
        # correctif, remplacer le module ou l'enseignant d'une séance déjà
        # reportée revalidait le créneau d'origine, plus occupé, au lieu du
        # créneau de report réellement utilisé.
        jour_effectif, debut_effectif, fin_effectif = self.creneau_effectif()

        # Séances exemptées du conflit enseignant car mutualisées avec
        # celle-ci — dans les deux sens (CORRECTIONS_A_FAIRE.md, point 11).
        pks_exemptes = list(
            self.seances_associees.values_list('pk', flat=True)
        ) if self.pk else []
        if self.seance_liee_id:
            pks_exemptes.append(self.seance_liee_id)

        valider_conflit_enseignant(
            self.enseignant,
            jour_effectif,
            debut_effectif,
            fin_effectif,
            self.pk,
            pks_exemptes=pks_exemptes,
        )

        valider_conflit_classe(
            self.classe if self.classe_id else None,
            jour_effectif,
            debut_effectif,
            fin_effectif,
            self.pk,
        )

        if debut_effectif and fin_effectif:
            duree = self.calculer_duree_effective(debut_effectif, fin_effectif)

            if self.module_id:
                valider_volume_module(self.module, duree, self.pk)

            if self.module_id and self.enseignant_id and self.type_seance:
                valider_affectation(
                    self.module, self.enseignant, self.type_seance, duree, self.pk
                )

            valider_volume_journalier(
                self.classe if self.classe_id else None,
                jour_effectif,
                debut_effectif,
                fin_effectif,
                self.pk,
            )

        if self.statut == 'Reportée':
            self._valider_creneau_report()

    def save(self, *args, **kwargs):
        """
        Valide et enregistre dans une transaction qui verrouille d'abord les
        séances existantes concernées par les contrôles de conflit/volume
        (même enseignant, même classe, même module). Sans ce verrou, deux
        requêtes concurrentes pouvaient chacune lire un état encore valide
        avant l'écriture de l'autre, passer leurs contrôles indépendamment,
        puis s'enregistrer toutes les deux — double-réservation ou
        dépassement de volume que ces contrôles sont censés interdire
        (CORRECTIONS_A_FAIRE.md, point 9). `select_for_update()` sérialise
        ces deux requêtes : la seconde attend que la première ait validé,
        écrit et libéré la transaction avant de relire un état à jour.
        """
        from django.db import transaction

        with transaction.atomic():
            filtres = models.Q()
            if self.enseignant_id:
                filtres |= models.Q(enseignant_id=self.enseignant_id)
            if self.classe_id:
                filtres |= models.Q(classe_id=self.classe_id)
            if self.module_id:
                filtres |= models.Q(module_id=self.module_id)
            if filtres:
                list(
                    Seance.objects.select_for_update()
                    .filter(filtres)
                    .exclude(pk=self.pk)
                    .values_list('pk', flat=True)
                )
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
    """Extension, taille et contenu réel : voir EDT_app/fichiers.py."""
    valider_fichier_televerse(value)


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
        upload_to=chemin_document,
        max_length=255,
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
