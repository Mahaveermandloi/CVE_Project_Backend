
import json
from datetime import datetime
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from .models import CveChange
from django.db.models import Count

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from .models import CveChange
import openpyxl


# ---------------------------------------------------------
# GLOBAL LIMIT
# ---------------------------------------------------------
MAX_LIMIT = 5000


def limit_results(queryset):
    """Returns only first MAX_LIMIT records"""
    return list(queryset[:MAX_LIMIT])


# ---------------------------------------------------------
# 1. LIST ALL RECORDS (LIMITED TO 5000)
# ---------------------------------------------------------
def cvechange_list(request):
    changes = CveChange.objects.all().order_by("id").values()
    limited = limit_results(changes)

    return JsonResponse({
        "count": len(limited),
        "data": limited
    })


# ---------------------------------------------------------
# 2. GET SINGLE RECORD
# ---------------------------------------------------------
def cvechange_detail(request, pk):
    change = get_object_or_404(CveChange, pk=pk)
    return JsonResponse({
        "id": change.id,
        "cveId": change.cveId,
        "eventName": change.eventName,
        "cveChangeId": change.cveChangeId,
        "sourceIdentifier": change.sourceIdentifier,
        "created": change.created,
        "details": change.details,
    })


# ---------------------------------------------------------
# 3. CREATE NEW RECORD
# ---------------------------------------------------------
@csrf_exempt
def cvechange_create(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=400)

    data = json.loads(request.body)

    change = CveChange.objects.create(
        cveId=data.get("cveId"),
        eventName=data.get("eventName"),
        cveChangeId=data.get("cveChangeId"),
        sourceIdentifier=data.get("sourceIdentifier"),
        created=data.get("created"),
        details=data.get("details", []),
    )

    return JsonResponse({"message": "Created successfully", "id": change.id})


# ---------------------------------------------------------
# 4. UPDATE RECORD
# ---------------------------------------------------------
@csrf_exempt
def cvechange_update(request, pk):
    if request.method != "PUT":
        return JsonResponse({"error": "PUT method required"}, status=400)

    data = json.loads(request.body)
    change = get_object_or_404(CveChange, pk=pk)

    change.cveId = data.get("cveId", change.cveId)
    change.eventName = data.get("eventName", change.eventName)
    change.cveChangeId = data.get("cveChangeId", change.cveChangeId)
    change.sourceIdentifier = data.get(
        "sourceIdentifier", change.sourceIdentifier)
    change.created = data.get("created", change.created)
    change.details = data.get("details", change.details)
    change.save()

    return JsonResponse({"message": "Updated successfully"})


# ---------------------------------------------------------
# 5. DELETE RECORD
# ---------------------------------------------------------
@csrf_exempt
def cvechange_delete(request, pk):
    if request.method != "DELETE":
        return JsonResponse({"error": "DELETE method required"}, status=400)

    change = get_object_or_404(CveChange, pk=pk)
    change.delete()

    return JsonResponse({"message": "Deleted successfully"})


# ---------------------------------------------------------
# 6. PAGINATED FETCH (FRONTEND CONTROLS LIMIT)
# ---------------------------------------------------------
def cvechange_paginated(request):
    results_per_page = int(request.GET.get("resultsPerPage", MAX_LIMIT))
    results_per_page = min(results_per_page, MAX_LIMIT)  # enforce limit

    start_index = int(request.GET.get("startIndex", 0))

    total = CveChange.objects.count()

    items = list(
        CveChange.objects.all()
        .order_by("id")
        .values()[start_index:start_index + results_per_page]
    )

    return JsonResponse({
        "resultsPerPage": results_per_page,
        "startIndex": start_index,
        "totalResults": total,
        "timestamp": datetime.utcnow().isoformat(),
        "data": items,
    })


# ---------------------------------------------------------
# 7. SEARCH RECORDS (LIMITED TO 5000)
# ---------------------------------------------------------
@csrf_exempt
def cvechange_search(request):
    print("Search API called", request.GET)

    query = request.GET.get("q") or request.GET.get("query") or ""
    query = query.strip()

    if not query:
        return JsonResponse({
            "resultsPerPage": MAX_LIMIT,
            "startIndex": 0,
            "totalResults": 0,
            "timestamp": datetime.utcnow().isoformat(),
            "data": []
        })

    # Pagination from query params
    results_per_page = int(request.GET.get("resultsPerPage", MAX_LIMIT))
    results_per_page = min(results_per_page, MAX_LIMIT)
    start_index = int(request.GET.get("startIndex", 0))

    queryset = CveChange.objects.filter(
        Q(cveId__icontains=query) |
        Q(cveChangeId__icontains=query) |
        Q(sourceIdentifier__icontains=query)
    ).order_by("id")

    total_found = queryset.count()

    sliced_results = queryset[start_index:start_index + results_per_page]

    results = [
        {
            "id": c.id,
            "cveId": c.cveId,
            "eventName": c.eventName,
            "cveChangeId": c.cveChangeId,
            "sourceIdentifier": c.sourceIdentifier,
            "created": c.created,
            "details": c.details,
        }
        for c in sliced_results
    ]

    return JsonResponse({
        "resultsPerPage": results_per_page,
        "startIndex": start_index,
        "totalResults": total_found,
        "timestamp": datetime.utcnow().isoformat(),
        "data": results
    })


