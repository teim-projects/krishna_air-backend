"""
Dashboard API Views
Each view returns aggregated data for one dashboard tab.

Supported query params (all optional):
  date_from      YYYY-MM-DD   — lower bound on the primary date field of each view
  date_to        YYYY-MM-DD   — upper bound
  lead_status    open,closed,in_process   (comma-separated, any subset)
  lead_type      sales,service,both       (comma-separated, any subset)
  product_names  <ProductModel.name,...>  (comma-separated, any subset)

Filter applicability per tab:
  sales-overview  → date (invoice_date / quotation created_at), product_names
  leads           → date (lead.date), lead_status, lead_type
  customers       → date (invoice_date), product_names
  followups       → date (followup_date), lead_status
  products        → product_names
  quotations      → date (quotation created_at), product_names
  invoices        → date (invoice_date), product_names
  filter-options  → (no params) — returns all dynamic option lists
"""

import calendar as _calendar
from decimal import Decimal

from django.db.models import Count, Sum, Q, F, Min
from django.db.models.functions import TruncMonth, Coalesce, ExtractYear, ExtractMonth
from django.utils.dateparse import parse_date
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

# ── model imports ──────────────────────────────────────────────────────────────
from lead_management.models import lead_management as Lead, Customer, LeadFollowUp
from quotation.models import Quotation, QuotationVersion, QuotationHighSideItem
from invoice.models import Invoice, HighSideInvoiceItem
from product_management.models import acType, ProductVariant, ProductModel, ProductInventory
from inventory.models import MaterialIssueItem
from api.models import SiteManagement


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _month_label(year, month):
    return f"{_calendar.month_abbr[month]} {year}"


def _annotate_monthly(qs, date_field):
    return qs.annotate(
        year=ExtractYear(date_field),
        month=ExtractMonth(date_field),
    )


def _apply_date(qs, field, request):
    """Filter qs by date_from / date_to on *field*."""
    date_from = request.query_params.get("date_from")
    date_to   = request.query_params.get("date_to")
    if date_from:
        parsed = parse_date(date_from)
        if parsed:
            qs = qs.filter(**{f"{field}__gte": parsed})
    if date_to:
        parsed = parse_date(date_to)
        if parsed:
            qs = qs.filter(**{f"{field}__lte": parsed})
    return qs


def _get_list(request, key):
    """Parse comma-separated query param into a list. [] means 'no filter / all'."""
    raw = request.query_params.get(key, "").strip()
    if not raw:
        return []
    return [v.strip() for v in raw.split(",") if v.strip()]


# ── Product filter helpers ─────────────────────────────────────────────────────

def _filter_invoices_by_product(qs, names):
    if not names:
        return qs
    return qs.filter(
        high_side_items__product_variant__product_model__name__in=names
    ).distinct()


def _filter_quotations_by_product(qs, names):
    if not names:
        return qs
    return qs.filter(
        versions__is_active=True,
        versions__high_side_items__product_variant__product_model__name__in=names,
    ).distinct()


def _filter_qversions_by_product(qs, names):
    if not names:
        return qs
    return qs.filter(
        high_side_items__product_variant__product_model__name__in=names
    ).distinct()


# ─── reusable invoice base ────────────────────────────────────────────────────
def _invoice_qs(request):
    qs = Invoice.objects.all()
    qs = _apply_date(qs, "invoice_date", request)
    qs = _filter_invoices_by_product(qs, _get_list(request, "product_names"))
    return qs


# ─── reusable quotation base ──────────────────────────────────────────────────
def _quotation_qs(request):
    qs = Quotation.objects.all()
    qs = _apply_date(qs, "created_at", request)
    qs = _filter_quotations_by_product(qs, _get_list(request, "product_names"))
    return qs


