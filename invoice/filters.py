import django_filters
from .models import Invoice


class InvoiceFilter(django_filters.FilterSet):
    """
    Filter set for Invoice model.
    Supports date range on invoice_date and gst_type exact match.
    """

    # Invoice date range
    date_from = django_filters.DateFilter(
        field_name="invoice_date",
        lookup_expr="gte"
    )
    date_to = django_filters.DateFilter(
        field_name="invoice_date",
        lookup_expr="lte"
    )

    # GST type exact match
    gst_type = django_filters.CharFilter(
        field_name="gst_type",
        lookup_expr="exact"
    )

    class Meta:
        model = Invoice
        fields = [
            "date_from",
            "date_to",
            "gst_type",
        ]
