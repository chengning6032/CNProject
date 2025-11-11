# accounts/urls.py (新增檔案)

from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    # path('simulate-purchase/<str:module_id>/', views.simulate_purchase_view, name='simulate_purchase'),
    path('api/send-verification-code/', views.send_verification_code_api, name='send_verification_code_api'),
    path('forgot-username/', views.forgot_username_view, name='forgot_username'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
]