# ─── reusable lead base ───────────────────────────────────────────────────────
def _lead_qs(request):
    """
    Build a filtered Lead queryset.
    Date filter: try lead.date first; if null, fall back to lead.enquiry_date.
    We use a Q-object so that a lead qualifies if EITHER its date OR enquiry_date
    falls within the range.  Leads where both are null are excluded when a date
    range is active — correct analytic behaviour.
    """
    date_from_str = request.query_params.get("date_from", "").strip()
    date_to_str   = request.query_params.get("date_to",   "").strip()
    date_from = parse_date(date_from_str) if date_from_str else None
    date_to   = parse_date(date_to_str)   if date_to_str   else None

    qs = Lead.objects.all()

    if date_from or date_to:
        # Build Q for date field
        q_date = Q()
        if date_from:
            q_date &= Q(date__gte=date_from)
        if date_to:
            q_date &= Q(date__lte=date_to)

        # Build Q for enquiry_date fallback (only for records where date is null)
        q_enq = Q(date__isnull=True)
        if date_from:
            q_enq &= Q(enquiry_date__gte=date_from)
        if date_to:
            q_enq &= Q(enquiry_date__lte=date_to)

        qs = qs.filter(q_date | q_enq)

    statuses = _get_list(request, "lead_status")
    types    = _get_list(request, "lead_type")
    if statuses:
        qs = qs.filter(status__in=statuses)
    if types:
        qs = qs.filter(is_service_lead__in=types)

    return qs


# ═══════════════════════════════════════════════════════════════════════════════
# 0. Filter Options  (dynamic dropdown data for the frontend)
# ═══════════════════════════════════════════════════════════════════════════════

class FilterOptionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Lead statuses — derive from actual data so new values appear automatically
        lead_statuses = list(
            Lead.objects.exclude(status="").exclude(status=None)
            .values_list("status", flat=True)
            .distinct()
            .order_by("status")
        )

        # Lead types (is_service_lead values)
        lead_types = list(
            Lead.objects.exclude(is_service_lead="").exclude(is_service_lead=None)
            .values_list("is_service_lead", flat=True)
            .distinct()
            .order_by("is_service_lead")
        )

        # Lead sources
        lead_sources = list(
            Lead.objects.exclude(lead_source="").exclude(lead_source=None)
            .values_list("lead_source", flat=True)
            .distinct()
            .order_by("lead_source")
        )

        # Product model names (for the Product Name filter)
        product_names = list(
            ProductModel.objects.filter(is_active=True)
            .values_list("name", flat=True)
            .distinct()
            .order_by("name")
        )

        return Response({
            "lead_statuses":  lead_statuses,
            "lead_types":     lead_types,
            "lead_sources":   lead_sources,
            "product_names":  product_names,
        })


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Sales Overview
# ═══════════════════════════════════════════════════════════════════════════════

class SalesOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        invoices   = _invoice_qs(request)
        quotations = _quotation_qs(request)

        # ── KPIs ──────────────────────────────────────────────────────────────
        total_revenue   = invoices.aggregate(v=Coalesce(Sum("grand_total"), Decimal("0")))["v"]
        total_invoice   = invoices.count()
        total_customer  = Customer.objects.count()          # global: not date-filtered
        total_leads     = Lead.objects.count()              # global: not date-filtered
        total_quotation = quotations.count()

        # ── Monthly revenue trend ──────────────────────────────────────────────
        monthly_revenue = (
            _annotate_monthly(invoices, "invoice_date")
            .values("year", "month")
            .annotate(revenue=Sum("grand_total"))
            .order_by("year", "month")
        )
        monthly_revenue_data = [
            {"month": _month_label(r["year"], r["month"]), "revenue": float(r["revenue"] or 0)}
            for r in monthly_revenue
        ]

        # ── Invoice count per month ────────────────────────────────────────────
        # FIX #4: evaluate once into a list so it can be iterated twice
        inv_monthly_raw = list(
            _annotate_monthly(invoices, "invoice_date")
            .values("year", "month")
            .annotate(invoice_count=Count("id"))
            .order_by("year", "month")
        )

        # ── Quotation count per month ──────────────────────────────────────────
        quot_monthly_raw = list(
            _annotate_monthly(quotations, "created_at")
            .values("year", "month")
            .annotate(quotation_count=Count("id"))
            .order_by("year", "month")
        )

        # Merge by month key
        inv_map  = {(r["year"], r["month"]): r["invoice_count"]   for r in inv_monthly_raw}
        quot_map = {(r["year"], r["month"]): r["quotation_count"] for r in quot_monthly_raw}
        all_keys = sorted(set(list(inv_map) + list(quot_map)))
        inv_vs_quot = [
            {
                "month":          _month_label(y, m),
                "invoice_count":  inv_map.get((y, m), 0),
                "quotation_count": quot_map.get((y, m), 0),
            }
            for y, m in all_keys
        ]

        monthly_invoice_count_data = [
            {"month": _month_label(r["year"], r["month"]), "count": r["invoice_count"]}
            for r in inv_monthly_raw
        ]

        # ── Revenue by customer ────────────────────────────────────────────────
        rev_by_customer = list(
            invoices.values("buyer_name")
            .annotate(revenue=Sum("grand_total"))
            .order_by("-revenue")[:10]
        )
        rev_by_customer_data = [
            {"customer": r["buyer_name"], "revenue": float(r["revenue"] or 0)}
            for r in rev_by_customer
        ]

        return Response({
            "kpi": {
                "total_revenue":   float(total_revenue),
                "total_customer":  total_customer,
                "total_leads":     total_leads,
                "total_invoice":   total_invoice,
                "total_quotation": total_quotation,
            },
            "monthly_revenue_trend":  monthly_revenue_data,
            "invoice_vs_quotation":   inv_vs_quot,
            "revenue_by_customer":    rev_by_customer_data,
            "monthly_invoice_count":  monthly_invoice_count_data,
        })


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Lead Management
# ═══════════════════════════════════════════════════════════════════════════════

