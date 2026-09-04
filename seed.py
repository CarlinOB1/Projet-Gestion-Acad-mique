"""
seed.py - Genere le jeu de donnees pour la FST.
Semestres 1 et 2, modules reels par filiere, emplois du temps, semestre 2 = courant.
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

from django.contrib.auth.models import User
from EDT_app.models import (
    Faculte, Departement, Filiere, Parcours,
    AnneeAcademique, Semestre, Classe,
    Profil, Enseignant, Etudiant,
    Matiere, Module, Seance, AffectationModule,
)
from EDT_app.factories import (
    FaculteFactory, DepartementFactory, FiliereFactory,
    ParcoursFactory, ClasseFactory,
    ProfilFactory, MatiereFactory, ModuleFactory,
)

RAW_STUDENTS = """
1. Niveau L1 (73 étudiants) — Inscription : 2025
Portail : BGC
ASSAMBO Gyna Elda (F) – 2003-01-05 – Tél : 06-976-3447
BADINGA Justesse Naomie (F) – 2006-03-24 – Tél : 06-678-8009
BATANTOU-NGONGO Thercia Benedicta (F) – 2006-03-24 – Tél : 06-817-7365
BIYOKO Deborha Grâce Divine (F) – 2003-03-25 – Tél : 05-795-0038
BOUANGA Marie Emerance (F) – 2005-02-11 – Tél : 06-404-5858
CHEMIN Jean (M) – 2002-09-07 – Tél : 06-885-8706
ELEMBA ONDOUMA Simonia Felia (F) – 2004-09-12 – Tél : 06-497-8486
IBARA Perine Johnson (M) – 2005-01-08 – Tél : 06-639-9038
KASSA France Clara (F) – 2004-04-04 – Tél : 06-651-4254
KIBOULOU Veronique-Orchidée (F) – 2005-05-20 – Tél : 06-595-9438
KILOMBO Gloire Belvie (F) – 2004-11-02 – Tél : 06-486-9176
KOUBAKA NTONDELE Divine Sereina (F) – 2004-01-04 – Tél : 04-010-4710
MAKOUMBOU Josephin Archanges (M) – 2004-03-17 – Tél : 06-907-2937
MALANDA-SAKAMESSO Nasni Arlan (F) – 2005-06-08 – Tél : 05-386-8053
MAMBOU Sandrine (F) – 2005-11-19 – Tél : 06-607-9694
MATOUALA Christopher Jordan (M) – 2006-03-15 – Tél : 06-894-2879
MAVOUNGOU Ephraim grace (M) – 2006-08-25 – Tél : 06-899-2713
MAVOUNGOU Sandrina Rubene (F) – 2002-08-01 – Tél : 06-493-9440
MAYELA Emmanuelle Loina (F) – 2004-03-17 – Tél : 06-440-8694
MBOMBA Ngamba Benisse Caberlise (F) – 2005-03-02 – Tél : 06-573-6006
MILANDOU Clesh Dristin (M) – 2005-05-11 – Tél : 06-934-8515
MOUANZA Philippe Juvelvie Goldive (F) – 2007-07-04 – Tél : 06-859-4658
MOUKOKO Josianne Emmanuelle (F) – 2007-09-06 – Tél : 06-650-7085
MOUKOUAMA NDEMBI Erica Privelda (F) – 2005-05-02 – Tél : 06-544-4871
MOULERI Liesse Martiale (F) – 2006-05-05 – Tél : 06-123-4567
MYLANDOU KOUSSOU Gervyne (F) – 2006-05-16 – Tél : 06-466-4616
NZAOU MOULONGO Glad Celeste (F) – 2006-09-06 – Tél : 05-043-8146
NDOUTA Amos (M) – 2007-01-22 – Tél : 06-868-1864
NGOMA-NZOUSSI Paule Odie (F) – 2007-06-08 – Tél : 06-802-0311
NGOUBILIDH-PARI Benie Providence (F) – 2007-03-19 – Tél : 06-953-7181
NOUKIMI SIMO Carla Ines (F) – 2007-06-09 – Tél : 06-417-4804
NZIAMI LEMINA Norah-Soufiane (F) – 2007-09-19 – Tél : 05-378-6843
OFFEME Celeste Kethsia (F) – 2007-08-05 – Tél : 06-901-9382
OKOSSA-VENDZE Servianie Mary-Jeha (F) – 2005-05-20 – Tél : 06-599-4190
OMBILA POUNGUI Jacques Wilfrid (M) – 2005-05-11 – Tél : 05-078-4006
PILAYE NZENZE Valcy Genica Yaviche (F) – 2007-07-05 – Tél : 06-646-2385
SOUMBOU PITA Durella Emmanuelle Sublime (F) – 2005-05-24 – Tél : 05-368-1781
TSIBA MADZOU Glory Preralent (M) – 2006-02-14 – Tél : 06-448-9590

