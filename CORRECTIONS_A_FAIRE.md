# Corrections à faire

Suivi des problèmes et points d'amélioration identifiés dans l'application
(backend `EDT_app` et frontend `edt-frontend`) mais pas encore traités.
Chaque entrée date sa découverte et référence le contexte qui a permis de la
repérer, pour pouvoir y revenir plus tard sans perdre le fil. La plupart sont
des bugs ; certaines (marquées comme telles) sont de simples suggestions
d'amélioration, pas des anomalies.

---

## 1. Le report d'une séance peut planter au lieu de refuser proprement

**Découvert le :** 2026-09-11, en écrivant les tests de report de séance
(`EDT_app/tests_seance_lifecycle.py`, `SeanceReportTest`).

**Problème :** si le volume d'heures d'une `AffectationModule` est réduit
*après* qu'une séance a déjà consommé l'ancien volume, reporter cette séance
via `PATCH /api/seances/{id}/reporter/` déclenche une
`django.core.exceptions.ValidationError` brute, non interceptée — une erreur
serveur au lieu d'une réponse 400 lisible.

**Cause :** `SeanceReportSerializer` (`EDT_app/serializers.py`) est un
`serializers.Serializer` simple, pas un `ModelSerializer` avec
`ValidateOnSaveMixin`. Sa méthode `save()` appelle `seance.save()`
directement, sans la conversion Django → DRF que ce mixin fournit ailleurs
dans l'application.

**Piste de correction :** donner à `SeanceReportSerializer.save()` la même
protection que `ValidateOnSaveMixin` (try/except autour de `seance.save()`,
conversion en `DRFValidationError`), ou déplacer cette logique dans
`SeanceViewSet.reporter()` (`EDT_app/views.py`).

---

## 2. Une affectation inter-département devient introuvable juste après sa création

**Découvert le :** 2026-09-11, en écrivant les tests de modification
d'affectation (`EDT_app/tests_affectation.py`,
`AffectationInterDepartementModificationAPITest`).

**Problème :** un chef de département peut créer une `AffectationModule`
avec `hors_departement=True` sur un module d'un autre département, tant que
ce module est enseigné dans une de ses classes (règle validée dans
`AffectationModuleSerializer.validate()`). Mais ce même chef ne peut plus
ensuite la relire, la modifier ou la supprimer via l'API standard — 404
immédiat.

**Cause :** `perimetre.modules_autorises()` (`EDT_app/perimetre.py`) ne
prolonge la règle « modules des classes que je gère » qu'aux **référents**
(`classe__in=classes_ref` / `seance__classe__in=classes_ref`), pas aux chefs.

**Piste de correction :** étendre `modules_autorises()` pour qu'un chef voie
aussi les modules `hors_departement=True` rattachés à une classe qu'il
dirige, symétriquement à la branche référent.

---

## 3. Code de retour incohérent (404 vs 403) selon le rôle, pour la même erreur d'autorisation

**Découvert le :** 2026-09-11, en écrivant les tests de suppression/
modification de séance et d'affectation hors périmètre.

**Problème :** sur `SeanceViewSet` et `AffectationModuleViewSet`, un chef
agissant hors de son propre département reçoit un **404** (l'objet est déjà
filtré hors de `get_queryset()`), alors qu'un référent dans la même
situation reçoit un **403** explicite (son `get_queryset()` n'est pas
filtré de la même façon, donc `perform_update`/`perform_destroy` s'exécute
et lève `PermissionDenied`). Deux comportements différents pour un cas
conceptuellement identique.

**Piste de correction :** décider d'un comportement uniforme (probablement
403 partout, en retirant le filtrage de queryset propre aux chefs et en
laissant `perform_update`/`perform_destroy`/le serializer trancher), puis
mettre à jour les tests qui documentent actuellement le 404 comme
comportement attendu.

---

## 4. Modifier une séance existante peut refuser à tort « enseignant non affecté », avec un panneau « Solde affectation » trompeur

**Découvert le :** 2026-09-11, signalé par l'utilisateur avec une capture
d'écran du formulaire « Modifier la séance ».

