"""
Les deux index d'unicité à expression créés par 0016 restent dans la base
(c'est elle qui bloque les doublons, même simultanés), mais Django cesse de
les connaître : pour les vérifier avant d'enregistrer, il comparait la
colonne à une valeur convertie avec la collation de la connexion
(utf8mb4_0900_ai_ci), ce que MySQL refuse quand les colonnes sont en
utf8mb4_unicode_ci (erreur 1267). Créer une classe de L1 ou une affectation
plantait alors. Les contrôles avec message clair sont dans Classe.clean() et
AffectationModule.clean() (CORRECTIONS_A_FAIRE.md point 31).
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('EDT_app', '0016_unicite_annee_affectation_classe'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveConstraint(
                    model_name='affectationmodule',
                    name='unique_affectation_module_enseignant_type',
                ),
                migrations.RemoveConstraint(
                    model_name='classe',
                    name='unique_classe_sans_filiere',
                ),
            ],
            database_operations=[],
        ),
    ]
