"""
seed.py - Genere le jeu de donnees de la FST.

Une seule annee academique (2026-2027, rentree le 16/09/2026), des semestres
de 15 semaines, et pour chaque classe une grille hebdomadaire recurrente :
chaque couple (module, CM/TD/TP) occupe une case fixe de la semaine et s'y
repete jusqu'a epuisement de son quota horaire.

Principes :
  - la grille horaire vient de EDT_app/validation_seance.py (source unique) ;
  - les volumes horaires des modules sont DEDUITS de la grille, jamais l'inverse,
    ce qui garantit que le moteur de validation accepte toutes les seances ;
  - les creneaux sont reserves en memoire avant toute ecriture : aucun conflit
    d'enseignant ou de classe n'est genere puis rattrape silencieusement ;
  - chaque module est rattache a sa classe (Module.classe), sans quoi il reste
    invisible dans le contenu pedagogique ;
  - aucune classe n'est creee sans etudiant ;
  - DATE_RENTREE (16/09/2026) est un mercredi : la grille hebdomadaire de
    seances s'ancre sur le lundi suivant (21/09/2026), la date de rentree
    elle-meme reste la date administrative du Semestre 1.
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import os
import django
import re
import random
from datetime import date, time, timedelta
import unicodedata

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_edt.settings')
django.setup()

import secrets
from django.conf import settings

# Ce script EFFACE tous les utilisateurs non superusers et les donnees
# academiques avant de tout recreer, et donne le meme mot de passe a tous les
# comptes generes : il ne doit jamais tourner sur une base reelle.
if not settings.DEBUG:
    sys.exit(
        "Refus : seed.py n'est autorise qu'avec DJANGO_DEBUG=True (base de "
        "developpement jetable). Il efface les utilisateurs existants."
    )

# Mot de passe commun des comptes generes : celui de SEED_PASSWORD (.env) s'il
# est defini, sinon un mot de passe aleatoire affiche une seule fois ci-dessous.
SEED_PASSWORD = os.environ.get('SEED_PASSWORD')
if not SEED_PASSWORD:
    SEED_PASSWORD = secrets.token_urlsafe(12)
    print(f"Mot de passe des comptes generes (a noter, non reaffiche) : {SEED_PASSWORD}\n")

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count
from EDT_app.models import (
    Faculte, Departement, Filiere, Parcours,
    AnneeAcademique, Semestre, Classe,
    Profil, Enseignant, Etudiant, ReferentClasse,
    Matiere, Module, Seance, AffectationModule, Inscription,
)
from EDT_app.validation_seance import BLOCS_JOURNEE, JOURS_OUVRES
from EDT_app.factories import (
    FaculteFactory, DepartementFactory, FiliereFactory,
    ParcoursFactory, ProfilFactory, MatiereFactory,
)

# Étudiants FICTIFS (noms, dates de naissance, téléphones et emails
# inventés) : ne jamais remettre ici de données de personnes réelles.
RAW_STUDENTS = """
1. Niveau L1 (73 étudiants) — Inscription : 2025
Portail : BGC
KASSAMBA Tania Maëlle (F) – 2003-10-23 – Tél : 06-000-0001
TATOUKA Noëlla (F) – 2006-03-07 – Tél : 06-000-0002
ZOKALA Aurore (F) – 2006-03-15 – Tél : 06-000-0003
MBAMBALI Élodie Nadège (F) – 2003-05-09 – Tél : 06-000-0004
MBAMBALI Alice Victoire (F) – 2005-04-26 – Tél : 06-000-0005
NKOMPASSI Landry Kévin (M) – 2002-03-12 – Tél : 06-000-0006
MBADONGO Josiane Nadège (F) – 2004-11-16 – Tél : 06-000-0007
DIKOMBO Isaac Daniel (M) – 2005-07-23 – Tél : 06-000-0008
GANNGOLO Lydie (F) – 2004-08-01 – Tél : 06-000-0009
YAMPASSI Pauline Nadège (F) – 2005-09-15 – Tél : 06-000-0010
EBOZINGA Nadège Esther (F) – 2004-04-03 – Tél : 06-000-0011
IBAMBALI Aurore (F) – 2004-10-11 – Tél : 06-000-0012
IBAYOKO Hervé (M) – 2004-06-19 – Tél : 06-000-0013
TAKALA Zoé (F) – 2005-08-27 – Tél : 06-000-0014
TAYOKO Maëlle Inès (F) – 2005-08-09 – Tél : 06-000-0015
NKOLANDA Rodrigue (M) – 2006-11-12 – Tél : 06-000-0016
MOUDONGO Thierry Exaucé (M) – 2006-04-18 – Tél : 06-000-0017
BITOUKA Chloé Béatrice (F) – 2002-04-27 – Tél : 06-000-0018
GANZINGA Esther Divine (F) – 2004-04-17 – Tél : 06-000-0019
MATANDOU Merveille (F) – 2005-03-23 – Tél : 06-000-0020
KILEKA Wilfried (M) – 2005-08-16 – Tél : 06-000-0021
GANLEKA Prisca (F) – 2007-11-27 – Tél : 06-000-0022
SALANDA Zoé Tania (F) – 2007-07-09 – Tél : 06-000-0023
BIMPASSI Alice (F) – 2005-10-13 – Tél : 06-000-0024
BIMBALI Victoire (F) – 2006-12-16 – Tél : 06-000-0025
EBOYOKO Maëlle (F) – 2006-09-11 – Tél : 06-000-0026
LOUYOKO Grâce Merveille (F) – 2006-11-13 – Tél : 06-000-0027
IBATANDOU Gildas (M) – 2007-01-24 – Tél : 06-000-0028
LOUMBALI Sarah Victoire (F) – 2007-11-04 – Tél : 06-000-0029
TAVOUNA Chloé Zoé (F) – 2007-09-26 – Tél : 06-000-0030
LOUTANDOU Victoire (F) – 2007-03-12 – Tél : 06-000-0031
KILEKA Josiane (F) – 2007-10-20 – Tél : 06-000-0032
EBOKOMBO Inès (F) – 2007-05-15 – Tél : 06-000-0033
IBALEKA Noëlla (F) – 2005-12-27 – Tél : 06-000-0034
NDOKOMBO Daniel (M) – 2005-11-11 – Tél : 06-000-0035
TANDELE Alice Zoé (F) – 2007-09-10 – Tél : 06-000-0036
EBONDELE Yolande Tania (F) – 2005-12-01 – Tél : 06-000-0037
TSIMBALI Christian (M) – 2006-05-27 – Tél : 06-000-0038

Portail : MIP
KOUYOKO Yolande (F) – 2007-01-15 – Tél : 06-000-0039
SALEKA Olivier (M) – 2005-03-04 – Tél : 06-000-0040
SABAKA Albert (M) – 2006-08-14 – Tél : 06-000-0041
SAMPASSI Rodrigue Marius (M) – 2004-09-24 – Tél : 06-000-0042
KAMPASSI Serge (M) – 2005-06-22 – Tél : 06-000-0043
DIZINGA Christian (M) – 2005-09-01 – Tél : 06-000-0044
ZOTANDOU Prisca (F) – 2005-07-15 – Tél : 06-000-0045
MBAMBALI Inès Lydie (F) – 2005-08-10 – Tél : 06-000-0046
TAKALA Merveille (F) – 2005-06-24 – Tél : 06-000-0047
MBAKOMBO Wilfried Isaac (M) – 2005-11-25 – Tél : 06-000-0048
EBOKALA Pauline Grâce (F) – 2005-02-16 – Tél : 06-000-0049
DIBAKA Landry (M) – 2005-10-19 – Tél : 06-000-0050
NDOLANDA Nadège (F) – 2005-10-22 – Tél : 06-000-0051
TASSAMBA Christian Kévin (M) – 2006-02-03 – Tél : 06-000-0052
KOUKOMBO Steve Daniel (M) – 2005-02-12 – Tél : 06-000-0053
MBAKALA Grâce Pauline (F) – 2005-11-22 – Tél : 06-000-0054
ZOYOKO Fabrice (M) – 2005-03-02 – Tél : 06-000-0055
MBATANDOU Steve (M) – 2007-08-06 – Tél : 06-000-0056
IBAKALA Maëlle Élodie (F) – 2005-06-18 – Tél : 06-000-0057
MATANDOU Océane (F) – 2007-06-20 – Tél : 06-000-0058
BOUNGOLO Fortuné Landry (M) – 2007-06-12 – Tél : 06-000-0059
MIBAKA Solange (F) – 2006-06-10 – Tél : 06-000-0060

