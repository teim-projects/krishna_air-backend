from django.urls import path
from .views import (
    FilterOptionsView,
    SalesOverviewView,
    LeadManagementView,
    CustomerManagementView,
    CustomerIntelligenceView,
    FollowupManagementView,
    ProductServiceView,
    QuotationManagementView,
    InvoiceManagementView,
)

urlpatterns = [
    # Dynamic filter option lists (lead statuses, types, sources, product names)
    path("filter-options/",  FilterOptionsView.as_view(),      name="dashboard-filter-options"),
    # Tab data
    path("sales-overview/",  SalesOverviewView.as_view(),      name="dashboard-sales-overview"),
    path("leads/",           LeadManagementView.as_view(),     name="dashboard-leads"),
    path("customers/",       CustomerManagementView.as_view(), name="dashboard-customers"),
    path(
    "customer-intelligence/",
    CustomerIntelligenceView.as_view(),
    name="dashboard-customer-intelligence"
    ),
    path("followups/",       FollowupManagementView.as_view(), name="dashboard-followups"),
    path("products/",        ProductServiceView.as_view(),     name="dashboard-products"),
    path("quotations/",      QuotationManagementView.as_view(),name="dashboard-quotations"),
    path("invoices/",        InvoiceManagementView.as_view(),  name="dashboard-invoices"),
]
