"""
seed.py — Génère le jeu de données pour la FST.
"""
import os
import django
import re
from datetime import date, time, timedelta
import unicodedata

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
MAVOUNGOU Ephraïm grâce (M) – 2006-08-25 – Tél : 06-899-2713
MAVOUNGOU Sandrina Rubene (F) – 2002-08-01 – Tél : 06-493-9440
MAYELA Emmanuelle Loïna (F) – 2004-03-17 – Tél : 06-440-8694
MBOMBA Ngamba Benisse Caberlise (F) – 2005-03-02 – Tél : 06-573-6006
MILANDOU Clesh Dristin (M) – 2005-05-11 – Tél : 06-934-8515
MOUANZA Philippe Juvelvie Goldive (F) – 2007-07-04 – Tél : 06-859-4658
MOUKOKO Josianne Emmanuelle (F) – 2007-09-06 – Tél : 06-650-7085
MOUKOUAMA NDEMBI Erica Privelda (F) – 2005-05-02 – Tél : 06-544-4871
MOULERI Liesse Martiale (F) – 2006-05-05 – Email corrigé – Réintégré (numéro de téléphone dupliqué traité)
MYLANDOU KOUSSOU Gervyne (F) – 2006-05-16 – Tél : 06-466-4616
N'ZAOU MOULONGO Glad Celeste (F) – 2006-09-06 – Tél : 05-043-8146
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
TSIBA MADZOU Glory Préralent (M) – 2006-02-14 – Tél : 06-448-9590

Portail : MIP
BALOSSAL Lauretha Perséverance (F) – 2007-07-11 – Tél : 06-701-3090
BASSISSA Yann Isaac Bonheur (M) – 2005-03-09 – Tél : non renseigné
DACOSTAS NGOMA Vicheldi Miveck (M) – 2006-01-16 – Tél : 06-564-7537
KINZIMOU Stephen Mike Kevin (M) – 2004-12-01 – Tél : 05-686-5891
KODIA KOUNDI Julander Bonheur (M) – 2005-07-29 – Tél : 06-979-2851
LIKIBI Dariesh (M) – 2005-03-03 – Tél : 06-703-3089
MBANZA JULIEN Lareine Rayonne (F) – 2005-08-25 – Tél : 06-823-0167
MBERI Paola Deroph (F) – 2005-01-02 – Tél : 06-787-2709
MBERI Rebecca Deroph (F) – 2005-01-02 – Tél : 06-787-2576
MBOKO Luck Beauvary (M) – 2005-07-21 – Tél : 06-810-9239
MISSOLO LEGO Grâce (F) – 2005-11-23 – Tél : 06-453-4076
MOUANDA Pierly Welcom (M) – 2005-02-05 – Tél : 05-053-0764
NGANGA Cecilia Jeanette (F) – 2005-08-25 – Tél : 05-042-7336
NGASSAKI Simoney Akim Marlon (M) – 2006-10-10 – Tél : 06-892-1935
NGOWAMA Patrice Winner (M) – 2005-01-02 – Tél : 06-588-3201
NZIENGUI BELLA Cherina Sanctifiée (F) – 2005-02-16 – Tél : 04-022-8405
NZIHOU-NZIHOU Fabrina Michepa (M) – 2005-09-01 – Tél : 04-457-4606
OTSOU Arty-Quenan (M) – 2007-05-05 – Tél : 06-468-6989
PANDZOU NKENGUE Justhe (F) – 2005-03-06 – Tél : 06-519-8478
SAMBA-SAMBA Reine Marie-Laure Desanges (F) – 2007-05-21 – Tél : 05-791-4816
SEKANGUE Guillaume Henry Davys (M) – 2007-08-31 – Tél : 05-791-0557
SIBA LEMBA NANA Graziella Aimée Colombe (F) – 2006-06-24 – Tél : 04-018-0252