Portail : PCG
MOULEKA Prisca (F) – 2006-05-06 – Tél : 06-000-0061
MOUKOMBO Béatrice Victoire (F) – 2006-09-13 – Tél : 06-000-0062
NKOTANDOU Grâce (F) – 2006-11-28 – Tél : 06-000-0063
BAZINGA Exaucé Albert (M) – 2006-09-01 – Tél : 06-000-0064
MBAMPASSI Josiane (F) – 2007-01-02 – Tél : 06-000-0065
DIKOMBO Esther Inès (F) – 2006-06-26 – Tél : 06-000-0066
SALANDA Aimé (M) – 2007-06-28 – Tél : 06-000-0067
EBOMPASSI Grâce Laure (F) – 2007-09-25 – Tél : 06-000-0068
MOUSSAMBA Gildas (M) – 2007-10-08 – Tél : 06-000-0069
MIZINGA Lydie Ruth (F) – 2007-02-05 – Tél : 06-000-0070
EBOKOMBO Steve Exaucé (M) – 2007-09-28 – Tél : 06-000-0071
LOUDONGO Pauline (F) – 2007-07-17 – Tél : 06-000-0072
YADONGO Serge Wilfried (M) – 2006-08-06 – Tél : 06-000-0073

2. Niveau L2 (50 étudiants) — Inscription : 2024
Filière : Biologie
LOULANDA Prisca Esther (F) – 2006-01-05 – Tél : 06-000-0074
OKOLANDA Fanny Chloé (F) – 2005-06-28 – Tél : 06-000-0075
MINGOLO Alice Grâce (F) – 2006-12-14 – Tél : 06-000-0076
MAKALA Inès Nadège (F) – 2004-04-20 – Email : etudiant077@exemple.test
YAKALA Landry (M) – 2006-07-18 – Tél : 06-000-0078
KALEKA Sarah (F) – 2007-11-11 – Tél : 06-000-0079
MAKOMBO Jordan Serge (M) – 2007-10-10 – Tél : 06-000-0080

Filière : Chimie
ZOBAKA Alice Grâce (F) – 2004-12-22 – Tél : 06-000-0081
DINDELE Sarah (F) – 2005-10-02 – Tél : 06-000-0082
BOUMBALI Noëlla (F) – 2005-11-24 – Tél : 06-000-0083
NKODONGO Yannick Hervé (M) – 2004-04-22 – Tél : 06-000-0084
NGANDELE Steve (M) – 2004-10-16 – Tél : 06-000-0085
EBOBAKA Prisca (F) – 2006-09-25 – Tél : 06-000-0086

Filière : Géosciences
MBASSAMBA Ulrich Patrick (M) – 2004-04-26 – Tél : 06-000-0087
DIMPASSI Fortuné (M) – 2004-03-14 – Tél : 06-000-0088
MISSAMBA Merveille (F) – 2006-06-19 – Tél : 06-000-0089
KAMBALI Chloé Pauline (F) – 2004-11-22 – Tél : 06-000-0090
NKOLANDA Zoé Élodie (F) – 2004-08-23 – Tél : 06-000-0091
ZONDELE Fabrice Patrick (M) – 2006-08-25 – Tél : 06-000-0092
NKOTOUKA Landry (M) – 2004-08-07 – Tél : 06-000-0093
SALANDA Océane Aurore (F) – 2004-04-23 – Tél : 06-000-0094
MANDELE Cédric Aimé (M) – 2004-01-01 – Tél : 06-000-0095

Filière : Informatique
TAMPASSI Aimé (M) – 2005-05-17 – Tél : 06-000-0096
NGADONGO Noëlla Victoire (F) – 2006-07-02 – Tél : 06-000-0097
NDONDELE Aurore Zoé (F) – 2004-11-05 – Tél : 06-000-0098
MINDELE Béatrice Hélène (F) – 2005-02-07 – Tél : 06-000-0099
IBAZINGA Ruth Solange (F) – 2006-02-03 – Tél : 06-000-0100
YAYOKO Zacharie (M) – 2006-10-18 – Tél : 06-000-0101
NKOVOUNA Yannick (M) – 2004-10-14 – Tél : 06-000-0102
NGAVOUNA Steve Cédric (M) – 2006-10-11 – Tél : 06-000-0103
SAKALA Isaac (M) – 2005-06-04 – Tél : 06-000-0104
IBATANDOU Hervé (M) – 2004-10-22 – Tél : 06-000-0105
IBANGOLO Alice Yolande (F) – 2005-05-15 – Tél : 06-000-0106
GANKOMBO Kévin Cédric (M) – 2004-03-18 – Tél : 06-000-0107
BIYOKO Hélène Josiane (F) – 2004-02-18 – Tél : 06-000-0108
DILEKA Lydie Océane (F) – 2004-08-03 – Tél : 06-000-0109
MBATOUKA Ruth Josiane (F) – 2004-08-16 – Tél : 06-000-0110
ZONGOLO Daniel (M) – 2004-06-03 – Tél : 06-000-0111
BOUNGOLO Hervé (M) – 2007-08-04 – Tél : 06-000-0112
DISSAMBA Divine (F) – 2005-07-18 – Tél : 06-000-0113
BOUKALA Merveille Océane (F) – 2005-06-13 – Tél : 06-000-0114
GANNGOLO Solange Maëlle (F) – 2005-08-04 – Tél : 06-000-0115
KOUZINGA Serge Olivier (M) – 2004-10-07 – Tél : 06-000-0116
MOUYOKO Alice (F) – 2004-05-12 – Tél : 06-000-0117

Filière : Mathématiques
MBAMBALI Cédric Rodrigue (M) – 2005-05-25 – Tél : 06-000-0118
NDOLEKA Ulrich Valentin (M) – 2004-10-01 – Tél : 06-000-0119
BOUNGOLO Pauline (F) – 2005-08-23 – Tél : 06-000-0120
TAKOMBO Divine (F) – 2004-02-12 – Tél : 06-000-0121
SAVOUNA Fortuné Isaac (M) – 2006-11-12 – Tél : 06-000-0122
MOUVOUNA Sarah Prisca (F) – 2005-10-20 – Tél : 06-000-0123
OKOYOKO Olivier (M) – 2004-01-08 – Tél : 06-000-0124
BILEKA Zoé Océane (F) – 2005-02-24 – Tél : 06-000-0125

Filière : Physique
BOUNDELE Jordan (M) – 2005-08-19 – Tél : 06-000-0126
NGAKOMBO Béatrice (F) – 2007-08-05 – Tél : 06-000-0127
NDODONGO Hervé (M) – 2006-09-17 – Tél : 06-000-0128
NKODONGO Laure Tania (F) – 2004-06-02 – Tél : 06-000-0129
MIZINGA Sarah (F) – 2007-01-08 – Tél : 06-000-0130

3. Niveau L3 (48 étudiants) — Inscription : 2023
Filière : Biologie
KOUZINGA Patrick (M) – 2002-09-01 – Tél : 06-000-0131
YADONGO Léa Inès (F) – 2005-01-18 – Tél : 06-000-0132
ZONGOLO Aurore (F) – 2004-10-10 – Tél : 06-000-0133
NGALANDA Hervé Gildas (M) – 2005-02-16 – Tél : 06-000-0134
MITOUKA Victoire (F) – 2004-07-15 – Tél : 06-000-0135
BIKOMBO Zoé Solange (F) – 2002-10-15 – Tél : 06-000-0136
YATANDOU Prisca (F) – 2005-03-02 – Tél : 06-000-0137
ZOSSAMBA Laure (F) – 2004-05-19 – Tél : 06-000-0138
BAMPASSI Zoé (F) – 2004-12-14 – Tél : 06-000-0139
TSITANDOU Fanny Alice (F) – 2005-05-18 – Tél : 06-000-0140
LOUTOUKA Noël (M) – 2004-03-21 – Tél : 06-000-0141
NDOMPASSI Grâce Nadège (F) – 2007-02-09 – Tél : 06-000-0142

Filière : Chimie
BIMBALI Maëlle (F) – 2004-04-20 – Tél : 06-000-0143
TSIKALA Alice Maëlle (F) – 2005-09-10 – Tél : 06-000-0144
MALANDA Hervé Jordan (M) – 2004-08-23 – Tél : 06-000-0145
MADONGO Serge (M) – 2005-08-23 – Tél : 06-000-0146
MBALANDA Élodie Nadège (F) – 2005-05-05 – Tél : 06-000-0147
SABAKA Tania (F) – 2005-10-03 – Tél : 06-000-0148
MBALEKA Prisca (F) – 2004-12-18 – Tél : 06-000-0149

Filière : Géosciences
IBALEKA Tania Divine (F) – 2002-10-07 – Tél : 06-000-0150
NGANGOLO Grâce (F) – 2004-08-17 – Tél : 06-000-0151
MOUMBALI Zoé Josiane (F) – 2006-10-04 – Tél : 06-000-0152
EBOTOUKA Steve (M) – 2006-08-04 – Tél : 06-000-0153
BOUNDELE Christian Steve (M) – 2004-04-10 – Tél : 06-000-0154
YAVOUNA Zoé Inès (F) – 2005-07-26 – Tél : 06-000-0155
BOUKOMBO Steve Patrick (M) – 2005-08-08 – Tél : 06-000-0156
NKONGOLO Bruno Albert (M) – 2006-12-09 – Tél : 06-000-0157
OKOVOUNA Yannick (M) – 2004-12-09 – Email : etudiant158@exemple.test
EBODONGO Nadège Josiane (F) – 2004-02-07 – Tél : 06-000-0159
NGAZINGA Valentin Hervé (M) – 2005-08-03 – Tél : 06-000-0160
MAVOUNA Carine (F) – 2004-11-02 – Tél : 06-000-0161
KAKALA Alice Inès (F) – 2005-01-22 – Tél : 06-000-0162
MOUVOUNA Ruth (F) – 2005-01-25 – Tél : 06-000-0163
SANDELE Pauline Nadège (F) – 2004-01-14 – Email : etudiant164@exemple.test
BOUTANDOU Landry Patrick (M) – 2005-11-07 – Tél : 06-000-0165

