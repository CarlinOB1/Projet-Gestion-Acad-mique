# Plan d'implémentation — Affectation des modules aux enseignants

Ce document décrit le plan d'implémentation des trois niveaux définis pour la
répartition des charges d'enseignement : la maquette (besoin pédagogique),
l'affectation (répartition des charges), et la séance (exécution).

Objectif : passer d'un système où une `Seance` consomme directement le volume
horaire d'un `Module`, à un système où une couche d'`AffectationModule`
s'intercale entre les deux.

---

## Vue d'ensemble des niveaux

| Niveau | Objet | Rôle | Statut actuel |
|---|---|---|---|
| 1 | `Module` | Volume horaire total à couvrir | Existe déjà (`heures_max()`) |
| 2 | `AffectationModule` | Qui couvre quoi, pour combien d'heures | À créer |
| 3 | `Seance` | Exécution concrète, datée | Existe déjà, à adapter |

---

## Phase 0 — Prérequis et décisions à figer avant de coder

Ces points doivent être validés avant d'écrire la moindre migration, car ils
conditionnent la structure du modèle `AffectationModule`.

- [ ] Confirmer que le niveau 1 (maquette) ne change pas dans l'immédiat :
      pas de champ CM/TD/TP séparé sur `Module` pour cette itération.
- [ ] Confirmer la règle de non-ambiguïté : un couple (module, enseignant) a
      un seul mode d'affectation (générique OU typée, jamais les deux).
- [ ] Décider si une affectation générique peut coexister avec une
      affectation typée pour deux enseignants différents sur le même module
      (oui, c'est le cas du partage CM/TP entre deux enseignants — déjà
      tranché, à confirmer explicitement dans la contrainte technique).
- [ ] Décider du comportement en cas de dépassement du volume horaire du
      module par la somme des affectations : erreur bloquante ou avertissement
      (point resté ouvert dans les échanges précédents).
- [ ] Décider qui a le droit de créer/modifier une affectation (chef de
      département uniquement, ou aussi référent de classe/L1 ?).

---

## Phase 1 — Modélisation (niveau 2 : `AffectationModule`)

### 1.1 Création du modèle

Nouveau modèle `AffectationModule` avec :

- `module` (FK vers `Module`)
- `enseignant` (FK vers `Enseignant`)
- `type_seance` (CM/TD/TP, **nullable** — null = affectation générique)
- `heures_prevues` (volume horaire affecté)
- horodatage standard (`created_at`)

### 1.2 Contraintes d'intégrité

- Contrainte d'unicité empêchant un couple (module, enseignant, type_seance)
  en doublon.
- Contrainte applicative (dans `clean()`) empêchant un couple
  (module, enseignant) d'avoir à la fois une affectation générique
  (`type_seance=None`) et une affectation typée.
- Validation : la somme des `heures_prevues` de toutes les affectations d'un
  module ne dépasse pas `Module.heures_max()` (bloquant ou avertissement,
  selon la décision de la phase 0).

### 1.3 Méthodes utilitaires sur `AffectationModule`

- `heures_consommees()` : somme des séances rattachées à cette affectation
  (filtrées sur `valide=True` si la logique de validation prévisionnel/réalisé
  est déjà en place, sinon sur toutes les séances confirmées).
- `heures_restantes()` : `heures_prevues - heures_consommees()`.

### 1.4 Méthodes utilitaires sur `Enseignant` ou `Departement`

- Une méthode de calcul de la charge totale d'un enseignant (somme des
  `heures_prevues` sur toutes ses affectations), utile pour un futur contrôle
  de quota statutaire (mentionné mais non implémenté ici — juste préparer le
  terrain).

### 1.5 Migration

- Migration standard de création de table, sans donnée rétroactive : aucune
  affectation n'est générée pour l'historique existant (cohérent avec la
  dégradation gracieuse décidée pour le niveau 3).

---

## Phase 2 — Résolution de l'affectation (niveau 3 : rattachement)

### 2.1 Méthode de résolution

Ajouter une méthode (sur `Seance` ou en fonction utilitaire séparée) qui,
étant donné `module`, `enseignant`, `type_seance` :

1. Cherche une `AffectationModule` typée correspondant exactement.
2. Si absente, cherche une `AffectationModule` générique
   (`type_seance=None`) pour ce couple.
3. Retourne `None` si aucune des deux n'existe.

### 2.2 Intégration dans `Seance.clean()`

- Appel de la méthode de résolution.
- Si résultat `None` **et** qu'au moins une `AffectationModule` existe pour
  ce module (tous enseignants confondus) → lever une erreur de validation :
  l'enseignant n'est pas affecté sur ce module.
- Si résultat `None` **et** qu'aucune `AffectationModule` n'existe pour ce
  module → dégradation gracieuse (comportement actuel inchangé, séance
  historique ou système pas encore utilisé sur ce module). Utiliser un
  `try/except AffectationModule.DoesNotExist` ou une vérification
  d'existence équivalente, dans le même esprit que les autres contrôles
  optionnels déjà présents dans `clean()`.
- Si une affectation est trouvée → vérifier
  `affectation.heures_restantes() >= duree_effective` avant d'autoriser la
  séance ; sinon lever une erreur de validation dédiée (distincte du message
  d'erreur du contrôle global sur le module, pour que l'utilisateur comprenne
  lequel des deux plafonds est atteint).
