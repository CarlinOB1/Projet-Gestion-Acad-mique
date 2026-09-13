# tests_perimetre.py
#
# Tests unitaires dédiés à EDT_app/perimetre.py : classes_autorisees(),
# modules_autorises() et le helper privé _enseignant_courant().
#
# Contrairement à tests_complets.py / tests_affectation.py, ces tests
# n'appellent PAS l'API : ils appellent directement les fonctions du module
# sur des objets construits en base de test. L'objectif est d'isoler chaque
# branche métier (chef de département, référent de classe, cumul des deux,
# enseignant simple, accès illimité) de tout ce qui relève du HTTP, de
# l'authentification ou des sérialiseurs — ces couches sont déjà couvertes
# ailleurs.
#
# Lancement :
#   python manage.py test EDT_app.tests_perimetre --verbosity=2

from django.contrib.auth.models import User, Group
from django.test import TestCase

from EDT_app.factories import (
    ClasseFactory,
    DepartementFactory,
    EnseignantFactory,
    FiliereFactory,
    MatiereFactory,
    ModuleFactory,
    ProfilFactory,
    SeanceFactory,
)
from EDT_app.models import Classe, Departement, Module, ReferentClasse
from EDT_app.perimetre import _enseignant_courant, classes_autorisees, modules_autorises


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def make_user(username):
    """Crée un User Django nu (sans profil), pour tester les cas dégradés."""
    return User.objects.create_user(username=username, password="pass1234")


def make_responsable(username):
    """Utilisateur membre du groupe 'responsable' (accès illimité), avec profil."""
    user = make_user(username)
    grp, _ = Group.objects.get_or_create(name="responsable")
    user.groups.add(grp)
    ProfilFactory(user=user)
    return user


def make_enseignant(username, departement):
    """Utilisateur avec profil + Enseignant rattaché au département donné."""
    user = make_user(username)
    profil = ProfilFactory(user=user)
    return EnseignantFactory(profil=profil, departement=departement)


def make_referent(enseignant, classes):
    """Fait de l'enseignant donné le référent des classes listées."""
    referent = ReferentClasse.objects.create(enseignant=enseignant)
    referent.classes.set(classes)
    return referent


def ids(queryset):
    return set(queryset.values_list("id", flat=True))


# ══════════════════════════════════════════════════════════════════════════════
# _enseignant_courant
# ══════════════════════════════════════════════════════════════════════════════

class EnseignantCourantTest(TestCase):

    def test_utilisateur_sans_profil_retourne_none(self):
        """Un User Django sans Profil lié ne doit pas faire planter l'accès à user.profil."""
        user = make_user("sans_profil")
        self.assertIsNone(_enseignant_courant(user))

    def test_utilisateur_avec_profil_sans_enseignant_retourne_none(self):
        """Cas d'un profil étudiant : profil existe, mais pas profil.enseignant."""
        user = make_user("profil_etudiant")
        ProfilFactory(user=user)
        self.assertIsNone(_enseignant_courant(user))

    def test_utilisateur_avec_enseignant_retourne_lenseignant(self):
        dept = DepartementFactory()
        enseignant = make_enseignant("prof", dept)
        self.assertEqual(_enseignant_courant(enseignant.profil.user), enseignant)


# ══════════════════════════════════════════════════════════════════════════════
# classes_autorisees
# ══════════════════════════════════════════════════════════════════════════════

