from .models import CveAnalysisStatus
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import CveYearCount

from django.db.models import Count
import json
from datetime import datetime
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Sum, Case, When, IntegerField
from django.db.models.functions import TruncYear

# graphviews.py
from django.http import JsonResponse, HttpRequest
from django.utils import timezone
from django.views.decorators.http import require_GET
from django.db.models import Count
from django.db.models.functions import ExtractYear, ExtractMonth
from typing import Dict, Any, List

from .models import CveChange
from .models import CveChange, CveOption

# Template mapping for analysis status (logical grouping)
STATUS_TEMPLATE = {
    "Received": ["CVE Received"],
    "Awaiting Analysis": ["CVE Source Update", "CVE Translated", "Vendor Comment"],
    "Undergoing Analysis": ["Initial Analysis", "Reanalysis"],
    "Modified": ["CVE Modified", "Modified Analysis"],
    "Deferred": ["CWE Remap", "Reference Tag Update", "CPE Deprecation Remap"],
    "Rejected": ["CVE Rejected"],
}


@csrf_exempt
def api_event_counts(request):

    # Fetch all options (name + stored count)
    options = list(CveOption.objects.values("eventName", "eventCount"))
    # If no options configured, return empty result
    if not options:
        return JsonResponse({
            "timestamp": timezone.now().isoformat(),
            "total_events_counted": 0,
            "event_counts": {},

        })

    # Build mapping of eventName -> stored_count (could be None)
    stored_map = {opt["eventName"]: (
        opt["eventCount"] if opt["eventCount"] is not None else None) for opt in options}
    event_names = list(stored_map.keys())

    # For any option where stored count is None, compute counts from cve_changes in one DB query
    need_counts = [name for name, cnt in stored_map.items() if cnt is None]
    computed_map = {}
    if need_counts:
        qs = (
            CveChange.objects
            .filter(eventName__in=need_counts)
            .values("eventName")
            .annotate(count=Count("id"))
        )
        computed_map = {item["eventName"]: item["count"] for item in qs}

    # Compose final event -> count, preferring stored count, else computed count, else 0
    final_counts = {}
    for name in event_names:
        if stored_map.get(name) is not None:
            final_counts[name] = int(stored_map[name])
        else:
            final_counts[name] = int(computed_map.get(name, 0))

    return JsonResponse({
        "timestamp": timezone.now().isoformat(),
        "total_events_counted": sum(final_counts.values()),
        "event_counts": final_counts,
    })


@csrf_exempt
def api_cve_year_counts(request):
    """
    Return all rows from cve_year_counts as JSON:
    [{ "event_year": 1999, "count": 123 }, ...]
    """
    qs = CveYearCount.objects.all().values(
        "event_year", "count").order_by("event_year")
    results = [{"event_year": r["event_year"],
                "count": int(r["count"])} for r in qs]

    return JsonResponse({
        "year_counts": results,
        # local path to your uploaded labels image (you said you'll transform it to a URL)

    })


@csrf_exempt
def api_top_sources(request):
    """
    Returns top N sourceIdentifier values by count.
    query param: ?limit=10  (defaults to 10)
    """
    try:
        limit = int(request.GET.get("limit", 10))
    except ValueError:
        limit = 10

    qs = (
        CveChange.objects
        .values("sourceIdentifier")
        .annotate(total_count=Count("id"))
        .order_by("-total_count")[:limit]
    )

    results = [
        {"source": r["sourceIdentifier"], "total_count": int(r["total_count"])}
        for r in qs
    ]

    return JsonResponse({
        "timestamp": timezone.now().isoformat(),
        "limit": limit,
        "top_sources": results,
    })


@csrf_exempt
def api_analysis_status(request):
    """
    Return vulnerability analysis status rows from cve_analysis_status table.
    """
    qs = CveAnalysisStatus.objects.all().values(
        "status_label", "count", "last_updated").order_by("status_label")
    results = [
        {
            "status_label": r["status_label"],
            "count": int(r["count"]),

        }
        for r in qs
    ]

    return JsonResponse({
        "timestamp": timezone.now().isoformat(),
        "total_statuses": len(results),
        "analysis_status": results,

    })


