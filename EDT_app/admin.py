# admin.py
from django.contrib import admin
from django.utils import timezone
from .models import (
    Faculte, Departement, Filiere, Parcours,
    AnneeAcademique, Semestre, Classe,
    Profil, Enseignant, Etudiant,
    Matiere, Module, Seance
)
from .forms import (
    SemestreAdminForm,
    AnneeAcademiqueAdminForm,
    SeanceAdminForm
)


# ==========================================
# 1. ORGANISATION ACADÉMIQUE
# ==========================================

@admin.register(Faculte)
class FaculteAdmin(admin.ModelAdmin):
    list_display = ('libelle',)
    search_fields = ('libelle',)


@admin.register(Departement)
class DepartementAdmin(admin.ModelAdmin):
    list_display = ('libelle', 'faculte')
    search_fields = ('libelle',)
    list_filter = ('faculte',)


@admin.register(Filiere)
class FiliereAdmin(admin.ModelAdmin):
    list_display = ('libelle', 'departement')
    search_fields = ('libelle',)
    list_filter = ('departement',)


@admin.register(Parcours)
class ParcoursAdmin(admin.ModelAdmin):
    list_display = ('type_parcours', 'niveau')
    list_filter = ('type_parcours',)


@admin.register(AnneeAcademique)
class AnneeAcademiqueAdmin(admin.ModelAdmin):
    form = AnneeAcademiqueAdminForm
    list_display = ('libelle', 'date_debut', 'date_fin', 'statut')
    search_fields = ('libelle',)
    list_filter = ('statut',)
    actions = ['archiver_annees']

    def archiver_annees(self, request, queryset):
        """
        Action groupée pour archiver les années sélectionnées.
        Vérifie pour chacune qu'il n'y a pas de séances confirmées
        dans le futur avant d'archiver.
        """
        today = timezone.now().date()
        archivees = 0
        erreurs = []

        for annee in queryset:
            seances_futures = Seance.objects.filter(
                annee=annee,
                statut='Confirmée',
                date_seance__gt=today
            )
            if seances_futures.exists():
                erreurs.append(
                    f"{annee.libelle} : {seances_futures.count()} "
                    f"séance(s) confirmée(s) dans le futur."
                )
            else:
                annee.statut = 'archivée'
                annee.save()
                archivees += 1

        if archivees:
            self.message_user(
                request,
                f"{archivees} année(s) archivée(s) avec succès."
            )
        if erreurs:
            self.message_user(
                request,
                f"Impossible d'archiver : {' | '.join(erreurs)}",
                level='error'
            )

    archiver_annees.short_description = "Archiver les années sélectionnées"


@admin.register(Semestre)
class SemestreAdmin(admin.ModelAdmin):
    form = SemestreAdminForm
    list_display = ('libelle', 'annee', 'date_debut', 'date_fin')
    search_fields = ('libelle',)
    list_filter = ('annee',)


@admin.register(Classe)
class ClasseAdmin(admin.ModelAdmin):
    list_display = ('libelle', 'parcours', 'filiere', 'semestre', 'annee')
    search_fields = ('libelle',)
    list_filter = ('parcours', 'filiere', 'semestre', 'annee')


# ==========================================
# 2. LES ACTEURS
# ==========================================

@admin.register(Profil)
class ProfilAdmin(admin.ModelAdmin):
    list_display = ('user', 'genre', 'telephone', 'statut', 'motif_suspension')
    search_fields = ('user__last_name', 'user__first_name')
    list_filter = ('statut', 'genre')


@admin.register(Enseignant)
class EnseignantAdmin(admin.ModelAdmin):
    list_display = ('profil', 'grade', 'contrat', 'departement')
    search_fields = ('profil__user__last_name', 'profil__user__first_name')
    list_filter = ('departement', 'grade', 'contrat')


@admin.register(Etudiant)
class EtudiantAdmin(admin.ModelAdmin):
    list_display = ('matricule', 'profil', 'parcours', 'filiere', 'classe')
    search_fields = ('matricule', 'profil__user__last_name')
    list_filter = ('parcours', 'filiere', 'classe')


# ==========================================
# 3. CONTENU PÉDAGOGIQUE
# ==========================================

@admin.register(Matiere)
class MatiereAdmin(admin.ModelAdmin):
    list_display = ('libelle', 'departement')
    search_fields = ('libelle',)
    list_filter = ('departement',)


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('libelle', 'matiere', 'semestre', 'credits', 'heures_max')
    search_fields = ('libelle',)
    list_filter = ('matiere', 'semestre')

    def heures_max(self, obj):
        """Affiche le volume horaire maximum du module."""
        return f"{obj.heures_max()}h"
    heures_max.short_description = 'Volume max'


# ==========================================
# 4. PLANIFICATION
# ==========================================

@admin.register(Seance)
class SeanceAdmin(admin.ModelAdmin):
    form = SeanceAdminForm
    list_display = (
        'module', 'enseignant', 'classe',
        'date_seance', 'heure_debut', 'heure_fin',
        'type_seance', 'statut', 'date_report'
    )
    search_fields = ('module__libelle', 'enseignant__profil__user__last_name')
    list_filter = ('type_seance', 'statut', 'classe', 'annee')