# EDT_app/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# ──────────────────────────────────────────────────────────────────────────────
# ROUTER — enregistrement des ViewSets
# ──────────────────────────────────────────────────────────────────────────────
#
# DefaultRouter génère automatiquement :
#   GET    /api/<prefix>/          → list
#   POST   /api/<prefix>/          → create
#   GET    /api/<prefix>/{id}/     → retrieve
#   PUT    /api/<prefix>/{id}/     → update
#   PATCH  /api/<prefix>/{id}/     → partial_update
#   DELETE /api/<prefix>/{id}/     → destroy
#
# Les @action custom y ajoutent leurs propres URLs.
# ──────────────────────────────────────────────────────────────────────────────

router = DefaultRouter()

# Organisation académique
router.register(r'facultes',    views.FaculteViewSet,         basename='faculte')
router.register(r'departements', views.DepartementViewSet,    basename='departement')
router.register(r'filieres',    views.FiliereViewSet,         basename='filiere')
router.register(r'parcours',    views.ParcoursViewSet,        basename='parcours')
router.register(r'annees',      views.AnneeAcademiqueViewSet, basename='annee')
router.register(r'semestres',   views.SemestreViewSet,        basename='semestre')
router.register(r'classes',     views.ClasseViewSet,          basename='classe')

# Acteurs
router.register(r'profils',      views.ProfilViewSet,    basename='profil')
router.register(r'enseignants',  views.EnseignantViewSet, basename='enseignant')
router.register(r'etudiants',    views.EtudiantViewSet,  basename='etudiant')

# Contenu pédagogique
router.register(r'matieres', views.MatiereViewSet, basename='matiere')
router.register(r'modules',  views.ModuleViewSet,  basename='module')

# Planification
router.register(r'seances', views.SeanceViewSet, basename='seance')
router.register(r'documents', views.DocumentViewSet, basename='document')


urlpatterns = [
    path('', include(router.urls)),
]