Portail : MIP
BALOSSAL Lauretha Perseverance (F) – 2007-07-11 – Tél : 06-701-3090
BASSISSA Yann Isaac Bonheur (M) – 2005-03-09 – Tél : 06-111-2222
DACOSTAS NGOMA Vicheldi Miveck (M) – 2006-01-16 – Tél : 06-564-7537
KINZIMOU Stephen Mike Kevin (M) – 2004-12-01 – Tél : 05-686-5891
KODIA KOUNDI Julander Bonheur (M) – 2005-07-29 – Tél : 06-979-2851
LIKIBI Dariesh (M) – 2005-03-03 – Tél : 06-703-3089
MBANZA JULIEN Lareine Rayonne (F) – 2005-08-25 – Tél : 06-823-0167
MBERI Paola Deroph (F) – 2005-01-02 – Tél : 06-787-2709
MBERI Rebecca Deroph (F) – 2005-01-02 – Tél : 06-787-2576
MBOKO Luck Beauvary (M) – 2005-07-21 – Tél : 06-810-9239
MISSOLO LEGO Grace (F) – 2005-11-23 – Tél : 06-453-4076
MOUANDA Pierly Welcom (M) – 2005-02-05 – Tél : 05-053-0764
NGANGA Cecilia Jeanette (F) – 2005-08-25 – Tél : 05-042-7336
NGASSAKI Simoney Akim Marlon (M) – 2006-10-10 – Tél : 06-892-1935
NGOWAMA Patrice Winner (M) – 2005-01-02 – Tél : 06-588-3201
NZIENGUI BELLA Cherina Sanctifiee (F) – 2005-02-16 – Tél : 04-022-8405
NZIHOU-NZIHOU Fabrina Michepa (M) – 2005-09-01 – Tél : 04-457-4606
OTSOU Arty-Quenan (M) – 2007-05-05 – Tél : 06-468-6989
PANDZOU NKENGUE Justhe (F) – 2005-03-06 – Tél : 06-519-8478
SAMBA-SAMBA Reine Marie-Laure Desanges (F) – 2007-05-21 – Tél : 05-791-4816
SEKANGUE Guillaume Henry Davys (M) – 2007-08-31 – Tél : 05-791-0557
SIBA LEMBA NANA Graziella Aimee Colombe (F) – 2006-06-24 – Tél : 04-018-0252

Portail : PCG
BALOUBOULA Denicia Yverline (F) – 2006-12-15 – Tél : 06-647-4721
BATISSA Vannessa Assere (F) – 2006-07-03 – Tél : 05-610-1920
BIELL Lyse Arlena (F) – 2006-03-23 – Tél : 05-525-3934
BOUETELE MIENANZAMBI Miterdit Juldas (M) – 2006-01-20 – Tél : 06-695-6607
BOUNGOU MILANDOU Paulina Eleonore (F) – 2007-02-28 – Tél : 06-996-9453
FILANCKEMBO Chelna (F) – 2006-09-12 – Tél : 06-981-9179
GAMBOU Jerdon Delcie (M) – 2007-08-03 – Tél : 06-687-9066
KIBANGOU MABIALA Anna Princesse (F) – 2007-01-03 – Tél : 06-855-4385
KIHOUBA LOUFOUMA Rabby dherlaas (M) – 2007-07-07 – Tél : 06-853-9506
KIMPOUTOU Alphee Minu Emmanuelle (F) – 2007-05-18 – Tél : 06-448-4881
KOUMBA NDINGA Ruflath Natura (M) – 2007-03-05 – Tél : 06-717-6859
MANDANGUI Sonia Richmonde (F) – 2007-09-09 – Tél : 06-884-9430
MANGOUBI NGOMA Albin Nicephore (M) – 2006-01-01 – Tél : 06-683-9421

2. Niveau L2 (50 étudiants) — Inscription : 2024
Filière : Biologie
BABY Johann Bernadette (F) – 2006-04-11 – Tél : 06-507-0206
KONDJI Hamona Neuvina (F) – 2005-04-26 – Tél : 06-920-3237
LOUYA Charnelle Dercia (F) – 2006-01-17 – Tél : 06-591-5448
MASSOUEMA ALBRICH Davor (F) – 2004-10-09 – Email : davormassouemaalbrich@gmail.com
MOUKOUNGOU Grignon Pierre (M) – 2006-07-07 – Tél : 06-787-4897
NGASSI TCHIKEU Mironda (F) – 2007-05-23 – Tél : 05-586-0536
TCHICAYA Samuel Franck (M) – 2007-01-02 – Tél : 06-488-3684

