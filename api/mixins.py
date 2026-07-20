from rest_framework.pagination import PageNumberPagination


class OptionalAllPaginationMixin:
    """Skip pagination when ?all=true is passed (for form dropdowns)."""

    def paginate_queryset(self, queryset):
        if self.request.query_params.get("all") == "true":
            return None
        return super().paginate_queryset(queryset)