**Problème :** en modifiant une séance déjà créée (module Immunologie,
enseignant ProfBiologie Claude, type CM), le formulaire affiche
« Solde affectation (CM) : 0h restantes / 26h prévues » — indiquant qu'une
affectation CM existe bien, entièrement consommée — mais la sauvegarde
échoue avec « Cet enseignant n'est pas affecté sur ce module (ni pour ce
type de séance, ni de manière générique) ». Ces deux messages sont
incompatibles : si l'affectation existait vraiment côté serveur au moment
de l'enregistrement, l'erreur aurait dû être un dépassement de volume, pas
une absence d'affectation (`valider_affectation` dans
`EDT_app/validation_seance.py`, lignes 245-291, distingue bien les deux cas).
Le panneau affiché ne reflète donc pas ce qui est réellement envoyé au
serveur au moment de la sauvegarde.

**Causes identifiées côté frontend** (`edt-frontend/src/features/seances/`) :
- `SeanceForm.jsx` : `getSoldeAffectation()` lit le type de séance via
  `control._formValues?.type_seance`, une lecture non réactive de
  react-hook-form. Si l'utilisateur change le champ « Type de séance »,
  ce panneau peut continuer d'afficher le solde de l'ANCIEN type
  (ex. CM) sans se rafraîchir, alors que c'est le NOUVEAU type qui part
  au serveur — expliquant l'incohérence observée.
- `SeanceForm.jsx` : au montage en mode édition, seul
  `setSelectedModuleId(defaultValues.module_id)` est appelé
  (`useEffect` ligne ~95) ; il n'existe **aucun** appel équivalent
  `setSelectedEnseignantId(defaultValues.enseignant_id)`. L'état qui pilote
  l'affichage du solde (`useCascadeSelects.js`) reste donc désynchronisé de
  l'enseignant réellement sélectionné tant que l'utilisateur n'a pas
  re-cliqué manuellement sur le champ Enseignant.

**Cause possible côté données** (à ne pas exclure) : le même phénomène que
le point 1 ci-dessus — l'affectation associée à ce module/enseignant a pu
être modifiée (retypée, réassignée) *après* la création initiale de cette
séance, ce qui casse silencieusement sa prochaine sauvegarde sans qu'aucun
message ne prévienne au moment du changement d'affectation.

**Piste de correction :** remplacer la lecture `control._formValues` par
`watch('type_seance')` pour que le panneau reste toujours synchronisé avec
la valeur réellement soumise ; ajouter le `useEffect` manquant pour
initialiser `selectedEnseignantId` depuis `defaultValues.enseignant_id` en
mode édition, symétriquement à celui du module.

**Statut :** cause probable identifiée par lecture de code, pas encore
reproduite pas à pas en conditions réelles ni corrigée.

---

## 5. Sur une séance déjà reportée, remplacer le module ou l'enseignant revalide le mauvais créneau

**Découvert le :** 2026-09-11, en analysant le comportement de
`Seance.clean()` (`EDT_app/models.py`, lignes 982-1061) pour répondre à une
question sur les scénarios de remplacement module/enseignant.

**Problème :** quand une séance a déjà été reportée (`statut='Reportée'`),
`Seance.clean()` calcule la durée et lance `valider_conflit_enseignant`,
`valider_conflit_classe`, `valider_volume_module` et `valider_affectation`
en utilisant `self.heure_debut`/`self.heure_fin`/`self.date_seance` — le
créneau ORIGINAL, avant report — jamais `date_report`/
`heure_debut_report`/`heure_fin_report`, le créneau où la séance a
réellement lieu aujourd'hui. Le contrôle du créneau de report
(`_valider_creneau_report()`) n'est qu'un ajout à la fin, qui revérifie
uniquement les bornes et les conflits sur CE créneau, mais ne remplace pas
les contrôles de volume/affectation faits plus haut sur l'ancien créneau.