# uploaded sample image path (will be transformed to URL by your frontend/tooling)
SAMPLE_PLOT_IMAGE_PATH = "/mnt/data/fe9cbd49-5480-4bc9-a1f6-83aeef865b56.png"


# def _int_or_none(v):
#     try:
#         return int(v)
#     except (TypeError, ValueError):
#         return None


# @require_GET
# def api_monthly_event_trends(request: HttpRequest) -> JsonResponse:
#     """
#     Minimal endpoint that accepts only `year` as a query parameter (optional).
#     GET /api/monthly-event-trends/?year=2025

#     Response:
#     {
#       "timestamp": "...",
#       "year": 2025,
#       "available_years": [1992, ..., 2025],
#       "top_n": 5,
#       "events": [
#         {"eventName":"Initial Analysis","monthly":[m1..m12],"total":N},
#          ...
#       ],
#       "sample_plot_image": "/mnt/data/fe9cbd49-5480-4bc9-a1f6-83aeef865b56.png"
#     }
#     """
#     # Only parse `year` (optional). Default = current year.
#     q_year = _int_or_none(request.GET.get("year"))
#     year = q_year if q_year is not None else timezone.now().year

#     TOP_N = 5  # fixed top N returned

#     # Build base queryset limited to the requested year
#     qs = CveChange.objects.annotate(
#         event_year=ExtractYear("created")).filter(event_year=year)

#     # Available years for the dropdown (distinct years present in DB)
#     years_qs = (
#         CveChange.objects
#         .annotate(y=ExtractYear("created"))
#         .values_list("y", flat=True)
#         .distinct()
#         .order_by("y")
#     )
#     available_years = [int(y) for y in years_qs if y is not None]

#     # Aggregate by eventName and month at DB-level
#     annotated = (
#         qs
#         .annotate(event_month=ExtractMonth("created"))
#         .values("eventName", "event_month")
#         .annotate(cnt=Count("id"))
#         .order_by("eventName", "event_month")
#     )

#     # Build mapping: eventName -> { month -> count }
#     event_month_map: Dict[str, Dict[int, int]] = {}
#     for row in annotated:
#         ev = row.get("eventName") or "unknown"
#         month = row.get("event_month")
#         cnt = int(row.get("cnt") or 0)
#         if month is None:
#             continue
#         event_month_map.setdefault(ev, {})[int(month)] = cnt

#     # Choose top N eventNames by total count in that year
#     totals = [(ev, sum(months.values()))
#               for ev, months in event_month_map.items()]
#     totals.sort(key=lambda x: x[1], reverse=True)
#     selected_events = [ev for ev, _ in totals[:TOP_N]]

#     # Helper to produce Jan..Dec array (ints)
#     def monthly_list(ev_map: Dict[int, int]) -> List[int]:
#         return [int(ev_map.get(m, 0)) for m in range(1, 13)]

#     events_out: List[Dict[str, Any]] = []
#     for ev in selected_events:
#         months_map = event_month_map.get(ev, {})
#         monthly = monthly_list(months_map)
#         total = sum(monthly)
#         events_out.append(
#             {"eventName": ev, "monthly": monthly, "total": int(total)})

#     response = {
#         "timestamp": timezone.now().isoformat(),
#         "year": int(year),
#         "available_years": available_years,
#         "top_n": TOP_N,
#         "events": events_out,
#         "sample_plot_image": SAMPLE_PLOT_IMAGE_PATH,
#     }

#     return JsonResponse(response, json_dumps_params={"indent": 2})



from django.http import JsonResponse, HttpRequest
from django.utils import timezone
from django.views.decorators.http import require_GET
from django.db.models import Count
from django.db.models.functions import ExtractMonth
from django.core.cache import cache
from typing import Dict, Any, List
from datetime import datetime

