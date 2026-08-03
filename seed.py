"""
seed.py — Génère un jeu de données léger et cohérent pour SIGU-UCCB.
Réinitialise entièrement les données (hors superusers) avant de seed.

Lancement : python seed.py
"""
import os
import django
from datetime import date, time, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_edt.settings')
django.setup()

from django.contrib.auth.models import User, Group

from EDT_app.models import (
    Faculte, Departement, Filiere, Parcours,
    AnneeAcademique, Semestre, Classe,
    Profil, Enseignant, Etudiant,
    Matiere, Module, Seance,
)
from EDT_app.factories import (
    FaculteFactory, DepartementFactory, FiliereFactory,
    ParcoursFactory, ClasseFactory,
    ProfilFactory, MatiereFactory, ModuleFactory,
)

MOT_DE_PASSE_DEFAUT = "Password123!"


# ══════════════════════════════════════════════════════════════════════════════
# 0. FLUSH — réinitialisation complète (hors superusers Django)
# ══════════════════════════════════════════════════════════════════════════════

def flush_data():
    print("→ Suppression des données existantes...")
    Seance.objects.all().delete()
    Module.objects.all().delete()
    Matiere.objects.all().delete()
    Etudiant.objects.all().delete()
    Enseignant.objects.all().delete()
    Profil.objects.all().delete()
    User.objects.filter(is_superuser=False).delete()
    Classe.objects.all().delete()
    Semestre.objects.all().delete()
    AnneeAcademique.objects.all().delete()
    Parcours.objects.all().delete()
    Filiere.objects.all().delete()
    Departement.objects.all().delete()
    Faculte.objects.all().delete()
    print("  Base nettoyée.\n")


def creer_utilisateur(username, first_name, last_name, password=MOT_DE_PASSE_DEFAUT):
    """Crée un User Django avec un mot de passe utilisable (login testable)."""
    User.objects.filter(username=username).delete()
    user = User.objects.create_user(
        username=username,
        password=password,
        first_name=first_name,
        last_name=last_name,
        email=f"{username}@uccb.cg",
    )
    return user


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

flush_data()

print("Création des données de simulation...")

# ── 1. ORGANISATION ACADÉMIQUE ─────────────────────────────────────────────────

print("→ Facultés, départements, filières...")
faculte = FaculteFactory(libelle='Faculté des Sciences et Technologies')
dept_info = DepartementFactory(libelle='Département Informatique', faculte=faculte)
dept_math = DepartementFactory(libelle='Département Mathématiques', faculte=faculte)

filiere_gl = FiliereFactory(libelle='Génie Logiciel', departement=dept_info)
filiere_math = FiliereFactory(libelle='Mathématiques Appliquées', departement=dept_math)

print("→ Parcours...")
parcours_l1 = ParcoursFactory(type_parcours='Licence', niveau=1)
parcours_l2 = ParcoursFactory(type_parcours='Licence', niveau=2)
parcours_m1 = ParcoursFactory(type_parcours='Master', niveau=1)

print("→ Année académique et semestres...")
today = date.today()
year_start = today.year if today.month >= 9 else today.year - 1
annee = AnneeAcademique.objects.create(
    libelle=f'{year_start}-{year_start+1}',
    date_debut=date(year_start, 9, 1),
    date_fin=date(year_start+1, 8, 31),
    statut='active',
)
semestre1 = Semestre.objects.create(
    libelle='Semestre 1',
    date_debut=date(year_start, 9, 1),
    date_fin=date(year_start+1, 8, 31),
    annee=annee,
)
semestre2 = Semestre.objects.create(
    libelle='Semestre 2',
    date_debut=date(year_start, 9, 1),
    date_fin=date(year_start+1, 8, 31),
    annee=annee,
)

print("→ Classes...")
classe_l1_s1 = ClasseFactory(parcours=parcours_l1, filiere=filiere_gl, semestre=semestre1)
classe_l2_s1 = ClasseFactory(parcours=parcours_l2, filiere=filiere_gl, semestre=semestre1)
classe_m1_s1 = ClasseFactory(parcours=parcours_m1, filiere=filiere_gl, semestre=semestre1)
classe_l1_s2 = ClasseFactory(parcours=parcours_l1, filiere=filiere_gl, semestre=semestre2)

# ── 2. LES ACTEURS ──────────────────────────────────────────────────────────────

print("→ Responsable pédagogique...")
groupe_responsable, _ = Group.objects.get_or_create(name='responsable')
resp_user = creer_utilisateur('responsable1', 'Jean', 'Moukala')
resp_user.groups.add(groupe_responsable)
ProfilFactory(user=resp_user, genre='M', telephone='060000001')

print("→ 4 enseignants...")
ens1_user = creer_utilisateur('e.mbemba', 'Alain', 'Mbemba')
ens1_profil = ProfilFactory(user=ens1_user, genre='M', telephone='060000002')
ens1 = Enseignant.objects.create(profil=ens1_profil, grade='Docteur', contrat='Permanent', departement=dept_info)

