# section_properties/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # 網址會是: domain/section/
    path('', views.index, name='section_index'),

    # 計算 API 網址會是: domain/section/api/calculate/
    path('api/calculate/', views.calculate_h_section, name='calculate_h'),
]