# EDT_app/pagination.py
#
# Pagination commune à toutes les listes de l'API.

from rest_framework.pagination import PageNumberPagination


class PaginationStandard(PageNumberPagination):
    """
    20 lignes par page, comme avant. L'interface peut demander jusqu'à 200
    lignes avec `?page_size=` quand elle sait que la liste est courte (une
    semaine de planning) : une seule requête au lieu d'une par tranche de 20
    (V5). Une valeur absurde (`abc`, `-1`) retombe sur 20 ; une valeur trop
    grande est ramenée à 200.
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 200
