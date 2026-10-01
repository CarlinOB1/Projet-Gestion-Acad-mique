"""
Données des tests navigateur (Playwright), sur la base jetable `edt_charge`.

    preparer_base.py preparer <fichier_etat.json>
    preparer_base.py nettoyer <fichier_etat.json>

Lancé par `global-setup.js` / `global-teardown.js` depuis la racine du
projet, avec les mêmes variables que le serveur des tests :
  - DB_NAME=edt_charge : refuse toute autre base (jamais la base de travail) ;
  - DJANGO_SECRET_KEY tirée au hasard à chaque lancement : les sessions
    créées ici ne valent rien sur un autre serveur ;
  - DJANGO_MEDIA_ROOT : dossier temporaire, les fichiers déposés n'arrivent
    pas dans media/.

Les comptes de test (préfixe « e2e. ») reçoivent un mot de passe tiré au
hasard à chaque lancement. Le fichier d'état, qui contient ces mots de passe
et des sessions, est écrit hors du dépôt et effacé par `nettoyer`.
"""
import json
import os
import secrets
import sys
from datetime import date, timedelta

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Gestion_edt.settings")
if os.environ.get("DB_NAME") != "edt_charge":
    sys.exit("Refus : les tests navigateur ne tournent que sur la base jetable edt_charge.")
if not os.environ.get("DJANGO_SECRET_KEY") or not os.environ.get("DJANGO_MEDIA_ROOT"):
    sys.exit("Refus : DJANGO_SECRET_KEY et DJANGO_MEDIA_ROOT propres aux tests sont obligatoires.")

import django  # noqa: E402

django.setup()

from django.contrib.auth.models import User  # noqa: E402
from django.core.exceptions import ValidationError  # noqa: E402
from django.core.files.base import ContentFile  # noqa: E402
from django.db import transaction  # noqa: E402

from EDT_app.authentication import CustomTokenObtainPairSerializer as Jetons  # noqa: E402
from EDT_app.models import (  # noqa: E402
    Departement, DocumentPedagogique, Enseignant, Etudiant, Module, Profil, Seance,
)
from EDT_app.validation_seance import BLOCS_JOURNEE  # noqa: E402

PREFIXE = "e2e."
# Code qui s'exécuterait si l'interface insérait ce texte comme du HTML.
CODE_PIEGE = '<img src=x onerror="window.__xss=(window.__xss||0)+1">'
PDF_MINIMAL = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def lundi_de(jour):
    return jour - timedelta(days=jour.weekday())


def session(user):
    """Contenu de `edt-auth` (localStorage) pour ce compte, comme après connexion."""
    jeton = Jetons.get_token(user)
    return {
        "accessToken": str(jeton.access_token),
        "refreshToken": str(jeton),
        "user": {
            "id": user.pk, "username": user.username,
            "nom_complet": Jetons._get_nom_complet(user), "role": Jetons._get_role(user),
            "statut": "actif", "photo": None, "departement_id": Jetons._get_departement_id(user),
        },
    }


def compte(username, prenom="E2E", nom="Test", **extra):
    mot_de_passe = secrets.token_urlsafe(18)
    user = User.objects.create_user(
        username=PREFIXE + username, password=mot_de_passe, first_name=prenom, last_name=nom, **extra,
    )
    return user, mot_de_passe


def etudiant(username, classe, matricule):
    user, mdp = compte(username)
    profil = Profil.objects.create(user=user, genre="F")
    etu = Etudiant.objects.create(profil=profil, matricule=matricule, classe=classe)
    etu.reinscrire(classe)
    return user, mdp


def nettoyer():
    with transaction.atomic():
        e2e = User.objects.filter(username__startswith=PREFIXE)
        enseignants = Enseignant.objects.filter(profil__user__in=e2e)
        for doc in DocumentPedagogique.objects.filter(enseignant__in=enseignants):
            doc.delete()  # efface aussi le fichier
        Seance.objects.filter(enseignant__in=enseignants).delete()
        Module.objects.filter(libelle=CODE_PIEGE).delete()
        Departement.objects.filter(chef__in=enseignants).update(chef=None)
        Departement.objects.filter(libelle="Département E2E").delete()
        for user in e2e:
            if hasattr(user, "profil") and hasattr(user.profil, "etudiant"):
                user.profil.etudiant.inscriptions.all().delete()
        enseignants.delete()
        e2e.delete()