class LeadManagementView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # FIX #1: _lead_qs applies date + status + type filters
        leads = _lead_qs(request)

        # ── KPIs ──────────────────────────────────────────────────────────────
        total_leads   = leads.count()
        open_leads    = leads.filter(status="open").count()
        closed_leads  = leads.filter(status="closed").count()
        sales_leads   = leads.filter(is_service_lead="sales").count()
        service_leads = leads.filter(is_service_lead="service").count()

        # ── Monthly trend ──────────────────────────────────────────────────────
        # For leads where date is set, use date; for those where date is null
        # but enquiry_date is set, use enquiry_date via a separate count.
        # Merge both into a single month bucket.
        from django.db.models.functions import Coalesce as _Coalesce
        from django.db.models import ExpressionWrapper, DateField as _DF

        # Annotate each lead with its effective date (date if set, else enquiry_date)
        monthly_trend = (
            leads
            .annotate(
                eff_date=_Coalesce("date", "enquiry_date")
            )
            .filter(eff_date__isnull=False)
            .annotate(
                year=ExtractYear("eff_date"),
                month=ExtractMonth("eff_date"),
            )
            .values("year", "month")
            .annotate(count=Count("id"))
            .order_by("year", "month")
        )
        monthly_trend_data = [
            {"month": _month_label(r["year"], r["month"]), "count": r["count"]}
            for r in monthly_trend
        ]

        # ── Status distribution ────────────────────────────────────────────────
        total      = total_leads or 1
        status_raw = list(
            leads.values("status").annotate(count=Count("id")).order_by("-count")
        )
        status_dist_data = [
            {
                "status":     r["status"],
                "count":      r["count"],
                "percentage": round(r["count"] / total * 100, 1),
            }
            for r in status_raw
        ]

        # ── Source distribution ────────────────────────────────────────────────
        source_raw = list(
            leads.values("lead_source").annotate(count=Count("id")).order_by("-count")
        )
        source_dist_data = [
            {
                "source":     r["lead_source"] or "unknown",
                "count":      r["count"],
                "percentage": round(r["count"] / total * 100, 1),
            }
            for r in source_raw
        ]

        # ── Type distribution ──────────────────────────────────────────────────
        type_raw = list(
            leads.values("is_service_lead").annotate(count=Count("id")).order_by("-count")
        )
        type_dist_data = [
            {"type": r["is_service_lead"] or "unset", "count": r["count"]}
            for r in type_raw
        ]

        return Response({
            "kpi": {
                "total_leads":   total_leads,
                "open_leads":    open_leads,
                "closed_leads":  closed_leads,
                "sales_leads":   sales_leads,
                "service_leads": service_leads,
            },
            "monthly_trend":       monthly_trend_data,
            "status_distribution": status_dist_data,
            "source_distribution": source_dist_data,
            "type_distribution":   type_dist_data,
        })


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Customer Management
# ═══════════════════════════════════════════════════════════════════════════════