Filière : Informatique
NKODONGO Daniel (M) – 2002-07-14 – Tél : 06-000-0166
KAYOKO Hélène (F) – 2005-04-08 – Tél : 06-000-0167
MBANGOLO Exaucé Serge (M) – 2004-08-16 – Tél : 06-000-0168
MALANDA Marius Ulrich (M) – 2005-01-03 – Tél : 06-000-0169
MANGOLO Wilfried (M) – 2005-08-21 – Tél : 06-000-0170
DILANDA Marius Yannick (M) – 2005-09-15 – Tél : 06-000-0171

Filière : Mathématiques
BANDELE Marius Kévin (M) – 2003-09-25 – Tél : 06-000-0172
NDOBAKA Yolande (F) – 2004-04-16 – Tél : 06-000-0173
BIYOKO Valentin Marius (M) – 2003-04-14 – Tél : 06-000-0174
MATANDOU Pauline Inès (F) – 2004-05-22 – Tél : 06-000-0175
IBANGOLO Albert (M) – 2003-10-17 – Tél : 06-000-0176
LOUVOUNA Inès Divine (F) – 2004-11-27 – Tél : 06-000-0177
MILEKA Landry (M) – 2003-11-07 – Tél : 06-000-0178

Filière : Physique
YALEKA Fabrice Zacharie (M) – 2004-01-04 – Tél : 06-000-0179
TAMBALI Rodrigue (M) – 2005-12-07 – Tél : 06-000-0180
IBASSAMBA Chloé (F) – 2006-08-23 – Tél : 06-000-0181
OKOSSAMBA Béatrice (F) – 2005-07-27 – Tél : 06-000-0182
TSIMBALI Isaac (M) – 2006-06-07 – Tél : 06-000-0183
"""


def slugify_name(text):
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    return re.sub(r'[^a-zA-Z0-9]', '', text).lower()


def flush_data():
    print("[*] Suppression des donnees existantes...")
    AffectationModule.objects.all().delete()
    Seance.objects.all().delete()
    Module.objects.all().delete()
    Matiere.objects.all().delete()
    Inscription.objects.all().delete()
    Etudiant.objects.all().delete()
    ReferentClasse.objects.all().delete()
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
    print("    Base nettoyee.\n")


def creer_utilisateur(username, first_name, last_name, email=None):
    User.objects.filter(username=username).delete()
    user = User.objects.create_user(
        username=username,
        password=SEED_PASSWORD,
        first_name=first_name,
        last_name=last_name,
        email=email if email else (username + "@uccb.cg"),
    )
    return user


def creer_enseignant(username, first_name, last_name, departement, grade='Docteur', contrat='Permanent'):
    user = creer_utilisateur(username, first_name, last_name)
    profil = ProfilFactory(user=user, genre='M', telephone='060000000')
    return Enseignant.objects.create(
        profil=profil,
        grade=grade,
        contrat=contrat,
        departement=departement,
    )


PORTAILS_L1 = ['BGC', 'MIP', 'PCG']

matricule_counter = 1


def generate_matricule():
    global matricule_counter
    mat = "ETU-" + str(matricule_counter).zfill(5)
    matricule_counter += 1
    return mat



# ═════════════════════════════════════════════════════════════════════════════
# CONSTANTES DE PLANIFICATION
# ═════════════════════════════════════════════════════════════════════════════

STATUT_CONFIRME = 'Confirmée'
STATUT_ANNULEE  = 'Annulée'
STATUT_REPORTEE = 'Reportée'

# La grille horaire vient du backend : c'est la seule source de verite
# (cf. EDT_app/validation_seance.py, aligne sur PlanningTableView.jsx).
BLOCS = list(BLOCS_JOURNEE)                      # 9h-11h, 11h15-13h15, 14h15-16h15
JOURS = list(JOURS_OUVRES)                       # lundi -> vendredi
CRENEAUX = [(j, b) for j in JOURS for b in range(len(BLOCS))]   # 15 creneaux/semaine

# Un semestre universitaire dure ~15 semaines de cours, pas 25 ou 34.
NB_SEMAINES_SEMESTRE = 15

# Date de rentree reelle de l'unique annee academique generee par ce seed.
DATE_RENTREE = date(2026, 9, 16)

# ── Roles pedagogiques d'un module ───────────────────────────────────────────
# Chaque module de chaque classe porte un role explicite (donne dans les
# curricula : MODULES_L1_PAR_PORTAIL, MODULES_L2_PAR_FILIERE,
# MODULES_L3_PAR_FILIERE), qui determine sa grille horaire :
#   (type_seance, nb_blocs_consecutifs, periodicite_semaines, occurrences, offset)
#
# `nb_blocs_consecutifs = 2` produit un cours long occupant deux blocs a la
# suite le meme jour (ex. lundi 9h00 -> 13h15), comme dans un emploi du temps reel.
# Les `offset` decalent les TD/TP d'un module a l'autre pour que chaque semaine
# reste dense au lieu d'alterner semaines pleines et semaines vides : 'standard_a'
# et 'standard_b' ne different que par cet offset, a utiliser quand un semestre a
# 2 modules 'standard' (le premier en 'standard_a', le second en 'standard_b').
#
# Un module "natal" (celui de la filiere/du departement porteur naturel) est
# 'majeur' (2 par semestre) ou 'standard_a'/'standard_b' ; un module "externe"
# (emprunte a un autre departement, volume reduit) est 'mineur_ext_2cr' ou
# 'mineur_ext_1cr'. Les volumes horaires sont TOUJOURS DEDUITS de ces roles
# (heures = blocs x occurrences x 2h), jamais l'inverse : c'est ce qui garantit
# que valider_volume_module() et valider_affectation() passent toujours.
ROLES = {
    'majeur':          [('CM', 2, 1, 12, 0), ('TD', 1, 1, 12, 0)],                    # 3 creneaux, 72h, 6cr
    'standard_a':      [('CM', 1, 1, 14, 0), ('TD', 1, 2, 7, 0), ('TP', 1, 2, 7, 1)], # 3 creneaux, 56h, 5cr
    'standard_b':      [('CM', 1, 1, 14, 0), ('TD', 1, 2, 7, 1), ('TP', 1, 2, 7, 0)], # 3 creneaux, 56h, 5cr
    'mineur_ext_2cr':  [('CM', 1, 1, 10, 0)],                                         # 1 creneau, 20h, 2cr
    'mineur_ext_1cr':  [('CM', 1, 2, 5, 0)],                                          # 1 creneau, 10h, 1cr
}


def premier_lundi(annee, mois):
    d = date(annee, mois, 1)
    while d.weekday() != 0:
        d += timedelta(days=1)
    return d


def premier_lundi_a_partir_de(d):
    """Le premier lundi a partir de la date `d` (elle-meme si deja un lundi)."""
    while d.weekday() != 0:
        d += timedelta(days=1)
    return d


def semaines_du_semestre(date_debut):
    """Les 15 lundis de cours du semestre."""
    return [date_debut + timedelta(weeks=w) for w in range(NB_SEMAINES_SEMESTRE)]


# ═════════════════════════════════════════════════════════════════════════════
# PLANIFICATEUR — alloue la grille hebdomadaire AVANT toute ecriture en base
# ═════════════════════════════════════════════════════════════════════════════

class Planificateur:
    """
    Reserve les creneaux hebdomadaires en tenant deux registres d'occupation :

      - par classe : une classe ne peut avoir qu'un cours sur un creneau donne ;
      - par (semestre, enseignant) : un enseignant ne peut pas etre dans deux
        classes au meme moment — ses seances se repetant chaque semaine, un
        conflit sur le creneau est un conflit sur tout le semestre.

    Tout est resolu ici, en memoire : aucune seance n'est ecrite puis rattrapee
    par un `except` silencieux, et `valider_conflit_*` n'a jamais rien a rejeter.
    """

    def __init__(self):
        self.occ_classe = set()        # (classe_pk, jour, bloc)
        self.occ_ens = set()           # (semestre_pk, enseignant_pk, jour, bloc)
        self.charge_ens = {}           # enseignant_pk -> nb de creneaux hebdo

    def _charge_jour(self, classe, jour):
        return sum(1 for b in range(len(BLOCS)) if (classe.pk, jour, b) in self.occ_classe)

    def _creneaux_candidats(self, classe, nb_blocs):
        """
        Suites de `nb_blocs` blocs consecutifs libres pour la classe, les jours
        les moins charges d'abord. Sans cet equilibrage, l'allocation remplit
        lundi -> jeudi et laisse le vendredi vide dans tous les emplois du temps.
        """
        candidats = []
        for jour in JOURS:
            for bloc in range(len(BLOCS) - nb_blocs + 1):
                suite = [(jour, bloc + k) for k in range(nb_blocs)]
                if all((classe.pk, j, b) not in self.occ_classe for j, b in suite):
                    candidats.append(suite)
        candidats.sort(key=lambda suite: (self._charge_jour(classe, suite[0][0]), suite))
        return candidats

    def reserver(self, classe, semestre, enseignants, nb_blocs):
        """
        Choisit une suite de creneaux libre pour la classe ET un enseignant du
        vivier libre sur toute la suite. Renvoie (enseignant, suite), ou
        (None, None) si la capacite est saturee.
        """
        candidats = self._creneaux_candidats(classe, nb_blocs)
        # Vivier trie par charge croissante : la charge se repartit d'elle-meme
        # entre le chef et les autres enseignants du departement.
        vivier = sorted(enseignants, key=lambda e: (self.charge_ens.get(e.pk, 0), e.pk))

        for suite in candidats:
            for ens in vivier:
                if all((semestre.pk, ens.pk, j, b) not in self.occ_ens for j, b in suite):
                    for j, b in suite:
                        self.occ_classe.add((classe.pk, j, b))
                        self.occ_ens.add((semestre.pk, ens.pk, j, b))
                    self.charge_ens[ens.pk] = self.charge_ens.get(ens.pk, 0) + nb_blocs
                    return ens, suite
        return None, None

    def creneau_commun(self, classes, semestre, enseignant):
        """Premier creneau libre simultanement pour toutes les classes et l'enseignant."""
        for jour, bloc in CRENEAUX:
            if any((c.pk, jour, bloc) in self.occ_classe for c in classes):
                continue
            if (semestre.pk, enseignant.pk, jour, bloc) in self.occ_ens:
                continue
            for c in classes:
                self.occ_classe.add((c.pk, jour, bloc))
            self.occ_ens.add((semestre.pk, enseignant.pk, jour, bloc))
            return jour, bloc
        return None, None