class ClassesAutoriseesTest(TestCase):

    def setUp(self):
        self.dept_a = DepartementFactory(libelle="Département A")
        self.dept_b = DepartementFactory(libelle="Département B")
        self.filiere_a = FiliereFactory(departement=self.dept_a)
        self.filiere_b = FiliereFactory(departement=self.dept_b)
        self.classe_a = ClasseFactory(filiere=self.filiere_a)
        self.classe_b = ClasseFactory(filiere=self.filiere_b)
        # Classe L1 : pas de filière (cf. commentaire du modèle Classe).
        self.classe_l1 = ClasseFactory(filiere=None, code="MIP")

    def test_superuser_a_un_acces_illimite(self):
        user = make_user("super")
        user.is_superuser = True
        user.save()
        self.assertIsNone(classes_autorisees(user))

    def test_groupe_responsable_a_un_acces_illimite(self):
        user = make_responsable("resp")
        self.assertIsNone(classes_autorisees(user))

    def test_sans_profil_enseignant_retourne_queryset_vide(self):
        user = make_user("etudiant")
        ProfilFactory(user=user)
        resultat = classes_autorisees(user)
        self.assertEqual(ids(resultat), set())

    def test_enseignant_simple_voit_uniquement_son_departement(self):
        enseignant = make_enseignant("prof_simple", self.dept_a)
        resultat = classes_autorisees(enseignant.profil.user)
        self.assertEqual(ids(resultat), {self.classe_a.id})
        self.assertNotIn(self.classe_b.id, ids(resultat))

    def test_chef_departement_voit_les_classes_de_son_departement(self):
        chef = make_enseignant("chef_a", self.dept_a)
        self.dept_a.chef = chef
        self.dept_a.save()
        resultat = classes_autorisees(chef.profil.user)
        self.assertEqual(ids(resultat), {self.classe_a.id})

    def test_chef_de_plusieurs_departements_voit_lunion(self):
        """
        Departement.clean() interdit normalement qu'un enseignant soit chef
        d'un département autre que le sien (son departement FK est unique) :
        ce cas n'est donc pas atteignable via le formulaire/API normal.
        perimetre.py reste toutefois défensif et boucle sur
        enseignant.departements_diriges.all() sans supposer qu'il n'y en a
        qu'un seul — on force donc l'état directement en base (update() ne
        déclenche pas full_clean(), contrairement à save()) pour vérifier
        que le code gère bien l'union sur plusieurs départements dirigés.
        """
        chef = make_enseignant("chef_multi", self.dept_a)
        Departement.objects.filter(pk=self.dept_a.pk).update(chef=chef)
        Departement.objects.filter(pk=self.dept_b.pk).update(chef=chef)
        resultat = classes_autorisees(chef.profil.user)
        self.assertEqual(ids(resultat), {self.classe_a.id, self.classe_b.id})

    def test_referent_seul_voit_uniquement_ses_classes_assignees(self):
        # Référent rattaché au département A, mais référent de la classe L1
        # (sans filière/département) : son accès ne doit venir QUE de
        # ReferentClasse, pas du filtre département.
        referent_ens = make_enseignant("referent_l1", self.dept_a)
        make_referent(referent_ens, [self.classe_l1])
        resultat = classes_autorisees(referent_ens.profil.user)
        self.assertEqual(ids(resultat), {self.classe_l1.id})
        self.assertNotIn(self.classe_a.id, ids(resultat))

    def test_cumul_chef_et_referent_additionne_les_deux_perimetres(self):
        """
        Cas mis en avant par le docstring de perimetre.py : un chef qui
        coordonne aussi une classe L1 doit voir l'union des deux périmètres,
        jamais un seul des deux (pas de if/elif exclusif caché).
        """
        chef_referent = make_enseignant("chef_referent", self.dept_a)
        self.dept_a.chef = chef_referent
        self.dept_a.save()
        make_referent(chef_referent, [self.classe_l1])

        resultat = classes_autorisees(chef_referent.profil.user)

        self.assertEqual(ids(resultat), {self.classe_a.id, self.classe_l1.id})
        self.assertNotIn(self.classe_b.id, ids(resultat))


# ══════════════════════════════════════════════════════════════════════════════
# modules_autorises
# ══════════════════════════════════════════════════════════════════════════════