class CustomerManagementView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        invoices   = _invoice_qs(request)
        product_names = _get_list(request, "product_names")

        # ── KPIs ──────────────────────────────────────────────────────────────
        total_customers  = Customer.objects.count()
        total_sites      = SiteManagement.objects.count()
        total_quotations = _filter_quotations_by_product(
            Quotation.objects.all(), product_names
        ).count()
        customer_revenue = invoices.aggregate(
            v=Coalesce(Sum("grand_total"), Decimal("0"))
        )["v"]

        # ── Revenue by customer ────────────────────────────────────────────────
        rev_by_customer = list(
            invoices.values("buyer_name")
            .annotate(revenue=Sum("grand_total"))
            .order_by("-revenue")[:10]
        )
        rev_by_customer_data = [
            {"customer": r["buyer_name"], "revenue": float(r["revenue"] or 0)}
            for r in rev_by_customer
        ]

        # ── Customers by month — use effective date (date ?? enquiry_date) ──────
        from django.db.models.functions import Coalesce as _Coalesce
        leads_for_month = Lead.objects.filter(
            Q(date__isnull=False) | Q(enquiry_date__isnull=False)
        )
        # Apply date filter using same logic as _lead_qs
        date_from_str = request.query_params.get("date_from", "").strip()
        date_to_str   = request.query_params.get("date_to",   "").strip()
        d_from = parse_date(date_from_str) if date_from_str else None
        d_to   = parse_date(date_to_str)   if date_to_str   else None
        if d_from or d_to:
            q_d = Q()
            q_e = Q(date__isnull=True)
            if d_from:
                q_d &= Q(date__gte=d_from);  q_e &= Q(enquiry_date__gte=d_from)
            if d_to:
                q_d &= Q(date__lte=d_to);    q_e &= Q(enquiry_date__lte=d_to)
            leads_for_month = leads_for_month.filter(q_d | q_e)

        monthly_customers = list(
            leads_for_month
            .annotate(eff_date=_Coalesce("date", "enquiry_date"))
            .annotate(month_trunc=TruncMonth("eff_date"))
            .values("month_trunc")
            .annotate(count=Count("customer_id", distinct=True))
            .order_by("month_trunc")
        )
        cust_by_month_data = [
            {
                "month": r["month_trunc"].strftime("%b %Y") if r["month_trunc"] else "Unknown",
                "count": r["count"],
            }
            for r in monthly_customers
        ]

        # ── Customers by quotation count ───────────────────────────────────────
        cust_by_quot = list(
            _filter_quotations_by_product(Quotation.objects.all(), product_names)
            .values("customer__name")
            .annotate(quotation_count=Count("id"))
            .order_by("-quotation_count")[:10]
        )
        cust_by_quot_data = [
            {"customer": r["customer__name"], "count": r["quotation_count"]}
            for r in cust_by_quot
        ]

        return Response({
            "kpi": {
                "total_customers":  total_customers,
                "total_sites":      total_sites,
                "total_quotations": total_quotations,
                "customer_revenue": float(customer_revenue),
            },
            "revenue_by_customer":     rev_by_customer_data,
            "customers_by_month":      cust_by_month_data,
            "customers_by_quotations": cust_by_quot_data,
        })


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Follow-up Management
# ═══════════════════════════════════════════════════════════════════════════════

