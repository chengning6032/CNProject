# products/urls.py (新增檔案)
from django.urls import path
from . import views

urlpatterns = [
    path('', views.product_list_view, name='list'), # 將 name 改為 'list' 更符合慣例
    path('simulate-checkout/', views.simulate_checkout_view, name='simulate_checkout'),
]