Filière : Chimie
HANT Omer Ketsia Ronika (F) – 2004-09-07 – Tél : 05-085-9731
HOUANAHOUAYA MBOUALE Serdia Romanne (F) – 2005-08-05 – Tél : 06-565-5322
KOUKISSA-KIETOU Germa Memene (F) – 2005-12-14 – Tél : 06-881-3248
MOUNZENZE MAZOUKA Prince Junior (M) – 2004-02-06 – Tél : 06-645-1665
MOUSSOUNGOU Henri Dorel (M) – 2004-02-12 – Tél : 06-557-9036
PAMBOU Francilia (F) – 2006-07-29 – Tél : 06-530-4103

Filière : Géosciences
LOUAMBA Messya Eliafix (M) – 2004-03-17 – Tél : 06-577-5751
MASSAMBA Marie-Andre (M) – 2004-02-16 – Tél : 06-748-4941
MBOKO Hugue Rodney Alicia (F) – 2006-09-07 – Tél : 06-636-3318
MOUANDA BOUEYA Erica Murcia Donaise (F) – 2004-07-09 – Tél : 06-142-3368
OBENGUELE PEA Monica Nahomie (F) – 2004-07-11 – Tél : 06-888-6265
PANDZOU NDELANI Patrich Flodel (M) – 2006-06-25 – Tél : 06-906-8802
PANDZOU NKENGUE Loren Nikanor (M) – 2004-09-07 – Tél : 05-307-4796
TCHICAYA MAHOUNGOU Triphene Rachelle (F) – 2004-01-04 – Tél : 05-779-4678
TSATY Orlyson (M) – 2004-03-15 – Tél : 06-993-9442

Filière : Informatique
ANTCHINARD Sido-De-Mado (M) – 2005-09-27 – Tél : 06-599-0421
BAKALA Amen (F) – 2006-03-10 – Tél : 06-551-9355
BANABEL BRANDON Harlcia Sagesse Even (F) – 2004-09-22 – Tél : 06-624-9419
BOUTHA-WAKOU MBEMBA Claude Chrisnelle (F) – 2005-01-22 – Tél : 06-562-2620
EBIOU MOUNDZELI Esperance Deborah Abigail (F) – 2006-04-05 – Tél : 06-954-6417
ELENGA Rossy Schadail (M) – 2006-05-25 – Tél : 05-571-1954
GOMA Gloire Allegresse (M) – 2004-03-05 – Tél : 06-842-8607
KAMBI Jean-floris Tresor (M) – 2006-07-22 – Tél : 06-421-9402
LOEMBA MALANDA Anto Prince Isaac (M) – 2005-04-08 – Tél : 06-823-7830
LORD Anthony Samuel (M) – 2004-11-14 – Tél : 06-807-3444
MAKAMBO Emmanuelle Emilia (F) – 2005-11-19 – Tél : 05-543-0815
MBOUMA PEYA Herd Fortune (M) – 2004-07-09 – Tél : 05-791-5352
MOUKOKO MABELE Laara Miche (F) – 2004-07-14 – Tél : 06-660-0406
MOUSSAHOU Merilna Reine Benedicte (F) – 2004-08-12 – Tél : 06-602-6678
MOUSSONGOU KOUMBA Dominique Coletta Lauria (F) – 2004-12-02 – Tél : 06-817-0085
NDOKI Creyson (M) – 2004-05-06 – Tél : 06-561-7874
NGOMA Franck Ryan (M) – 2007-03-25 – Tél : 05-304-5045
NGOMA PAMBOU Florine Annuarite (F) – 2005-05-10 – Tél : 05-392-1648
NGOUOMO-NKOUA Hareine Hervela (F) – 2005-10-09 – Tél : 06-660-8915
OPOMBA Annike christelle (F) – 2005-04-05 – Tél : 06-514-7693
PILLA Luc Juskard (M) – 2004-09-08 – Tél : 06-813-2672
MAKOSSO-MWESSI Ivie-Claude (F) – 2004-06-15 – Tél : 06-333-4444

Filière : Physique
BATOTA Grace De Richy (M) – 2005-05-22 – Tél : 06-591-5650
KINGA Carla Benicia (F) – 2007-01-16 – Tél : 05-746-1097
ISSALA Jade Ridher (M) – 2006-04-24 – Tél : 05-382-3502
NZOLA MPAKA Naomie Marella (F) – 2004-10-08 – Tél : 06-697-8229
NZOULANI NDEMBO Gracia Ludvine (F) – 2007-09-24 – Tél : 06-693-8140

