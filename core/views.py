import json
import openpyxl
from datetime import datetime, timedelta

from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Count
from django.utils import timezone

from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils.timezone import now

from .models import CveChange

# ---------------------------------------------------------
# GLOBAL LIMIT
# ---------------------------------------------------------
MAX_LIMIT = 500


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
# def cvechange_paginated(request):
#     results_per_page = int(request.GET.get("resultsPerPage", MAX_LIMIT))
#     results_per_page = min(results_per_page, MAX_LIMIT)  # enforce limit

#     start_index = int(request.GET.get("startIndex", 0))

#     total = CveChange.objects.count()

#     items = list(
#         CveChange.objects.all()
#         .order_by("id")
#         .values()[start_index:start_index + results_per_page]
#     )

#     return JsonResponse({
#         "resultsPerPage": results_per_page,
#         "startIndex": start_index,
#         "totalResults": total,
#         "timestamp": datetime.utcnow().isoformat(),
#         "data": items,
#     })


def cvechange_paginated(request):
    results_per_page = int(request.GET.get("resultsPerPage", MAX_LIMIT))
    results_per_page = min(results_per_page, MAX_LIMIT)
    start_index = int(request.GET.get("startIndex", 0))

    page_number = (start_index // results_per_page) + 1

    # Only fetch required fields + avoid heavy ORM objects
    queryset = CveChange.objects.only(
        "id", "cveId", "eventName", "cveChangeId", 
        "sourceIdentifier", "created", "details"
    ).order_by("id")

    paginator = Paginator(queryset, results_per_page)

    page = paginator.get_page(page_number)

    return JsonResponse({
        "resultsPerPage": results_per_page,
        "startIndex": start_index,
        "totalResults": paginator.count,
        "timestamp": now().isoformat(),
        "data": list(page.object_list.values()),
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



# views.py (or search_views.py)
from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.utils.timezone import now

from .models import CveChange

MAX_SUGGESTIONS = 10
MAX_RESULTS_PAGE = 500  # max per page for rendered page (you can change)

def search_page(request):
    """
    Rendered search page at /search?q=...
    Accepts:
      - q: query string (required)
      - page: page number (optional, default 1)
      - per_page: items per page (optional)
    """
    q = (request.GET.get("q") or "").strip()
    page = int(request.GET.get("page", 1))
    per_page = int(request.GET.get("per_page", 50))
    per_page = min(per_page, MAX_RESULTS_PAGE)

    if not q:
        # Render an empty search page (or message)
        return render(request, "search_results.html", {
            "query": q,
            "results": [],
            "total": 0,
            "page": page,
            "per_page": per_page,
            "timestamp": now(),
        })

    # Reuse same search logic as cvechange_search: allow matches across
    queryset = CveChange.objects.filter(
        Q(cveId__icontains=q) |
        Q(cveChangeId__icontains=q) |
        Q(sourceIdentifier__icontains=q) |
        Q(eventName__icontains=q)
    ).order_by("id")

    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(page)

    # keep the context lightweight for template
    results = list(page_obj.object_list.values(
        "id", "cveId", "eventName", "cveChangeId", "sourceIdentifier", "created"
    ))

    context = {
        "query": q,
        "results": results,
        "total": paginator.count,
        "page": page_obj.number,
        "num_pages": paginator.num_pages,
        "per_page": per_page,
        "has_previous": page_obj.has_previous(),
        "has_next": page_obj.has_next(),
        "timestamp": now(),
    }
    return render(request, "search_results.html", context)


def suggestions_api(request):
  
    q = (request.GET.get("q") or "").strip()

    if len(q) <= 3:
        return JsonResponse({"data": [], "total": 0})

    # prefer startswith-like matches for snappy autosuggest
    # check several fields; try to return unique human-friendly display strings
    qs_cveid = CveChange.objects.filter(cveId__istartswith=q).values(
        "id", "cveId", "eventName", "sourceIdentifier"
    )[:MAX_SUGGESTIONS]

    # if not enough, try eventName startswith
    results = list(qs_cveid)
    if len(results) < MAX_SUGGESTIONS:
        needed = MAX_SUGGESTIONS - len(results)
        qs_event = CveChange.objects.filter(eventName__istartswith=q).exclude(
            id__in=[r["id"] for r in results]
        ).values("id", "cveId", "eventName", "sourceIdentifier")[:needed]
        results.extend(list(qs_event))

    if len(results) < MAX_SUGGESTIONS:
        needed = MAX_SUGGESTIONS - len(results)
        qs_source = CveChange.objects.filter(sourceIdentifier__istartswith=q).exclude(
            id__in=[r["id"] for r in results]
        ).values("id", "cveId", "eventName", "sourceIdentifier")[:needed]
        results.extend(list(qs_source))

    # Compose suggestion payload: text, subtitle, id, and a field to indicate which to use for search
    suggestions = []
    seen_texts = set()
    for r in results:
        primary = r.get("cveId") or r.get("eventName") or r.get("sourceIdentifier") or ""
        secondary = r.get("eventName") if r.get("cveId") else r.get("sourceIdentifier", "")
        text = str(primary).strip()
        if not text or text in seen_texts:
            continue
        seen_texts.add(text)
        suggestions.append({
            "id": r["id"],
            "text": text,
            "subtitle": secondary or "",
            # for frontend convenience
            "cveId": r.get("cveId"),
            "eventName": r.get("eventName"),
            "sourceIdentifier": r.get("sourceIdentifier"),
        })
        if len(suggestions) >= MAX_SUGGESTIONS:
            break

    return JsonResponse({
        "data": suggestions,
        "total": len(suggestions),
        "timestamp": now().isoformat()
    })






import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import now

from .models import CveOption


def event_options_list(request):
   
    q = (request.GET.get("q") or "").strip()

    qs = CveOption.objects.all().order_by("id")

    if q:
        qs = qs.filter(eventName__icontains=q)

    # return ALL items (no limit)
    items = list(qs.values("id", "eventName"))

    return JsonResponse({
        "timestamp": now().isoformat(),
        "total": qs.count(),
        "data": items,
    })


@csrf_exempt
def event_options_create(request):
    """
    POST /api/event-options/create/
    Body: JSON {"eventName": "..."}
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)

    try:
        payload = json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    eventName = (payload.get("eventName") or "").strip()

    if not eventName:
        return JsonResponse({"error": "eventName is required"}, status=400)

    # Prevent duplicates
    if CveOption.objects.filter(eventName__iexact=eventName).exists():
        return JsonResponse({"error": "eventName already exists"}, status=409)

    opt = CveOption.objects.create(eventName=eventName)

    return JsonResponse({
        "message": "Created successfully",
        "id": opt.id,
        "eventName": opt.eventName,
    }, status=201)