from .models import CveChange

SAMPLE_PLOT_IMAGE_PATH = "/mnt/data/fe9cbd49-5480-4bc9-a1f6-83aeef865b56.png"

def _int_or_none(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None

@require_GET
def api_monthly_event_trends(request: HttpRequest) -> JsonResponse:
    """
    Optimized version:
    - Accepts ?year=YYYY (defaults to current year)
    - Finds TOP_N event names within that year using a lightweight aggregation
    - Then aggregates monthly counts only for those TOP_N events
    - Caches the response per-year for TTL seconds
    """
    q_year = _int_or_none(request.GET.get("year"))
    year = q_year if q_year is not None else timezone.now().year
    TOP_N = 5
    CACHE_TTL = 60 * 5  # 5 minutes (adjust)

    cache_key = f"monthly_event_trends:{year}:top{TOP_N}"
    cached = cache.get(cache_key)
    if cached is not None:
        return JsonResponse(cached, json_dumps_params={"indent": 2})

    # Use range filter on created to allow index on created to be used
    start = datetime(year, 1, 1)
    end = datetime(year + 1, 1, 1)

    base_qs = CveChange.objects.filter(created__gte=start, created__lt=end)

    # Quick path: if no rows for that year, return empty structure quickly
    if not base_qs.exists():
        resp = {
            "timestamp": timezone.now().isoformat(),
            "year": year,
            "available_years": [],  # could fill cheaply below
            "top_n": TOP_N,
            "events": [],
            "sample_plot_image": SAMPLE_PLOT_IMAGE_PATH,
        }
        cache.set(cache_key, resp, CACHE_TTL)
        return JsonResponse(resp, json_dumps_params={"indent": 2})

    # 1) find top N event names within the year (DB-side)
    top_events_qs = (
        base_qs
        .values("eventName")
        .annotate(total=Count("id"))
        .order_by("-total")
    )[:TOP_N]

    top_names = [r["eventName"] for r in top_events_qs]

    # 2) aggregate monthly counts only for those top event names
    annotated = (
        base_qs
        .filter(eventName__in=top_names)
        .annotate(event_month=ExtractMonth("created"))
        .values("eventName", "event_month")
        .annotate(cnt=Count("id"))
        .order_by("eventName", "event_month")
    )

    # Build a small in-memory map (only top N × 12 rows)
    event_month_map: Dict[str, Dict[int, int]] = {}
    for row in annotated:
        ev = row.get("eventName") or "unknown"
        month = row.get("event_month")
        cnt = int(row.get("cnt") or 0)
        if month is None:
            continue
        event_month_map.setdefault(ev, {})[int(month)] = cnt

    # Ensure ordering matches top_names order (keeps stable output)
    def monthly_list(ev_map: Dict[int, int]) -> List[int]:
        return [int(ev_map.get(m, 0)) for m in range(1, 13)]

    events_out: List[Dict[str, Any]] = []
    for ev in top_names:
        months_map = event_month_map.get(ev, {})
        monthly = monthly_list(months_map)
        total = sum(monthly)
        events_out.append({"eventName": ev, "monthly": monthly, "total": int(total)})

    # get available years (cheap aggregation on created years) - can be cached separately
    years_qs = (
        CveChange.objects
        .extra(select={'year': "EXTRACT(YEAR FROM created)"})  # uses DB EXTRACT, slightly faster
        .values_list("year", flat=True)
        .distinct()
        .order_by("year")
    )
    available_years = [int(y) for y in years_qs if y is not None]

    response = {
        "timestamp": timezone.now().isoformat(),
        "year": int(year),
        "available_years": available_years,
        "top_n": TOP_N,
        "events": events_out,
        "sample_plot_image": SAMPLE_PLOT_IMAGE_PATH,
    }

    cache.set(cache_key, response, CACHE_TTL)
    return JsonResponse(response, json_dumps_params={"indent": 2})