def creneau_libre(classe, enseignant, module, debut_semaine):
    """Premier créneau de la semaine accepté par toutes les règles d'une séance."""
    for decalage in range(6):
        jour = debut_semaine + timedelta(days=decalage)
        for debut, fin in BLOCS_JOURNEE:
            seance = Seance(
                module=module, enseignant=enseignant, classe=classe, annee=classe.annee,
                date_seance=jour, heure_debut=debut, heure_fin=fin, type_seance="CM",
                statut="Confirmée",
            )
            try:
                seance.save()
                return seance
            except ValidationError:
                continue
    raise SystemExit("Aucun créneau libre cette semaine pour la séance de test.")


def preparer(chemin_etat):
    nettoyer()
    aujourdhui = date.today()
    semaine = lundi_de(aujourdhui)

    # Une séance confirmée cette semaine donne la classe, le module et le chef
    # de référence : le planning affiché par défaut n'est donc pas vide.
    reference = (
        Seance.objects.filter(
            statut="Confirmée", date_seance__range=(semaine, semaine + timedelta(days=5)),
            classe__filiere__departement__chef__isnull=False,
        )
        .select_related("classe__filiere__departement__chef__profil__user", "module__matiere__departement")
        .order_by("classe_id", "date_seance")
        .first()
    )
    if reference is None:
        raise SystemExit("Aucune séance confirmée cette semaine dans edt_charge : relancer seed.py.")
    classe = reference.classe
    departement = reference.module.matiere.departement
    chef_reel = classe.filiere.departement.chef.profil.user
    autre_classe = (
        classe.semestre.classe_set.exclude(pk=classe.pk).exclude(modules=reference.module).first()
    )

    with transaction.atomic():
        etu, mdp_etu = etudiant("etudiant", classe, "ETU-99001")
        suspendu, _ = etudiant("suspendu", classe, "ETU-99002")
        autre, _ = etudiant("autre", autre_classe, "ETU-99003")

        ens_user, mdp_ens = compte("enseignant", prenom=CODE_PIEGE, nom="Piégé")
        ens = Enseignant.objects.create(
            profil=Profil.objects.create(user=ens_user, genre="M"),
            grade="Docteur", contrat="Vacataire", departement=departement,
        )

        chef_user, mdp_chef = compte("chef")
        chef = Enseignant.objects.create(
            profil=Profil.objects.create(user=chef_user, genre="M"),
            grade="Docteur", contrat="Permanent", departement=departement,
        )
        Departement.objects.create(libelle="Département E2E", faculte=departement.faculte, chef=chef)

        admin, mdp_admin = compte("admin", is_superuser=True, is_staff=True)

        # Module et document dont le nom contient du code : l'interface doit
        # l'afficher comme du texte, sans jamais l'exécuter.
        module_piege = Module.objects.create(
            libelle=CODE_PIEGE, credits=2, matiere=reference.module.matiere,
            semestre=classe.semestre, classe=classe, heures_cm=24,
        )
        seance_piege = creneau_libre(classe, ens, module_piege, semaine)
        document = DocumentPedagogique(titre=CODE_PIEGE, module=reference.module, enseignant=ens)
        document.fichier.save("support-e2e.pdf", ContentFile(PDF_MINIMAL), save=False)
        document.save()

    etat = {
        "comptes": {
            "etudiant": {"username": etu.username, "password": mdp_etu},
            "enseignant": {"username": ens_user.username, "password": mdp_ens},
            "chef": {"username": chef_user.username, "password": mdp_chef},
            "admin": {"username": admin.username, "password": mdp_admin},
        },
        "sessions": {
            "etudiant": session(etu),
            "suspendu": session(suspendu),
            "autre": session(autre),
            "enseignant": session(ens_user),
            "chef_reel": session(chef_reel),
            "admin": session(admin),
        },
        "donnees": {
            "classe_id": classe.pk,
            "classe_libelle": classe.libelle,
            "semestre_id": classe.semestre_id,
            "module_reference_id": reference.module_id,
            "module_reference_libelle": reference.module.libelle,
            "enseignant_reference_id": reference.enseignant_id,
            "suspendu_profil_id": suspendu.profil.pk,
            "document_id": document.pk,
            "seance_piege_date": str(seance_piege.date_seance),
            "lundi": str(semaine),
            "code_piege": CODE_PIEGE,
        },
    }
    with open(chemin_etat, "w", encoding="utf-8") as f:
        json.dump(etat, f, ensure_ascii=False)
    print("données e2e prêtes :", classe.libelle)


if __name__ == "__main__":
    action, chemin = sys.argv[1], sys.argv[2]
    if action == "preparer":
        preparer(chemin)
    elif action == "nettoyer":
        nettoyer()
        if os.path.exists(chemin):
            os.remove(chemin)
        print("données e2e effacées")
    else:
        sys.exit(f"action inconnue : {action}")