**Conséquence concrète :** remplacer l'enseignant ou le module d'une séance
déjà reportée peut être accepté en vérifiant la disponibilité de volume et
l'absence de conflit sur un créneau qui n'est plus celui occupé
(l'ancien), et ne rien vérifier de cette nature sur le créneau réellement
utilisé (le nouveau, celui du report).

**Piste de correction :** dans `Seance.clean()`, utiliser
`date_report`/`heure_debut_report`/`heure_fin_report` (si `statut ==
'Reportée'`) au lieu des champs originaux pour tous les contrôles de
conflit et de volume, pas seulement pour `_valider_creneau_report()`.

**Statut :** identifié par lecture de code, pas encore reproduit ni corrigé.

---

## 6. Une séance mutualisée peut se retrouver avec un module différent de sa jumelle

**Découvert le :** 2026-09-11, même analyse que le point 5.

**Problème :** rien ne contrôle que les deux séances reliées par
`seance_liee` portent le même module. `valider_conflit_enseignant` exempte
le conflit horaire par simple correspondance de `pk` (`seance_liee_pk`),
sans jamais comparer les modules des deux séances. Si on change le module
d'une seule des deux séances liées (cas courant testé dans
`SeanceRemplacementEnseignantMutualiseeTest`, mais côté module plutôt
qu'enseignant), l'enregistrement peut réussir alors que les deux séances
« mutualisées » enseignent désormais des matières différentes au même
enseignant sur le même créneau — l'exemption de conflit s'applique quand
même, sans plus aucune justification métier.

**Piste de correction :** dans `valider_conflit_enseignant` (ou en amont,
dans `Seance.clean()`), vérifier que `seance_liee.module_id == self.module_id`
avant d'appliquer l'exemption, ou lever une alerte explicite si les modules
divergent.

**Statut :** identifié par lecture de code, pas encore reproduit ni corrigé.

---

## 7. Le cache frontend des heures/soldes n'est jamais rafraîchi après une sauvegarde de séance

**Découvert le :** 2026-09-11, en lisant `useSeanceMutations.js`.

**Problème :** après une création/modification réussie, seul le cache
`['seances']` est invalidé (`queryClient.invalidateQueries({ queryKey:
['seances'] })` dans `useCreateSeance`/`useUpdateSeance`). Les caches
`['modules', 'classe', classeId]`, `['affectations-module', ...]` et
`['affectations', ...]`, qui alimentent respectivement l'indicateur
« Heures restantes » du module et le panneau « Solde affectation » de
l'enseignant (`SeanceForm.jsx`), ne sont jamais invalidés. Après avoir
enregistré une séance qui consomme des heures, ces indicateurs peuvent donc
continuer d'afficher les anciennes valeurs (non décrémentées) pour toute
séance ouverte ensuite dans la même session, jusqu'à expiration naturelle
du cache TanStack Query.

**Conséquence :** compose avec le point 4 déjà répertorié — une partie de
ce qui rend le panneau « Solde affectation » trompeur peut venir de ce
défaut d'invalidation, en plus des deux causes déjà identifiées.

**Piste de correction :** invalider aussi `['modules']`, `['affectations']`
et `['affectations-module']` dans les callbacks `onSuccess` de
`useCreateSeance`/`useUpdateSeance`/`useDeleteSeance`/`useReporterSeance`
(`edt-frontend/src/hooks/useSeanceMutations.js`).

**Statut :** identifié par lecture de code, pas encore reproduit ni corrigé.

---

## 8. Le contrôle « hors département » peut être contourné en éditant directement une séance

**Découvert le :** 2026-09-11, même analyse.

**Problème :** `AffectationModuleSerializer.validate()` exige explicitement
le flag `hors_departement` (coché volontairement) avant qu'un chef puisse
affecter un enseignant à un module d'un autre département via une
`AffectationModule`. Mais `SeanceViewSet.perform_update`/`perform_create`
ne vérifient que le périmètre de la **classe** ; ils ne consultent aucune
règle équivalente pour le département du **module** choisi. Si le module
cible n'a aucune `AffectationModule` déclarée (dégradation gracieuse de
`valider_affectation`), un chef peut assigner directement, via une simple
modification de séance, un module et un enseignant d'un département qu'il
ne dirige pas à une de ses classes — sans jamais cocher ni justifier quoi
que ce soit, contournant de fait le garde-fou explicite prévu pour les
affectations.

