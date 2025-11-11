from django.urls import path
from . import views

app_name = 'EqStaticAnalysis_TW'

urlpatterns = [
    path('', views.calculator_view, name='EQ_calculator'),
    path('report/', views.report_view, name='report'),
    path('api/get_townships/<str:county>/', views.get_townships, name='get_townships'),
    path('api/get_villages/<str:county>/<str:township>/', views.get_villages, name='get_villages'),
    path('api/check_faults/<str:county>/<str:township>/', views.check_faults, name='check_faults'),
]