Portail : PCG
BALOUBOULA Denicia Yverline (F) – 2006-12-15 – Tél : 06-647-4721
BATISSA Vannessa Assère (F) – 2006-07-03 – Tél : 05-610-1920
BIELL Lyse Arlena (F) – 2006-03-23 – Tél : 05-525-3934
BOUETELE MIENANZAMBI Miterdit Juldas (M) – 2006-01-20 – Tél : 06-695-6607
BOUNGOU MILANDOU Paulina Eléonore (F) – 2007-02-28 – Tél : 06-996-9453
FILANCKEMBO Chelna (F) – 2006-09-12 – Tél : 06-981-9179
GAMBOU Jerdon Delcie (M) – 2007-08-03 – Tél : 06-687-9066
KIBANGOU MABIALA Anna Princesse (F) – 2007-01-03 – Tél : 06-855-4385
KIHOUBA LOUFOUMA Rabby dherla'as (M) – 2007-07-07 – Tél : 06-853-9506
KIMPOUTOU Alphée Minu Emmanuelle (F) – 2007-05-18 – Tél : 06-448-4881
KOUMBA NDINGA Ruflath Natura (M) – 2007-03-05 – Tél : 06-717-6859
MANDANGUI Sonia Richmonde (F) – 2007-09-09 – Tél : 06-884-9430
MANGOUBI NGOMA Albin Nicephore (M) – 2006-01-01 – Tél : 06-683-9421

2. Niveau L2 (50 étudiants) — Inscription : 2024
Filière : Biologie
BABY Johann Bernadette (F) – 2006-04-11 – Tél : 06-507-0206
KONDJI Hamôna Neuvina (F) – 2005-04-26 – Tél : 06-920-3237
LOUYA Charnelle Dercia (F) – 2006-01-17 – Tél : 06-591-5448
MASSOUEMA ALBRICH D'avor (F) – 2004-10-09 – Email : davormassouemaalbrich@gmail.com – Réintégré
MOUKOUNGOU Grignon Pierre (M) – 2006-07-07 – Tél : 06-787-4897
NGASSI TCHIKEU Mironda (F) – 2007-05-23 – Tél : 05-586-0536
TCHICAYA Samuel Franck (M) – 2007-01-02 – Tél : 06-488-3684

Filière : Chimie
HANT Omer Ketsia Ronika (F) – 2004-09-07 – Tél : 05-085-9731
HOUANAHOUAYA MBOUALE Serdia Romanne (F) – 2005-08-05 – Tél : 06-565-5322
KOUKISSA-KIETOU Germa Mémène (F) – 2005-12-14 – Tél : 06-881-3248
MOUNZENZE MAZOUKA Prince Junior (M) – 2004-02-06 – Tél : 06-645-1665
MOUSSOUNGOU Henri Dorel (M) – 2004-02-12 – Tél : 06-557-9036
PAMBOU Francilia (F) – 2006-07-29 – Tél : 06-530-4103

Filière : Géosciences
LOUAMBA Messya Eliafix (M) – 2004-03-17 – Tél : 06-577-5751
MASSAMBA Marie-André (M) – 2004-02-16 – Tél : 06-748-4941
MBOKO Hugue Rodney Alicia (F) – 2006-09-07 – Tél : 06-636-3318
MOUANDA BOUEYA Erica Murcia Donaise (F) – 2004-07-09 – Tél : 06-142-3368
OBENGUELE PEA Monica Nahomie (F) – 2004-07-11 – Tél : 06-888-6265
PANDZOU NDELANI Patrich Flodel (M) – 2006-06-25 – Tél : 06-906-8802
PANDZOU NKENGUE Loren Nikanor (M) – 2004-09-07 – Tél : 05-307-4796
TCHICAYA MAHOUNGOU Triphène Rachelle (F) – 2004-01-04 – Tél : 05-779-4678
TSATY Orlyson (M) – 2004-03-15 – Tél : 06-993-9442

