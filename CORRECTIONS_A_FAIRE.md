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

**Statut :** corrigé dans le code par le commit 7d2549d (`Seance.clean()`
contrôle tout sur `creneau_effectif()`), statut mis à jour le 2026-10-01.
Complété par le point 32 : les autres séances sont maintenant lues, elles
aussi, sur leur créneau réel. Pas de test dédié au remplacement sur une
séance reportée.

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

**Statut :** corrigé dans le code par le commit 7d2549d
(`valider_module_seance_liee`, dans les deux sens), statut mis à jour le
2026-10-01. Pas de test dédié.

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

**Mise à jour du 2026-10-01 :** les verrous posés par
`SeanceViewSet._locker_pour_validation` (fusion de
`fix/bugs-decouverts-tests`) ferment le cas principal. Vérifié par
`tests_solidite.RequetesSimultaneesTest` (tag `concurrence`) : 20 paires de
créations simultanées, même enseignant et même créneau, dans deux classes
différentes → une seule séance à chaque fois, aucune erreur serveur. Restent
non couverts : le volume de module et d'affectation sous concurrence, et les
séances reportées (point 32).

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

**Statut :** corrigé dans le code par le commit 7d2549d (`pks_exemptes`
inclut `seances_associees`), statut mis à jour le 2026-10-01 ; la
détection des conflits applique la même exemption depuis le point 32.
Constat d'origine : identifié par lecture de code et reproduit via le contrôle
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

**Statut :** corrigé par le commit 7d2549d (`reinscrire()` rouvre la ligne
historique), test inversé :
`test_retour_sur_une_classe_deja_quittee_reactive_linscription`. Statut mis
à jour le 2026-10-01.

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

**Statut :** corrigé par le commit 7d2549d, test inversé :
`test_seance_reportee_compte_sur_son_nouveau_jour_pas_sur_lancien`. Statut
mis à jour le 2026-10-01.

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

> **Points 17 à 34 — campagne « solidité et sécurité » du 2026-10-01**
> (branche `test/solidite-securite`). Chacun est reproduit par un test qui
> décrit la règle voulue et porte `@faille_connue(N)`
> (`EDT_app/outils_tests.py`) : le test échoue tant que la faille existe et
> passe en « unexpected success » quand elle est corrigée — retirer alors le
> décorateur. `VOIR_FAILLES=1` affiche la raison de chaque échec attendu.
> Règles de droits de référence (validées le 2026-10-01) : un chef n'agit que
> sur son département ; facultés, départements et leur chef, années,
> semestres et parcours sont réservés à l'admin et à la scolarité
> (`responsable`) ; un référent publie, dépublie et reporte dans ses classes ;
> le planning est public, les coordonnées personnelles non.
> Les numéros 15 et 16 cités dans d'anciennes notes ne figurent sur aucune
> branche ; ils ne sont pas réattribués.

---

## 17. Un compte suspendu garde l'accès à plusieurs actions de chef

**Découvert le :** 2026-10-01 (`tests_securite_roles.py`, `CompteSuspenduTest`).

**Problème :** un chef suspendu alors que sa session est ouverte peut encore
archiver une année, faire passer une classe au semestre suivant, reporter une
séance et lancer la détection des conflits. Il peut aussi renouveler sa
session indéfiniment : la suspension ne l'empêche jamais de rester connecté.

**Cause :** `ProfilActifPermission` absente des actions `archiver`,
`passer_semestre`, `reporter` et `conflits` (`EDT_app/views.py`, leurs
`permission_classes` se limitent à `IsAuthenticated, IsChefDepartement`).
`/api/token/refresh/` utilise la vue standard `TokenRefreshView`, qui ne lit
pas `Profil.statut`. (Publier, dépublier, publier en masse et changer de
statut vérifient bien la suspension : contrôles dans le même fichier.)

