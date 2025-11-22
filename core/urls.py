"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from . import views
from . import graphviews


urlpatterns = [
    path("api/cvechanges/", views.cvechange_list),
    path("api/cvechanges/<int:pk>/", views.cvechange_detail),
    path("api/cvechanges/create/", views.cvechange_create),
    path("api/cvechanges/update/<int:pk>/", views.cvechange_update),
    path("api/cvechanges/delete/<int:pk>/", views.cvechange_delete),
    path("api/cvechanges/paginated/", views.cvechange_paginated),
    path("api/cvechanges/search/", views.cvechange_search),
    path('api/cvechanges/filter/', views.cvechange_filter, name='cvechange_filter'),
    path("api/cvechanges/export/", views.cvechange_export, name="cvechange_export"),
    path("search/", views.search_page, name="search_page"),
    path("api/cvechanges/suggestions/",
         views.suggestions_api, name="cvechange_suggestions"),    path("api/event-options/", views.event_options_list, name="event_options_list"),
    path("api/event-options/create/", views.event_options_create,
         name="event_options_create"),
    path("api/event-counts/", graphviews.api_event_counts, name="api_event_counts"),


    path("api/cve-year-counts/", graphviews.api_cve_year_counts,
         name="api_cve_year_counts"),

    path("api/top-sources/", graphviews.api_top_sources, name="api_top_sources"),
    path("api/analysis-status/", graphviews.api_analysis_status,
         name="api_analysis_status"),
    # path("api/cve-scatter/", graphviews.api_cve_scatter, name="api_cve_scatter"),

# urls.py (add to urlpatterns)
path("api/monthly-event-trends/", graphviews.api_monthly_event_trends, name="api_monthly_event_trends"),

]


# add this line where you list graph endpoints
