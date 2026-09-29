# tests_securite.py
#
# Tests du durcissement de sécurité (audit du 2026-09-18) :
#   - périmètre des données personnelles (étudiants, enseignants, inscriptions) ;
#   - limitation du nombre de tentatives de connexion ;
#   - durée de vie des jetons ;
#   - téléchargement protégé et validation des fichiers téléversés.
#
# Dans le style des autres fichiers de tests : authentification directe via
# force_authenticate (sauf pour le login, testé pour de vrai), helpers locaux.
#
# Lancement :
#   ./.venv/Scripts/python.exe manage.py test EDT_app.tests_securite --verbosity=2

import re
import shutil
import tempfile
from datetime import time, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from EDT_app.factories import (
    AffectationModuleFactory,
    AnneeAcademiqueFactory,
    ClasseFactory,
    DepartementFactory,
    EnseignantFactory,
    EtudiantFactory,
    FiliereFactory,
    MatiereFactory,
    ModuleFactory,
    ProfilFactory,
    SeanceFactory,
    Semestre1Factory,
)
from EDT_app.models import DocumentPedagogique, ReferentClasse


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def make_user(username, password="pass1234"):
    return User.objects.create_user(username=username, password=password)


def make_enseignant(username, departement):
    profil = ProfilFactory(user=make_user(username))
    return EnseignantFactory(profil=profil, departement=departement)


def make_etudiant(username, classe):
    profil = ProfilFactory(user=make_user(username))
    return EtudiantFactory(profil=profil, classe=classe)


def client_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def pks(response):
    """Identifiants (profil_id) des éléments d'une réponse paginée."""
    return sorted(item['profil_id'] for item in response.data['results'])


# ══════════════════════════════════════════════════════════════════════════════
# 1. PÉRIMÈTRE DES DONNÉES PERSONNELLES
# ══════════════════════════════════════════════════════════════════════════════