class ModulesAutorisesTest(TestCase):

    def setUp(self):
        self.dept_a = DepartementFactory(libelle="Département A")
        self.dept_b = DepartementFactory(libelle="Département B")
        self.matiere_a = MatiereFactory(departement=self.dept_a)
        self.matiere_b = MatiereFactory(departement=self.dept_b)
        # Libellés explicites et uniques : ModuleFactory fait un
        # django_get_or_create sur (libelle, semestre), et son libelle par
        # défaut vient d'un factory.Iterator à 2 valeurs partagé entre tous
        # les tests — sans libelle explicite, deux modules du même test
        # peuvent silencieusement se résoudre au même enregistrement.
        self.module_a = ModuleFactory(libelle="Module A", matiere=self.matiere_a)
        self.module_b = ModuleFactory(libelle="Module B", matiere=self.matiere_b)

        self.filiere_a = FiliereFactory(departement=self.dept_a)
        self.classe_ref = ClasseFactory(filiere=self.filiere_a)

    def test_superuser_a_un_acces_illimite(self):
        user = make_user("super_mod")
        user.is_superuser = True
        user.save()
        self.assertIsNone(modules_autorises(user))

    def test_groupe_responsable_a_un_acces_illimite(self):
        user = make_responsable("resp_mod")
        self.assertIsNone(modules_autorises(user))

    def test_sans_profil_enseignant_retourne_queryset_vide(self):
        user = make_user("etudiant_mod")
        ProfilFactory(user=user)
        self.assertEqual(ids(modules_autorises(user)), set())

    def test_enseignant_simple_voit_les_modules_de_son_departement(self):
        enseignant = make_enseignant("prof_mod_simple", self.dept_a)
        resultat = modules_autorises(enseignant.profil.user)
        self.assertEqual(ids(resultat), {self.module_a.id})
        self.assertNotIn(self.module_b.id, ids(resultat))

    def test_chef_departement_voit_les_modules_des_matieres_dirigees(self):
        chef = make_enseignant("chef_mod", self.dept_a)
        self.dept_a.chef = chef
        self.dept_a.save()
        resultat = modules_autorises(chef.profil.user)
        self.assertEqual(ids(resultat), {self.module_a.id})

    def test_referent_voit_module_rattache_directement_a_sa_classe(self):
        # Module d'un département tiers, mais rattaché directement (FK classe)
        # à une classe dont l'enseignant est référent.
        dept_c = DepartementFactory(libelle="Département C")
        matiere_c = MatiereFactory(departement=dept_c)
        module_direct = ModuleFactory(libelle="Module Direct", matiere=matiere_c, classe=self.classe_ref)

        referent_ens = make_enseignant("referent_mod_direct", self.dept_b)
        make_referent(referent_ens, [self.classe_ref])

        resultat = modules_autorises(referent_ens.profil.user)
        self.assertEqual(ids(resultat), {module_direct.id})

    def test_referent_voit_module_accessible_seulement_via_une_seance(self):
        """
        Un module peut n'avoir aucune FK directe vers la classe (module.classe
        est vide) et n'être relié à la classe référencée que par une Seance
        planifiée dessus. C'est le cas explicitement documenté dans
        perimetre.modules_autorises : 'utilisé dedans via une séance planifiée'.
        """
        dept_c = DepartementFactory(libelle="Département D")
        matiere_c = MatiereFactory(departement=dept_c)
        module_via_seance = ModuleFactory(libelle="Module Via Seance", matiere=matiere_c, classe=None)
        SeanceFactory(module=module_via_seance, classe=self.classe_ref)

        referent_ens = make_enseignant("referent_mod_seance", self.dept_b)
        make_referent(referent_ens, [self.classe_ref])

        resultat = modules_autorises(referent_ens.profil.user)
        self.assertIn(module_via_seance.id, ids(resultat))

    def test_module_rattache_et_via_seance_napparait_quune_fois(self):
        """Le .distinct() du code doit dédupliquer un module atteint par les
        deux chemins (classe directe ET séance) à la fois."""
        dept_c = DepartementFactory(libelle="Département E")
        matiere_c = MatiereFactory(departement=dept_c)
        module_double = ModuleFactory(libelle="Module Double", matiere=matiere_c, classe=self.classe_ref)
        SeanceFactory(module=module_double, classe=self.classe_ref)

        referent_ens = make_enseignant("referent_mod_double", self.dept_b)
        make_referent(referent_ens, [self.classe_ref])

        resultat = modules_autorises(referent_ens.profil.user)
        self.assertEqual(list(resultat.values_list("id", flat=True)).count(module_double.id), 1)

    def test_cumul_chef_et_referent_additionne_les_deux_perimetres(self):
        chef_referent = make_enseignant("chef_referent_mod", self.dept_a)
        self.dept_a.chef = chef_referent
        self.dept_a.save()

        dept_c = DepartementFactory(libelle="Département F")
        matiere_c = MatiereFactory(departement=dept_c)
        module_referent = ModuleFactory(libelle="Module Referent", matiere=matiere_c, classe=self.classe_ref)
        make_referent(chef_referent, [self.classe_ref])

        resultat = modules_autorises(chef_referent.profil.user)

        self.assertEqual(ids(resultat), {self.module_a.id, module_referent.id})
        self.assertNotIn(self.module_b.id, ids(resultat))

    def test_module_hors_perimetre_est_exclu(self):
        """Contrôle négatif : ni département dirigé, ni classe référencée."""
        enseignant = make_enseignant("prof_hors_perimetre", self.dept_a)
        resultat = modules_autorises(enseignant.profil.user)
        self.assertNotIn(self.module_b.id, ids(resultat))