ens2_user = creer_utilisateur('e.nkounkou', 'Sylvie', 'Nkounkou')
ens2_profil = ProfilFactory(user=ens2_user, genre='F', telephone='060000003')
ens2 = Enseignant.objects.create(profil=ens2_profil, grade='Professeur', contrat='Permanent', departement=dept_info)

ens3_user = creer_utilisateur('e.bakala', 'Patrick', 'Bakala')
ens3_profil = ProfilFactory(user=ens3_user, genre='M', telephone='060000004')
ens3 = Enseignant.objects.create(profil=ens3_profil, grade='Ingénieur', contrat='Vacataire', departement=dept_info)

ens4_user = creer_utilisateur('e.loubaki', 'Chantal', 'Loubaki')
ens4_profil = ProfilFactory(user=ens4_user, genre='F', telephone='060000005')
ens4 = Enseignant.objects.create(profil=ens4_profil, grade='Docteur', contrat='Permanent', departement=dept_math)

print("→ Étudiants (dont 2 suspendus)...")

def creer_etudiant(username, first_name, last_name, matricule, parcours, filiere, classe,
                    statut='actif', motif=''):
    user = creer_utilisateur(username, first_name, last_name)
    profil = ProfilFactory(user=user, genre='M', telephone='069000000', statut=statut, motif_suspension=motif)
    return Etudiant.objects.create(
        profil=profil, matricule=matricule,
        parcours=parcours, filiere=filiere, classe=classe,
    )

etudiants_l1 = [
    creer_etudiant('etu.mabiala', 'David', 'Mabiala', 'ETU-00001', parcours_l1, filiere_gl, classe_l1_s1),
    creer_etudiant('etu.samba', 'Grâce', 'Samba', 'ETU-00002', parcours_l1, filiere_gl, classe_l1_s1),
    creer_etudiant('etu.kimbembe', 'Fabrice', 'Kimbembe', 'ETU-00003', parcours_l1, filiere_gl, classe_l1_s1),
    creer_etudiant('etu.malonga', 'Odette', 'Malonga', 'ETU-00004', parcours_l1, filiere_gl, classe_l1_s1,
                statut='suspendu', motif='Dossier administratif incomplet'),
    creer_etudiant('etu.ngoma', 'Steve', 'Ngoma', 'ETU-00005', parcours_l1, filiere_gl, classe_l1_s1),
]

etudiants_l2 = [
    creer_etudiant('etu.bantsimba', 'Prisca', 'Bantsimba', 'ETU-00006', parcours_l2, filiere_gl, classe_l2_s1),
    creer_etudiant('etu.moukoko', 'Yannick', 'Moukoko', 'ETU-00007', parcours_l2, filiere_gl, classe_l2_s1),
    creer_etudiant('etu.tchicaya', 'Anicet', 'Tchicaya', 'ETU-00008', parcours_l2, filiere_gl, classe_l2_s1),
    creer_etudiant('etu.foundou', 'Larissa', 'Foundou', 'ETU-00009', parcours_l2, filiere_gl, classe_l2_s1),
]

etudiants_m1 = [
    creer_etudiant('etu.mavoungou', 'Christel', 'Mavoungou', 'ETU-00010', parcours_m1, filiere_gl, classe_m1_s1),
    creer_etudiant('etu.dzon', 'Bienvenu', 'Dzon', 'ETU-00011', parcours_m1, filiere_gl, classe_m1_s1,
                statut='suspendu', motif='Absences répétées non justifiées'),
    creer_etudiant('etu.mahoungou', 'Reine', 'Mahoungou', 'ETU-00012', parcours_m1, filiere_gl, classe_m1_s1),
]

etudiant_l1_s2 = creer_etudiant('etu.ondongo', 'Hardy', 'Ondongo', 'ETU-00013', parcours_l1, filiere_gl, classe_l1_s2)

# ── 3. CONTENU PÉDAGOGIQUE ───────────────────────────────────────────────────────

print("→ Matières et modules...")
matiere_prog = MatiereFactory(libelle='Programmation', departement=dept_info)
matiere_reseaux = MatiereFactory(libelle='Réseaux', departement=dept_info)
matiere_analyse = MatiereFactory(libelle='Analyse Mathématique', departement=dept_math)

mod_poo = ModuleFactory(
    libelle='Programmation Orientée Objet', matiere=matiere_prog, semestre=semestre1,
    credits=4, description="Bases de la POO en Python.",
)
mod_bdd = ModuleFactory(
    libelle='Bases de Données', matiere=matiere_prog, semestre=semestre1,
    credits=3, description="Modélisation et SQL.",
)
mod_reseaux1 = ModuleFactory(
    libelle='Introduction aux Réseaux', matiere=matiere_reseaux, semestre=semestre1,
    credits=3, description="Notions fondamentales des réseaux informatiques.",
)
mod_algo_avance = ModuleFactory(
    libelle='Algorithmique Avancée', matiere=matiere_prog, semestre=semestre1,
    credits=4, description="Structures de données et complexité.",
)
mod_analyse1 = ModuleFactory(
    libelle='Analyse 1', matiere=matiere_analyse, semestre=semestre1,
    credits=3, description="Suites, limites, continuité.",
)
mod_poo_web = ModuleFactory(
    libelle='Programmation Web', matiere=matiere_prog, semestre=semestre2,
    credits=3, description="Développement web côté client et serveur.",
)

