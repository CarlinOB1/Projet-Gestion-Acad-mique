"""
generer_sessions.py — prépare les sessions du test de charge (étape 3 du plan
« solidité et sécurité »).

Pourquoi : la connexion est limitée à 120 tentatives par minute et par
adresse. Faire se connecter 300 utilisateurs virtuels depuis le même poste
mesurerait cette limite, pas l'application. On fabrique donc à l'avance un
jeton d'accès par compte, exactement comme le ferait une connexion réussie.

Le fichier produit contient des jetons valides 30 minutes : il ne doit jamais
être placé dans le dépôt ni dans `edt-frontend/public/`. Le ranger dans un
dossier temporaire et le supprimer après le test.

Usage (sur la base jetable, JAMAIS sur la base de développement) :
    DB_NAME=edt_charge ./.venv/Scripts/python.exe charge/generer_sessions.py <fichier_sortie.json>
"""
import json
import os
import sys
from datetime import timedelta

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Gestion_edt.settings")
django.setup()

from django.conf import settings  # noqa: E402

from EDT_app.authentication import CustomTokenObtainPairSerializer  # noqa: E402
from EDT_app.models import Enseignant, Etudiant, Seance  # noqa: E402

NB_ETUDIANTS = 300
NB_ENSEIGNANTS = 40


def jeton(user):
    return str(CustomTokenObtainPairSerializer.get_token(user).access_token)


def main(sortie):
    base = settings.DATABASES["default"]["NAME"]
    if base != "edt_charge":
        sys.exit(f"Refus : base « {base} ». Ce script ne tourne que sur edt_charge (DB_NAME=edt_charge).")

    premiere = Seance.objects.filter(statut="Confirmée").order_by("date_seance").first()
    if premiere is None:
        sys.exit("Aucune séance confirmée : lancer seed.py sur edt_charge d'abord.")
    # Une semaine pleine, deux semaines après le début des cours.
    lundi = premiere.date_seance - timedelta(days=premiere.date_seance.weekday()) + timedelta(weeks=2)

    etudiants = list(
        Etudiant.objects.filter(profil__statut="actif")
        .select_related("profil__user", "classe")[:NB_ETUDIANTS]
    )
    chefs = list(
        Enseignant.objects.filter(departements_diriges__isnull=False, profil__statut="actif")
        .select_related("profil__user").distinct()
    )
    enseignants = list(
        Enseignant.objects.filter(departements_diriges__isnull=True, profil__statut="actif")
        .select_related("profil__user")[:NB_ENSEIGNANTS]
    )

    sessions_chefs = []
    for chef in chefs:
        classes = list(
            Seance.objects.filter(classe__filiere__departement__chef=chef)
            .values_list("classe_id", "classe__semestre_id").distinct()[:10]
        )
        if classes:
            sessions_chefs.append({
                "jeton": jeton(chef.profil.user),
                "classes": [{"classe_id": c, "semestre_id": s} for c, s in classes],
            })

    donnees = {
        "semaine": lundi.isoformat(),
        "etudiants": [jeton(e.profil.user) for e in etudiants],
        "enseignants": [jeton(e.profil.user) for e in enseignants],
        "chefs": sessions_chefs,
        # Comptes réels pour la rafale de connexions (identifiants seulement,
        # le mot de passe est lu dans SEED_PASSWORD au moment du test).
        "identifiants_connexion": [e.profil.user.username for e in etudiants[:20]],
    }
    with open(sortie, "w", encoding="utf-8") as f:
        json.dump(donnees, f)
    print(
        f"Semaine {lundi} : {len(donnees['etudiants'])} étudiants, "
        f"{len(donnees['enseignants'])} enseignants, {len(sessions_chefs)} chefs -> {sortie}"
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