Filière : Informatique
ANTCHINARD Sido-De-Mado (M) – 2005-09-27 – Tél : 06-599-0421
BAKALA Amen (F) – 2006-03-10 – Tél : 06-551-9355
BANABEL BRANDON Harlcia Sagesse Even (F) – 2004-09-22 – Tél : 06-624-9419
BOUTHA-WAKOU MBEMBA Claude Chrisnelle (F) – 2005-01-22 – Tél : 06-562-2620
EBIOU MOUNDZELI Espérance Deborah Abigail (F) – 2006-04-05 – Tél : 06-954-6417
ELENGA Rossy Schadail (M) – 2006-05-25 – Tél : 05-571-1954
GOMA Gloire Allégresse (M) – 2004-03-05 – Tél : 06-842-8607
KAMBI Jean-floris Trésor (M) – 2006-07-22 – Tél : 06-421-9402
LOEMBA MALANDA Anto Prince Isaac (M) – 2005-04-08 – Tél : 06-823-7830
LORD Anthony Samuel (M) – 2004-11-14 – Tél : 06-807-3444
MAKAMBO Emmanuelle Emilia (F) – 2005-11-19 – Tél : 05-543-0815
MBOUMA PEYA Herd Fortuné (M) – 2004-07-09 – Tél : 05-791-5352
MOUKOKO MABELE Laara Miche (F) – 2004-07-14 – Tél : 06-660-0406
MOUSSAHOU Mérilna Reine Bénédicte (F) – 2004-08-12 – Tél : 06-602-6678
MOUSSONGOU KOUMBA Dominique Coletta Lauria (F) – 2004-12-02 – Tél : 06-817-0085
NDOKI Creyson (M) – 2004-05-06 – Tél : 06-561-7874
NGOMA Franck Ryan (M) – 2007-03-25 – Tél : 05-304-5045
NGOMA PAMBOU Florine Annuarite (F) – 2005-05-10 – Tél : 05-392-1648
NGOUOMO-NKOUA Hareine Hervela (F) – 2005-10-09 – Tél : 06-660-8915
OPOMBA Annike christelle (F) – 2005-04-05 – Tél : 06-514-7693
PILLA Luc Juskard (M) – 2004-09-08 – Tél : 06-813-2672

Filière : Physique
BATOTA Grâce De Richy (M) – 2005-05-22 – Tél : 06-591-5650
KINGA Carla Benicia (F) – 2007-01-16 – Tél : 05-746-1097
ISSALA Jade Ridher (M) – 2006-04-24 – Tél : 05-382-3502
NZOLA MPAKA Naomie Marella (F) – 2004-10-08 – Tél : 06-697-8229
NZOULANI NDEMBO Gracia Ludvine (F) – 2007-09-24 – Tél : 06-693-8140

Non affecté à une filière (L2)
MAKOSSO-MWESSI Ivie-Claude (F) – Date de naissance normalisée – Réintégré

3. Niveau L3 (48 étudiants) — Inscription : 2023
Filière : Biologie
DIAKABOU Minion Chance Fresnel (M) – 2002-04-19 – Tél : 06-471-1236
KIBOULOU Veronique-Orchidée (F) – 2005-05-20 – Tél : 06-595-9438
KILOMBO Gloire Belvie (F) – 2004-11-02 – Tél : 06-486-9176
MALALOU Edemond Jessie (M) – 2005-04-01 – Tél : 06-982-0292
MAMBOU MALIA Espoire (F) – 2004-07-20 – Tél : 06-496-7767
MAVOUNGOU Berdrina Rubene (F) – 2002-08-01 – Tél : 06-493-9440
MBOMBA NGAMBA Benisse Caberlise (F) – 2005-03-02 – Tél : 06-573-6006
MOUANDA France Chadelvie (F) – 2004-04-04 – Tél : 06-651-4254
MOUNDOUNGA SIMBOU Gloria Marlyta (F) – 2004-01-20 – Tél : 06-175-8146
MOUYOKI MBOYO Clara Bel-monde (F) – 2005-03-12 – Tél : 05-317-5624
MPEMBA TATY Chris-Béni (M) – 2004-08-25 – Tél : 06-874-7302
VAMBA Emmanuelle Van-liane Judelvie (F) – 2007-03-15 – Tél : 05-667-6141