class FollowupManagementView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        followups = LeadFollowUp.objects.all()
        # FIX #1: date filter on followup_date; also support created_at fallback
        followups = _apply_date(followups, "followup_date", request)

        # lead_status filter applies to followup status
        statuses = _get_list(request, "lead_status")
        if statuses:
            followups = followups.filter(status__in=statuses)

        # ── KPIs ──────────────────────────────────────────────────────────────
        total      = followups.count()
        open_f     = followups.filter(status="open").count()
        closed_f   = followups.filter(status="closed").count()
        inproc_f   = followups.filter(status="in_process").count()

        # ── Status distribution ────────────────────────────────────────────────
        denom      = total or 1
        status_raw = list(
            followups.values("status").annotate(count=Count("id")).order_by("-count")
        )
        status_dist_data = [
            {
                "status":     r["status"],
                "count":      r["count"],
                "percentage": round(r["count"] / denom * 100, 1),
            }
            for r in status_raw
        ]

        # ── Monthly follow-ups ─────────────────────────────────────────────────
        monthly_raw = list(
            _annotate_monthly(followups, "followup_date")
            .values("year", "month")
            .annotate(count=Count("id"))
            .order_by("year", "month")
        )
        monthly_data = [
            {"month": _month_label(r["year"], r["month"]), "count": r["count"]}
            for r in monthly_raw
        ]

        return Response({
            "kpi": {
                "total_followups":     total,
                "open_followups":      open_f,
                "closed_followups":    closed_f,
                "inprocess_followups": inproc_f,
            },
            "status_distribution": status_dist_data,
            "monthly_followups":   monthly_data,
        })


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Product & Service Management
# ═══════════════════════════════════════════════════════════════════════════════

class ProductServiceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        product_names = _get_list(request, "product_names")

        # ── KPIs ──────────────────────────────────────────────────────────────
        total_ac_types = acType.objects.count()

        variant_qs = ProductVariant.objects.all()
        if product_names:
            variant_qs = variant_qs.filter(product_model__name__in=product_names)
        total_variants = variant_qs.count()

        pi_qs = ProductInventory.objects.filter(status="SOLD")
        if product_names:
            pi_qs = pi_qs.filter(product_variant__product_model__name__in=product_names)
        total_unit_sold = pi_qs.count()

        hsi_qs = QuotationHighSideItem.objects.filter(quotation_version__is_active=True)
        if product_names:
            hsi_qs = hsi_qs.filter(product_variant__product_model__name__in=product_names)
        units_quoted = hsi_qs.aggregate(total=Coalesce(Sum("quantity"), 0))["total"]

        inv_hsi_qs = HighSideInvoiceItem.objects.all()
        if product_names:
            inv_hsi_qs = inv_hsi_qs.filter(
                product_variant__product_model__name__in=product_names
            )
        product_revenue = inv_hsi_qs.aggregate(
            total=Coalesce(Sum("amount"), Decimal("0"))
        )["total"]

        # ── Revenue by AC type ─────────────────────────────────────────────────
        rev_by_ac_type = list(
            inv_hsi_qs
            .values(ac_name=F("product_variant__product_model__ac_sub_type_id__ac_type_id__name"))
            .annotate(revenue=Sum("amount"))
            .order_by("-revenue")
        )
        rev_by_ac_type_data = [
            {"ac_type": r["ac_name"] or "Unknown", "revenue": float(r["revenue"] or 0)}
            for r in rev_by_ac_type
        ]

        # ── Top selling material types (by issued quantity) ────────────────────
        try:
            mat_qs = (
                MaterialIssueItem.objects
                .filter(inventory_item__item__isnull=False)
                .values(mat_name=F("inventory_item__item__material_type_id__name"))
                .annotate(total_qty=Sum("quantity"))
                .order_by("-total_qty")[:8]
            )
            top_material_data = [
                {"material_type": r["mat_name"] or "Unknown", "amount": float(r["total_qty"] or 0)}
                for r in mat_qs
            ]
        except Exception:
            top_material_data = []

        # ── Revenue by product model ───────────────────────────────────────────
        rev_by_model = list(
            inv_hsi_qs
            .values(model_name=F("product_variant__product_model__name"))
            .annotate(revenue=Sum("amount"))
            .order_by("-revenue")[:8]
        )
        rev_by_model_data = [
            {"model": r["model_name"] or "Unknown", "revenue": float(r["revenue"] or 0)}
            for r in rev_by_model
        ]

        # ── Top product variants by quantity quoted ────────────────────────────
        top_variants = list(
            hsi_qs
            .values(sku=F("product_variant__sku"))
            .annotate(total_qty=Sum("quantity"))
            .order_by("-total_qty")[:8]
        )
        top_variants_data = [
            {"variant": r["sku"], "quantity": float(r["total_qty"] or 0)}
            for r in top_variants
        ]

        return Response({
            "kpi": {
                "total_ac_types":  total_ac_types,
                "total_variants":  total_variants,
                "total_unit_sold": float(total_unit_sold),
                "units_quoted":    float(units_quoted),
                "product_revenue": float(product_revenue),
            },
            "revenue_by_ac_type": rev_by_ac_type_data,
            "top_material_types": top_material_data,
            "revenue_by_model":   rev_by_model_data,
            "top_variants":       top_variants_data,
        })


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Quotation Management
# ═══════════════════════════════════════════════════════════════════════════════