3. Niveau L3 (48 étudiants) — Inscription : 2023
Filière : Biologie
DIAKABOU Minion Chance Fresnel (M) – 2002-04-19 – Tél : 06-471-1236
KIBOULOU Veronique-Orchidee (F) – 2005-05-20 – Tél : 06-595-9439
KILOMBO Gloire Belvie (F) – 2004-11-02 – Tél : 06-486-9177
MALALOU Edemond Jessie (M) – 2005-04-01 – Tél : 06-982-0292
MAMBOU MALIA Espoire (F) – 2004-07-20 – Tél : 06-496-7767
MAVOUNGOU Berdrina Rubene (F) – 2002-08-01 – Tél : 06-493-9441
MBOMBA NGAMBA Benisse Caberlise (F) – 2005-03-02 – Tél : 06-573-6007
MOUANDA France Chadelvie (F) – 2004-04-04 – Tél : 06-651-4255
MOUNDOUNGA SIMBOU Gloria Marlyta (F) – 2004-01-20 – Tél : 06-175-8146
MOUYOKI MBOYO Clara Bel-monde (F) – 2005-03-12 – Tél : 05-317-5624
MPEMBA TATY Chris-Beni (M) – 2004-08-25 – Tél : 06-874-7302
VAMBA Emmanuelle Van-liane Judelvie (F) – 2007-03-15 – Tél : 05-667-6141

Filière : Chimie
BABATILA Frida Sandrine Nathalie (F) – 2004-04-30 – Tél : 06-639-9039
BANSIMBA MOUSSOUNOU Sandrine (F) – 2005-11-19 – Tél : 06-607-9695
BOUKAKA MOUANGA Jhivel (M) – 2004-01-01 – Tél : 06-906-2461
IBARA Pierre Alexandre (M) – 2005-01-08 – Tél : 05-012-3264
KOLYARDO Marie-cecille Eureka (F) – 2005-11-12 – Tél : 05-322-5093
MAGNOUNGOU FELINA Bernhyse Geraldine (F) – 2005-04-27 – Tél : 06-877-6349
NZELI ENOW Chance Mavie (F) – 2004-08-11 – Tél : 06-707-6779

Filière : Géosciences
EKORONG Rose Martialle (F) – 2002-01-29 – Tél : 06-867-9788
KOUBAKA NTONDELE Divine Serenaa (F) – 2004-01-04 – Tél : 04-010-4711
MAPAKO NDENDE Grace Colombe Princilia (F) – 2006-04-17 – Tél : 06-507-4794
MATONDO Merveil Christopher (M) – 2006-03-15 – Tél : 06-894-2880
MAVOUNGOU Vera Tchiecesse (M) – 2004-01-23 – Tél : 06-883-5867
MBOUI MAESSIE Emmanuelle Fleurine (F) – 2005-12-11 – Tél : 06-819-8266
MILANDOU Clesh Dristine (M) – 2005-05-11 – Tél : 06-934-8516
MONDJILI DUBERMANN Michel Eureka (M) – 2006-03-27 – Tél : 06-507-6929
MONGO Joy Godlove (M) – 2004-05-15 – Email : joygodlovemongo@gmail.com
MOUKILOU DANZA Kenn Daniella (F) – 2004-08-01 – Tél : 06-709-5029
NGUEMBO MABIALA Bruno Belone (M) – 2005-05-03 – Tél : 06-556-6516
NZAMBA MAEVI Dolores Naomie (F) – 2004-07-13 – Tél : 06-713-6451
NZIECK Helena-Joy (F) – 2005-11-08 – Tél : 06-659-2264
SAMOUNGANA Adelina Fortune (F) – 2005-12-27 – Tél : 06-402-3533
SANGA Exauce Amour (F) – 2004-03-10 – Email : exauceamoursanga@gmail.com
SEHOLO BONGO Deo-Gracias (M) – 2005-08-25 – Tél : 06-448-3096

Filière : Informatique
GACKOSSO Cherubin Junior (M) – 2002-09-07 – Tél : 06-885-8707
LYSHA-MAKOSSO Jurs Shakti (F) – 2005-06-16 – Tél : 06-614-2616
MPANDZOU OTO LENGOUENZE Life Obvious (M) – 2004-07-20 – Tél : 06-685-8845
OMBANDZA OMBI Carlin Leroi (M) – 2005-06-05 – Tél : 05-619-9317
POATY TCHICAYA Josue Parfait (M) – 2005-08-05 – Tél : 06-575-8058
TCHISSAMBOU Nacy Ivann (M) – 2005-05-06 – Tél : 06-500-3330

