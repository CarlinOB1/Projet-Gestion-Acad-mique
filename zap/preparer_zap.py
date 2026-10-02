"""
Prépare le scan ZAP sur la base jetable `edt_zap` : sessions d'un chef et
d'un étudiant, et liste des requêtes à faire passer par ZAP (toutes les
routes de l'API, avec des paramètres et des corps de requête plausibles,
pour que le scan actif ait de quoi tester).

    DB_NAME=edt_zap DJANGO_SECRET_KEY=<clé du lancement> \
        python zap/preparer_zap.py <fichier_etat.json>

Appelé par zap/lancer_zap.py. Refuse toute autre base que edt_zap : le scan
actif crée, modifie et supprime des données.
"""
import json
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Gestion_edt.settings")
if os.environ.get("DB_NAME") != "edt_zap":
    sys.exit("Refus : le scan ZAP ne tourne que sur la base jetable edt_zap.")
if not os.environ.get("DJANGO_SECRET_KEY"):
    sys.exit("Refus : DJANGO_SECRET_KEY propre au scan obligatoire.")

import django  # noqa: E402

django.setup()

from EDT_app.authentication import CustomTokenObtainPairSerializer as Jetons  # noqa: E402
from EDT_app.models import (  # noqa: E402
    AffectationModule, DocumentPedagogique, Etudiant, Seance, Semestre,
)
from EDT_app.urls import router  # noqa: E402


def jeton(user):
    return str(Jetons.get_token(user).access_token)


def premier_pk(viewset):
    modele = viewset.queryset.model if viewset.queryset is not None else None
    objet = modele.objects.order_by("pk").first() if modele else None
    return objet.pk if objet else 1


def preparer(chemin_etat):
    seance = (
        # Classe qui a encore des étudiants : un scan précédent a pu en vider
        # une (« passer au semestre suivant » rejoué par le scan actif).
        Seance.objects.filter(statut="Confirmée", classe__filiere__departement__chef__isnull=False,
                              classe__etudiant__isnull=False)
        .distinct()
        .select_related("classe__filiere__departement__chef__profil__user", "classe__semestre")
        .order_by("pk").first()
    )
    if seance is None:
        sys.exit("Aucune séance dans edt_zap : lancer seed.py sur cette base.")
    classe = seance.classe
    chef = classe.filiere.departement.chef.profil.user
    etudiant = Etudiant.objects.filter(classe=classe).select_related("profil__user").first()
    semestre_cible = Semestre.objects.filter(annee=classe.annee).exclude(pk=classe.semestre_id).first()
    lundi = seance.date_seance - timedelta(days=seance.date_seance.weekday())
    affectation = AffectationModule.objects.filter(module=seance.module).first()
    document = DocumentPedagogique.objects.filter(module__classe=classe).first()

    ids = {
        "classe": classe.pk, "semestre": classe.semestre_id, "annee": classe.annee_id,
        "seance": seance.pk, "module": seance.module_id, "enseignant": seance.enseignant_id,
        "departement": classe.filiere.departement_id, "filiere": classe.filiere_id,
        "profil_etudiant": etudiant.profil.pk,
    }

    # Paramètres de liste réellement lus par les vues (voir views.py).
    filtres = {
        "seances": f"classe_id={classe.pk}&semestre_id={classe.semestre_id}&enseignant_id={seance.enseignant_id}"
                   f"&date_debut={lundi}&date_fin={lundi + timedelta(days=6)}&statut=Confirm%C3%A9e"
                   f"&type_seance=CM&annee_id={classe.annee_id}&page_size=50",
        "modules": f"classe_id={classe.pk}&semestre_id={classe.semestre_id}",
        "affectations": f"module_id={seance.module_id}&enseignant_id={seance.enseignant_id}",
        "documents": f"module_id={seance.module_id}",
        "enseignants": f"departement_id={ids['departement']}&tous_departements=1",
        "classes": f"semestre_id={classe.semestre_id}&annee_id={classe.annee_id}&filiere_id={classe.filiere_id}",
        "etudiants": f"classe_id={classe.pk}",
        "filieres": f"departement_id={ids['departement']}",
    }

    requetes = []
    for prefixe, viewset, _ in router.registry:
        requetes.append({"method": "GET", "url": f"{prefixe}/" + (f"?{filtres[prefixe]}" if prefixe in filtres else "")})
        pk = ids.get(prefixe.rstrip("s"), premier_pk(viewset))
        requetes.append({"method": "GET", "url": f"{prefixe}/{pk}/"})
        for action in viewset.get_extra_actions():
            if "get" in action.mapping:
                chemin = f"{prefixe}/{pk}/{action.url_path}/" if action.detail else f"{prefixe}/{action.url_path}/"
                requetes.append({"method": "GET", "url": chemin})
    requetes += [
        {"method": "GET", "url": f"etudiants/mon_planning/?semaine={lundi}&semestre_id={classe.semestre_id}"},
        {"method": "GET", "url": f"enseignants/mon_planning/?semaine={lundi}&semestre_id={classe.semestre_id}"},
        {"method": "GET", "url": f"seances/conflits/?semestre_id={classe.semestre_id}"},
        {"method": "POST", "url": "seances/", "data": {
            "module_id": seance.module_id, "enseignant_id": seance.enseignant_id, "classe_id": classe.pk,
            "annee_id": classe.annee_id, "date_seance": str(lundi + timedelta(days=5)),
            "heure_debut": "14:15", "heure_fin": "16:15", "type_seance": "CM", "statut": "brouillon"}},
        {"method": "PATCH", "url": f"seances/{seance.pk}/", "data": {"heure_debut": "09:00", "heure_fin": "11:00"}},
        {"method": "PATCH", "url": f"seances/{seance.pk}/reporter/", "data": {
            "date_report": str(lundi + timedelta(days=5)), "heure_debut_report": "09:00", "heure_fin_report": "11:00"}},
        {"method": "POST", "url": f"seances/{seance.pk}/publier/", "data": {}},
        {"method": "POST", "url": f"seances/{seance.pk}/depublier/", "data": {}},
        {"method": "POST", "url": "seances/publier_masse/", "data": {"seance_ids": [seance.pk]}},
        {"method": "PATCH", "url": f"profils/{etudiant.profil.pk}/changer_statut/", "data": {"statut": "actif"}},
        {"method": "PATCH", "url": "profils/me/", "data": {"telephone": "060000000"}},
        {"method": "POST", "url": "affectations/", "data": {
            "module_id": seance.module_id, "enseignant_id": seance.enseignant_id,
            "heures_prevues": 10, "type_seance": "TD"}},
    ]
    if semestre_cible:
        requetes.append({"method": "POST", "url": f"classes/{classe.pk}/passer_semestre/",
                         "data": {"semestre_cible_id": semestre_cible.pk}})
    if affectation:
        requetes.append({"method": "PATCH", "url": f"affectations/{affectation.pk}/", "data": {"heures_prevues": 12}})
    if document:
        requetes.append({"method": "GET", "url": f"documents/{document.pk}/telecharger/"})

    etat = {
        "sessions": {"chef": jeton(chef), "etudiant": jeton(etudiant.profil.user)},
        "comptes": {"chef": chef.username, "etudiant": etudiant.profil.user.username},
        "requetes": requetes,
        "date": str(date.today()),
    }
    with open(chemin_etat, "w", encoding="utf-8") as f:
        json.dump(etat, f, ensure_ascii=False)
    print(f"scan prêt : {len(requetes)} requêtes, chef {chef.username}, étudiant {etudiant.profil.user.username}")


if __name__ == "__main__":
    preparer(sys.argv[1])
