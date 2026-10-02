# outils_tests.py
#
# Outils partagés par les tests du plan « solidité et sécurité »
# (tests_securite_roles.py, tests_securite_jetons.py, tests_solidite.py).
# Le nom ne commence pas par « test » : le lanceur de tests ne le parcourt pas.

import functools
import os
import sys
import unittest


def faille_connue(point):
    """
    Marque un test dont la règle n'est pas encore respectée par l'application.

    Le test décrit le comportement VOULU. Tant que la faille existe, il échoue
    et compte comme « expected failure » ; le jour où elle est corrigée, il
    réussit et apparaît en « unexpected success » : retirer alors ce
    décorateur et clore le point de CORRECTIONS_A_FAIRE.md.

    Diagnostic : lancer les tests avec la variable VOIR_FAILLES=1 affiche la
    raison de chaque échec attendu, pour vérifier qu'il échoue bien à cause
    de la faille et pas d'une donnée de test mal construite.
    """
    def decorer(test):
        @functools.wraps(test)
        def enveloppe(self, *args, **kwargs):
            try:
                return test(self, *args, **kwargs)
            except Exception as exc:
                if os.environ.get("VOIR_FAILLES"):
                    sys.stderr.write(
                        f"\n[faille point {point}] {self.id()}\n"
                        f"    {type(exc).__name__}: {str(exc)[:600]}\n"
                    )
                raise
        enveloppe.point_corrections = point
        return unittest.expectedFailure(enveloppe)
    return decorer


def refus_manquants(requetes, codes_refus):
    """
    Exécute chaque requête (libellé, fonction) et renvoie la liste de celles
    qui n'ont PAS été refusées, avec leur code et le début de la réponse.
    Remplace subTest dans les tests marqués faille_connue : un échec dans un
    subTest n'est pas visible par le décorateur.
    """
    acceptees = []
    for libelle, requete in requetes:
        resp = requete()
        if resp.status_code not in codes_refus:
            acceptees.append(f"{libelle} → {resp.status_code} {resp.content[:120]!r}")
    return acceptees