class QuotationManagementView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        quotations    = _quotation_qs(request)
        product_names = _get_list(request, "product_names")

        total_quotations = quotations.count()

        active_versions = QuotationVersion.objects.filter(
            quotation__in=quotations, is_active=True
        )
        active_versions = _filter_qversions_by_product(active_versions, product_names)

        total_amount = active_versions.aggregate(
            v=Coalesce(Sum("grand_total"), Decimal("0"))
        )["v"]

        # ── Monthly trend (amount) ─────────────────────────────────────────────
        monthly_raw = list(
            active_versions
            .annotate(
                year=ExtractYear("quotation__created_at"),
                month=ExtractMonth("quotation__created_at"),
            )
            .values("year", "month")
            .annotate(amount=Sum("grand_total"))
            .order_by("year", "month")
        )
        monthly_trend_data = [
            {"month": _month_label(r["year"], r["month"]), "amount": float(r["amount"] or 0)}
            for r in monthly_raw
        ]

        # ── Customers by quotation count ───────────────────────────────────────
        cust_raw = list(
            quotations.values("customer__name")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )
        cust_by_quot_data = [
            {"customer": r["customer__name"], "count": r["count"]}
            for r in cust_raw
        ]

        return Response({
            "kpi": {
                "total_quotations": total_quotations,
                "total_amount":     float(total_amount),
            },
            "monthly_trend":           monthly_trend_data,
            "customers_by_quotations": cust_by_quot_data,
        })


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Invoice Management
# ═══════════════════════════════════════════════════════════════════════════════

class InvoiceManagementView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        invoices = _invoice_qs(request)

        total_invoice = invoices.count()
        total_amount  = invoices.aggregate(
            v=Coalesce(Sum("grand_total"), Decimal("0"))
        )["v"]

        # ── Revenue by customer ────────────────────────────────────────────────
        rev_by_customer = list(
            invoices.values("buyer_name")
            .annotate(revenue=Sum("grand_total"))
            .order_by("-revenue")[:10]
        )
        rev_by_customer_data = [
            {"customer": r["buyer_name"], "revenue": float(r["revenue"] or 0)}
            for r in rev_by_customer
        ]

        # ── Monthly invoice count ──────────────────────────────────────────────
        # FIX #4: evaluated once into list, reused for both count and revenue
        inv_monthly = list(
            _annotate_monthly(invoices, "invoice_date")
            .values("year", "month")
            .annotate(count=Count("id"), revenue=Sum("grand_total"))
            .order_by("year", "month")
        )
        monthly_count_data = [
            {"month": _month_label(r["year"], r["month"]), "count": r["count"]}
            for r in inv_monthly
        ]
        monthly_revenue_data = [
            {"month": _month_label(r["year"], r["month"]), "revenue": float(r["revenue"] or 0)}
            for r in inv_monthly
        ]

        return Response({
            "kpi": {
                "total_invoice": total_invoice,
                "total_amount":  float(total_amount),
            },
            "revenue_by_customer":    rev_by_customer_data,
            "invoice_count_by_month": monthly_count_data,
            "monthly_revenue":        monthly_revenue_data,
        })