# ═════════════════════════════════════════════════════════════════════════════
# CURRICULA — par filiere/portail, par niveau et par semestre
# ═════════════════════════════════════════════════════════════════════════════
#
# Chaque entree est (libelle, departement_porteur, role, semestre). Un module
# "natal" (celui de la filiere/du departement porteur naturel) est 'majeur'
# (exactement 2 par semestre) ou 'standard_a'/'standard_b' (le reste) ; un
# module "externe" (emprunte a un autre departement, volume reduit) est
# 'mineur_ext_2cr' ou 'mineur_ext_1cr'. Cf. ROLES pour le detail des volumes.

MODULES_L2_PAR_FILIERE = {
    'Biologie': [
        ('Biologie Cellulaire et Moléculaire', 'Biologie', 'majeur', 'S1'),
        ('Zoologie Générale', 'Biologie', 'majeur', 'S1'),
        ('Anatomie Végétale', 'Biologie', 'standard_a', 'S1'),
        ('Statistiques Biologiques', 'Mathématiques', 'mineur_ext_2cr', 'S1'),
        ('Biochimie Structurale', 'Chimie', 'mineur_ext_1cr', 'S1'),
        ('Génétique Classique', 'Biologie', 'majeur', 'S2'),
        ('Physiologie Animale', 'Biologie', 'majeur', 'S2'),
        ('Microbiologie Générale', 'Biologie', 'standard_a', 'S2'),
        ('Écologie Fondamentale', 'Biologie', 'standard_b', 'S2'),
        ('Bioinformatique', 'Informatique', 'mineur_ext_2cr', 'S2'),
    ],
    'Chimie': [
        ('Chimie Organique I', 'Chimie', 'majeur', 'S1'),
        ('Chimie du Solide', 'Chimie', 'majeur', 'S1'),
        ('Thermodynamique Chimique', 'Chimie', 'standard_a', 'S1'),
        ('Chimie Analytique', 'Chimie', 'standard_b', 'S1'),
        ('Mathématiques pour Chimistes', 'Mathématiques', 'mineur_ext_2cr', 'S1'),
        ('Cinétique Chimique', 'Chimie', 'majeur', 'S2'),
        ('Chimie Minérale', 'Chimie', 'majeur', 'S2'),
        ('Chimie des Solutions', 'Chimie', 'standard_a', 'S2'),
        ('Travaux Pratiques de Synthèse', 'Chimie', 'standard_b', 'S2'),
        ('Spectroscopie', 'Physique', 'mineur_ext_2cr', 'S2'),
    ],
    'Géosciences': [
        ('Géologie Générale', 'Géosciences', 'majeur', 'S1'),
        ('Sédimentologie', 'Géosciences', 'majeur', 'S1'),
        ('Cartographie et Topographie', 'Géosciences', 'standard_a', 'S1'),
        ('Mathématiques Appliquées', 'Mathématiques', 'mineur_ext_2cr', 'S1'),
        ('Cristallographie', 'Chimie', 'mineur_ext_1cr', 'S1'),
        ('Minéralogie', 'Géosciences', 'majeur', 'S2'),
        ('Pétrographie', 'Géosciences', 'majeur', 'S2'),
        ('Stratigraphie', 'Géosciences', 'standard_a', 'S2'),
        ('Télédétection', 'Géosciences', 'standard_b', 'S2'),
        ('Géochimie', 'Chimie', 'mineur_ext_2cr', 'S2'),
    ],
    'Informatique': [
        ('Algorithmique et Structures de Données', 'Informatique', 'majeur', 'S1'),
        ('Programmation en C', 'Informatique', 'majeur', 'S1'),
        ('Architecture des Ordinateurs', 'Informatique', 'standard_a', 'S1'),
        ('Théorie des Graphes', 'Informatique', 'standard_b', 'S1'),
        ('Mathématiques Discrètes', 'Mathématiques', 'mineur_ext_2cr', 'S1'),
        ('Programmation Orientée Objet', 'Informatique', 'majeur', 'S2'),
        ('Bases de Données Relationnelles', 'Informatique', 'majeur', 'S2'),
        ('Réseaux Informatiques', 'Informatique', 'standard_a', 'S2'),
        ("Systèmes d'Exploitation", 'Informatique', 'standard_b', 'S2'),
        ('Probabilités et Statistiques', 'Mathématiques', 'mineur_ext_2cr', 'S2'),
    ],
    'Mathématiques': [
        ('Algèbre Linéaire et Bilinéaire', 'Mathématiques', 'majeur', 'S1'),
        ('Analyse Réelle', 'Mathématiques', 'majeur', 'S1'),
        ('Probabilités', 'Mathématiques', 'standard_a', 'S1'),
        ('Structures Algébriques', 'Mathématiques', 'standard_b', 'S1'),
        ("Introduction à l'Algorithmique", 'Informatique', 'mineur_ext_2cr', 'S1'),
        ('Analyse Complexe', 'Mathématiques', 'majeur', 'S2'),
        ('Topologie Générale', 'Mathématiques', 'majeur', 'S2'),
        ('Statistique Inférentielle', 'Mathématiques', 'standard_a', 'S2'),
        ('Géométrie Différentielle', 'Mathématiques', 'standard_b', 'S2'),
        ('Programmation Scientifique', 'Informatique', 'mineur_ext_2cr', 'S2'),
    ],
    'Physique': [
        ('Mécanique du Point et du Solide', 'Physique', 'majeur', 'S1'),
        ('Électrocinétique', 'Physique', 'majeur', 'S1'),
        ('Optique Géométrique', 'Physique', 'standard_a', 'S1'),
        ('Mathématiques pour Physiciens', 'Mathématiques', 'mineur_ext_2cr', 'S1'),
        ('Informatique Scientifique', 'Informatique', 'mineur_ext_1cr', 'S1'),
        ('Électromagnétisme', 'Physique', 'majeur', 'S2'),
        ('Mécanique Quantique I', 'Physique', 'majeur', 'S2'),
        ('Thermodynamique Physique', 'Physique', 'standard_a', 'S2'),
        ('Physique Numérique', 'Physique', 'standard_b', 'S2'),
    ],
}

