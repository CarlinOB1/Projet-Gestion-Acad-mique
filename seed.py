import os
import django
from datetime import date, time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_edt.settings')
django.setup()

from EDT_app.factories import (
    FaculteFactory, DepartementFactory, FiliereFactory,
    ParcoursFactory, AnneeAcademiqueFactory,
    Semestre1Factory, Semestre2Factory,
    ClasseFactory, EnseignantFactory, EtudiantFactory,
    MatiereFactory, ModuleFactory, SeanceFactory
)

print("Création des données de test...")

# Organisation académique
print("→ Faculté, Département, Filière...")
faculte = FaculteFactory(libelle='Faculté des Sciences')
departement = DepartementFactory(libelle='Département Informatique', faculte=faculte)
filiere = FiliereFactory(libelle='Informatique', departement=departement)

# Parcours
print("→ Parcours...")
parcours_l1 = ParcoursFactory(type_parcours='Licence', niveau=1)
parcours_l2 = ParcoursFactory(type_parcours='Licence', niveau=2)
parcours_m1 = ParcoursFactory(type_parcours='Master', niveau=1)

# Année académique avec dates
print("→ Année académique et semestres...")
annee = AnneeAcademiqueFactory(
    libelle='2025-2026',
    date_debut=date(2025, 9, 1),
    date_fin=date(2026, 6, 30)
)
semestre1 = Semestre1Factory(
    annee=annee,
    date_debut=date(2025, 9, 1),
    date_fin=date(2026, 1, 31)
)
semestre2 = Semestre2Factory(
    annee=annee,
    date_debut=date(2026, 2, 1),
    date_fin=date(2026, 6, 30)
)

# Classes
print("→ Classes...")
classe_l1_s1 = ClasseFactory(
    parcours=parcours_l1, filiere=filiere,
    semestre=semestre1, annee=annee
)
classe_l1_s2 = ClasseFactory(
    parcours=parcours_l1, filiere=filiere,
    semestre=semestre2, annee=annee
)
classe_l2_s1 = ClasseFactory(
    parcours=parcours_l2, filiere=filiere,
    semestre=semestre1, annee=annee
)

# Enseignants
print("→ 5 enseignants...")
enseignants = [
    EnseignantFactory(
        departement=departement,
        grade='Docteur',
        contrat='Permanent'
    ),
    EnseignantFactory(
        departement=departement,
        grade='Professeur',
        contrat='Permanent'
    ),
    EnseignantFactory(
        departement=departement,
        grade='Ingénieur',
        contrat='Vacataire'
    ),
    EnseignantFactory(
        departement=departement,
        grade='',
        contrat='Vacataire'
    ),
    EnseignantFactory(
        departement=departement,
        grade='Docteur',
        contrat='Permanent'
    ),
]

# Etudiants
print("→ 10 étudiants en L1 S1...")
for _ in range(10):
    EtudiantFactory(
        parcours=parcours_l1,
        filiere=filiere,
        classe=classe_l1_s1
    )

# Matières et modules
print("→ Matières et modules...")
matiere = MatiereFactory(libelle='Programmation', departement=departement)
module_s1 = ModuleFactory(
    libelle='Python',
    matiere=matiere,
    semestre=semestre1,
    credits=3,
    description='Introduction à la programmation Python'
)
module_s2 = ModuleFactory(
    libelle='Django',
    matiere=matiere,
    semestre=semestre2,
    credits=4,
    description='Développement web avec Django'
)

# Séances — heure de début fixe à 09h00
print("→ Séances...")
SeanceFactory(
    module=module_s1,
    enseignant=enseignants[0],
    classe=classe_l1_s1,
    annee=annee,
    date_seance=date(2025, 10, 1),
    heure_debut=time(9, 0),
    heure_fin=time(11, 0),
    type_seance='CM',
    statut='Confirmée'
)
SeanceFactory(
    module=module_s1,
    enseignant=enseignants[1],
    classe=classe_l2_s1,  # classe différente pour éviter conflit
    annee=annee,
    date_seance=date(2025, 10, 1),
    heure_debut=time(9, 0),
    heure_fin=time(11, 0),
    type_seance='TD',
    statut='Confirmée'
)
SeanceFactory(
    module=module_s1,
    enseignant=enseignants[2],
    classe=classe_l1_s1,
    annee=annee,
    date_seance=date(2025, 10, 2),  # jour différent pour éviter conflit
    heure_debut=time(9, 0),
    heure_fin=time(13, 15),
    type_seance='TP',
    statut='Confirmée'
)

print("\nDonnées de test créées avec succès !")
print("- 1 faculté, 1 département, 1 filière")
print("- 3 parcours, 3 classes")
print("- 5 enseignants, 10 étudiants")
print("- 1 matière, 2 modules, 3 séances")