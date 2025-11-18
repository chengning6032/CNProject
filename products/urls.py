# products/urls.py
from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('', views.product_list_view, name='list'), # 將 name 改為 'list' 更符合慣例
    path('simulate-checkout/', views.simulate_checkout_view, name='simulate_checkout'),

    # 【核心新增】三個處理金流的 URL
    # 1. 前端點擊結帳後，請求這個 URL 來建立訂單
    path('ecpay-checkout/', views.ecpay_checkout_view, name='ecpay_checkout'),
    # 2. 使用者在綠界付款成功後，瀏覽器會被導回這個 URL (給使用者看的)
    path('ecpay-return/', views.ecpay_return_view, name='ecpay_return'),
    # 3. 綠界伺服器在背景發送付款成功通知到這個 URL (給系統處理的)
    path('ecpay-notify/', views.ecpay_notify_view, name='ecpay_notify'),
]