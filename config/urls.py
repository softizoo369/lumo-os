from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # 🟢 ফিক্স ১: আপনার আগে থেকে বানানো কাস্টম Identity অ্যাপটি সবার আগে লোড হবে।
    # এর ফলে /login/ এবং /register/ রাউটগুলো সরাসরি apps/identity/urls.py থেকে কাজ করবে।
    path('', include('apps.identity.urls')),

    # 🟢 ফিক্স ২: এরপর SaaS Core-এর রাউটগুলো কাজ করবে।
    path('', include('apps.saas_core.urls')),

    # 🟢 ফিক্স ৩: ওয়েবসাইটের রাউট (যেখানে ডাইনামিক slug আছে) সবার নিচে থাকবে।
    path('site/', include('apps.lumo_sites.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)