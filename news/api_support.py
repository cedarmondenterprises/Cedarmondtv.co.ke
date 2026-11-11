from rest_framework.pagination import PageNumberPagination
from rest_framework.throttling import AnonRateThrottle

from .security import client_ip


class PublicAPIThrottle(AnonRateThrottle):
    scope = 'public_api'

    def get_ident(self, request):
        return client_ip(request._request)


class PublicPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 50
