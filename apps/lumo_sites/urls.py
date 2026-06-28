from django.urls import path
from . import views
from . import views_superadmin # একদম ওপরে এটি ইমপোর্ট করবেন

app_name = 'lumo_sites'

urlpatterns = [
    # 🟢 ফিক্স: <int:..> এর জায়গায় <uuid:..> বসানো হয়েছে
    path('dashboard/', views.builder_dashboard_view, name='builder_dashboard'),
    path('dashboard/publish/<uuid:revision_id>/', views.publish_action_view, name='publish_action'),
    
    # 🟢 সেকশন এডিটরের রাউটেও uuid বসাতে হবে
    path('editor/section/<uuid:section_id>/', views.edit_section_view, name='edit_section'),
    path('dashboard/theme/', views.theme_editor_view, name='theme_editor'),
    path('dashboard/forms/', views.form_submissions_view, name='form_submissions'),
    path('dashboard/pages/create/', views.page_create_view, name='page_create'),
    path('dashboard/pages/<uuid:page_id>/edit/', views.page_edit_view, name='page_edit'),
    path('dashboard/assets/', views.asset_library_view, name='asset_library'),
    path('dashboard/assets/<uuid:asset_id>/delete/', views.asset_delete_view, name='asset_delete'),
    path('dashboard/navigation/', views.navigation_manager_view, name='navigation_manager'),
    path('dashboard/navigation/item/<uuid:item_id>/delete/', views.navigation_item_delete, name='navigation_item_delete'),
    # সুপার-অ্যাডমিন (SiteKit Builder) রাউটসমূহ
    path('superadmin/sitekits/', views_superadmin.superadmin_sitekit_list, name='superadmin_sitekit_list'),
    path('superadmin/sitekits/create/', views_superadmin.superadmin_sitekit_create, name='superadmin_sitekit_create'),
    path('superadmin/sitekits/version/<uuid:version_id>/builder/', views_superadmin.superadmin_sitekit_builder, name='superadmin_sitekit_builder'),
    path('dashboard/store/', views.theme_store_view, name='theme_store'),
    path('dashboard/store/install/<uuid:version_id>/', views.install_theme_view, name='install_theme'),
    # UI Components (Atomic Sections)
    path('superadmin/sections/', views_superadmin.superadmin_section_list, name='superadmin_section_list'),
    path('superadmin/sections/create/', views_superadmin.superadmin_section_create, name='superadmin_section_create'),
    path('superadmin/sections/<uuid:section_id>/version/create/', views_superadmin.superadmin_section_version_create, name='superadmin_section_version_create'),
    # Preview Route (Builder এর জন্য)
    path('site/preview/<slug:slug>/', views.preview_page_view, name='preview_page'),
    
    # Public Live Routes (একদম শেষে রাখবেন)
    path('', views.public_page_view, name='public_home'),
    path('<slug:slug>/', views.public_page_view, name='public_page'),

    path('dashboard/domains/', views.domain_manager_view, name='domain_manager'),
    path('dashboard/domains/<uuid:domain_id>/delete/', views.domain_delete_view, name='domain_delete'),

    path('dashboard/forms/', views.form_submissions_view, name='form_submissions'),
    # 🟢 ফিক্স: Form Builder-এর রাউটটি যুক্ত করা হলো
    path('dashboard/forms/builder/', views.form_builder_view, name='form_builder'),

    path('editor/pages/<uuid:page_id>/publish/', views.publish_page_view, name='publish_page'),
    path('domains/<uuid:domain_id>/verify/', views.domain_verify_action_view, name='verify_domain'),
    path('dashboard/pages/<uuid:page_id>/edit/', views.page_edit_view, name='page_edit'),
    # 🟢 TASK D: Delete Route
    path('dashboard/pages/<uuid:page_id>/delete/', views.page_delete_view, name='page_delete'),
    # 🟢 SPRINT 3: Page Builder Routes
    path('dashboard/pages/<uuid:page_id>/builder/', views.page_builder_view, name='page_builder'),
    path('dashboard/revisions/<uuid:revision_id>/sections/add/<uuid:version_id>/', views.section_add_view, name='section_add'),
    # 🟢 SPRINT 4: Section Delete & Reorder Routes
    path('dashboard/sections/<uuid:section_id>/delete/', views.section_delete_view, name='section_delete'),
    path('dashboard/sections/<uuid:section_id>/reorder/<str:direction>/', views.section_reorder_view, name='section_reorder'),





]