# ---------------------------------------------------------
# 8. FILTER RECORDS (by eventName and date range)
# ---------------------------------------------------------
@csrf_exempt
def cvechange_filter(request):
    """
    Query params:
      - event  (can appear multiple times) e.g. ?event=CVE%20Modified&event=Reanalysis
      - startDate (YYYY-MM-DD)
      - endDate   (YYYY-MM-DD)
      - resultsPerPage (optional)
      - startIndex (optional)
    """

    print("Filter API called", request.GET)

    # pagination params
    results_per_page = int(request.GET.get("resultsPerPage", MAX_LIMIT))
    results_per_page = min(results_per_page, MAX_LIMIT)
    start_index = int(request.GET.get("startIndex", 0))

    # events (multi-select)
    events = request.GET.getlist("event")  # ?event=a&event=b
    # also support comma separated fallback
    if not events:
        events_raw = request.GET.get("events", "")
        if events_raw:
            events = [e.strip() for e in events_raw.split(",") if e.strip()]

    # date range (ISO date yyyy-mm-dd)
    start_date = request.GET.get("startDate")
    end_date = request.GET.get("endDate")

    queryset = CveChange.objects.all()

    # event filter
    if events:
        queryset = queryset.filter(eventName__in=events)

    # date filters - supports created as datetime field
    # If only start_date provided -> filter exact day and above
    # If both provided -> inclusive range
    try:
        if start_date:
            # created__date >= start_date
            queryset = queryset.filter(created__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created__date__lte=end_date)
    except Exception as e:
        print("Date filter parse error:", e)

    queryset = queryset.order_by("id")

    total_found = queryset.count()

    sliced = queryset[start_index:start_index + results_per_page]

    results = [
        {
            "id": c.id,
            "cveId": c.cveId,
            "eventName": c.eventName,
            "cveChangeId": c.cveChangeId,
            "sourceIdentifier": c.sourceIdentifier,
            "created": c.created,
            "details": c.details,
        }
        for c in sliced
    ]

    return JsonResponse({
        "resultsPerPage": results_per_page,
        "startIndex": start_index,
        "totalResults": total_found,
        "timestamp": datetime.utcnow().isoformat(),
        "data": results
    })


MAX_EXPORT_LIMIT = 5000  # Maximum records to export


# ---------------------------------------------------------
# 9. EXPORT FILTERED RECORDS TO EXCEL
# ---------------------------------------------------------


@csrf_exempt
def cvechange_export(request):
    """
    Export filtered CVE changes to Excel.
    Query params:
      - event (multiple allowed) e.g. ?event=CVE%20Modified&event=Reanalysis
      - startDate (YYYY-MM-DD)
      - endDate   (YYYY-MM-DD)
    """

    # events filter
    events = request.GET.getlist("event")
    if not events:
        events_raw = request.GET.get("events", "")
        if events_raw:
            events = [e.strip() for e in events_raw.split(",") if e.strip()]

    # date range filter
    start_date = request.GET.get("startDate")
    end_date = request.GET.get("endDate")

    queryset = CveChange.objects.all()

    # Apply event filter
    if events:
        queryset = queryset.filter(eventName__in=events)

    # Apply date filters
    try:
        if start_date:
            queryset = queryset.filter(created__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created__date__lte=end_date)
    except Exception as e:
        print("Date filter parse error:", e)

    queryset = queryset.order_by("id")  # NO LIMIT

    # Create Excel workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "CVE Changes"

    # Header row
    headers = ["ID", "CVE ID", "Event Name", "CVE Change ID",
               "Source Identifier", "Created", "Details"]
    ws.append(headers)

    # Data rows
    for c in queryset:
        ws.append([
            c.id,
            c.cveId,
            c.eventName,
            c.cveChangeId,
            c.sourceIdentifier,
            c.created.strftime("%Y-%m-%d %H:%M:%S"),
            json.dumps(c.details),
        ])

    # Prepare response
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    filename = f"CVE_Changes_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    wb.save(response)
    return response


#

# ---------------------------------------------------------
# 10. COUNT ALL EVENT OPTIONS
# ---------------------------------------------------------


EVENT_OPTIONS = [
    "CVE Received",
    "Initial Analysis",
    "Reanalysis",
    "CVE Modified",
    "Modified Analysis",
    "CVE Translated",
    "Vendor Comment",
    "CVE Source Update",
    "CPE Deprecation Remap",
    "CWE Remap",
    "Reference Tag Update",
    "CVE Rejected",
    "CVE Unrejected",
    "CVE CISA KEV Update",
]

def cvechange_event_counts(request):
    """
    Returns counts of CVE changes for each event in EVENT_OPTIONS.
    Useful for a frontend pie chart.
    """
    # Aggregate counts for each eventName in EVENT_OPTIONS
    queryset = CveChange.objects.filter(eventName__in=EVENT_OPTIONS)
    counts = queryset.values('eventName').annotate(count=Count('id'))

    # Convert to dict for easy frontend use
    # Make sure all EVENT_OPTIONS are present even if count is 0
    result = {event: 0 for event in EVENT_OPTIONS}
    for item in counts:
        result[item['eventName']] = item['count']

    return JsonResponse({
        "timestamp": datetime.utcnow().isoformat(),
        "data": result
    })