**Piste de correction :** ajouter `ProfilActifPermission` à ces quatre
actions (ou l'intégrer à `IsChefDepartement`) ; sous-classer
`TokenRefreshSerializer` pour refuser un profil suspendu.

**Statut :** corrigé le 2026-10-01 (branche `fix/securite-solidite`) :
`ProfilActifPermission` ajoutée aux quatre actions (`reporter` passe par
les permissions communes des séances) ; `/api/token/refresh/` utilise
`CustomTokenRefreshView` (`EDT_app/authentication.py`), qui refuse un
profil suspendu ou absent. Les 5 tests passent.

---

## 18. Un chef peut modifier les réglages communs de tout l'établissement

**Découvert le :** 2026-10-01 (`ReglagesCommunsTest`).

**Problème :** n'importe quel chef de département peut créer, modifier ou
supprimer des facultés, des départements (y compris remplacer le chef de son
propre département), des années académiques (et les archiver), des semestres
et des parcours. Ces réglages doivent être réservés à l'admin et à la
scolarité.

**Cause :** `IsChefDepartementOrReadOnly` (`EDT_app/permissions.py`) donne
l'écriture à tout chef sur `FaculteViewSet`, `DepartementViewSet`,
`AnneeAcademiqueViewSet`, `SemestreViewSet` et `ParcoursViewSet` ;
`archiver` utilise `IsChefDepartement`. `DepartementSerializer.chef_id` est
modifiable.

**Piste de correction :** une permission « admin ou scolarité en écriture,
lecture pour tous » sur ces cinq ViewSets et sur `archiver`.

**Statut :** corrigé le 2026-10-01 (lot 2) : `IsResponsableOrReadOnly`
sur les cinq ViewSets et sur `archiver` ; un chef lit ces réglages sans
pouvoir les modifier. L'interface n'affichait déjà aucun bouton d'écriture
sur ces écrans.

---

## 19. Un chef peut agir sur l'organisation d'un autre département

**Découvert le :** 2026-10-01 (`OrganisationAutreDepartementTest`).

**Problème :** un chef peut modifier ou supprimer les filières d'un autre
département (en ajoutant un simple paramètre à l'adresse), modifier ou
supprimer ses matières, et y créer des classes. Il peut aussi lire une
affectation d'un autre département en tapant son numéro, alors que la liste
la lui cache.

**Cause :**
- `FiliereViewSet.get_queryset` : `?departement_id=` court-circuite le
  cloisonnement du chef, sur toutes les actions (écriture comprise).
- `MatiereViewSet` : aucun cloisonnement.
- `ClasseSerializer.validate` : ne vérifie pas que la filière choisie relève
  du chef (le `get_queryset` ne protège que les classes existantes).
- `AffectationModuleViewSet.get_queryset` : ne filtre que `list`.

**Piste de correction :** ne garder `?departement_id=` que comme filtre à
l'intérieur du périmètre ; cloisonner les matières comme les modules ;
contrôler le département de la filière à la création d'une classe ; appliquer
`modules_autorises()` à `retrieve` des affectations.

**Statut :** corrigé le 2026-10-01 (lot 2) :
- `?departement_id=` ne filtre plus qu'à l'intérieur du périmètre du chef
  pour l'écriture (la lecture reste possible pour les formulaires) ;
- matières : modification et suppression limitées aux départements du chef,
  création contrôlée (`MatiereSerializer.validate`) ;
- filières et classes : le département choisi doit être celui du chef ;
- affectations : la lecture par numéro suit la liste (`retrieve` cloisonné).

À noter au passage : l'API exige le champ `code` à la création de toute
classe, même avec une filière (règle d'unicité qui le rend obligatoire).
L'interface envoie `code: null`, à vérifier.

---

## 20. Un chef peut agir sur les personnes d'un autre département

**Découvert le :** 2026-10-01 (`PersonnesTest`).

**Problème :** un chef peut suspendre un enseignant d'un autre département,
et même un autre chef ; lire la fiche complète de n'importe qui ; modifier ou
supprimer un enseignant d'un autre département (en ajoutant
`?tous_departements=1`) ; inscrire un étudiant dans une classe d'un autre
département ou y déplacer un de ses étudiants. Il peut aussi rattacher un
profil à un autre compte utilisateur.

**Cause :**
- `ProfilViewSet` : aucun `get_queryset` cloisonné ; `IsOwnerOrChefDepartement`
  accepte tout chef sur tout profil ; `changer_statut` ne vérifie pas la cible.
- `EnseignantViewSet.get_queryset` : `?tous_departements=1` élargit aussi
  PATCH/DELETE (déjà noté le 2026-09-29).
- `EtudiantSerializer.validate` : `classe_id` accepté sans contrôle de périmètre.
- `ProfilSerializer.user_id` modifiable en écriture.

**Piste de correction :** cloisonner les profils et `changer_statut`
(suspendre un chef : admin ou scolarité) ; limiter `tous_departements` à la
lecture ; contrôler `classe_id` contre `classes_autorisees()` ; rendre
`user_id` non modifiable après création.

**Statut :** corrigé le 2026-10-01 (lot 2) :
- `ProfilViewSet.get_queryset` : son profil, plus les enseignants des
  départements dirigés et les étudiants de ses classes
  (`perimetre.profils_autorises`) ; une fiche hors périmètre répond 404 ;
- suspendre ou réactiver un chef (soi-même compris) : admin et scolarité
  seulement, par `changer_statut` comme par la fiche ; `changer_statut`
  exige de plus un rôle de chef (la permission déclarée était ignorée) ;
- `?tous_departements=1` vaut pour la lecture seulement ;
- `classe_id` d'un étudiant et `departement_id` d'un enseignant contrôlés ;
- `user_id` d'un profil non modifiable après création.

Au passage : modifier une fiche profil sans envoyer le statut effaçait le
motif d'un profil suspendu ; le statut non envoyé garde maintenant sa valeur.

---

## 21. Les coordonnées des enseignants sont visibles par tous

**Découvert le :** 2026-10-01 (`CoordonneesPersonnellesTest`, `PersonnesTest`).

**Problème :** un étudiant reçoit l'email et le téléphone des enseignants dans
la liste des séances et dans son planning. Un chef les reçoit aussi pour les
enseignants des autres départements. L'interface les masque parfois, mais le
serveur les envoie toujours.

**Cause :** `EnseignantSerializer` imbrique le `ProfilSerializer` complet
(email, téléphone, statut, motif de suspension), réutilisé par
`SeanceSerializer`, `AffectationModuleSerializer` et
`DocumentPedagogiqueSerializer`.

**Piste de correction :** un sérialiseur réduit (nom, grade, département)
pour toutes les imbrications et pour les fiches hors périmètre.

**Statut :** corrigé le 2026-10-01 (lot 3) :
- `EnseignantResumeSerializer` (nom, grade, département, identifiant du
  compte) pour les séances, affectations et documents ;
- la liste des enseignants ne montre email, téléphone et motif qu'à
  l'intéressé, au chef de son département et à la scolarité.

---

## 22. Publier, dépublier ou reporter ne vérifie pas la classe de la séance

**Découvert le :** 2026-10-01 (`ActionsSeancesTest`).

**Problème :** un chef peut publier, dépublier, reporter ou publier en masse
les séances d'un autre département. Un référent peut publier ou dépublier les
séances de n'importe quelle classe, pas seulement des siennes.

**Cause :** `publier`, `depublier` et `reporter` récupèrent la séance avec
`get_object()`, alors que `SeanceViewSet.get_queryset` ne cloisonne que
`list` ; `publier_masse` part de `get_queryset()` non cloisonné. Aucune de ces
actions ne vérifie `_get_classes_autorisees()`, contrairement à
`perform_update`.

**Piste de correction :** appliquer dans les quatre actions le même contrôle
de classe que `perform_update` et `perform_destroy`.

**Statut :** corrigé le 2026-10-01 : `reporter` avec le point 23, puis
publier, dépublier et publier en masse (lot 2) par un contrôle commun
`SeanceViewSet._verifier_classe`.

---

## 23. Un référent ne peut pas reporter une séance de sa classe

**Découvert le :** 2026-10-01 (`ActionsSeancesTest.test_referent_reporte_dans_sa_classe`).

**Problème :** règle validée : le référent publie, dépublie et reporte les
séances de ses classes. Il publie et dépublie déjà, mais le report lui est
refusé.

**Cause :** `SeanceViewSet.get_permissions` renvoie pour `reporter` les
`permission_classes` propres à l'action (`IsChefDepartement`), alors que
publier et dépublier passent par `IsChefOrReferentOrReadOnly`.

**Piste de correction :** aligner `reporter` sur publier et dépublier, avec
le contrôle de classe du point 22.

**Statut :** corrigé le 2026-10-01 : `reporter` suit les permissions de
publier et dépublier, avec contrôle de la classe de la séance.

---

## 24. Un compte avec un profil mais sans rôle voit tous les documents

**Découvert le :** 2026-10-01 (`DocumentsSansRoleTest`).

**Problème :** un utilisateur qui a un profil mais n'est ni étudiant, ni
enseignant, ni membre de la scolarité voit tous les documents pédagogiques.

**Cause :** `DocumentViewSet.get_queryset` n'a pas de branche finale : sans
étudiant ni enseignant, le queryset complet est renvoyé.

**Piste de correction :** renvoyer `qs.none()` en dernier recours, sauf pour
la scolarité.

**Statut :** corrigé le 2026-10-01 : un profil sans rôle ne voit aucun
document ; la scolarité voit tout.

---

## 25. La connexion à l'administration Django n'est pas limitée

**Découvert le :** 2026-10-01 (`LimitationTentativesTest`).

**Problème :** après dix mots de passe faux, la page `/admin/` accepte encore
la connexion : on peut y essayer des mots de passe sans frein, alors que la
connexion de l'application est limitée à 5 essais par minute.

**Cause :** la limitation (`EDT_app/throttles.py`) ne s'applique qu'à
`/api/token/`.

**Piste de correction :** en production, nginx réserve `/admin/` à des
adresses internes (`DEPLOIEMENT.md`), à vérifier en Phase B. En complément,
limiter aussi la connexion admin.

**Statut :** corrigé le 2026-10-01 (lot 6) : `limiter_connexion_admin`
(`EDT_app/throttles.py`, branchée dans `EDT_app/admin.py`) applique à
`/admin/login/` les mêmes limites que la connexion de l'application
(5 essais par minute et par compte, 120 par adresse), avec des compteurs
séparés ; au-delà, réponse 429 sans vérifier le mot de passe. Le filtrage
de `/admin/` par nginx reste à vérifier en Phase B.

---

## 26. Le partage entre origines autorise l'envoi d'identifiants sans en avoir besoin

**Découvert le :** 2026-10-01 (`ConfigurationProductionTest`).

**Problème :** le réglage CORS autorise le navigateur à joindre cookies et
identifiants aux requêtes venant des origines autorisées. L'application n'en
a pas besoin (le jeton voyage dans un en-tête), et ce réglage élargit
inutilement la surface d'attaque.

**Cause :** `CORS_ALLOW_CREDENTIALS = True` (`Gestion_edt/settings.py`).

**Piste de correction :** passer à `False` et vérifier que l'interface
fonctionne toujours.

**Statut :** corrigé le 2026-10-01 (`CORS_ALLOW_CREDENTIALS = False` ;
l'interface n'utilise pas `withCredentials`).

---

## 27. Des saisies absurdes font planter le serveur au lieu d'être refusées

**Découvert le :** 2026-10-01 (`tests_solidite.py`, `SaisiesMalformeesTest`).

**Problème :** au lieu d'un refus clair, le serveur plante (erreur 500)
quand :
- un filtre de liste reçoit autre chose qu'un nombre (`?classe_id=abc`, sur
  la plupart des listes) ;
- la détection des conflits reçoit un semestre non numérique ;
- le planning de l'enseignant reçoit une semaine en l'an 9999 ou un semestre
  non numérique (le planning étudiant plante aussi sur l'an 9999) ;
- la publication en masse reçoit une liste mal formée (un nombre seul, un
  texte, une liste nue, un objet) ;
- le passage au semestre suivant reçoit un semestre non numérique.

**Cause :** les paramètres sont passés tels quels à `.filter()` ou `.get()`
(`ValueError`) ; `mon_planning` n'attrape que `ValueError`, pas
`OverflowError` ; `publier_masse` suppose une liste d'entiers.

**Piste de correction :** un utilitaire qui lit un paramètre entier et lève
une `ValidationError` (400), utilisé dans tous les `get_queryset` ; valider
le corps de `publier_masse` avec `serializers.ListField(child=IntegerField())`.

**Statut :** corrigé le 2026-10-01 (lot 4) :
- `lire_id` / `_id_param` (`views.py`) : tout identifiant reçu (adresse ou
  corps) doit être un entier positif, sinon refus 400 ;
- `_lire_semaine` : une semaine impossible (an 9999) répond 400 ;
- `publier_masse` refuse tout corps qui n'est pas `{"seance_ids": [...]}`.

---

## 28. Suppressions bloquées et cas limites qui plantent

**Découvert le :** 2026-10-01 (`SuppressionsEtCasLimitesTest`).

**Problème :**
- supprimer un département qui a des enseignants, une classe qui a des
  étudiants, ou une année académique qui a des étudiants, plante au lieu
  d'expliquer pourquoi c'est impossible ;
- un administrateur sans profil fait planter « mon profil » et le dépôt de
  document ;
- télécharger un document dont le fichier a disparu du disque plante ;
- supprimer un module laisse ses fichiers sur le disque, sans plus aucun lien.

**Cause :** `ProtectedError` non convertie (le gestionnaire global
`EDT_app/exception_handlers.py` ne traite que `ValidationError`) ;
`request.user.profil` lu sans garde ; `open()` sans gestion de
`FileNotFoundError` dans `telecharger` ; aucun nettoyage des fichiers à la
suppression d'un `DocumentPedagogique`.

**Piste de correction :** convertir `ProtectedError` en 409 dans le
gestionnaire global ; protéger l'accès au profil ; renvoyer 404 si le fichier
manque ; supprimer le fichier à la suppression du document (signal
`post_delete`).

**Statut :** corrigé le 2026-10-01 (lot 4) :
- suppression bloquée : réponse 409 avec la liste de ce qui l'empêche
  (`exception_handlers.py`), rien n'est effacé ;
- « mon profil » sans profil : 404 ; dépôt de document sans fiche
  enseignant : 403 ;
- fichier disparu : 404 ;
- le fichier d'un document est effacé avec lui, y compris par cascade
  (signal `post_delete` dans `models.py`). Limite connue : si la
  suppression était annulée ensuite, le fichier serait déjà parti ; le
  document répondrait alors 404 au téléchargement.

---

## 29. Annuler une séance par une modification partielle est refusé

**Découvert le :** 2026-10-01 (`SeancesSaisiesTest`).

**Problème :** changer uniquement le statut d'une séance (par exemple
l'annuler) est refusé avec « Horaires obligatoires », alors que la séance a
déjà ses horaires.

**Cause :** `SeanceSerializer.validate` lit `data.get(...)` : sur un PATCH,
les champs non envoyés valent `None`.

**Piste de correction :** compléter `data` avec les valeurs de
`self.instance` avant les contrôles croisés.

**Statut :** corrigé le 2026-10-01 : `SeanceSerializer.validate`
contrôle les valeurs envoyées complétées par celles de la séance.

---

## 30. Le passage au semestre suivant n'inscrit pas les étudiants et accepte une autre année

**Découvert le :** 2026-10-01 (`PasserSemestreTest`).

**Problème :** après « passer au semestre suivant », les étudiants sont bien
dans la nouvelle classe, mais sans inscription active pour elle. Et on peut
les envoyer vers un semestre d'une autre année académique, alors que la
documentation de l'action dit le contraire.

**Cause :** `ClasseViewSet.passer_semestre` modifie `etudiant.classe`
directement au lieu d'appeler `Etudiant.reinscrire()`, ne vérifie pas
`semestre_cible.annee == classe_source.annee`, et n'est pas dans une
transaction : un échec en cours de boucle laisse une partie des étudiants
déplacés.

**Piste de correction :** vérifier l'année, passer par `reinscrire()` (ou
écrire l'inscription), et envelopper la boucle dans `transaction.atomic()`.

**Statut :** corrigé le 2026-10-01 (lot 5) : le semestre cible doit être
de la même année (et différent du semestre actuel) ; chaque étudiant passe
par `reinscrire()`, qui ouvre son inscription dans la nouvelle classe ; le
tout dans une transaction. La classe cible d'une classe de L1 se choisit
aussi par son code (MIP, BCG, PCG) : avant, avec plusieurs L1 dans le même
semestre, la recherche pouvait planter ou viser la mauvaise classe.

---

## 31. Doublons acceptés

**Découvert le :** 2026-10-01 (`DoublonsTest`).

**Problème :** on peut créer deux années académiques du même nom et deux
affectations génériques identiques (même module, même enseignant). Les
classes en double sont refusées par l'application, mais pas par la base :
deux enregistrements simultanés peuvent passer.

**Cause :** pas d'unicité sur `AnneeAcademique.libelle` ; la contrainte
d'affectation inclut `type_seance`, et MySQL considère deux valeurs vides
comme différentes ; MySQL ignore les contraintes d'unicité conditionnelles
de `Classe` (avertissement `models.W036` au démarrage).

**Piste de correction :** unicité du libellé d'année ; contrôle explicite des
affectations génériques dans le sérialiseur ; pour les classes, une colonne
calculée unique ou un verrou à la création.

**Statut :** corrigé le 2026-10-01 (lot 5, migration 0016), après
vérification qu'aucun doublon n'existait dans `edt_uccb` ni `edt_charge` :
- libellé d'année unique ;
- affectations : contrainte d'unicité sur (module, enseignant, type vide
  ramené à '') et message clair dans `AffectationModule.clean()` ;
- classes : contraintes réécrites sans `condition=` (ignorée par MySQL),
  en s'appuyant sur le fait que deux NULL ne se gênent pas dans un index
  unique. L'avertissement `models.W036` a disparu.
Le test qui exigeait `supports_partial_indexes` (toujours faux sous MySQL)
est remplacé par des tests qui écrivent un vrai doublon en base et
attendent son refus. La même migration aligne aussi en base la longueur
des noms de fichiers (255 caractères), déjà déclarée dans le modèle.

**Régression corrigée le 2026-10-01 (migration 0017)**, trouvée en remplissant
la base du scan ZAP : sur une base dont les colonnes sont en
`utf8mb4_unicode_ci` (`edt_charge`, `edt_zap`, et possiblement la future base
de production), créer une classe de L1 ou une affectation plantait (MySQL,
erreur 1267 « Illegal mix of collations »). Pour vérifier les deux
contraintes à expression avant d'enregistrer, Django comparait la colonne à
une valeur convertie avec la collation de la connexion
(`utf8mb4_0900_ai_ci`). Les tests ne le voyaient pas : leur base suit la
collation par défaut du serveur, comme `edt_uccb`. Correctif : les deux index
restent en base (ils bloquent toujours les doublons), mais Django ne les
connaît plus (`SeparateDatabaseAndState`) ; les contrôles avec message
clair sont dans `Classe.clean()` et `AffectationModule.clean()` (classe de
L1 en double, affectation typée ou générique en double). Vérifié en
remplissant `edt_zap` par seed.py, qui échouait avant.

---

## 32. Une séance reportée bloque son ancien créneau et pas le nouveau

**Découvert le :** 2026-10-01 (`CreneauxSeancesReporteesTest`).

**Problème :** une fois une séance reportée, on ne peut plus placer un autre
cours de l'enseignant sur l'ancien créneau (pourtant libéré), mais on peut en
placer un sur le nouveau (pourtant occupé) : l'enseignant se retrouve réservé
deux fois. La détection des conflits ne voit pas non plus les séances
reportées. Même famille que les points 5 et 13.

**Cause :** `valider_conflit_enseignant` et `valider_conflit_classe`
(`EDT_app/validation_seance.py`), ainsi que `SeanceViewSet.conflits`, ne
lisent que `date_seance`/`heure_debut`/`heure_fin`, jamais les champs de
report.

**Piste de correction :** une fonction unique « créneau réel d'une séance »
(celui du report si `Reportée`), utilisée par toutes les validations et par
`conflits`.

**Statut :** corrigé le 2026-10-01 (lot 5) : `q_occupe_creneau()`
(`EDT_app/validation_seance.py`) traduit `creneau_effectif()` en requête et
sert à tous les contrôles de conflit (enseignant, classe, créneau de
report). `conflits` lit aussi les séances reportées sur leur créneau réel,
n'oppose plus deux séances mutualisées, et ne charge les fiches complètes
que pour les séances en conflit.

---

## 33. Chaque ligne affichée déclenche des dizaines de requêtes à la base

**Découvert le :** 2026-10-01 (`NombreDeRequetesTest`).

**Problème :** le temps de chargement grandit avec le nombre de séances :
environ 23 requêtes par séance dans la liste des séances, environ 30 dans le
planning étudiant ou enseignant, 16 par affectation et 6 par module. Pour
15 séances, le planning étudiant fait 451 requêtes. C'est la cause probable
des 21 s mesurées sur le planning du chef le 2026-09-23.

**Cause :** sérialiseurs imbriqués (module → classe → filière →
département → chef → profil ; heures recalculées à chaque ligne ;
`is_mutualise` interrogé séance par séance) sans `select_related` ni
`prefetch_related` suffisants. `conflits` a déjà été corrigé (contrôle dans
le même fichier).

**Piste de correction :** sérialiseurs allégés pour les listes, préchargement
des relations, calcul des heures en une requête groupée.

**Statut :** corrigé le 2026-10-01 (V2 à V4) :
- `SeanceListeSerializer` pour la liste des séances, les deux plannings
  personnels, `conflits` et `seances_liees` : module, enseignant et classe
  réduits, heures des modules calculées une fois par module, séances
  mutualisées repérées en une requête. Sur `edt_charge`, 20 séances
  coûtaient 610 requêtes, elles en coûtent 3 ;
- relations préchargées (`SEANCE_RELATIONS`) dans les plannings ;
- modules : fiches liées préchargées, nombres de séances et d'affectations
  calculés par la base (`modules_optimises`) ; affectations et documents :
  module et enseignant réduits, heures préchargées.
Le SeanceSerializer complet reste pour l'ouverture et la modification
d'une séance.
V5 (2026-10-01) : le planning ne demande plus que la semaine affichée
(`date_debut`/`date_fin` pour un gestionnaire, `semaine` pour un enseignant
ou un étudiant), en une page de 200 lignes au plus (`?page_size=`,
`EDT_app/pagination.py`). Planning d'un chef : 1 requête par semaine au lieu
de 14 pour tout le semestre (vérifié dans le navigateur).

**Test de charge du 2026-10-01** (`charge/locustfile.py`, base `edt_charge`
remplie par `seed.py` : 183 étudiants, 31 enseignants, 4 285 séances ;
serveur de développement, donc temps pessimistes — à comparer avant/après
correctif, pas à promettre en ligne). Temps médians :

| Utilisateurs simultanés | 10 | 25 | 50 |
|---|---|---|---|
| Planning de la semaine (étudiant) | 2,2 s | 15 s | 28 s |
| Planning de la semaine (enseignant) | 1,7 s | 10 s | 20 s |
| Une page du planning d'une classe (chef) | 2,9 s | 27 s | 55 s |
| Mes modules (enseignant) | 2,1 s | 12 s | 21 s |
| Documents | 0,1 s | 0,5 s | 0,8 s |

Le serveur plafonne vers 2 requêtes par seconde quel que soit le nombre
d'utilisateurs : au-delà, chacun attend son tour. Les documents, qui ne
passent pas par les sérialiseurs imbriqués, restent rapides — ce qui désigne
bien les séances comme cause. Aucune erreur serveur ni blocage de base, sauf
la détection des conflits (point 34). Rejouer les mêmes paliers après
correctif pour mesurer le gain.

**Après correctif (V2 à V4, même base, même serveur, 2026-10-01 au soir).**
Temps médians, entre parenthèses le temps sous lequel passent 95 % des
requêtes :

| Utilisateurs simultanés | 10 | 25 | 50 |
|---|---|---|---|
| Planning de la semaine (étudiant) | 0,1 s (0,7) | 0,1 s (0,5) | 0,3 s (4,2) |
| Planning de la semaine (enseignant) | 0,1 s (0,2) | 0,1 s (0,5) | 0,3 s (2,6) |
| Une page du planning d'une classe (chef) | 0,1 s (0,3) | 0,1 s (0,4) | 0,3 s (2,3) |
| Mes modules (enseignant) | 0,2 s (1,3) | 0,2 s (1,0) | 0,5 s (5,4) |
| Détection des conflits (chef) | 1,0 s (3,2) | 1,0 s (17) | 1,8 s (9,8) |

Le serveur traite maintenant 17 requêtes par seconde à 50 utilisateurs
(1,7 avant), sans aucune erreur. Le planning étudiant passe de 28 s à
0,3 s en médiane à 50 utilisateurs. Objectif local atteint (moins de 1 s à
25 utilisateurs). Reste plus lente : la détection des conflits, qui compare
toutes les séances du semestre ; à surveiller, mais rarement appelée.

---

## 34. La détection des conflits plante pour tout chef de département

**Découvert le :** 2026-10-01 (`ActionsSeancesTest.test_un_chef_detecte_les_conflits_de_son_semestre`).

**Problème :** quand un chef lance la détection des conflits sur son propre
semestre, le serveur plante (erreur 500). Seuls l'admin et la scolarité
peuvent s'en servir. Les tests existants passaient tous par la scolarité, ce
qui masquait le défaut.

**Cause :** `SeanceViewSet.conflits` filtre sur
`classes__filiere__departement__in`, mais la relation inverse de
`Classe.semestre` s'appelle `classe` (pas de `related_name`), d'où une
`FieldError`.

**Piste de correction :** remplacer `classes__` par `classe__`.

**Statut :** corrigé le 2026-10-01 (`classes__` → `classe__`).

---

## 35. Fichiers téléversés : contenu Office non vérifié et nom trop long qui plante

**Découvert le :** 2026-10-01 (`tests_securite.py`, `DocumentsNomsEtContenusTest`, étape C1).

**Problème :**
- un fichier `.docx`, `.xlsx` ou `.pptx` n'est vérifié que sur ses quatre
  premiers octets (ceux de toute archive ZIP) : une archive contenant un
  programme, renommée en `cours.docx`, est acceptée et distribuée aux
  étudiants ; un document à macros (`.docm`) simplement renommé en `.docx`
  passe aussi ;
- un nom de fichier de 300 caractères fait planter le dépôt (erreur 500) au
  lieu d'être raccourci ou refusé.

**Cause :** `EDT_app/fichiers.py` compare seulement la signature `PK`
pour les formats Office récents ; le chemin enregistré
(`documents/AAAA/MM/<32 caractères>/<nom>`) dépasse les 100 caractères du
champ `DocumentPedagogique.fichier` et MySQL refuse l'écriture (`1406 Data
too long`).

**Piste de correction :** ouvrir l'archive (`zipfile`) et exiger
`[Content_Types].xml` et le dossier attendu (`word/`, `xl/`, `ppt/`), refuser
`vbaProject.bin` ; raccourcir le nom d'origine dans `chemin_televerse` (en
gardant l'extension) ou porter `max_length` à 255. Mettre alors à jour
`test_docx_valide_accepte` (`tests_securite.py`), qui dépose une simple
signature ZIP et non un vrai document.

**Statut :** nom trop long corrigé le 2026-10-01 par la migration 0016 : la
base acceptait 100 caractères alors que le modèle en déclarait 255 ; Django
raccourcit maintenant le nom (extension gardée) et l'écriture passe.
Contenu Office : reproduit (2 tests), non corrigé. Contrôles qui passent : noms
piégés (guillemets, retour à la ligne, `../`) neutralisés en développement et
en production, double extension `.pdf.exe` et formats à macros
(`.docm`/`.xlsm`/`.pptm`/`.dotm`) refusés, texte contenant du HTML servi
comme texte brut.

---

## 36. Supprimer un enseignant efface tout son historique

**Découvert le :** 2026-10-01 (`tests_solidite.py`, `SuppressionEnseignantTest`, étape C2).

**Problème :** supprimer un enseignant qui a déjà des séances réussit et
efface en cascade toutes ses séances (y compris celles déjà faites, donc la
progression des classes), ses affectations et ses documents, dont les
fichiers restent sur le disque. Son compte et son profil, eux, restent :
un compte sans rôle.

**Cause :** `Seance.enseignant`, `AffectationModule.enseignant` et
`DocumentPedagogique.enseignant` sont en `on_delete=CASCADE`
(`EDT_app/models.py`).

**Règle validée (2026-10-01) :** à terme, on peut supprimer un enseignant,
mais les séances déjà effectuées restent à son nom (il faudra alors garder
une trace de l'enseignant, par exemple un enseignant « archivé », plutôt que
d'effacer sa ligne). Pour l'instant, la suppression d'un enseignant qui a
des séances est refusée et propose la suspension.

**Statut :** étape provisoire faite le 2026-10-01 :
`EnseignantViewSet.perform_destroy` refuse (400) avec un message qui renvoie
vers la suspension. Reste à faire : la suppression qui garde les séances
effectuées. L'interface ne propose pas de bouton de suppression
d'enseignant. Contrôle : un enseignant sans activité se supprime
normalement.

---

## 37. Des textes d'un million de caractères sont acceptés

**Découvert le :** 2026-10-01 (`tests_solidite.py`, `TextesTresLongsTest`, étape C2).

**Problème :** la description d'un module et le motif de suspension (par la
fiche profil) acceptent un million de caractères. La description est
ensuite renvoyée dans chaque module, et donc dans chaque séance affichée :
un seul module ainsi rempli alourdit tous les plannings qui le contiennent.

**Cause :** `Module.description` et `Profil.motif_suspension` sont des
`TextField` sans limite (MySQL les stocke en `LONGTEXT`) ; seul
`changer_statut` limite le motif à 255 caractères
(`ProfilSuspensionSerializer`).

**Piste de correction :** `max_length` côté sérialiseur (par exemple 2 000
caractères pour la description, 255 pour le motif, comme `changer_statut`).

**Statut :** reproduit (2 tests), non corrigé.

---

## 38. Deux réinscriptions simultanées du même étudiant se bloquent ou l'inscrivent deux fois

**Découvert le :** 2026-10-01 (`tests_solidite.py`,
`RequetesSimultaneesTest.test_reinscriptions_simultanees_une_seule_inscription_active`, étape C2).

**Problème :** deux réinscriptions du même étudiant au même instant (double
clic, deux onglets, import lancé deux fois) provoquent un interblocage de la
base (erreur MySQL 1213, donc une erreur serveur), ou laissent l'étudiant
avec deux inscriptions actives. Mesuré sur 20 essais : 16 erreurs et 3
doubles inscriptions au premier passage, 20 erreurs au second.

**Cause :** `Etudiant.reinscrire()` lit puis écrit les inscriptions sans
verrouiller l'étudiant ; rien n'interdit en base deux inscriptions actives
pour un même étudiant (l'unicité porte sur le couple étudiant-classe).

**Piste de correction :** verrouiller la ligne de l'étudiant
(`select_for_update`) au début de la transaction de `reinscrire()`. Priorité
basse tant que `reinscrire()` n'est appelée par aucune page (elle le
deviendra avec la correction du point 30).

**Statut :** reproduit, non corrigé. Contrôle : deux publications en masse
croisées des mêmes séances ne se bloquent pas (verrous ordonnés de
`_locker_pour_validation`).

---

## 39. Bibliothèques avec des failles connues

**Découvert le :** 2026-10-01 (étape C5 : base publique OSV pour Python,
`npm audit` pour l'interface).

**Problème :** plusieurs bibliothèques installées ont des failles publiées et
corrigées dans des versions plus récentes.

- **Serveur (Python) :**
  - Django 6.0.2 → **6.0.8** : 22 failles, dont 4 « hautes ». Deux touchent
    directement l'application : la limite de taille des requêtes peut être
    contournée, et une requête peut consommer trop de ressources. Les autres
    visent des parties non utilisées (cache, ASGI, GeoDjango, admin).
  - Django REST framework 3.17.1 → **3.17.2** : contournement de la limite de
    taille des requêtes JSON.
  - PyJWT 2.12.1 → **2.15.0** : surtout des failles liées aux clés publiques
    (non utilisées ici, l'application signe avec une clé secrète), à mettre à
    jour par prudence. Une faille n'a pas encore de correctif.
  - sqlparse 0.5.5 → **0.6.0** : lenteurs volontaires possibles, exposition
    faible (sert à l'affichage du SQL en développement).
  - anyio : présent dans l'environnement mais pas utilisé par l'application
    (vient d'un outil de développement), hors `requirements.txt`.
- **Interface (npm)** : 19 paquets signalés (13 « hauts »), tous corrigeables
  sans changement majeur (`npm audit fix`). Ceux qui partent chez
  l'utilisateur : `axios`, `react-router` / `react-router-dom` (redirections
  vers un site extérieur), `dompurify`. Les autres ne servent qu'à la
  construction (`postcss`, `browserslist`, `js-yaml`, `brace-expansion`,
  outils de développement).

**Piste de correction :** fixer `Django==6.0.8` et
`djangorestframework==3.17.2` dans `requirements.txt`, ajouter
`PyJWT>=2.15.0` et `sqlparse>=0.6.0`, réinstaller puis relancer toute la
suite de tests ; côté interface, `npm audit fix` puis `npm run build` et
`npm run lint`. Refaire l'audit à chaque mise en ligne.

**Statut :** corrigé, sauf le reste connu ci-dessous.
- **Serveur : corrigé le 2026-10-01.** Installés : Django 6.0.8, DRF
  3.17.2, PyJWT 2.15.1, sqlparse 0.6.0 (et anyio 4.15.1, pip 26.2.1 dans
  l'environnement de développement). `requirements.txt` mis à jour. Audit
  OSV après mise à jour : 0 faille connue sur les 34 paquets de `.venv` et
  les 41 de `.venv-charge`.
- **Interface : corrigé le 2026-10-01** (`npm audit fix`, commit d7fdc3a) :
  25 mises à jour mineures, aucune version majeure (axios 1.20.0,
  react-router-dom 6.30.6, dompurify 3.4.16…), toutes vérifiées sur OSV.
  `npm audit` : 19 paquets signalés avant, 2 après (`react-router` et
  `react-router-dom`, ci-dessous). Construction OK, lint inchangé (84
  erreurs préexistantes), connexion et redirections vérifiées dans le
  navigateur.
- **Reste connu, sans effet sur l'application :** `react-router` 6.30.6 garde
  deux failles moyennes corrigées seulement en version 7
  (GHSA-337j-9hxr-rhxg : rendu côté serveur, que l'application n'utilise
  pas ; GHSA-wrjc-x8rr-h8h6 : redirection vers un site extérieur quand une
  adresse fournie par l'utilisateur est passée à la navigation, alors que
  toutes les navigations de l'application vont vers des adresses écrites en
  dur). Passer à React Router 7 lors d'un prochain chantier d'interface.

---

## 40. Mauvais mot de passe : aucun message, la page de connexion se recharge

**Découvert le :** 2026-10-01 (tests navigateur, `e2e/01-connexion.spec.js`).

**Problème :** quand on se trompe de mot de passe, rien ne s'affiche : la
page de connexion se recharge à vide. La personne ne sait pas si elle a mal
tapé ou si l'application est en panne.

**Cause :** le refus du serveur (401) passe par l'intercepteur de
`edt-frontend/src/api/client.js`, prévu pour les sessions expirées : il
tente un renouvellement de session (il n'y en a pas), vide la session puis
renvoie vers `/login` par un rechargement complet, ce qui efface le message
d'erreur. Constaté dans le navigateur : 401 sur `/api/token/`, puis
rechargement de `/login`.

**Piste de correction :** ne pas appliquer le renouvellement aux appels de
connexion (`/token/` et `/token/refresh/`). Une autre session de travail a
déjà des modifications en cours dans `client.js` et `useLogin.js` sur ce
sujet (copie de travail `.claude/worktrees/affectionate-jang-4dc4cc`, non
commitée) : à reprendre de là.

**Statut :** corrigé le 2026-10-02, en reprenant ces modifications (la copie
de travail elle-même n'a pas été touchée) : l'intercepteur ne tente plus de
renouvellement sur `/token/` et `/token/refresh/`, et un refus à la
connexion affiche « Identifiant ou mot de passe incorrect. »
(`useLogin.js`). Une erreur 500 à la connexion affiche un message fixe au
lieu de « Impossible de joindre le serveur ». Scénario
`e2e/01-connexion.spec.js` au vert.

---

## 41. Compte suspendu en cours de session : message vague

**Découvert le :** 2026-10-01 (tests navigateur, `e2e/04-suspension.spec.js`).

**Problème :** une personne suspendue pendant qu'elle est connectée voit,
à l'action suivante, « Une erreur est survenue. Veuillez rafraîchir la page
ou réessayer plus tard. » Rafraîchir n'y change rien, et rien ne dit que le
compte est suspendu. Le refus lui-même fonctionne (le serveur répond 403).

**Cause :** le serveur envoie pourtant un message clair (« Votre profil est
suspendu. Contactez le responsable pédagogique. », `ProfilActifPermission`),
mais les pages n'affichent qu'un texte d'erreur générique.

**Piste de correction :** dans l'intercepteur de `client.js`, repérer ce
refus (403 avec ce message) et l'afficher une fois pour toute
l'application, par exemple en déconnectant avec ce message sur la page de
connexion.

**Statut :** corrigé le 2026-10-02.
- Serveur : le refus porte un code stable, `"code": "profil_suspendu"`
  (`ProfilActifPermission`, `permissions.py`), comme le renouvellement de
  session refusé, qui l'avait déjà.
- Interface : `client.js` reconnaît ce code, vide la session et ramène à la
  page de connexion, qui affiche « Votre profil est suspendu. Contactez le
  responsable pédagogique. » (`lib/messageConnexion.js`, `LoginPage.jsx`).
- Même chemin pour une session expirée : « Votre session a expiré.
  Reconnectez-vous. » au lieu d'un retour muet à la connexion.
- Un renouvellement impossible parce que le serveur ne répond pas ne
  déconnecte plus : la session n'est pas en cause, la page affiche l'erreur.

Tests : `CompteSuspenduTest` (code dans les deux refus),
`e2e/03-session.spec.js` et `e2e/04-suspension.spec.js` au vert.

---

## 42. Un serveur qui ne répond pas fait attendre sans fin

**Découvert le :** 2026-10-01 (tests navigateur, `e2e/06-pannes.spec.js`).

**Problème :** si le serveur reçoit la demande mais ne répond jamais
(surcharge, coupure réseau à mi-chemin), le planning reste en chargement
indéfiniment, sans message. Un serveur éteint ou une erreur 500 donnent bien,
eux, un message lisible.

**Cause :** aucun délai maximal n'est réglé dans `axios.create()`
(`client.js`).

**Piste de correction :** `timeout: 30000` (30 s) dans `axios.create()`. Les
dépôts de documents (jusqu'à 20 Mo) pourront demander un délai plus long,
réglé sur leur appel.

**Statut :** corrigé le 2026-10-02 : délai de 30 s pour toute requête
(`client.js`, renouvellement de session compris), 5 minutes pour l'envoi et
le téléchargement de documents (`api/documents.js`). Pas de nouvel essai
automatique après un délai dépassé (`main.jsx`) : sans cela, le message
n'arrivait qu'au bout d'une minute. Scénario `e2e/06-pannes.spec.js` au
vert (message au bout de 30 s).

---

## 43. Double clic sur « Enregistrer la séance » : deux séances créées

**Découvert le :** 2026-10-01 (tests navigateur, `e2e/08-double-clic.spec.js`).

**Problème :** un double clic sur « Enregistrer la séance » crée deux
séances identiques (même classe, même créneau, même enseignant).

**Cause :** deux causes cumulées :
- l'interface : le bouton n'est désactivé qu'après le premier rendu qui
  suit l'envoi, trop tard pour un double clic (`SeanceDrawer.jsx`,
  `SeanceForm.jsx`) ;
- le serveur : une séance créée sans statut est un brouillon, et les
  contrôles de conflit ignorent les brouillons
  (`q_occupe_creneau`, statuts `Confirmée` et `Reportée` seulement). Deux
  brouillons identiques sont donc acceptés.

**Piste de correction :** dans `SeanceDrawer.handleSubmit`, ignorer un
second envoi tant que le premier n'est pas terminé (drapeau dans un
`useRef`). Côté serveur, à décider : refuser deux séances identiques, même
en brouillon (même classe, même date, même heure, même module).

**Statut :** corrigé le 2026-10-02, des deux côtés.
- Interface : un second envoi est ignoré tant que le premier n'a pas abouti
  (`SeanceDrawer.jsx`).
- Serveur : un brouillon identique à une séance déjà enregistrée,
  brouillon ou confirmée (même classe, même module, même jour, mêmes
  heures), est refusé : « Cette séance existe déjà : même module, même
  classe, même créneau. » (`valider_doublon`, `validation_seance.py`). Le
  contrôle se refait sous les verrous de l'enregistrement : deux envois
  simultanés ne passent pas tous les deux, et les appels directs à l'API
  sont couverts. Deux séances confirmées identiques étaient déjà refusées
  par le contrôle de conflit de la classe.
- Restent permis : refaire une séance sur le créneau d'une séance annulée
  ou reportée, préparer deux brouillons de modules différents sur le même
  créneau, et publier un brouillon dont un double existait avant ce
  correctif (le double est alors refusé à sa propre publication).

Tests : `SeancesEnDoubleTest`, `RequetesSimultaneesTest.
test_double_clic_un_seul_brouillon` (20 essais simultanés, une seule
séance à chaque fois), `e2e/08-double-clic.spec.js` au vert.

---

## 44. Erreur 500 à la suspension : la page HTML du serveur s'affiche dans le panneau

**Découvert le :** 2026-10-01 (tests navigateur, `e2e/06-pannes.spec.js`).

**Problème :** si le serveur plante pendant une suspension ou une
réactivation, le panneau affiche le code de la page d'erreur
(« <!DOCTYPE html><html>… ») au lieu d'un message.

**Cause :** `parseApiError` de `StatutDrawer.jsx` renvoie tel quel tout
corps de réponse en texte (`typeof data === 'string'`).

**Piste de correction :** n'afficher que `detail`, `message` ou les erreurs
de champ, et sinon un message fixe (« Le serveur a rencontré une erreur.
Réessayez plus tard. »). Les autres panneaux (`SeanceDrawer`,
`ReportDrawer`) ne sont pas touchés : ils ignorent les réponses en texte.

**Statut :** corrigé le 2026-10-02 comme proposé : seules les réponses de
l'API (JSON) sont affichées ; sinon « Le serveur a rencontré une erreur.
Réessayez plus tard. », ou « Impossible de joindre le serveur » sans
réponse du tout. Scénario `e2e/06-pannes.spec.js` au vert.

---

## 45. L'export CSV ne neutralise pas les formules (code inutilisé)

**Découvert le :** 2026-10-01 (préparation des tests navigateur).

**Problème :** `exportToCsv` (`edt-frontend/src/lib/exportCsv.js`) recopie
les valeurs telles quelles. Une cellule qui commence par `=`, `+`, `-` ou
`@` (un nom de module `=HYPERLINK(...)`) serait interprétée comme une
formule à l'ouverture dans Excel.

**Cause :** aucune page n'appelle aujourd'hui cette fonction : le risque
n'existe pas tant qu'elle reste inutilisée.

**Piste de correction :** la supprimer, ou, si un export CSV revient,
préfixer d'une apostrophe les valeurs qui commencent par `=`, `+`, `-`, `@`,
une tabulation ou un retour chariot.

**Statut :** relevé, sans effet actuel. Priorité basse.

---

## 46. Scan d'attaque automatique (OWASP ZAP) : version du serveur annoncée

**Découvert le :** 2026-10-02 (étape C4, `zap/lancer_zap.py`, ZAP 2.17.0).

**Déroulé du scan :** base jetable `edt_zap`, serveur de développement à
part, 53 requêtes couvrant toutes les routes de l'API (paramètres et corps
plausibles), puis scan passif et actif complet avec la session d'un chef de
département, puis d'un étudiant (environ 7 minutes chacun, toutes les
règles passées). Environ 30 000 requêtes : injections SQL et de commandes,
inclusion de fichiers, contournement de chemins, en-têtes piégés...

**Résultat :** aucune faille confirmée.
- Aucune injection ni fuite détectée ; les saisies piégées sont refusées
  (12 500 réponses 400, 6 100 refus 403).
- Aucune écriture acceptée avec la session étudiant. Les écritures réussies
  de la phase chef (report, suspension d'un étudiant de ses classes,
  affectation, passage au semestre suivant) sont permises à un chef.
- 282 erreurs 500, toutes du même cas propre au mode développement : un
  POST sur une adresse sans « / » final, que Django refuse de rediriger
  quand `DEBUG=True` (en production, il redirige). Sans effet en ligne.
- Alertes ZAP restantes : le serveur annonce sa version (« WSGIServer/0.2
  CPython/3.14.2 », serveur de développement), et une réponse qui varie
  selon le navigateur annoncé (information, sans risque démontré).

**Piste de correction :** en production, nginx remplace l'en-tête du
serveur ; `server_tokens off;` lui évite d'annoncer sa propre version.

**Statut :** ajouté le 2026-10-02 à la configuration nginx de
`DEPLOIEMENT.md`. À revérifier en Phase B, avec un scan ZAP sur le serveur
réel (HTTPS, nginx, `DEBUG=False`) : le plan de scan de `zap/lancer_zap.py`
sert de base, à adapter pour viser ce serveur au lieu d'en démarrer un en
local.

---

<!-- Ajouter les prochains points ci-dessous, avec le même format
     (titre, date de découverte, problème, cause, piste de correction). -->