Filière : Chimie
BABATILA Frida Sandrine Nathalie (F) – 2004-04-30 – Tél : 06-639-9038
BANSIMBA MOUSSOUNOU Sandrine (F) – 2005-11-19 – Tél : 06-607-9694
BOUKAKA MOUANGA Jhivel (M) – 2004-01-01 – Tél : 06-906-2461
IBARA Pierre Alexandre (M) – 2005-01-08 – Tél : 05-012-3264
KOLYARDO Marie-cecille Euréka (F) – 2005-11-12 – Tél : 05-322-5093
MAGNOUNGOU FELINA Bernhyse Géraldine (F) – 2005-04-27 – Tél : 06-877-6349
NZELI ENOW Chance Mavie (F) – 2004-08-11 – Tél : 06-707-6779

Filière : Géosciences
EKORONG Rose Martialle (F) – 2002-01-29 – Tél : 06-867-9788
KOUBAKA NTONDELE Divine Sereina (F) – 2004-01-04 – Tél : 04-010-4710
MAPAKO NDENDE Grâce Colombe Princilia (F) – 2006-04-17 – Tél : 06-507-4794
MATONDO Merveil Christopher (M) – 2006-03-15 – Tél : 06-894-2879
MAVOUNGOU Vera Tchiecesse (M) – 2004-01-23 – Tél : 06-883-5867
MBOUI MAESSIE Emmanuelle Fleurine (F) – 2005-12-11 – Tél : 06-819-8266
MILANDOU Clesh Dristin (M) – 2005-05-11 – Tél : 06-934-8515
MONDJILI DUBERMANN Michel Eurêka (M) – 2006-03-27 – Tél : 06-507-6929
MONGO Joy Godlove (M) – Matricule : UCCB23FSTMONJO00029 – Email : joygodlovemongo@gmail.com – Réintégré
MOUKILOU DANZA Kenn Daniella (F) – 2004-08-01 – Tél : 06-709-5029
NGUEMBO MABIALA Bruno Bélone (M) – 2005-05-03 – Tél : 06-556-6516
NZAMBA MAEVI Dolorès Naomie (F) – 2004-07-13 – Tél : 06-713-6451
NZIECK Héléna-Joy (F) – 2005-11-08 – Tél : 06-659-2264
SAMOUNGANA Adelina Fortuné (F) – 2005-12-27 – Tél : 06-402-3533
SANGA Exaucé Amour (F) – Matricule : UCCB23FSTSANEX00044 – Email : exauceamoursanga@gmail.com – Réintégré
SEHOLO BONGO Déo-Gracias (M) – 2005-08-25 – Tél : 06-448-3096

Filière : Informatique
GACKOSSO Cherubin Junior (M) – 2002-09-07 – Tél : 06-885-8706
LYSHÂ-MAKOSSO Jurs Shakti (F) – 2005-06-16 – Tél : 06-614-2616
MPANDZOU OTÔ LENGOUENZE Life Obvious (M) – Matricule : UCCB23FSTMPALI00034 – Tél : 06-685-8845 – Réintégré
OMBANDZA OMBI Carlin Leroi (M) – 2005-06-05 – Tél : 05-619-9317
POATY TCHICAYA Josué Parfait (M) – 2005-08-05 – Tél : 06-575-8058
TCHISSAMBOU Nacy Ivann (M) – 2005-05-06 – Tél : 06-500-3330

Filière : Physique
BA MISSAMOU Macylan Dieuveille (M) – Matricule : UCCB23FSTBAMA00001 – Réintégré
KOUBIKANI-MBOUI Victoire-Jeph (M) – 2005-04-04 – Tél : 06-843-6515
MAYANDZI MAHOUNGOU Thérésa Rosemonde (F) – 2006-06-20 – Tél : 06-858-8220
NKOUKA Once Capriani (F) – 2005-08-06 – Tél : 04-440-3413
TATI KOULESSE Saxe Dervick (M) – 2006-02-23 – Tél : 06-899-4074
"""

