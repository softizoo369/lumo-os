from django.contrib import admin
from django.urls import path, include, re_path
from apps.lumo_sites.views import public_page_view

urlpatterns = [
    # ১. Superadmin Route
    path('admin/', admin.site.urls),

    # ২. Identity & Auth (login, register, logout ইত্যাদি)
    # এটি অবশ্যই ক্যাচ-অলের উপরে থাকতে হবে!
    path('', include('apps.identity.urls')), 
    
    # ৩. SaaS Core Dashboard (যদি থাকে)
    path('', include('apps.saas_core.urls')), 
    
    # ৪. Builder URLs
    path('site/', include('apps.lumo_sites.urls')), 
]

# ৫. CATCH-ALL ROUTE (The Tenant Sites)
# এটি সবার শেষে থাকবে, যাতে উপরের কোনোটির সাথে ম্যাচ না করলে তবেই এটি কাজ করে।
urlpatterns += [
    path('', public_page_view, name='public_home'),
    re_path(r'^(?P<slug>[-\w]+)/$', public_page_view, name='public_page'),
]