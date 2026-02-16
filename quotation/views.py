from rest_framework import viewsets, status, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action

from rest_framework_simplejwt.authentication import JWTAuthentication

from django.db.models import Prefetch
from django.utils import timezone

from .models import Quotation, QuotationVersion,QuotationHighSideItem
from .serializers import QuotationSerializer


class QuotationViewSet(viewsets.ModelViewSet):

    serializer_class = QuotationSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    filter_backends = [filters.SearchFilter]

    # 🔎 Allow searching like LeadViewSet
    search_fields = [
        "quotation_no",
        "customer__name",
        "customer__contact_number",
        "subject",
        "site_name"
    ]

    # ============================
    # QUERYSET OPTIMIZATION
    # ============================
    def get_queryset(self):

        return (
            Quotation.objects
            .select_related("customer")
            .prefetch_related(
                Prefetch(
    "versions",
    queryset=QuotationVersion.objects.all().order_by("-version_no")
)

            )
            .order_by("-id")
        )

    # ============================
    # AUTO SET USER ON CREATE
    # ============================
    def perform_create(self, serializer):
        serializer.save()

    # ============================
    # 🔥 CUSTOM API
    # Get latest active version
    # ============================
    @action(detail=True, methods=["get"], url_path="latest-version")
    def latest_version(self, request, pk=None):

        quotation = self.get_object()

        version = quotation.versions.filter(is_active=True).first()

        if not version:
            return Response(
                {"message": "No active version found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(quotation)
        return Response(serializer.data)