MODULES_L3_PAR_FILIERE = {
    'Biologie': [
        ('Biologie Moléculaire Avancée', 'Biologie', 'majeur', 'S1'),
        ('Immunologie', 'Biologie', 'majeur', 'S1'),
        ('Endocrinologie', 'Biologie', 'standard_a', 'S1'),
        ('Parasitologie', 'Biologie', 'standard_b', 'S1'),
        ('Biostatistiques Appliquées', 'Mathématiques', 'mineur_ext_2cr', 'S1'),
        ('Biotechnologies', 'Biologie', 'majeur', 'S2'),
        ('Génie Génétique', 'Biologie', 'majeur', 'S2'),
        ('Physiologie Comparée', 'Biologie', 'standard_a', 'S2'),
        ('Écologie des Populations', 'Biologie', 'standard_b', 'S2'),
        ('Analyse de Données Biologiques', 'Informatique', 'mineur_ext_1cr', 'S2'),
    ],
    'Chimie': [
        ('Chimie Organique II', 'Chimie', 'majeur', 'S1'),
        ('Génie Chimique', 'Chimie', 'majeur', 'S1'),
        ('Chimie de Coordination', 'Chimie', 'standard_a', 'S1'),
        ('Chimie Quantique', 'Physique', 'mineur_ext_2cr', 'S1'),
        ('Outils Informatiques pour la Chimie', 'Informatique', 'mineur_ext_1cr', 'S1'),
        ('Catalyse', 'Chimie', 'majeur', 'S2'),
        ('Chimie Industrielle', 'Chimie', 'majeur', 'S2'),
        ('Chimie des Polymères', 'Chimie', 'standard_a', 'S2'),
        ("Chimie de l'Environnement", 'Chimie', 'standard_b', 'S2'),
        ('Électrochimie', 'Physique', 'mineur_ext_2cr', 'S2'),
    ],
    'Géosciences': [
        ('Géologie Structurale', 'Géosciences', 'majeur', 'S1'),
        ('Volcanologie', 'Géosciences', 'majeur', 'S1'),
        ('Hydrogéologie', 'Géosciences', 'standard_a', 'S1'),
        ('Géomorphologie', 'Géosciences', 'standard_b', 'S1'),
        ('Géostatistique', 'Mathématiques', 'mineur_ext_2cr', 'S1'),
        ('Géophysique', 'Géosciences', 'majeur', 'S2'),
        ('Ressources Minières', 'Géosciences', 'majeur', 'S2'),
        ('Paléontologie', 'Géosciences', 'standard_a', 'S2'),
        ('Géologie Appliquée', 'Géosciences', 'standard_b', 'S2'),
        ("Systèmes d'Information Géographique", 'Informatique', 'mineur_ext_2cr', 'S2'),
    ],
    'Informatique': [
        ('Génie Logiciel', 'Informatique', 'majeur', 'S1'),
        ('Intelligence Artificielle', 'Informatique', 'majeur', 'S1'),
        ('Sécurité Informatique', 'Informatique', 'standard_a', 'S1'),
        ('Compilation', 'Informatique', 'standard_b', 'S1'),
        ('Développement Web Avancé', 'Informatique', 'majeur', 'S2'),
        ('Systèmes Distribués', 'Informatique', 'majeur', 'S2'),
        ('Apprentissage Automatique', 'Informatique', 'standard_a', 'S2'),
        ("Projet de Fin d'Études", 'Informatique', 'standard_b', 'S2'),
    ],
    'Mathématiques': [
        ('Analyse Fonctionnelle', 'Mathématiques', 'majeur', 'S1'),
        ('Équations Différentielles', 'Mathématiques', 'majeur', 'S1'),
        ('Théorie de la Mesure', 'Mathématiques', 'standard_a', 'S1'),
        ('Optimisation', 'Mathématiques', 'standard_b', 'S1'),
        ('Calcul Scientifique', 'Informatique', 'mineur_ext_2cr', 'S1'),
        ('Algèbre Avancée', 'Mathématiques', 'majeur', 'S2'),
        ('Processus Stochastiques', 'Mathématiques', 'majeur', 'S2'),
        ('Analyse Numérique', 'Mathématiques', 'standard_a', 'S2'),
        ('Mémoire de Recherche', 'Mathématiques', 'standard_b', 'S2'),
    ],
    'Physique': [
        ('Mécanique Quantique II', 'Physique', 'majeur', 'S1'),
        ('Physique du Solide', 'Physique', 'majeur', 'S1'),
        ('Astrophysique', 'Physique', 'standard_a', 'S1'),
        ('Physique Statistique', 'Physique', 'standard_b', 'S1'),
        ('Méthodes Numériques', 'Mathématiques', 'mineur_ext_2cr', 'S1'),
        ('Physique Nucléaire', 'Physique', 'majeur', 'S2'),
        ('Relativité Restreinte', 'Physique', 'majeur', 'S2'),
        ('Physique des Matériaux', 'Physique', 'standard_a', 'S2'),
        ('Physique Théorique', 'Physique', 'standard_b', 'S2'),
        ('Instrumentation et Mesures', 'Informatique', 'mineur_ext_2cr', 'S2'),
    ],
}

# L1 : chaque portail (BGC / MIP / PCG) a desormais son propre programme.
# BGC et PCG partagent Chimie/Geosciences (module natal commun) mais avec un
# equilibre majeur/standard et un 4e module differents ; MIP est structure
# autour de Mathematiques/Informatique/Physique, aucun module Biologie ou
# Geosciences n'y figure en majeur/standard.
MODULES_L1_PAR_PORTAIL = {
    'BGC': [
        ('Biologie Générale', 'Biologie', 'majeur', 'S1'),
        ('Géosciences Introductives', 'Géosciences', 'majeur', 'S1'),
        ('Chimie Générale', 'Chimie', 'standard_a', 'S1'),
        ('Zoologie et Botanique', 'Biologie', 'standard_b', 'S1'),
        ('Mathématiques Générales', 'Mathématiques', 'mineur_ext_2cr', 'S1'),
        ('Biologie Cellulaire Intro', 'Biologie', 'majeur', 'S2'),
        ('Géologie Introductive', 'Géosciences', 'majeur', 'S2'),
        ('Chimie Appliquée', 'Chimie', 'standard_a', 'S2'),
        ('Écologie Générale', 'Biologie', 'standard_b', 'S2'),
        ('Statistiques Descriptives', 'Mathématiques', 'mineur_ext_2cr', 'S2'),
    ],
    'MIP': [
        ('Mathématiques Générales', 'Mathématiques', 'majeur', 'S1'),
        ('Physique Générale', 'Physique', 'majeur', 'S1'),
        ('Algorithmique et Programmation', 'Informatique', 'standard_a', 'S1'),
        ('Électricité et Électronique', 'Physique', 'standard_b', 'S1'),
        ('Chimie Générale', 'Chimie', 'mineur_ext_2cr', 'S1'),
        ('Analyse et Algèbre Linéaire', 'Mathématiques', 'majeur', 'S2'),
        ('Informatique Générale', 'Informatique', 'majeur', 'S2'),
        ('Mécanique Générale', 'Physique', 'standard_a', 'S2'),
        ('Probabilités et Statistiques', 'Mathématiques', 'standard_b', 'S2'),
        ('Biologie Générale', 'Biologie', 'mineur_ext_2cr', 'S2'),
    ],
    'PCG': [
        ('Chimie Générale', 'Chimie', 'majeur', 'S1'),
        ('Physique Générale', 'Physique', 'majeur', 'S1'),
        ('Géosciences Introductives', 'Géosciences', 'standard_a', 'S1'),
        ('Techniques de Laboratoire', 'Chimie', 'standard_b', 'S1'),
        ('Mathématiques Générales', 'Mathématiques', 'mineur_ext_2cr', 'S1'),
        ('Chimie Appliquée', 'Chimie', 'majeur', 'S2'),
        ('Physique Appliquée', 'Physique', 'majeur', 'S2'),
        ('Géologie Introductive', 'Géosciences', 'standard_a', 'S2'),
        ('Thermodynamique Élémentaire', 'Physique', 'standard_b', 'S2'),
        ('Biologie Générale', 'Biologie', 'mineur_ext_2cr', 'S2'),
    ],
}

# ── Departement transversal (langues, methodologie, insertion professionnelle) ──
# Pas de chef : Departement.chef est facultatif, et un "chef de departement
# d'anglais" n'aurait pas de sens academique. Un seul module transversal de
# plus par classe et par semestre, EN PLUS du curriculum disciplinaire
# ci-dessus (pas de substitution) — cf. construire_semestre().
DEPT_TRANSVERSAL = 'Transversal'
MODULE_TRANSVERSAL = {
    ('L1', 'S1'): ('Méthodologie du Travail Universitaire', 'mineur_ext_1cr'),
    ('L1', 'S2'): ('Anglais', 'mineur_ext_1cr'),
    ('L2', 'S1'): ('Anglais', 'mineur_ext_2cr'),
    ('L2', 'S2'): ('Anglais', 'mineur_ext_2cr'),
    ('L3', 'S1'): ('Anglais', 'mineur_ext_2cr'),
    ('L3', 'S2'): ('Entrepreneuriat et Insertion Professionnelle', 'mineur_ext_2cr'),
}


# ═════════════════════════════════════════════════════════════════════════════
# CONSTRUCTION D'UN SEMESTRE
# ═════════════════════════════════════════════════════════════════════════════

