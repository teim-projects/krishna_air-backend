import django_filters
from django.utils import timezone
from .models import lead_management


class LeadFilter(django_filters.FilterSet):
    # 🔹 Follow-up date range
    followup_date_from = django_filters.DateFilter(
        field_name="followup_date",
        lookup_expr="gte"
    )
    followup_date_to = django_filters.DateFilter(
        field_name="followup_date",
        lookup_expr="lte"
    )

    # 🔹 Lead date range
    date_from = django_filters.DateFilter(
        field_name="date",
        lookup_expr="gte"
    )
    date_to = django_filters.DateFilter(
        field_name="date",
        lookup_expr="lte"
    )

    # 🔹 Overdue follow-ups
    overdue = django_filters.BooleanFilter(method="filter_overdue")

    def filter_overdue(self, queryset, name, value):
        """
        overdue=true → followup_date < today AND followup_date IS NOT NULL
        """
        if value:
            today = timezone.localdate()
            return queryset.filter(
                followup_date__lt=today,
                followup_date__isnull=False
            ).exclude(status="closed")
        return queryset

    class Meta:
        model = lead_management
        fields = [
            "assign_to",
            "status",
            "followup_date_from",
            "followup_date_to",
            "date_from",
            "date_to",
            "overdue",
        ]
