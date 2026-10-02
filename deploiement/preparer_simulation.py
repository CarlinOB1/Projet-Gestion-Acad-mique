"""
Données de la simulation de mise en ligne (deploiement/simulation_production.py) :
un document de vérification, rangé dans le dossier de fichiers temporaire de
la simulation, et la session de l'étudiant qui a le droit de le télécharger.

    DB_NAME=edt_charge DJANGO_SECRET_KEY=<clé de la simulation> DJANGO_MEDIA_ROOT=<dossier> \
        python deploiement/preparer_simulation.py preparer|nettoyer <fichier_etat.json>

Refuse toute autre base que les bases jetables : jamais la base de travail.
"""
import json
import os
import sys

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Gestion_edt.settings")
if os.environ.get("DB_NAME") not in ("edt_charge", "edt_zap"):
    sys.exit("Refus : la simulation ne tourne que sur une base jetable (edt_charge ou edt_zap).")

import django  # noqa: E402

django.setup()

from django.core.files.base import ContentFile  # noqa: E402

from EDT_app.authentication import CustomTokenObtainPairSerializer as Jetons  # noqa: E402
from EDT_app.models import DocumentPedagogique, Etudiant, Seance  # noqa: E402

TITRE = "Document de vérification (simulation de mise en ligne)"
PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n"


def preparer(chemin_etat):
    seance = (
        Seance.objects.filter(statut="Confirmée", classe__etudiant__profil__statut="actif")
        .select_related("module", "enseignant").order_by("pk").first()
    )
    if seance is None:
        sys.exit("Aucune séance confirmée dans une classe avec étudiants : lancer seed.py sur cette base.")
    etudiant = Etudiant.objects.filter(classe=seance.classe, profil__statut="actif").select_related("profil__user").first()
    document = DocumentPedagogique(titre=TITRE, module=seance.module, enseignant=seance.enseignant)
    document.fichier.save("verification.pdf", ContentFile(PDF), save=False)
    document.save()
    with open(chemin_etat, "w", encoding="utf-8") as f:
        json.dump({
            "document": document.pk,
            "jeton_etudiant": str(Jetons.get_token(etudiant.profil.user).access_token),
        }, f)


def nettoyer(chemin_etat):
    with open(chemin_etat, encoding="utf-8") as f:
        etat = json.load(f)
    for document in DocumentPedagogique.objects.filter(pk=etat["document"], titre=TITRE):
        document.fichier.delete(save=False)
        document.delete()


if __name__ == "__main__":
    {"preparer": preparer, "nettoyer": nettoyer}[sys.argv[1]](sys.argv[2])