**Piste de correction :** décider si ce contournement est acceptable
(la classe reste dans le périmètre du chef) ou s'il faut étendre le
contrôle `hors_departement` (ou un équivalent) à `SeanceViewSet` quand le
module choisi ne relève pas du département de l'enseignant du chef.

**Statut :** identifié par lecture de code, pas encore reproduit ni corrigé.

---

## 9. Contrôles de conflit et de volume sans verrou : risque de double-réservation en cas de requêtes concurrentes

**Découvert le :** 2026-09-11, même analyse.

**Problème :** `valider_conflit_enseignant`, `valider_conflit_classe`,
`valider_volume_module` et `valider_affectation` lisent l'état actuel de la
base puis, séparément, `Seance.save()` écrit — sans transaction
`select_for_update()` ni contrainte d'unicité en base sur les créneaux.
Deux requêtes de modification simultanées (ex. deux onglets, ou deux
gestionnaires différents) portant sur des séances distinctes mais visant le
même créneau/enseignant, ou le même volume de module/affectation, peuvent
chacune lire un état encore valide avant l'écriture de l'autre, passer
leurs contrôles indépendamment, puis s'enregistrer toutes les deux — créant
un double-booking ou un dépassement de volume que l'application est censée
interdire.

**Piste de correction :** envelopper la validation + sauvegarde dans une
transaction avec verrouillage (`select_for_update()` sur les séances
concurrentes du même enseignant/classe/jour), ou ajouter une contrainte
d'exclusion au niveau base de données.

**Statut :** risque structurel identifié par lecture de code ; probabilité
d'occurrence réelle non mesurée (dépend du volume d'utilisateurs
simultanés), pas de reproduction ni de correctif.

---

## 10. Saisie libre des horaires au lieu d'un choix parmi les 3 créneaux fixes

**Type :** amélioration d'ergonomie, pas un bug — signalé tel quel par
l'utilisateur.

**Découvert le :** 2026-09-11, signalé par l'utilisateur avec une capture
d'écran du formulaire « Modifier la séance » (erreur « empiète sur la pause
méridienne » obtenue en saisissant 09:00–16:00 à la main).

**Constat :** les cours se déroulent uniquement sur trois créneaux fixes :
9h–11h, 11h15–13h15 et 14h15–16h15 (`BLOCS_JOURNEE` dans
`EDT_app/validation_seance.py`, lignes 38-42 — c'est déjà la source unique
de vérité que `seed.py` importe). Pourtant, le formulaire de création/
modification de séance (`SeanceForm.jsx`, champs « Heure de début » /
« Heure de fin ») laisse saisir n'importe quelle heure via deux champs
`<input type="time">` libres. L'utilisateur peut donc composer un horaire
qui n'existe pas dans la grille (ex. empiétant sur la pause méridienne
13h15–14h15, ou sur la courte pause 11h–11h15), et ne le découvre qu'au
rejet côté serveur après coup.

**Piste d'ajustement suggérée par l'utilisateur :** remplacer les deux
champs horaires libres par un sélecteur unique proposant directement les 3
créneaux de `BLOCS_JOURNEE`, pour qu'un horaire hors grille ne puisse
simplement plus être saisi. Le frontend a déjà une référence à ces mêmes
horaires (`edt-frontend/src/features/planning/PlanningTableView.jsx`,
`TIME_SLOTS`, censé rester aligné sur `BLOCS_JOURNEE` d'après le
commentaire du backend) — à réutiliser plutôt qu'à dupliquer.

**Statut :** consigné à la demande de l'utilisateur, non implémenté pour
l'instant (décision explicite de reporter la mise en œuvre).

---

## 11. L'exemption de conflit `seance_liee` ne fonctionne que dans un sens

**Découvert le :** 2026-09-15, en vérifiant le contrôle d'intégrité de
`seed.py` après la refonte de l'année académique (revalidation d'un
échantillon de séances via `full_clean()`).