class PerimetreDonneesPersonnellesTest(TestCase):
    """
    Étudiant : uniquement lui-même. Enseignant simple : son département.
    Chef / référent : son périmètre. Responsable (superuser) : tout.
    """

    def setUp(self):
        self.annee = AnneeAcademiqueFactory()
        self.sem = Semestre1Factory(annee=self.annee)

        self.dept_a = DepartementFactory(libelle="Département Sécurité A")
        self.dept_b = DepartementFactory(libelle="Département Sécurité B")
        filiere_a = FiliereFactory(libelle="Filière Sécurité A", departement=self.dept_a)
        filiere_b = FiliereFactory(libelle="Filière Sécurité B", departement=self.dept_b)
        self.classe_a = ClasseFactory(filiere=filiere_a, semestre=self.sem, annee=self.annee)
        self.classe_b = ClasseFactory(filiere=filiere_b, semestre=self.sem, annee=self.annee)

        self.etu_a1 = make_etudiant("etu_a1", self.classe_a)
        self.etu_a2 = make_etudiant("etu_a2", self.classe_a)
        self.etu_b1 = make_etudiant("etu_b1", self.classe_b)

        self.ens_a1 = make_enseignant("ens_a1", self.dept_a)
        self.ens_a2 = make_enseignant("ens_a2", self.dept_a)
        self.ens_b1 = make_enseignant("ens_b1", self.dept_b)

        self.chef_a = make_enseignant("chef_a", self.dept_a)
        self.dept_a.chef = self.chef_a
        self.dept_a.save()

        self.admin = User.objects.create_superuser("admin_secu", password="pass1234")

    # ── Étudiant ─────────────────────────────────────────────────────────────

    def test_etudiant_ne_liste_que_sa_propre_fiche(self):
        resp = client_for(self.etu_a1.profil.user).get('/api/etudiants/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(pks(resp), [self.etu_a1.pk])

    def test_etudiant_ne_lit_pas_la_fiche_d_un_camarade(self):
        client = client_for(self.etu_a1.profil.user)
        # Même classe, autre classe : dans les deux cas, introuvable.
        self.assertEqual(client.get(f'/api/etudiants/{self.etu_a2.pk}/').status_code, 404)
        self.assertEqual(client.get(f'/api/etudiants/{self.etu_b1.pk}/').status_code, 404)

    def test_etudiant_lit_sa_propre_fiche(self):
        resp = client_for(self.etu_a1.profil.user).get(f'/api/etudiants/{self.etu_a1.pk}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_etudiant_ne_liste_aucun_enseignant(self):
        resp = client_for(self.etu_a1.profil.user).get('/api/enseignants/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(pks(resp), [])

    def test_etudiant_ne_lit_pas_la_fiche_d_un_enseignant(self):
        resp = client_for(self.etu_a1.profil.user).get(f'/api/enseignants/{self.ens_a1.pk}/')
        self.assertEqual(resp.status_code, 404)

    # ── Enseignant simple ────────────────────────────────────────────────────

    def test_enseignant_simple_ne_liste_que_les_etudiants_de_son_departement(self):
        resp = client_for(self.ens_a1.profil.user).get('/api/etudiants/')
        self.assertEqual(pks(resp), sorted([self.etu_a1.pk, self.etu_a2.pk]))

    def test_enseignant_simple_ne_lit_pas_un_etudiant_d_un_autre_departement(self):
        resp = client_for(self.ens_a1.profil.user).get(f'/api/etudiants/{self.etu_b1.pk}/')
        self.assertEqual(resp.status_code, 404)

    def test_enseignant_simple_ne_liste_que_les_enseignants_de_son_departement(self):
        resp = client_for(self.ens_a1.profil.user).get('/api/enseignants/')
        attendus = sorted([self.ens_a1.pk, self.ens_a2.pk, self.chef_a.pk])
        self.assertEqual(pks(resp), attendus)

    def test_enseignant_simple_ne_lit_pas_un_enseignant_d_un_autre_departement(self):
        resp = client_for(self.ens_a1.profil.user).get(f'/api/enseignants/{self.ens_b1.pk}/')
        self.assertEqual(resp.status_code, 404)

    # ── Chef de département : comportement existant conservé ─────────────────

    def test_chef_ne_liste_que_son_departement_par_defaut(self):
        client = client_for(self.chef_a.profil.user)
        etudiants = client.get('/api/etudiants/')
        self.assertEqual(pks(etudiants), sorted([self.etu_a1.pk, self.etu_a2.pk]))
        enseignants = client.get('/api/enseignants/')
        self.assertNotIn(self.ens_b1.pk, pks(enseignants))

    def test_chef_voit_tous_les_enseignants_sur_demande_explicite(self):
        # Formulaires d'affectation inter-départements.
        resp = client_for(self.chef_a.profil.user).get('/api/enseignants/?tous_departements=1')
        self.assertIn(self.ens_b1.pk, pks(resp))
        self.assertIn(self.ens_a1.pk, pks(resp))

    # ── Responsable / admin ──────────────────────────────────────────────────

    def test_admin_voit_tout(self):
        client = client_for(self.admin)
        self.assertEqual(
            pks(client.get('/api/etudiants/')),
            sorted([self.etu_a1.pk, self.etu_a2.pk, self.etu_b1.pk]),
        )
        self.assertIn(self.ens_b1.pk, pks(client.get('/api/enseignants/')))

    # ── Inscriptions : même donnée personnelle, autre porte d'entrée ─────────

    def test_enseignant_simple_ne_voit_que_les_inscriptions_de_son_departement(self):
        self.etu_a1.reinscrire(self.classe_a)
        self.etu_b1.reinscrire(self.classe_b)
        resp = client_for(self.ens_a1.profil.user).get('/api/inscriptions/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        classes = {item['classe']['id'] for item in resp.data['results']}
        self.assertEqual(classes, {self.classe_a.pk})


# ══════════════════════════════════════════════════════════════════════════════
# 2. AUTHENTIFICATION : LIMITATION DES TENTATIVES ET JETONS
# ══════════════════════════════════════════════════════════════════════════════

class LimitationConnexionTest(TestCase):
    """
    5 tentatives par minute et par (adresse, compte) : un attaquant qui vise un
    compte est freiné, sans bloquer les autres étudiants qui partagent la même
    adresse réseau (NAT de l'université).
    """

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        for nom in ("cible_secu", "autre_secu"):
            ProfilFactory(user=make_user(nom, password="Bon-mot-de-passe-42"))

    def _login(self, username, password="mauvais"):
        return APIClient().post(
            '/api/token/', {'username': username, 'password': password}, format='json'
        )

    def test_six_tentatives_sur_le_meme_compte_sont_limitees(self):
        for _ in range(5):
            self.assertEqual(self._login("cible_secu").status_code, 401)
        self.assertEqual(self._login("cible_secu").status_code, 429)

    def test_le_bon_mot_de_passe_ne_passe_pas_une_fois_limite(self):
        for _ in range(5):
            self._login("cible_secu")
        resp = self._login("cible_secu", password="Bon-mot-de-passe-42")
        self.assertEqual(resp.status_code, 429)

    def test_un_autre_compte_depuis_la_meme_adresse_n_est_pas_bloque(self):
        for _ in range(6):
            self._login("cible_secu")
        resp = self._login("autre_secu", password="Bon-mot-de-passe-42")
        self.assertEqual(resp.status_code, 200)

    def test_connexion_normale_reste_possible(self):
        resp = self._login("cible_secu", password="Bon-mot-de-passe-42")
        self.assertEqual(resp.status_code, 200)
        self.assertIn('access', resp.data)


class ParametresSecuriteTest(SimpleTestCase):

    def test_duree_de_vie_des_jetons_raisonnable(self):
        self.assertLessEqual(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'], timedelta(hours=1))
        self.assertLessEqual(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'], timedelta(days=1))

    def test_middleware_cors_avant_common_et_sans_doublon(self):
        mw = settings.MIDDLEWARE
        self.assertEqual(mw.count('django.middleware.common.CommonMiddleware'), 1)
        self.assertLess(
            mw.index('corsheaders.middleware.CorsMiddleware'),
            mw.index('django.middleware.common.CommonMiddleware'),
        )

    def test_mot_de_passe_minimum_10_caracteres(self):
        validateur = next(
            v for v in settings.AUTH_PASSWORD_VALIDATORS if v['NAME'].endswith('MinimumLengthValidator')
        )
        self.assertGreaterEqual(validateur.get('OPTIONS', {}).get('min_length', 8), 10)

    def test_limitation_globale_configuree(self):
        rates = settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']
        self.assertIn('anon', rates)
        self.assertIn('user', rates)
        self.assertTrue(settings.REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'])


# ══════════════════════════════════════════════════════════════════════════════
# 3. DOCUMENTS : TÉLÉCHARGEMENT PROTÉGÉ ET VALIDATION DES FICHIERS
# ══════════════════════════════════════════════════════════════════════════════

PDF_MINIMAL = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n"
ZIP_MINIMAL = b"PK\x03\x04" + b"\x00" * 60           # signature commune docx/xlsx/pptx
OLE_MINIMAL = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 60  # doc/xls/ppt anciens
EXE_DEGUISE = b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 60        # exécutable Windows


class DocumentsSecuriteTest(TestCase):

    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=self.media)
        override.enable()
        self.addCleanup(override.disable)

        self.annee = AnneeAcademiqueFactory()
        self.sem = Semestre1Factory(annee=self.annee)
        self.dept = DepartementFactory(libelle="Département Documents")
        filiere = FiliereFactory(libelle="Filière Documents", departement=self.dept)
        self.classe = ClasseFactory(filiere=filiere, semestre=self.sem, annee=self.annee)
        matiere = MatiereFactory(libelle="Matière Documents", departement=self.dept)
        self.module = ModuleFactory(
            libelle="Module Documents", matiere=matiere, semestre=self.sem, credits=6
        )
        self.prof = make_enseignant("prof_docs", self.dept)

        # Lien module <-> classe : c'est ce qui donne accès aux étudiants.
        SeanceFactory(
            module=self.module, enseignant=self.prof, classe=self.classe,
            annee=self.annee, date_seance=self.sem.date_debut, type_seance="CM",
            heure_debut=time(9, 0), heure_fin=time(11, 0), statut="Confirmée",
        )
        self.etu = make_etudiant("etu_docs", self.classe)

        autre_filiere = FiliereFactory(libelle="Filière Documents 2", departement=self.dept)
        autre_classe = ClasseFactory(filiere=autre_filiere, semestre=self.sem, annee=self.annee)
        self.etu_hors_module = make_etudiant("etu_hors_module", autre_classe)

    def _deposer(self, nom="cours.pdf", contenu=PDF_MINIMAL, client=None):
        client = client or client_for(self.prof.profil.user)
        return client.post(
            '/api/documents/',
            {
                'titre': 'Support',
                'type_doc': 'cours',
                'module_id': self.module.pk,
                'fichier': SimpleUploadedFile(nom, contenu),
            },
            format='multipart',
        )

    def _document_existant(self):
        resp = self._deposer()
        self.assertEqual(resp.status_code, 201, resp.data)
        return DocumentPedagogique.objects.get(pk=resp.data['id'])

    # ── Téléchargement protégé ───────────────────────────────────────────────

    def test_telechargement_refuse_sans_authentification(self):
        doc = self._document_existant()
        resp = APIClient().get(f'/api/documents/{doc.pk}/telecharger/')
        self.assertEqual(resp.status_code, 401)

    def test_etudiant_du_module_telecharge_le_fichier(self):
        doc = self._document_existant()
        resp = client_for(self.etu.profil.user).get(f'/api/documents/{doc.pk}/telecharger/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(b"".join(resp.streaming_content), PDF_MINIMAL)
        self.assertIn('attachment', resp['Content-Disposition'])

    def test_etudiant_hors_module_ne_telecharge_pas(self):
        doc = self._document_existant()
        resp = client_for(self.etu_hors_module.profil.user).get(
            f'/api/documents/{doc.pk}/telecharger/'
        )
        self.assertEqual(resp.status_code, 404)

    def test_le_lien_expose_par_l_api_passe_par_l_api_et_pas_par_media(self):
        doc = self._document_existant()
        resp = client_for(self.etu.profil.user).get(f'/api/documents/{doc.pk}/')
        url = resp.data['fichier_url']
        self.assertTrue(url.endswith(f'/api/documents/{doc.pk}/telecharger/'), url)
        self.assertNotIn('/media/', url)

    @override_settings(PROTECTED_MEDIA_INTERNAL_PREFIX='/protected_media/')
    def test_en_production_nginx_sert_le_fichier_via_x_accel_redirect(self):
        doc = self._document_existant()
        resp = client_for(self.etu.profil.user).get(f'/api/documents/{doc.pk}/telecharger/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['X-Accel-Redirect'], '/protected_media/' + doc.fichier.name)
        self.assertEqual(resp.content, b"")

    # ── Noms de fichiers non devinables ──────────────────────────────────────

    def test_le_fichier_est_range_sous_un_dossier_aleatoire(self):
        doc = self._document_existant()
        self.assertRegex(doc.fichier.name, r'^documents/\d{4}/\d{2}/[0-9a-f]{32}/cours\.pdf$')

    def test_le_nom_affiche_reste_le_nom_d_origine(self):
        resp = self._deposer(nom="cours.pdf")
        self.assertEqual(resp.data['nom_fichier'], 'cours.pdf')

    def test_les_photos_de_profil_sont_rangees_sous_un_dossier_aleatoire(self):
        from EDT_app.models import chemin_photo
        self.assertRegex(chemin_photo(None, 'moi.png'), r'^profils/[0-9a-f]{32}/moi\.png$')

    # ── Validation du contenu ────────────────────────────────────────────────

    def test_pdf_valide_accepte(self):
        self.assertEqual(self._deposer("a.pdf", PDF_MINIMAL).status_code, 201)

    def test_docx_valide_accepte(self):
        self.assertEqual(self._deposer("a.docx", ZIP_MINIMAL).status_code, 201)

    def test_doc_ancien_format_accepte(self):
        self.assertEqual(self._deposer("a.doc", OLE_MINIMAL).status_code, 201)

    def test_texte_accepte(self):
        self.assertEqual(self._deposer("a.txt", "Bonjour é".encode('utf-8')).status_code, 201)

    def test_executable_renomme_en_pdf_refuse(self):
        resp = self._deposer("faux.pdf", EXE_DEGUISE)
        self.assertEqual(resp.status_code, 400)
        self.assertIn('fichier', resp.data)

    def test_pdf_renomme_en_docx_refuse(self):
        self.assertEqual(self._deposer("faux.docx", PDF_MINIMAL).status_code, 400)

    def test_texte_binaire_refuse(self):
        self.assertEqual(self._deposer("faux.txt", b"\x00\x01\x02\xff\xfe" * 20).status_code, 400)

    def test_extension_non_autorisee_toujours_refusee(self):
        self.assertEqual(self._deposer("page.html", b"<script>1</script>").status_code, 400)

    @override_settings(DOCUMENT_MAX_UPLOAD_BYTES=1024)
    def test_fichier_trop_volumineux_refuse(self):
        resp = self._deposer("gros.pdf", PDF_MINIMAL + b"0" * 2048)
        self.assertEqual(resp.status_code, 400)
        self.assertIn('fichier', resp.data)

    @override_settings(DOCUMENT_MAX_UPLOAD_BYTES=1024)
    def test_fichier_a_la_limite_accepte(self):
        contenu = PDF_MINIMAL + b"0" * (1024 - len(PDF_MINIMAL))
        self.assertEqual(self._deposer("limite.pdf", contenu).status_code, 201)


# ══════════════════════════════════════════════════════════════════════════════
# 4. DOCUMENTS : PÉRIMÈTRE DU MODULE CHOISI (module_id, POST et PATCH)
# ══════════════════════════════════════════════════════════════════════════════

class DocumentPerimetreModuleTest(TestCase):
    """
    DocumentPedagogiqueSerializer.validate() doit refuser, à la création
    comme à la modification, tout module hors du périmètre de l'enseignant
    connecté — même logique que perimetre.modules_autorises() côté lecture
    (DocumentViewSet.get_queryset(), ModuleViewSet) :
      - enseignant simple : seulement les modules qu'il dispense réellement
        (affectation ou séance), pas tout son département ;
      - chef de département : tout module de son département, même sans
        affectation/séance personnelle ;
      - référent de classe(s) : les modules utilisés dans ses classes en
        référence, même sans affectation/séance personnelle.
    """

    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=self.media)
        override.enable()
        self.addCleanup(override.disable)

        self.annee = AnneeAcademiqueFactory()
        self.sem = Semestre1Factory(annee=self.annee)

        self.dept = DepartementFactory(libelle="Département Périmètre Doc")
        self.autre_dept = DepartementFactory(libelle="Autre Département Doc")
        self.filiere = FiliereFactory(libelle="Filière Périmètre Doc", departement=self.dept)
        self.classe = ClasseFactory(filiere=self.filiere, semestre=self.sem, annee=self.annee)

        matiere = MatiereFactory(libelle="Matière Périmètre Doc", departement=self.dept)
        autre_matiere = MatiereFactory(libelle="Matière Autre Dept Doc", departement=self.autre_dept)

        # Module que "prof" dispense réellement (affectation directe).
        self.module_a = ModuleFactory(
            libelle="Module Dispensé", matiere=matiere, semestre=self.sem, credits=3,
        )
        self.prof = make_enseignant("prof_perimetre_doc", self.dept)
        AffectationModuleFactory(module=self.module_a, enseignant=self.prof)

        # Deuxième module dispensé par "prof", pour tester le PATCH vers un
        # module toujours dans son périmètre (doit rester accepté).
        self.module_a2 = ModuleFactory(
            libelle="Module Dispensé 2", matiere=matiere, semestre=self.sem, credits=3,
        )
        AffectationModuleFactory(module=self.module_a2, enseignant=self.prof)

        # Module du même département, mais que "prof" ne dispense pas.
        self.module_collegue = ModuleFactory(
            libelle="Module Collègue", matiere=matiere, semestre=self.sem, credits=3,
        )

        # Module d'un autre département.
        self.module_hors_dept = ModuleFactory(
            libelle="Module Hors Dept", matiere=autre_matiere, semestre=self.sem, credits=3,
        )

        self.chef = make_enseignant("chef_perimetre_doc", self.dept)
        self.dept.chef = self.chef
        self.dept.save()

        # Module utilisé dans une classe dont "referent" a la référence,
        # sans aucune affectation ni séance pour lui.
        self.classe_l1 = ClasseFactory(filiere=self.filiere, semestre=self.sem, annee=self.annee)
        self.module_l1 = ModuleFactory(
            libelle="Module Référent L1", matiere=matiere, semestre=self.sem, credits=3,
            classe=self.classe_l1,
        )
        self.referent = make_enseignant("referent_perimetre_doc", self.dept)
        ref = ReferentClasse.objects.create(enseignant=self.referent)
        ref.classes.add(self.classe_l1)

    def _deposer(self, user, module, nom="doc.pdf"):
        return client_for(user).post(
            '/api/documents/',
            {
                'titre': 'Support',
                'type_doc': 'cours',
                'module_id': module.pk,
                'fichier': SimpleUploadedFile(nom, PDF_MINIMAL),
            },
            format='multipart',
        )

    # ── Enseignant simple : seulement ses propres modules ────────────────────

    def test_enseignant_simple_upload_sur_son_module_accepte(self):
        resp = self._deposer(self.prof.profil.user, self.module_a)
        self.assertEqual(resp.status_code, 201, resp.data)

    def test_enseignant_simple_upload_sur_module_d_un_collegue_refuse(self):
        resp = self._deposer(self.prof.profil.user, self.module_collegue)
        self.assertEqual(resp.status_code, 400)
        self.assertIn('module_id', resp.data)

    def test_enseignant_simple_upload_sur_module_d_un_autre_departement_refuse(self):
        resp = self._deposer(self.prof.profil.user, self.module_hors_dept)
        self.assertEqual(resp.status_code, 400)
        self.assertIn('module_id', resp.data)

    # ── Chef de département : tout son département ───────────────────────────

    def test_chef_upload_sur_module_de_son_departement_non_dispense_accepte(self):
        resp = self._deposer(self.chef.profil.user, self.module_collegue)
        self.assertEqual(resp.status_code, 201, resp.data)

    def test_chef_upload_sur_module_d_un_autre_departement_refuse(self):
        resp = self._deposer(self.chef.profil.user, self.module_hors_dept)
        self.assertEqual(resp.status_code, 400)
        self.assertIn('module_id', resp.data)

    # ── Référent : les modules de ses classes en référence ────────────────────

    def test_referent_upload_sur_module_de_sa_classe_l1_accepte(self):
        resp = self._deposer(self.referent.profil.user, self.module_l1)
        self.assertEqual(resp.status_code, 201, resp.data)

    def test_referent_upload_hors_de_son_perimetre_refuse(self):
        # Même département, mais ni dispensé par lui, ni utilisé dans une de
        # ses classes en référence.
        resp = self._deposer(self.referent.profil.user, self.module_collegue)
        self.assertEqual(resp.status_code, 400)
        self.assertIn('module_id', resp.data)

    # ── Modification (PATCH) : la même règle s'applique à module_id ─────────

    def test_patch_module_id_vers_un_module_hors_perimetre_refuse(self):
        doc = DocumentPedagogique.objects.create(
            titre="Support", type_doc="cours", module=self.module_a, enseignant=self.prof,
            fichier=SimpleUploadedFile("doc.pdf", PDF_MINIMAL),
        )
        resp = client_for(self.prof.profil.user).patch(
            f'/api/documents/{doc.pk}/', {'module_id': self.module_collegue.pk}, format='json',
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('module_id', resp.data)
        doc.refresh_from_db()
        self.assertEqual(doc.module_id, self.module_a.pk)

    def test_patch_module_id_vers_un_module_dans_le_perimetre_accepte(self):
        doc = DocumentPedagogique.objects.create(
            titre="Support", type_doc="cours", module=self.module_a, enseignant=self.prof,
            fichier=SimpleUploadedFile("doc.pdf", PDF_MINIMAL),
        )
        resp = client_for(self.prof.profil.user).patch(
            f'/api/documents/{doc.pk}/', {'module_id': self.module_a2.pk}, format='json',
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        doc.refresh_from_db()
        self.assertEqual(doc.module_id, self.module_a2.pk)