def _creer_module_et_seances(classe, libelle, dept_nom, role, matiere_de, enseignants_de,
                             planif, lundis, seances_buffer, stats, tag):
    """
    Reserve les creneaux du `role` donne (cf. ROLES), cree le Module, ses
    AffectationModule typees CM/TD/TP et toutes ses Seance de la grille
    hebdomadaire. Partage par construire_semestre() (modules disciplinaires)
    et l'ajout systematique du module transversal (Anglais, Methodologie...).
    Renvoie le Module cree, ou None si aucun creneau n'a pu etre reserve.
    """
    semestre = classe.semestre
    vivier = enseignants_de[dept_nom]
    matiere = matiere_de[dept_nom]
    besoins = ROLES[role]

    # 1. Reserver les creneaux et l'enseignant de chaque type de seance.
    planning = []   # [(type_seance, enseignant, [(jour, bloc), ...], periodicite, occurrences, offset)]
    heures = {'CM': 0, 'TD': 0, 'TP': 0}
    for type_seance, nb_blocs, periodicite, occurrences, offset in besoins:
        ens, suite = planif.reserver(classe, semestre, vivier, nb_blocs)
        if ens is None:
            stats['creneaux_introuvables'] += 1
            continue
        planning.append((type_seance, ens, suite, periodicite, occurrences, offset))
        heures[type_seance] += nb_blocs * occurrences * 2

    if not planning:
        return None

    # 2. Volume et credits DEDUITS du role (1 credit = 12h).
    total = sum(heures.values())
    credits = max(1, min(6, -(-total // 12)))

    module = Module.objects.create(
        libelle=libelle,
        matiere=matiere,
        semestre=semestre,
        classe=classe,
        credits=credits,
        description=f"{libelle} — {classe.libelle} ({tag}).",
        heures_cm=heures['CM'],
        heures_td=heures['TD'],
        heures_tp=heures['TP'],
    )
    stats['modules'] += 1

    # 3. Une affectation typee par type de seance : CM, TD et TP sont
    #    portes par des enseignants distincts du meme departement.
    for type_seance, ens, _suite, _p, _o, _off in planning:
        AffectationModule.objects.create(
            module=module,
            enseignant=ens,
            type_seance=type_seance,
            heures_prevues=float(heures[type_seance]),
        )
        stats['affectations'] += 1

    # 4. Seances : la meme case chaque semaine, jusqu'a epuisement du quota.
    for type_seance, ens, suite, periodicite, occurrences, offset in planning:
        for n in range(occurrences):
            semaine = offset + n * periodicite
            if semaine >= len(lundis):
                break
            for jour, bloc in suite:
                heure_debut, heure_fin = BLOCS[bloc]
                seances_buffer.append(Seance(
                    libelle=f"{type_seance} — {libelle}",
                    module=module,
                    enseignant=ens,
                    classe=classe,
                    annee=classe.annee,
                    date_seance=lundis[semaine] + timedelta(days=jour),
                    heure_debut=heure_debut,
                    heure_fin=heure_fin,
                    type_seance=type_seance,
                    statut=STATUT_CONFIRME,
                ))
                stats['seances'] += 1

    return module


def construire_semestre(classe, curriculum, matiere_de, enseignants_de,
                        planif, seances_buffer, stats):
    """
    Cree les modules disciplinaires d'une classe pour un semestre a partir de
    `curriculum`, plus systematiquement un module transversal (Anglais,
    Methodologie du Travail Universitaire, Entrepreneuriat...).

    `curriculum` : liste de tuples (libelle, departement_porteur, role). Le
    `role` (cf. ROLES) determine le volume horaire et donc les credits du
    module, independamment du departement qui le porte : un module "natal"
    est 'majeur'/'standard_a'/'standard_b', un module "externe" (emprunte a
    un autre departement) est 'mineur_ext_2cr'/'mineur_ext_1cr'.
    """
    semestre = classe.semestre
    lundis = semaines_du_semestre(premier_lundi_a_partir_de(semestre.date_debut))

    for libelle, dept_nom, role in curriculum:
        _creer_module_et_seances(classe, libelle, dept_nom, role, matiere_de,
                                 enseignants_de, planif, lundis, seances_buffer,
                                 stats, tag=role)

    # Module transversal : un de plus par classe et par semestre, en plus du
    # curriculum disciplinaire (pas de substitution), identique pour toutes
    # les filieres/portails d'un meme niveau.
    niveau = f'L{classe.parcours.niveau}'
    sem = 'S1' if semestre.libelle == 'Semestre 1' else 'S2'
    libelle_t, role_t = MODULE_TRANSVERSAL[(niveau, sem)]
    _creer_module_et_seances(classe, libelle_t, DEPT_TRANSVERSAL, role_t, matiere_de,
                             enseignants_de, planif, lundis, seances_buffer,
                             stats, tag='transversal')


def creer_annee_complete(year_start, deps_names, filieres, parcours,
                         enseignants_de, matiere_de, niveaux, stats):
    """
    Construit l'unique annee academique : semestres, classes des `niveaux`
    demandes, modules, affectations et emplois du temps complets.
    """
    # 15 semaines de cours par semestre : S1 a la rentree reelle (DATE_RENTREE),
    # S2 en fevrier. La grille hebdomadaire s'ancre sur le premier lundi a
    # partir de la date de debut du semestre (construire_semestre) : inutile
    # de le faire ici aussi, sauf pour calculer la date de fin du semestre 1.
    debut_s1 = DATE_RENTREE
    debut_s2 = premier_lundi(year_start + 1, 2)
    ancre_s1 = premier_lundi_a_partir_de(debut_s1)

    annee = AnneeAcademique.objects.create(
        libelle=f"{year_start}-{year_start + 1}",
        date_debut=min(date(year_start, 9, 1), debut_s1),
        date_fin=date(year_start + 1, 8, 31),
        statut='active',
    )

    semestre1 = Semestre.objects.create(
        libelle='Semestre 1',
        date_debut=debut_s1,
        date_fin=ancre_s1 + timedelta(weeks=NB_SEMAINES_SEMESTRE) - timedelta(days=3),
        annee=annee,
    )
    semestre2 = Semestre.objects.create(
        libelle='Semestre 2',
        date_debut=debut_s2,
        date_fin=debut_s2 + timedelta(weeks=NB_SEMAINES_SEMESTRE) - timedelta(days=3),
        annee=annee,
    )
    semestres = {'S1': semestre1, 'S2': semestre2}

    classes = {'L1': {'S1': {}, 'S2': {}},
               'L2': {'S1': {}, 'S2': {}},
               'L3': {'S1': {}, 'S2': {}}}

    if 'L1' in niveaux:
        for code in PORTAILS_L1:
            for sem in ('S1', 'S2'):
                classes['L1'][sem][code] = Classe.objects.create(
                    parcours=parcours['L1'], semestre=semestres[sem], annee=annee, code=code)
    for niveau in ('L2', 'L3'):
        if niveau not in niveaux:
            continue
        for f_name, f_obj in filieres.items():
            for sem in ('S1', 'S2'):
                classes[niveau][sem][f_name] = Classe.objects.create(
                    parcours=parcours[niveau], semestre=semestres[sem],
                    annee=annee, filiere=f_obj)

    planif = Planificateur()
    seances_buffer = []

    # ── L2 / L3 : curriculum porte par le departement precise pour chaque
    #    module (le plus souvent celui de la filiere, mais certains modules
    #    sont empruntes a un autre departement quand c'est pertinent — ex.
    #    "Statistiques Biologiques" est porte par Mathematiques, pas Biologie).
    for niveau, table in (('L2', MODULES_L2_PAR_FILIERE), ('L3', MODULES_L3_PAR_FILIERE)):
        if niveau not in niveaux:
            continue
        for f_name in deps_names:
            for sem in ('S1', 'S2'):
                curriculum = [(lib, dept, role) for (lib, dept, role, s) in table[f_name] if s == sem]
                construire_semestre(
                    classes[niveau][sem][f_name], curriculum,
                    matiere_de, enseignants_de, planif, seances_buffer, stats,
                )

    # ── L1 : chaque portail a son propre programme (MODULES_L1_PAR_PORTAIL) ──
    if 'L1' in niveaux:
        for sem in ('S1', 'S2'):
            for code in PORTAILS_L1:
                curriculum = [
                    (lib, dept, role)
                    for (lib, dept, role, s) in MODULES_L1_PAR_PORTAIL[code] if s == sem
                ]
                construire_semestre(
                    classes['L1'][sem][code], curriculum,
                    matiere_de, enseignants_de, planif, seances_buffer, stats,
                )

    Seance.objects.bulk_create(seances_buffer, batch_size=500)

    return {'annee': annee, 'semestres': semestres, 'classes': classes,
            'planif': planif}


# ═════════════════════════════════════════════════════════════════════════════
# ETUDIANTS
# ═════════════════════════════════════════════════════════════════════════════

def parser_etudiants():
    """
    Lit RAW_STUDENTS et renvoie [{niveau, groupe, first_name, last_name,
    genre, phone, email}] sans rien ecrire en base.
    """
    etudiants = []
    niveau = None
    groupe = None

    for line in RAW_STUDENTS.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        if line.startswith('1. Niveau L1'):
            niveau = 'L1'
            continue
        if line.startswith('2. Niveau L2'):
            niveau = 'L2'
            continue
        if line.startswith('3. Niveau L3'):
            niveau = 'L3'
            continue
        if line.startswith('Portail :') or line.startswith('Filière :'):
            groupe = line.split(' : ')[1].strip()
            continue
        if not niveau or not groupe:
            continue

        parts = line.split(' – ')
        name_genre = parts[0].strip()
        genre = 'F' if '(F)' in name_genre else 'M'
        name_part = name_genre.replace('(F)', '').replace('(M)', '').strip()
        tokens = name_part.split(' ')
        last_name = tokens[0]
        first_name = ' '.join(tokens[1:]) if len(tokens) > 1 else last_name

        contact = ' '.join(parts[2:]) if len(parts) > 2 else ''
        if len(parts) == 2 and 'Tél' in parts[1]:
            contact = parts[1]

        phone = ''
        email = ''
        m = re.search(r'Tél\s*:\s*([\d-]+)', contact)
        if m:
            phone = m.group(1).replace('-', '')
        m = re.search(r'Email\s*:\s*([^\s]+)', contact)
        if m:
            email = m.group(1)

        etudiants.append({
            'niveau': niveau, 'groupe': groupe,
            'first_name': first_name, 'last_name': last_name,
            'genre': genre, 'phone': phone, 'email': email,
        })
    return etudiants


def classe_pour(donnees_annee, niveau, groupe, sem):
    """Classe d'un niveau/groupe pour un semestre, ou None si non generee."""
    table = donnees_annee['classes'].get(niveau, {}).get(sem, {})
    if niveau == 'L1':
        return table.get(groupe)
    return table.get(groupe if groupe in table else 'Informatique')


# ═════════════════════════════════════════════════════════════════════════════
# EXECUTION
# ═════════════════════════════════════════════════════════════════════════════

random.seed(42)
flush_data()

print("[*] Faculte, departements et filieres...")
faculte = FaculteFactory(libelle='Faculté des Sciences et Technologie')

deps_names = ['Biologie', 'Chimie', 'Géosciences', 'Informatique', 'Mathématiques', 'Physique']
deps = {n: DepartementFactory(libelle='Département ' + n, faculte=faculte) for n in deps_names}
filieres = {n: FiliereFactory(libelle=n, departement=deps[n]) for n in deps_names}

print("[*] Parcours...")
parcours = {
    'L1': ParcoursFactory(type_parcours='Licence', niveau=1),
    'L2': ParcoursFactory(type_parcours='Licence', niveau=2),
    'L3': ParcoursFactory(type_parcours='Licence', niveau=3),
}

print("[*] Enseignants (4 par departement) et matieres...")
enseignants_de = {}
matiere_de = {}
for f_name, dept in deps.items():
    slug = slugify_name(f_name)
    chef = creer_enseignant('chef.' + slug, 'Chef', 'Prof' + f_name, dept,
                            grade='Professeur', contrat='Permanent')
    dept.chef = chef
    dept.save()
    filieres[f_name].responsable = chef
    filieres[f_name].save()

    enseignants_de[f_name] = [
        chef,
        creer_enseignant('ens2.' + slug, 'Alice', 'Prof' + f_name, dept,
                         grade='Docteur', contrat='Permanent'),
        creer_enseignant('ens3.' + slug, 'Bob', 'Prof' + f_name, dept,
                         grade='Docteur', contrat='Permanent'),
        creer_enseignant('ens4.' + slug, 'Claude', 'Prof' + f_name, dept,
                         grade='Ingénieur', contrat='Vacataire'),
    ]
    matiere_de[f_name] = MatiereFactory(
        libelle='Matières Fondamentales ' + f_name, departement=dept)

print("[*] Service commun des langues et competences transversales...")
dept_transversal = DepartementFactory(
    libelle='Service Commun des Langues et Compétences Transversales', faculte=faculte)
matiere_de[DEPT_TRANSVERSAL] = MatiereFactory(
    libelle='Compétences Transversales et Langues', departement=dept_transversal)
enseignants_de[DEPT_TRANSVERSAL] = [
    creer_enseignant('langues1', 'Aline', 'ProfLangues', dept_transversal,
                     grade='Docteur', contrat='Vacataire'),
    creer_enseignant('langues2', 'Boris', 'ProfLangues', dept_transversal,
                     grade='Docteur', contrat='Vacataire'),
    creer_enseignant('langues3', 'Chantal', 'ProfLangues', dept_transversal,
                     grade='Ingénieur', contrat='Vacataire'),
    creer_enseignant('langues4', 'Dorian', 'ProfLangues', dept_transversal,
                     grade='Ingénieur', contrat='Vacataire'),
    creer_enseignant('langues5', 'Estelle', 'ProfLangues', dept_transversal,
                     grade='Docteur', contrat='Vacataire'),
    creer_enseignant('langues6', 'Fabrice', 'ProfLangues', dept_transversal,
                     grade='Ingénieur', contrat='Vacataire'),
]
# Un module transversal (Anglais, Methodologie, Entrepreneuriat) est du a
# CHAQUE classe du niveau, chaque semestre : ~15 classes/semestre pour un
# seul creneau chacune, un vivier de 3 enseignants suffirait en theorie
# (3 x 15 creneaux = 45 disponibilites) mais les classes les plus chargees
# (L1, certaines L3) n'ont plus qu'1-2 creneaux libres au moment ou leur tour
# vient — 5 enseignants donnent assez de marge pour qu'un des cinq soit
# toujours libre sur le peu de creneaux qui restent.

stats = {
    'modules': 0, 'affectations': 0, 'seances': 0,
    'creneaux_introuvables': 0, 'annulees': 0, 'reportees': 0,
    'inscriptions': 0,
}

today = date.today()
year_start = DATE_RENTREE.year

print(f"[*] Annee academique {year_start}-{year_start + 1} (L1, L2, L3)...")
with transaction.atomic():
    annee_n = creer_annee_complete(
        year_start, deps_names, filieres, parcours, enseignants_de, matiere_de,
        niveaux=('L1', 'L2', 'L3'), stats=stats,
    )

# ── Referent L1 : coordinateur des 3 portails (BGC, MIP, PCG) ────────────────
# Cas d'usage principal de ReferentClasse (cf. modele) : un enseignant qui gere
# l'emploi du temps des classes L1 sans en diriger le departement.
print("[*] Referent L1 (coordinateur des 3 portails)...")
referent_l1 = creer_enseignant('referent.l1', 'Referent', 'CoordinateurL1',
                               deps['Informatique'], grade='Docteur', contrat='Permanent')
referent_classe = ReferentClasse.objects.create(enseignant=referent_l1)
referent_classe.classes.set([
    annee_n['classes']['L1'][sem][code]
    for sem in ('S1', 'S2') for code in PORTAILS_L1
])

# ── Seance mutualisee : un seminaire commun a deux classes L3 ────────────────
print("[*] Seance mutualisee entre L3 Informatique et L3 Physique...")
try:
    sem2 = annee_n['semestres']['S2']
    classe_a = annee_n['classes']['L3']['S2']['Informatique']
    classe_b = annee_n['classes']['L3']['S2']['Physique']
    ens_seminaire = enseignants_de['Informatique'][3]   # le vacataire

    jour, bloc = annee_n['planif'].creneau_commun([classe_a, classe_b], sem2, ens_seminaire)
    if jour is None:
        raise RuntimeError("aucun creneau commun libre")

    heure_debut, heure_fin = BLOCS[bloc]
    module_seminaire = Module.objects.create(
        libelle='Séminaire Scientifique Interdisciplinaire',
        matiere=matiere_de['Informatique'],
        semestre=sem2,
        classe=classe_a,
        credits=2,
        description='Module électif mutualisé entre L3 Informatique et L3 Physique.',
        heures_cm=24, heures_td=0, heures_tp=0,
    )
    AffectationModule.objects.create(
        module=module_seminaire, enseignant=ens_seminaire,
        type_seance='CM', heures_prevues=24.0,
    )
    lundis = semaines_du_semestre(premier_lundi_a_partir_de(sem2.date_debut))
    for n in range(6):   # 6 seances x 2 classes x 2h = 24h, le quota du module
        d = lundis[n] + timedelta(days=jour)
        seance_a = Seance.objects.create(
            libelle='CM — Séminaire Scientifique Interdisciplinaire',
            module=module_seminaire, enseignant=ens_seminaire, classe=classe_a,
            annee=annee_n['annee'], date_seance=d,
            heure_debut=heure_debut, heure_fin=heure_fin,
            type_seance='CM', statut=STATUT_CONFIRME,
        )
        Seance.objects.create(
            libelle='CM — Séminaire Scientifique Interdisciplinaire',
            module=module_seminaire, enseignant=ens_seminaire, classe=classe_b,
            annee=annee_n['annee'], date_seance=d,
            heure_debut=heure_debut, heure_fin=heure_fin,
            type_seance='CM', statut=STATUT_CONFIRME,
            seance_liee=seance_a,
        )
        stats['seances'] += 2
except Exception as exc:
    print("    [!] Seance mutualisee non creee :", exc)

# ── Cas limites : annulations et reports ─────────────────────────────────────
# Avec une rentree reelle (DATE_RENTREE), l'annee generee est presque toujours
# entierement a venir par rapport a la date du jour : ne choisir que des
# seances DEJA PASSEES (comme le faisait l'ancien modele avec son decalage de
# demo) ne trouverait quasiment jamais rien. Une annulation ou un report est
# tout aussi realiste sur une seance a venir (un enseignant indisponible la
# semaine prochaine, une salle a liberer...) : on tire donc parmi toutes les
# seances confirmees de l'annee, passees ou futures.
print("[*] Annulations et reports (cas limites du moteur de validation)...")
passees = list(
    Seance.objects.filter(annee=annee_n['annee'], statut=STATUT_CONFIRME)
    .order_by('pk')[:400]
)
random.shuffle(passees)
for i, seance in enumerate(passees[:30]):
    if i % 2 == 0:
        seance.statut = STATUT_ANNULEE
        try:
            seance.save()
            stats['annulees'] += 1
        except Exception:
            pass
    else:
        semestre = seance.classe.semestre
        for offset in (7, 14, 21, -7, -14):
            report = seance.date_seance + timedelta(days=offset)
            if not (semestre.date_debut <= report <= semestre.date_fin):
                continue
            seance.statut = STATUT_REPORTEE
            seance.date_report = report
            seance.heure_debut_report = seance.heure_debut
            seance.heure_fin_report = seance.heure_fin
            try:
                seance.save()
                stats['reportees'] += 1
                break
            except Exception:
                continue

# ── Etudiants et inscriptions ───────────────────────────────────────────────
print("[*] Etudiants, rattachement S1 + S2 et historique d'inscriptions...")

# Le pointeur Etudiant.classe designe la classe du semestre en cours ;
# l'historique complet (S1, S2, annee precedente) vit dans Inscription.
sem_courant = 'S1'
for code in ('S1', 'S2'):
    s = annee_n['semestres'][code]
    if s.date_debut <= today <= s.date_fin:
        sem_courant = code
        break
else:
    if today > annee_n['semestres']['S2'].date_fin:
        sem_courant = 'S2'

used_usernames = set()
for donnees in parser_etudiants():
    niveau, groupe = donnees['niveau'], donnees['groupe']

    classes_n = {sem: classe_pour(annee_n, niveau, groupe, sem) for sem in ('S1', 'S2')}
    if not classes_n[sem_courant]:
        continue

    fn = slugify_name(donnees['first_name'])[:15]
    ln = slugify_name(donnees['last_name'])[:15]
    base = f"{fn}.{ln}"
    username = base
    i = 1
    while username in used_usernames:
        username = base + str(i)
        i += 1
    used_usernames.add(username)

    user = creer_utilisateur(username, donnees['first_name'], donnees['last_name'],
                             donnees['email'])
    profil = ProfilFactory(user=user, genre=donnees['genre'],
                           telephone=donnees['phone'], statut='actif')
    etudiant = Etudiant.objects.create(
        profil=profil,
        matricule=generate_matricule(),
        classe=classes_n[sem_courant],
    )

    # Type d'inscription : nouvel entrant en L1, reinscription sinon (etudiant
    # deja present a l'universite, meme sans ligne d'historique en base : il
    # n'existe qu'une seule annee academique).
    type_courant = (Inscription.TYPE_INSCRIPTION if niveau == 'L1'
                    else Inscription.TYPE_REINSCRIPTION)
    for sem in ('S1', 'S2'):
        classe_courante = classes_n[sem]
        if not classe_courante:
            continue
        Inscription.objects.create(
            etudiant=etudiant, classe=classe_courante, annee=annee_n['annee'],
            type_inscription=type_courant,
            date_inscription=classe_courante.semestre.date_debut,
            statut='active',
        )
        stats['inscriptions'] += 1

# ═════════════════════════════════════════════════════════════════════════════
# CONTROLES D'INTEGRITE
# ═════════════════════════════════════════════════════════════════════════════

print("")
print("[*] Controles d'integrite...")
anomalies = []

classes_vides = [c.libelle for c in Classe.objects.all()
                 if not Inscription.objects.filter(classe=c).exists()]
if classes_vides:
    anomalies.append(f"{len(classes_vides)} classe(s) sans etudiant : {classes_vides[:5]}")

modules_orphelins = Module.objects.filter(classe__isnull=True).count()
if modules_orphelins:
    anomalies.append(f"{modules_orphelins} module(s) sans classe (invisibles dans le contenu pedagogique)")

heures_valides = {(hd, hf) for hd, hf in BLOCS}
hors_grille = [
    f"{s.heure_debut}-{s.heure_fin}"
    for s in Seance.objects.all().only('heure_debut', 'heure_fin')
    if (s.heure_debut, s.heure_fin) not in heures_valides
]
if hors_grille:
    anomalies.append(f"{len(hors_grille)} seance(s) hors grille : {sorted(set(hors_grille))[:5]}")

# Conflit enseignant : deux seances actives, meme enseignant, meme date/creneau,
# sans lien de mutualisation.
conflits_ens = (
    Seance.objects.filter(statut__in=[STATUT_CONFIRME, STATUT_REPORTEE])
    .values('enseignant_id', 'date_seance', 'heure_debut')
    .annotate(n=Count('id')).filter(n__gt=1).count()
)
mutualisees = Seance.objects.filter(seance_liee__isnull=False).count()
if conflits_ens > mutualisees:
    anomalies.append(f"{conflits_ens - mutualisees} conflit(s) d'enseignant non mutualise(s)")

conflits_classe = (
    Seance.objects.filter(statut__in=[STATUT_CONFIRME, STATUT_REPORTEE])
    .values('classe_id', 'date_seance', 'heure_debut')
    .annotate(n=Count('id')).filter(n__gt=1).count()
)
if conflits_classe:
    anomalies.append(f"{conflits_classe} conflit(s) de classe")

if stats['creneaux_introuvables']:
    anomalies.append(f"{stats['creneaux_introuvables']} creneau(x) non attribue(s) faute de capacite")

# Revalidation d'un echantillon par le moteur metier de l'application.
echantillon = list(
    Seance.objects.filter(annee=annee_n['annee'], statut=STATUT_CONFIRME)
    .order_by('?')[:150]
)
refus = 0
for seance in echantillon:
    try:
        seance.full_clean()
    except Exception as exc:
        refus += 1
        if refus == 1:
            anomalies.append(f"validation refusee sur un echantillon : {exc}")
if refus:
    anomalies.append(f"{refus}/{len(echantillon)} seances de l'echantillon rejetees par full_clean()")

# ═════════════════════════════════════════════════════════════════════════════
# RESUME
# ═════════════════════════════════════════════════════════════════════════════

nb_classes = Classe.objects.count()
seances_par_semaine = {}
for s in Seance.objects.filter(annee=annee_n['annee']).values('classe_id', 'date_seance'):
    cle = (s['classe_id'], s['date_seance'].isocalendar()[:2])
    seances_par_semaine[cle] = seances_par_semaine.get(cle, 0) + 1
charges = sorted(seances_par_semaine.values()) if seances_par_semaine else [0]

print("")
print("=" * 64)
print("  RESUME DU JEU DE DONNEES")
print("=" * 64)
print("  Annees academiques :", AnneeAcademique.objects.count())
print("  Semestre courant   :", annee_n['semestres'][sem_courant])
print("  Classes            :", nb_classes, "— sans etudiant :", len(classes_vides))
print("  Etudiants          :", Etudiant.objects.count())
print("  Inscriptions       :", Inscription.objects.count(),
      "(reinscriptions :",
      Inscription.objects.filter(type_inscription=Inscription.TYPE_REINSCRIPTION).count(), ")")
print("  Enseignants        :", Enseignant.objects.count(),
      "— referents classe :", ReferentClasse.objects.count())
print("  Modules            :", Module.objects.count(),
      "— sans classe :", modules_orphelins)
print("  Affectations       :", AffectationModule.objects.count(),
      "— CM/TD/TP :",
      AffectationModule.objects.filter(type_seance='CM').count(),
      AffectationModule.objects.filter(type_seance='TD').count(),
      AffectationModule.objects.filter(type_seance='TP').count())
print("  Seances            :", Seance.objects.count(),
      "— annulees :", stats['annulees'], "— reportees :", stats['reportees'])
print("  Seances/semaine/classe (annee en cours) : min",
      charges[0], "| median", charges[len(charges) // 2], "| max", charges[-1])
print("-" * 64)
if anomalies:
    print("  ANOMALIES :")
    for a in anomalies:
        print("    -", a)
else:
    print("  Aucune anomalie detectee.")
print("=" * 64)