**Problème :** pour la séance mutualisée entre deux classes (ex. séminaire
partagé L3 Informatique / L3 Physique, `seed.py`), `full_clean()` échoue sur
la séance **pivot** (celle que l'autre référence via `seance_liee`) avec
« L'enseignant a déjà une séance le `<date>` sur ce créneau », alors que les
deux séances sont volontairement mutualisées (même enseignant, même
créneau, exactement le cas que `seance_liee` est censé couvrir).

**Cause :** `valider_conflit_enseignant` (`EDT_app/validation_seance.py`,
lignes 184-209) reçoit `seance_liee_pk` et exclut cette séance-là de la
recherche de conflit — mais uniquement du point de vue de la séance qui
**possède** ce `seance_liee`. La séance pivot, elle, a `seance_liee=None`
(rien ne pointe "vers l'avant") ; elle ignore qu'une autre séance pointe
*vers elle* (`related_name='seances_associees'`), donc rien n'exclut cette
séance associée de sa propre recherche de conflit.

**Piste de correction :** dans `valider_conflit_enseignant`, exclure aussi
les séances de `seance.seances_associees.all()` (pas seulement
`seance_liee_pk`), pour que l'exemption s'applique dans les deux sens.

**Statut :** identifié par lecture de code et reproduit via le contrôle
d'intégrité de `seed.py` (pas de correction appliquée, hors périmètre de la
refonte du seed en cours).

---

## 12. Ramener un étudiant sur une classe qu'il a quittée le laisse sans inscription active

**Découvert le :** 2026-09-15, en écrivant les tests unitaires de
`Etudiant.reinscrire()` (`EDT_app/tests_inscription.py`,
`EtudiantReinscriptionTest`).

**Problème :** si la scolarité corrige une erreur de saisie en ramenant un
étudiant sur une classe qu'il a déjà quittée (L1 → L2 → retour L1),
`reinscrire()` repointe bien `Etudiant.classe` sur L1, mais l'inscription L1
reste au statut `terminée`. L'étudiant se retrouve rattaché à une classe pour
laquelle il n'a **aucune inscription active** — état incohérent qu'aucun
message ne signale.

**Cause :** `Etudiant.reinscrire()` (`EDT_app/models.py`) clôture d'abord les
inscriptions actives, puis appelle
`Inscription.objects.get_or_create(etudiant=self, classe=nouvelle_classe, defaults={...})`.
La contrainte d'unicité `('etudiant', 'classe')` fait que `get_or_create`
**retrouve la ligne historique** au lieu d'en créer une : les `defaults`
(dont `statut='active'`) ne sont alors pas appliqués, et la ligne est renvoyée
telle quelle, toujours `terminée`. Le même mécanisme rend d'ailleurs un second
appel sur la classe courante totalement sans effet (ni date, ni référence
externe, ni type ne sont réécrits) — comportement voulu dans ce cas-là, mais
c'est le même angle mort.

**Piste de correction :** après le `get_or_create`, si la ligne existait déjà
et que son statut n'est pas `active`, la rouvrir explicitement (repasser
`statut='active'`, rafraîchir `date_inscription`) plutôt que de la renvoyer en
l'état ; ou refuser explicitement la réinscription sur une classe déjà
historisée, si la règle métier est qu'on ne revient jamais en arrière.

**Statut :** reproduit et figé par
`test_retour_sur_une_classe_deja_quittee_ne_reactive_pas_linscription`, qui
documente le comportement actuel — ce test sera à mettre à jour le jour où la
correction sera appliquée. Code applicatif inchangé.

---

## 13. Le plafond journalier d'une classe ignore le créneau de report d'une séance

**Découvert le :** 2026-09-15, en écrivant les tests unitaires de
`valider_volume_journalier` (`EDT_app/tests_volume_journalier.py`,
`VolumeJournalierTest`).

**Problème :** `valider_volume_journalier`
(`EDT_app/validation_seance.py`) interroge les séances d'une classe pour un
jour donné (`Seance.objects.filter(classe=..., date_seance=...)`), puis
somme `s.heure_debut`/`s.heure_fin` — le créneau **d'origine**, jamais
`s.heure_debut_report`/`s.heure_fin_report`. Une séance reportée continue
donc de peser sur le quota de 6h/jour de son **ancien** jour, qu'elle
n'occupe plus, et ne pèse jamais sur celui de son **nouveau** jour (celui de
`date_report`), qu'elle occupe réellement — puisque la requête filtre sur
`date_seance`, qui ne change jamais lors d'un report.

