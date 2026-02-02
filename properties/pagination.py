from rest_framework.pagination import PageNumberPagination


class PropertyPagination(PageNumberPagination):
    """
    Pagination settings for property listings.
    """

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