- Conserver ensuite, inchangé, le contrôle existant sur
  `Module.heures_restantes()` comme garde-fou global.

### 2.3 Ordre final des vérifications dans `Seance.clean()`

1. Contrôles horaires déjà existants (heure_debut, heure_fin, pause, etc.)
2. Cohérence département enseignant / matière du module
3. Date dans les bornes du semestre
4. Conflit enseignant (inchangé, y compris l'exclusion de la séance liée)
5. **Résolution de l'affectation + volume disponible sur l'affectation**
   *(nouveau)*
6. Volume disponible sur le module *(existant, conservé)*
7. Validation du créneau de report si statut « Reportée » *(inchangé)*

---

## Phase 3 — Adaptation du serializer et de l'API

### 3.1 `AffectationModuleSerializer`

- Nouveau serializer suivant le même schéma que les autres
  (`ValidateOnSaveMixin`, champs `_id` en écriture, objets imbriqués en
  lecture).
- Reprend en `validate()` les mêmes contrôles que le modèle (non-ambiguïté
  générique/typée, dépassement de volume) pour renvoyer des erreurs 400
  lisibles côté frontend plutôt qu'une 500.

### 3.2 `AffectationModuleViewSet`

- CRUD standard, `router.register(r'affectations', ...)`.
- Permissions : réservées au chef de département (et éventuellement au
  référent, selon la décision de la phase 0) — probablement
  `IsChefDepartementOrReadOnly` ou une permission dédiée si le périmètre
  diffère de celui déjà utilisé pour les autres ressources pédagogiques.
- Filtrage par `module_id`, `enseignant_id`, `semestre_id` (via
  `module__semestre_id`).

### 3.3 Adaptation de `SeanceSerializer`

- Le message d'erreur de dépassement de volume doit distinguer clairement
  « volume de l'affectation dépassé » de « volume du module dépassé », pour
  que l'utilisateur sache quoi corriger (redemander une affectation
  supplémentaire, ou constater que le module est complet).
- Aucun nouveau champ obligatoire côté `SeanceSerializer` : le rattachement
  à l'affectation est résolu côté serveur, pas saisi par l'utilisateur.

---

## Phase 4 — Frontend

### 4.1 Nouvelle vue de répartition (côté chef de département)

- Écran dédié à la création/modification des `AffectationModule` pour un
  module donné : liste des enseignants du département, volume affecté,
  volume restant sur le module en temps réel.
- Emplacement dans la navigation : probablement à côté de la page
  « Modules » existante (`ModulesPage.jsx`), en complément — par exemple un
  onglet « Répartition » sur la fiche module, plutôt qu'une page séparée
  dans le menu principal (point de décision UI ouvert, à discuter selon vos
  préférences d'ergonomie).

### 4.2 Adaptation de `SeanceForm.jsx`

- L'indicateur d'heures restantes déjà présent
  (`moduleSelectionne.heures_restantes`) doit être complété par un second
  indicateur : les heures restantes sur l'affectation de l'enseignant
  sélectionné, une fois qu'il est choisi dans le formulaire.
- Le message d'erreur serveur (déjà géré via le `Popover` d'erreur existant)
  affichera naturellement la distinction affectation/module si le backend la
  fournit distinctement.

### 4.3 Adaptation de `useCascadeSelects.js`

- Prévoir un filtrage optionnel de la liste des enseignants proposés pour un
  module donné, limité à ceux qui ont une affectation dessus (si aucune
  affectation n'existe pour le module, on retombe sur le comportement actuel
  — tous les enseignants du département).

---

## Phase 5 — Migration des données existantes et bascule

- Aucune régénération rétroactive d'affectations (décision déjà actée).
- Communication aux chefs de département : à partir de la mise en service,
  toute nouvelle séance sur un module déjà couvert par des affectations
  devra respecter ces affectations ; les modules sans affectation
  continuent de fonctionner comme avant tant qu'aucune affectation n'y est
  créée.
- Prévoir une période de transition où les chefs de département saisissent
  progressivement les affectations pour le semestre en cours, sans bloquer
  la création de séances entre-temps (cohérent avec la dégradation
  gracieuse du niveau 3).

---

## Phase 6 — Tests

- Modèle `AffectationModule` : contrainte de non-ambiguïté
  générique/typée, contrainte de dépassement de volume du module.
- Résolution d'affectation dans `Seance.clean()` : les trois cas (typée
  trouvée, générique trouvée en repli, aucune trouvée avec/sans affectations
  existantes sur le module).
- Dégradation gracieuse : séance créée sur un module sans aucune
  affectation → comportement identique à l'existant.
- Dépassement du volume d'une affectation individuelle → erreur distincte
  du dépassement du volume global du module.
- Tests d'API sur `AffectationModuleViewSet` (permissions, validation,
  filtrage).

---

## Ordre de mise en œuvre recommandé

1. Phase 0 (décisions) — bloquant pour la suite.
2. Phase 1 (modèle `AffectationModule` + migration).
3. Phase 6, partiellement — tests du modèle seul, avant d'toucher à `Seance`.
4. Phase 2 (intégration dans `Seance.clean()`).
5. Phase 6, complément — tests d'intégration séance/affectation.
6. Phase 3 (serializers + API).
7. Phase 4 (frontend).
8. Phase 5 (bascule en production).
