from django.contrib import admin
from django.urls import path, include
from main import views

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', views.CZ_homepage, name='CZ_homepage'),
    path('about/', views.CZ_about, name='CZ_about'),
    path('services/', views.CZ_services, name='CZ_services'),
    path('contact/', views.CZ_contact, name='CZ_contact'),  # 新增這一行
    path('contact/success/', views.CZ_contact_success, name='CZ_contact_success'),  # 【核心】新增這一行

    path('OLi/', views.homepage, name='homepage'),
    path('OLi/steel/', include('SteelDesign.urls')),

    path('OLi/eqTW/', include(('EqStaticAnalysis_TW.urls', 'EqStaticAnalysis_TW'), namespace='EqStaticAnalysis_TW')),
    path('OLi/windTW/', include('Wind_TW.urls')),
    path('OLi/section/', include('section_properties.urls')),
    path('OLi/retaining-wall/', include(('retaining_wall_cantilever.urls', 'retaining_wall_cantilever'),
                                        namespace='retaining_wall_cantilever')),
    path('OLi/accounts/', include('accounts.urls')),
    path('OLi/products/', include(('products.urls', 'products'), namespace='products')),

]
