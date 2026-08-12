# factories.py
import factory
from factory.django import DjangoModelFactory
from faker import Faker
from django.contrib.auth.models import User
from datetime import date, time
from .models import (
    Faculte, Departement, Filiere, Parcours,
    AnneeAcademique, Semestre, Classe,
    Profil, Enseignant, Etudiant,
    Matiere, Module, Seance
)

fake = Faker('fr_FR')


# ==========================================
# 1. ORGANISATION ACADÉMIQUE
# ==========================================

class FaculteFactory(DjangoModelFactory):
    class Meta:
        model = Faculte
        django_get_or_create = ('libelle',)

    libelle = factory.Iterator([
        'Faculté des Sciences',
        'Faculté des Lettres',
        'Faculté de Droit',
    ])


class DepartementFactory(DjangoModelFactory):
    class Meta:
        model = Departement
        django_get_or_create = ('libelle', 'faculte')

    libelle = factory.Iterator([
        'Département Informatique',
        'Département Mathématiques',
        'Département Physique',
    ])
    faculte = factory.SubFactory(FaculteFactory)


class FiliereFactory(DjangoModelFactory):
    class Meta:
        model = Filiere
        django_get_or_create = ('libelle', 'departement')

    libelle = factory.Iterator([
        'Informatique',
        'Mathématiques',
        'Physique',
    ])
    departement = factory.SubFactory(DepartementFactory)


class ParcoursFactory(DjangoModelFactory):
    class Meta:
        model = Parcours
        django_get_or_create = ('type_parcours', 'niveau')

    type_parcours = 'Licence'
    niveau = 1


class AnneeAcademiqueFactory(DjangoModelFactory):
    class Meta:
        model = AnneeAcademique
        django_get_or_create = ('libelle',)

    libelle = '2025-2026'
    date_debut = date(2025, 9, 1)
    date_fin = date(2026, 6, 30)


class Semestre1Factory(DjangoModelFactory):
    class Meta:
        model = Semestre
        django_get_or_create = ('libelle', 'annee')

    libelle = 'Semestre 1'
    date_debut = date(2025, 9, 1)
    date_fin = date(2026, 1, 31)
    annee = factory.SubFactory(AnneeAcademiqueFactory)


class ClasseFactory(DjangoModelFactory):
    class Meta:
        model = Classe
        django_get_or_create = ('parcours', 'filiere', 'semestre', 'annee')

    parcours = factory.SubFactory(ParcoursFactory)
    filiere = factory.SubFactory(FiliereFactory)
    semestre = factory.SubFactory(Semestre1Factory)
    annee = factory.SelfAttribute('semestre.annee')


# ==========================================
# 2. LES ACTEURS
# ==========================================

class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ('username',)

    username = factory.LazyFunction(lambda: fake.unique.user_name())
    first_name = factory.LazyFunction(lambda: fake.first_name())
    last_name = factory.LazyFunction(lambda: fake.last_name())
    email = factory.LazyFunction(lambda: fake.email())


class ProfilFactory(DjangoModelFactory):
    class Meta:
        model = Profil
        django_get_or_create = ('user',)

    user = factory.SubFactory(UserFactory)
    genre = factory.Iterator(['M', 'F'])
    telephone = factory.LazyFunction(lambda: fake.phone_number()[:20])


class EnseignantFactory(DjangoModelFactory):
    class Meta:
        model = Enseignant
        django_get_or_create = ('profil',)

    profil = factory.SubFactory(ProfilFactory)
    grade = "Docteur"
    contrat = "Permanent"
    departement = factory.SubFactory(DepartementFactory)


class EtudiantFactory(DjangoModelFactory):
    class Meta:
        model = Etudiant
        django_get_or_create = ('matricule',)

    profil = factory.SubFactory(ProfilFactory)
    matricule = factory.Sequence(lambda n: f'ETU-{n:05d}')
    parcours = factory.SubFactory(ParcoursFactory)
    filiere = factory.SubFactory(FiliereFactory)

    # Correction : Lier la classe au même parcours/filière que l'étudiant
    classe = factory.SubFactory(
        ClasseFactory,
        parcours=factory.SelfAttribute('..parcours'),
        filiere=factory.SelfAttribute('..filiere')
    )


# ==========================================
# 3. CONTENU PÉDAGOGIQUE
# ==========================================

class MatiereFactory(DjangoModelFactory):
    class Meta:
        model = Matiere
        django_get_or_create = ('libelle', 'departement')

    libelle = factory.Iterator(['Python', 'Java', 'Algorithmique'])
    departement = factory.SubFactory(DepartementFactory)


class ModuleFactory(DjangoModelFactory):
    class Meta:
        model = Module
        django_get_or_create = ('libelle', 'semestre')

    libelle = factory.Iterator(['Programmation Orientée Objet', 'Structure de Données'])
    credits = 3
    matiere = factory.SubFactory(MatiereFactory)
    semestre = factory.SubFactory(Semestre1Factory)


# ==========================================
# 4. PLANIFICATION
# ==========================================

class SeanceFactory(DjangoModelFactory):
    class Meta:
        model = Seance

    # Heure flexible : 09:00 par défaut (conforme au model >= 09:00)
    heure_debut = time(9, 0)
    heure_fin = time(11, 0)
    type_seance = 'CM'
    statut = 'Confirmée'

    module = factory.SubFactory(ModuleFactory)

    # Correction : L'enseignant DOIT appartenir au département de la matière du module
    enseignant = factory.SubFactory(
        EnseignantFactory,
        departement=factory.SelfAttribute('..module.matiere.departement')
    )

    # Correction : La date doit être comprise dans le semestre du module
    @factory.lazy_attribute
    def date_seance(self):
        return self.module.semestre.date_debut

    # Correction : L'année doit être celle du semestre
    annee = factory.SelfAttribute('module.semestre.annee')

    # Correction : La classe doit être rattachée au même semestre que le module
    @factory.lazy_attribute
    def classe(self):
        # On cherche une filière compatible pour la classe
        # (La filière doit appartenir au département de la matière)
        return ClasseFactory(
            semestre=self.module.semestre,
            annee=self.module.semestre.annee,
            filiere=self.module.matiere.departement.filieres.first() or FiliereFactory(
                departement=self.module.matiere.departement)
        )