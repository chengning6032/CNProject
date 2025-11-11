# products/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('BPandAnchor/', views.bpandanchor, name='bp_anchor_calculate_input'),
    path('BPandAnchor/calculate/', views.bp_anchor_calculate_api, name='bp_anchor_calculate_api'),
    path('BPandAnchor/report/', views.generate_report_view, name='bp_anchor_report'),
]
