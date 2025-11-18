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
    path('api/cvechanges/event-counts/', views.cvechange_event_counts),
    

]