**Cause :** contrairement à `Module.heures_consommees()`
(`EDT_app/models.py:650-661`), qui bascule bien sur le créneau de report pour
une séance `Reportée`, `valider_volume_journalier` ne lit jamais les trois
champs de report. C'est un point de divergence de plus dans la même veine
que les points 5 et 11 (traitement incohérent du report entre plusieurs
fonctions de validation censées appliquer la même règle).

**Conséquence concrète :** une classe peut se voir planifier plus de 6h
réelles un jour donné (le jour de report d'une séance déjà comptée ailleurs
n'a aucune limite effective ce jour-là), tandis que son ancien jour reste
artificiellement bridé par des heures qui ne s'y déroulent plus.

**Piste de correction :** dans `valider_volume_journalier`, appliquer la même
bascule que `Module._heures`/`Module.heures_consommees()` — utiliser
`date_report`/`heure_debut_report`/`heure_fin_report` pour toute séance
`Reportée`, à la fois pour décider quel jour elle occupe (filtrer sur
`date_report` plutôt que `date_seance` quand le statut est `Reportée`) et
pour la durée sommée.

**Statut :** reproduit et figé par
`test_seance_reportee_reste_comptee_sur_son_ancien_jour_jamais_sur_le_nouveau`,
qui documente le comportement actuel dans les deux sens (ancien jour /
nouveau jour) — ce test sera à inverser le jour où la correction sera
appliquée. Code applicatif inchangé.

---

## 14. Publier une séance en conflit plante au lieu de refuser proprement

**Découvert le :** 2026-09-15, en écrivant les tests de
`SeanceViewSet.publier` (`EDT_app/tests_seance_publication.py`,
`SeancePublicationTest.test_publier_revalide_les_conflits`).

**Problème :** `POST /api/seances/{id}/publier/` (passage `brouillon` →
`Confirmée`) rejoue bien toutes les validations métier via
`seance.full_clean()` (`EDT_app/views.py:921`) — la revalidation elle-même
fonctionne (un conflit d'horaire créé après coup est bien détecté). Mais
quand `full_clean()` échoue, l'erreur remonte comme une
`django.core.exceptions.ValidationError` **brute**, non interceptée : une
erreur serveur (500) au lieu d'une réponse 400 lisible.

**Cause :** `publier()` appelle `seance.full_clean()` puis
`seance.save(update_fields=['statut'])` sans aucun `try/except`. C'est la
même catégorie de bug que le point 1 (`SeanceReportSerializer.save()`),
mais sur un point d'entrée entièrement différent — et jusqu'ici non
répertorié. Notamment, l'action jumelle `publier_masse()`
(`EDT_app/views.py:942-980`) fait, elle, bien le travail : chaque
`seance.full_clean()` y est protégé par un `try/except ValidationError`
individuel à l'intérieur de la boucle, avec conversion en réponse 400
(`erreurs`). Seule l'action `publier()` unitaire (et sa jumelle
`depublier()`, qui n'appelle `full_clean()` sur aucun changement de statut
sortant de brouillon donc moins exposée) n'a pas cette protection.

**Piste de correction :** envelopper `seance.full_clean()` dans `publier()`
avec le même patron try/except → `DRFValidationError` que `publier_masse()`
utilise déjà pour une seule séance, ou centraliser cette conversion dans un
helper partagé entre les trois actions (`publier`, `depublier`,
`publier_masse`) pour éviter que ce genre d'écart ne se reproduise à la
prochaine action ajoutée.

**Statut :** reproduit et figé par `test_publier_revalide_les_conflits`, qui
documente le comportement actuel (`assertRaises(ValidationError)` plutôt
qu'un `resp.status_code == 400`) — ce test sera à corriger le jour où la
protection sera ajoutée. Code applicatif inchangé.

---

<!-- Ajouter les prochains points ci-dessous, avec le même format
     (titre, date de découverte, problème, cause, piste de correction). -->