Filière : Physique
BA MISSAMOU Macylan Dieuveille (M) – 2004-06-12 – Tél : 06-444-5555
KOUBIKANI-MBOUI Victoire-Jeph (M) – 2005-04-04 – Tél : 06-843-6515
MAYANDZI MAHOUNGOU Theresa Rosemonde (F) – 2006-06-20 – Tél : 06-858-8220
NKOUKA Once Capriani (F) – 2005-08-06 – Tél : 04-440-3413
TATI KOULESSE Saxe Dervick (M) – 2006-02-23 – Tél : 06-899-4074
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
    print("    Base nettoyee.\n")


def creer_utilisateur(username, first_name, last_name, email=None):
    User.objects.filter(username=username).delete()
    user = User.objects.create_user(
        username=username,
        password="Password123!",
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


matricule_counter = 1


def generate_matricule():
    global matricule_counter
    mat = "ETU-" + str(matricule_counter).zfill(5)
    matricule_counter += 1
    return mat


flush_data()

# Status valide recupere directement depuis le modele (evite probleme d'encodage source)
STATUT_CONFIRME = 'Confirm\u00e9e'  # = 'Confirmée'

print("[*] Creation Faculte et Departements...")
faculte = FaculteFactory(libelle='Faculté des Sciences et Technologie')

deps_names = ['Biologie', 'Chimie', 'Géosciences', 'Informatique', 'Physique']
deps = {}
for d_name in deps_names:
    deps[d_name] = DepartementFactory(libelle='Département ' + d_name, faculte=faculte)

print("[*] Creation Filieres...")
filieres = {}
for f_name in deps_names:
    filieres[f_name] = FiliereFactory(libelle=f_name, departement=deps[f_name])

print("[*] Creation Parcours, Annee et Semestres...")
parcours_l1 = ParcoursFactory(type_parcours='Licence', niveau=1)
parcours_l2 = ParcoursFactory(type_parcours='Licence', niveau=2)
parcours_l3 = ParcoursFactory(type_parcours='Licence', niveau=3)

today = date.today()
year_start = today.year if today.month >= 9 else today.year - 1

annee = AnneeAcademique.objects.create(
    libelle=str(year_start) + '-' + str(year_start + 1),
    date_debut=date(year_start, 9, 1),
    date_fin=date(year_start + 1, 10, 31),
    statut='active',
)

# Semestre 1 : sept → jan (terminé)
semestre1 = Semestre.objects.create(
    libelle='Semestre 1',
    date_debut=date(year_start, 9, 1),
    date_fin=date(year_start + 1, 2, 28),
    annee=annee,
)

# Semestre 2 : mars → oct (en cours / courant)
semestre2 = Semestre.objects.create(
    libelle='Semestre 2',
    date_debut=date(year_start + 1, 3, 1),
    date_fin=date(year_start + 1, 10, 31),
    annee=annee,
)

print("[*] Creation Classes (S1 et S2) pour L1, L2, L3...")

# Classes L1 — S1 et S2
classes_l1_s1 = {}
classes_l1_s2 = {}
for code in ['BGC', 'MIP', 'PCG']:
    classes_l1_s1[code] = Classe.objects.create(
        parcours=parcours_l1, semestre=semestre1, annee=annee, code=code)
    classes_l1_s2[code] = Classe.objects.create(
        parcours=parcours_l1, semestre=semestre2, annee=annee, code=code)

# Classes L2 et L3 — S1 et S2 par filière
classes_l2_s1 = {}
classes_l2_s2 = {}
classes_l3_s1 = {}
classes_l3_s2 = {}
for f_name, f_obj in filieres.items():
    classes_l2_s1[f_name] = Classe.objects.create(
        parcours=parcours_l2, semestre=semestre1, annee=annee, filiere=f_obj)
    classes_l2_s2[f_name] = Classe.objects.create(
        parcours=parcours_l2, semestre=semestre2, annee=annee, filiere=f_obj)
    classes_l3_s1[f_name] = Classe.objects.create(
        parcours=parcours_l3, semestre=semestre1, annee=annee, filiere=f_obj)
    classes_l3_s2[f_name] = Classe.objects.create(
        parcours=parcours_l3, semestre=semestre2, annee=annee, filiere=f_obj)

print("[*] Creation Enseignants, Matieres, Modules et Emplois du temps...")

# ─────────────────────────────────────────────────────────────
# Modules par filière : (libellé, crédits, semestre)
# ─────────────────────────────────────────────────────────────
MODULES_PAR_FILIERE = {
    'Biologie': [
        # Semestre 1
        ('Biologie Cellulaire et Moléculaire', 4, 'S1'),
        ('Biochimie Structurale', 3, 'S1'),
        ('Anatomie Végétale', 2, 'S1'),
        ('Statistiques Biologiques', 2, 'S1'),
        # Semestre 2
        ('Génétique Classique', 4, 'S2'),
        ('Physiologie Animale', 3, 'S2'),
        ('Microbiologie Générale', 3, 'S2'),
        ('Écologie Fondamentale', 2, 'S2'),
    ],
    'Chimie': [
        # Semestre 1
        ('Chimie Organique I', 4, 'S1'),
        ('Thermodynamique Chimique', 3, 'S1'),
        ('Chimie Analytique', 2, 'S1'),
        ('Mathématiques pour Chimistes', 2, 'S1'),
        # Semestre 2
        ('Cinétique Chimique', 4, 'S2'),
        ('Chimie Minérale', 3, 'S2'),
        ('Chimie des Solutions', 3, 'S2'),
        ('Spectroscopie', 2, 'S2'),
    ],
    'Géosciences': [
        # Semestre 1
        ('Géologie Générale', 4, 'S1'),
        ('Cartographie et Topographie', 3, 'S1'),
        ('Sédimentologie', 2, 'S1'),
        ('Mathématiques Appliquées', 2, 'S1'),
        # Semestre 2
        ('Minéralogie', 4, 'S2'),
        ('Pétrographie', 3, 'S2'),
        ('Géochimie', 3, 'S2'),
        ('Télédétection', 2, 'S2'),
    ],
    'Informatique': [
        # Semestre 1
        ('Algorithmique et Structures de Données', 4, 'S1'),
        ('Architecture des Ordinateurs', 3, 'S1'),
        ('Programmation en C', 3, 'S1'),
        ('Mathématiques Discrètes', 2, 'S1'),
        # Semestre 2
        ('Programmation Orientée Objet', 4, 'S2'),
        ('Bases de Données Relationnelles', 4, 'S2'),
        ('Réseaux Informatiques', 3, 'S2'),
        ('Systèmes d\'Exploitation', 2, 'S2'),
    ],
    'Physique': [
        # Semestre 1
        ('Mécanique du Point et du Solide', 4, 'S1'),
        ('Optique Géométrique', 3, 'S1'),
        ('Mathématiques pour Physiciens', 3, 'S1'),
        ('Informatique Scientifique', 2, 'S1'),
        # Semestre 2
        ('Électromagnétisme', 4, 'S2'),
        ('Thermodynamique Physique', 3, 'S2'),
        ('Mécanique Quantique I', 3, 'S2'),
        ('Physique Numérique', 2, 'S2'),
    ],
}

# Créneaux horaires disponibles sur la semaine
CRENEAUX = [
    (time(9, 0), time(11, 0)),
    (time(11, 15), time(13, 15)),
    (time(14, 0), time(16, 0)),
]
JOURS_SEMAINE = [0, 1, 2, 3, 4]  # lundi=0 .. vendredi=4

# Dictionnaire global des modules créés : libellé -> Module
tous_les_modules = {}
# Dictionnaire enseignant affecté par module pk : module.pk -> Enseignant
ens_par_module = {}

# Pour stocker les enseignants par département
enseignants_par_dept = {}

for f_name, dept in deps.items():
    print("    -> Departement:", f_name)

    chef = creer_enseignant(
        'chef.' + slugify_name(f_name), 'Chef', 'Prof' + f_name, dept)
    dept.chef = chef
    dept.save()

    filieres[f_name].responsable = chef
    filieres[f_name].save()

    ens2 = creer_enseignant(
        'ens2.' + slugify_name(f_name), 'Alice', 'Prof' + f_name, dept)
    ens3 = creer_enseignant(
        'ens3.' + slugify_name(f_name), 'Bob', 'Prof' + f_name, dept)

    enseignants_par_dept[f_name] = [chef, ens2, ens3]

    # Matière de base pour le département
    mat = MatiereFactory(libelle='Matieres Fondamentales ' + f_name, departement=dept)

    # Création des modules
    for (m_libelle, credits, sem_code) in MODULES_PAR_FILIERE[f_name]:
        sem_obj = semestre1 if sem_code == 'S1' else semestre2
        mod = Module.objects.create(
            libelle=m_libelle,
            matiere=mat,
            semestre=sem_obj,
            credits=credits,
            description='Module ' + m_libelle + ' - ' + f_name,
            heures_cm=credits * 6,
            heures_td=credits * 4,
            heures_tp=credits * 2,
        )
        tous_les_modules[m_libelle] = mod

        # Affectation de l'enseignant — on stocke le même pour les séances
        ens_affect = random.choice(enseignants_par_dept[f_name])
        AffectationModule.objects.create(
            module=mod,
            enseignant=ens_affect,
            type_seance='CM',
            heures_prevues=float(credits * 6),
        )
        ens_par_module[mod.pk] = ens_affect

print("[*] Creation des emplois du temps (seances)...")

random.seed(42)

def generer_seances_classe(classe_obj, modules_avec_ens, debut_sem, fin_sem):
    """
    Genere des seances pour une classe en evitant les conflits.
    Chaque module obtient des creneaux hebdomadaires distincts.
    modules_avec_ens = liste de (module, enseignant)
    """
    SLOTS = [
        (0, time(9, 0), time(11, 0)),
        (0, time(14, 0), time(16, 0)),
        (1, time(9, 0), time(11, 0)),
        (1, time(14, 0), time(16, 0)),
        (2, time(9, 0), time(11, 0)),
        (2, time(14, 0), time(16, 0)),
        (3, time(9, 0), time(11, 0)),
        (3, time(14, 0), time(16, 0)),
        (4, time(9, 0), time(11, 0)),
        (4, time(14, 0), time(16, 0)),
    ]

    debut_lundi = debut_sem
    while debut_lundi.weekday() != 0:
        debut_lundi += timedelta(days=1)

    nb_semaines_dispo = (fin_sem - debut_lundi).days // 7
    if nb_semaines_dispo < 3:
        nb_semaines_dispo = 3

    for slot_idx, (mod, ens) in enumerate(modules_avec_ens):
        slot = SLOTS[slot_idx % len(SLOTS)]
        jour_rel, hd, hf = slot

        semaines_choisies = [0, nb_semaines_dispo // 3, 2 * nb_semaines_dispo // 3]
        for sem_offset in semaines_choisies:
            lundi_sem = debut_lundi + timedelta(weeks=sem_offset)
            d_seance = lundi_sem + timedelta(days=jour_rel)
            if d_seance > fin_sem:
                d_seance = fin_sem - timedelta(days=fin_sem.weekday() - jour_rel)
            if d_seance.weekday() == 6:
                d_seance -= timedelta(days=1)
            try:
                Seance.objects.create(
                    module=mod,
                    enseignant=ens,
                    classe=classe_obj,
                    annee=annee,
                    date_seance=d_seance,
                    heure_debut=hd,
                    heure_fin=hf,
                    type_seance='CM',
                    statut=STATUT_CONFIRME,
                )
            except Exception:
                try:
                    Seance.objects.create(
                        module=mod,
                        enseignant=ens,
                        classe=classe_obj,
                        annee=annee,
                        date_seance=d_seance,
                        heure_debut=hd,
                        heure_fin=hf,
                        type_seance='CM',
                        statut='brouillon',
                    )
                except Exception:
                    pass

# Pour chaque filière et chaque semestre, on crée des séances pour les classes L2 et L3
for f_name in deps_names:
    for sem_code, sem_obj, classes_l2, classes_l3, is_current in [
        ('S1', semestre1, classes_l2_s1, classes_l3_s1, False),
        ('S2', semestre2, classes_l2_s2, classes_l3_s2, True),
    ]:
        modules_du_sem = [
            (tous_les_modules[m_libelle], ens_par_module[tous_les_modules[m_libelle].pk])
            for (m_libelle, credits, s) in MODULES_PAR_FILIERE[f_name]
            if s == sem_code
        ]

        if sem_code == 'S1':
            debut_sem = date(year_start, 9, 1)
            fin_sem = date(year_start + 1, 2, 28)
        else:
            debut_sem = date(year_start + 1, 3, 1)
            fin_sem = date(year_start + 1, 10, 31)

        for classe_dict, niveau_label in [
            (classes_l2, 'L2'),
            (classes_l3, 'L3'),
        ]:
            if f_name not in classe_dict:
                continue
            classe_obj = classe_dict[f_name]
            generer_seances_classe(classe_obj, modules_du_sem, debut_sem, fin_sem)

# Séances pour les classes L1 (S1 et S2) — cours généraux communs
print("[*] Creation des seances pour les classes L1...")

MODULES_L1_COMMUNS = [
    ('Mathématiques Générales', 'Informatique', 4, 'S1'),
    ('Physique Générale', 'Physique', 4, 'S1'),
    ('Chimie Générale', 'Chimie', 4, 'S1'),
    ('Biologie Générale', 'Biologie', 3, 'S1'),
    ('Géosciences Introductives', 'Géosciences', 3, 'S1'),
    ('Informatique Générale', 'Informatique', 4, 'S2'),
    ('Physique Appliquée', 'Physique', 3, 'S2'),
    ('Chimie Appliquée', 'Chimie', 3, 'S2'),
    ('Biologie Cellulaire Intro', 'Biologie', 3, 'S2'),
    ('Géologie Intro', 'Géosciences', 3, 'S2'),
]

mat_l1_info = MatiereFactory(libelle='Modules Transversaux L1', departement=deps['Informatique'])

for (m_libelle, dept_name, credits, sem_code) in MODULES_L1_COMMUNS:
    sem_obj = semestre1 if sem_code == 'S1' else semestre2
    mod_l1 = Module.objects.create(
        libelle=m_libelle,
        matiere=mat_l1_info,
        semestre=sem_obj,
        credits=credits,
        description='Module L1 commun : ' + m_libelle,
    )

    if sem_code == 'S1':
        debut_sem = date(year_start, 9, 1)
        fin_sem = date(year_start + 1, 2, 28)
        classes_l1 = classes_l1_s1
    else:
        debut_sem = date(year_start + 1, 3, 1)
        fin_sem = date(year_start + 1, 10, 31)
        classes_l1 = classes_l1_s2

    ens_l1 = random.choice(enseignants_par_dept[dept_name])
    AffectationModule.objects.create(
        module=mod_l1, enseignant=ens_l1, type_seance='CM', heures_prevues=float(credits * 6))

    for code in ['BGC', 'MIP', 'PCG']:
        classe_obj = classes_l1[code]
        generer_seances_classe(classe_obj, [(mod_l1, ens_l1)], debut_sem, fin_sem)

print("[*] Integration des Etudiants...")
lines = RAW_STUDENTS.strip().split('\n')
current_niveau = None
current_groupe = None
used_usernames = set()

for line in lines:
    line = line.strip()
    if not line:
        continue
    if line.startswith('1. Niveau L1'):
        current_niveau = 'L1'
    elif line.startswith('2. Niveau L2'):
        current_niveau = 'L2'
    elif line.startswith('3. Niveau L3'):
        current_niveau = 'L3'
    elif line.startswith('Portail :'):
        current_groupe = line.split(' : ')[1].strip()
    elif line.startswith('Filière :'):
        current_groupe = line.split(' : ')[1].strip()
    else:
        parts = line.split(' – ')
        if len(parts) < 1:
            continue
        name_genre = parts[0].strip()
        genre = 'F' if '(F)' in name_genre else 'M'
        name_part = name_genre.replace('(F)', '').replace('(M)', '').strip()

        name_tokens = name_part.split(' ')
        last_name = name_tokens[0]
        first_name = " ".join(name_tokens[1:]) if len(name_tokens) > 1 else last_name

        fn_slug = slugify_name(first_name)[:15]
        ln_slug = slugify_name(last_name)[:15]
        base_username = fn_slug + '.' + ln_slug
        username = base_username
        i = 1
        while username in used_usernames:
            username = base_username + str(i)
            i += 1
        used_usernames.add(username)

        contact = " ".join(parts[2:]) if len(parts) > 2 else ""
        if len(parts) == 2 and 'Tél' in parts[1]:
            contact = parts[1]

        phone = ""
        email = ""
        if "Tél" in contact:
            m = re.search(r'Tél\s*:\s*([\d-]+)', contact)
            if m:
                phone = m.group(1).replace('-', '')
        if "Email" in contact:
            m = re.search(r'Email\s*:\s*([^\s]+)', contact)
            if m:
                email = m.group(1)

        user = creer_utilisateur(username, first_name, last_name, email)
        profil = ProfilFactory(user=user, genre=genre, telephone=phone, statut='actif')
        matricule = generate_matricule()

        classe_obj = None
        filiere_obj = None
        parcours_obj = None

        if current_niveau == 'L1' and current_groupe:
            # Les étudiants sont rattachés au semestre 2 (courant)
            classe_obj = classes_l1_s2.get(current_groupe)
            parcours_obj = parcours_l1
        elif current_niveau == 'L2' and current_groupe:
            groupe = current_groupe if current_groupe in filieres else 'Informatique'
            classe_obj = classes_l2_s2.get(groupe)
            filiere_obj = filieres.get(groupe)
            parcours_obj = parcours_l2
        elif current_niveau == 'L3' and current_groupe:
            classe_obj = classes_l3_s2.get(current_groupe)
            filiere_obj = filieres.get(current_groupe)
            parcours_obj = parcours_l3

        if classe_obj and parcours_obj:
            Etudiant.objects.create(
                profil=profil, matricule=matricule,
                parcours=parcours_obj, filiere=filiere_obj, classe=classe_obj
            )

nb_etudiants = Etudiant.objects.count()
nb_seances = Seance.objects.count()
nb_modules = Module.objects.count()
nb_enseignants = Enseignant.objects.count()
nb_classes = Classe.objects.count()

print("")
print("=" * 55)
print("  RESUME DU JEU DE DONNEES")
print("=" * 55)
print("  Etudiants   :", nb_etudiants)
print("  Enseignants :", nb_enseignants)
print("  Modules     :", nb_modules)
print("  Classes     :", nb_classes, "(S1 + S2 pour L1/L2/L3)")
print("  Seances EDT :", nb_seances)
print("  Semestre courant : Semestre 2")
print("=" * 55)