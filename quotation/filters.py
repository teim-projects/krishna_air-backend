import django_filters
from .models import Quotation


class QuotationFilter(django_filters.FilterSet):
    """
    Filter set for Quotation model.
    Supports date range on created_at (quotation creation date).
    created_at is a DateTimeField so we use DateTimeFromToRangeFilter
    or cast via DateFilter with the 'date' transform.
    """

    # Quotation creation date range — compare against date portion of DateTimeField
    date_from = django_filters.DateFilter(
        field_name="created_at",
        lookup_expr="date__gte"
    )
    date_to = django_filters.DateFilter(
        field_name="created_at",
        lookup_expr="date__lte"
    )

    class Meta:
        model = Quotation
        fields = [
            "date_from",
            "date_to",
        ]
