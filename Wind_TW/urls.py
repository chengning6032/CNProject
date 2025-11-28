from django.urls import path
from . import views  # 從當前目錄引入 views.py

urlpatterns = [
    # 當使用者訪問 /wind/ 時 (空字串 '' 代表根路徑)
    # 執行 views.py 中的 wind_calculation_view 函式
    path('close/', views.wind_calculation_close_view, name='wind_calculation_close'),
    path('open/', views.wind_calculation_open_view, name='wind_calculation_open'),
    path('calculate/', views.calculate_api_view, name='calculate_api'),
    path('calculate_open/', views.calculate_open_api_view, name='calculate_open_api'),
    # path('report/', views.wind_report_view, name='wind_report'),
    path('report_open/', views.wind_report_open_view, name='wind_report_open'),
    path('report_v2/', views.wind_report_v2_view, name='wind_report_v2'),
]
