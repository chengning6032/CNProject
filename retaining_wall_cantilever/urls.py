# retaining_wall_cantilever/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('input/', views.input_view, name='input_view'),
    path('report/', views.report_view, name='report_view'),
]