# ── 4. SÉANCES (~15, relatives à aujourd'hui) ─────────────────────────────────────

print("→ Séances relatives à aujourd'hui (Confirmées, Annulées, Reportées)...")

def creer_seance(module, enseignant, classe, date_seance, heure_debut, heure_fin,
                type_seance, statut='Confirmée',
                date_report=None, heure_debut_report=None, heure_fin_report=None, seance_liee=None):
    return Seance.objects.create(
        module=module, enseignant=enseignant, classe=classe, annee=annee,
        date_seance=date_seance, heure_debut=heure_debut, heure_fin=heure_fin,
        type_seance=type_seance, statut=statut,
        date_report=date_report,
        heure_debut_report=heure_debut_report,
        heure_fin_report=heure_fin_report,
        seance_liee=seance_liee,
    )

# Classe L1 GL — Semestre 1 (passé ou présent selon date)
creer_seance(mod_poo, ens1, classe_l1_s1, today - timedelta(days=2), time(9, 0), time(11, 0), 'CM')
creer_seance(mod_bdd, ens3, classe_l1_s1, today - timedelta(days=1), time(13, 0), time(15, 0), 'TD')
creer_seance(mod_poo, ens1, classe_l1_s1, today, time(9, 0), time(12, 0), 'TP')
creer_seance(mod_bdd, ens3, classe_l1_s1, today + timedelta(days=1), time(9, 0), time(11, 0), 'CM')
creer_seance(mod_poo, ens1, classe_l1_s1, today + timedelta(days=2), time(13, 0), time(15, 30), 'TD', statut='Annulée')

# Classe L2 GL — Semestre 1
creer_seance(mod_reseaux1, ens2, classe_l2_s1, today - timedelta(days=1), time(9, 0), time(11, 0), 'CM')
creer_seance(mod_algo_avance, ens3, classe_l2_s1, today, time(10, 0), time(12, 0), 'TD')
creer_seance(mod_reseaux1, ens2, classe_l2_s1, today + timedelta(days=2), time(9, 0), time(11, 30), 'TP')
creer_seance(
    mod_algo_avance, ens3, classe_l2_s1, today + timedelta(days=3), time(14, 0), time(16, 0), 'CM',
    statut='Reportée',
    date_report=today + timedelta(days=5), heure_debut_report=time(9, 0), heure_fin_report=time(11, 0),
)

# Classe M1 GL — Semestre 1
creer_seance(mod_analyse1, ens4, classe_m1_s1, today - timedelta(days=2), time(9, 0), time(11, 0), 'CM')
creer_seance(mod_analyse1, ens4, classe_m1_s1, today, time(13, 0), time(15, 0), 'TD')
creer_seance(mod_analyse1, ens4, classe_m1_s1, today + timedelta(days=1), time(9, 0), time(12, 0), 'TP', statut='Annulée')
creer_seance(
    mod_analyse1, ens4, classe_m1_s1, today + timedelta(days=4), time(9, 0), time(11, 0), 'CM',
    statut='Reportée',
    date_report=today + timedelta(days=6), heure_debut_report=time(13, 0), heure_fin_report=time(15, 0),
)

# Classe L1 GL — Semestre 2
creer_seance(mod_poo_web, ens1, classe_l1_s2, today + timedelta(days=1), time(9, 0), time(11, 0), 'CM')
creer_seance(mod_poo_web, ens1, classe_l1_s2, today + timedelta(days=3), time(13, 0), time(15, 0), 'TD')

# ══════════════════════════════════════════════════════════════════════════════
# RÉCAPITULATIF
# ══════════════════════════════════════════════════════════════════════════════

print("\n✅ Données de simulation créées avec succès !\n")
print(f"  Organisation : 1 faculté, 2 départements, 2 filières")
print(f"  Académique   : 1 année (2025-2026), 2 semestres, 4 classes")
print(f"  Contenu      : 3 matières, 6 modules")
print(f"  Séances      : {Seance.objects.count()} au total "
    f"({Seance.objects.filter(statut='Confirmée').count()} confirmées, "
    f"{Seance.objects.filter(statut='Annulée').count()} annulées, "
    f"{Seance.objects.filter(statut='Reportée').count()} reportées)")
print(f"  Acteurs      : 1 responsable, 4 enseignants, "
    f"{Etudiant.objects.count()} étudiants (dont {Profil.objects.filter(statut='suspendu').count()} suspendus)\n")

print("── Comptes de test (mot de passe par défaut : Password123!) ──────────────")
print(f"  Responsable  : responsable1")
print(f"  Enseignant   : e.mbemba   (dept. Informatique, module POO)")
print(f"  Enseignant   : e.loubaki  (dept. Mathématiques, module Analyse 1)")
print(f"  Étudiant     : etu.mabiala   (classe L1 GL, actif)")
print(f"  Étudiant     : etu.malonga   (classe L1 GL, SUSPENDU)")
print(f"  Étudiant     : etu.mavoungou (classe M1 GL, actif)")