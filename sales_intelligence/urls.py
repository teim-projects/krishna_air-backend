from django.urls import path

from .views import (
    LeadScoringView,
    LeadConversionView,
)


urlpatterns = [
    path(
        "lead-scoring/",
        LeadScoringView.as_view(),
        name="lead-scoring",
    ),

    path(
        "lead-conversion/",
        LeadConversionView.as_view(),
        name="lead-conversion",
    ),
]