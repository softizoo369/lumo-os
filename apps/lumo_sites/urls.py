from django.urls import path
from . import views

app_name = 'lumo_sites'

urlpatterns = [
    # ==========================================
    # 1. SPECIFIC ROUTES (Must come FIRST)
    # ==========================================
    # Dashboard & Management
    path('dashboard/', views.builder_dashboard_view, name='builder_dashboard'),
    path('dashboard/domains/', views.domain_manager_view, name='domain_manager'),
    path('dashboard/domains/<uuid:domain_id>/delete/', views.domain_delete_view, name='domain_delete'),
    path('dashboard/domains/<uuid:domain_id>/verify/', views.domain_verify_action_view, name='domain_verify_action'),
    
    path('dashboard/pages/create/', views.page_create_view, name='page_create'),
    path('dashboard/pages/<uuid:page_id>/edit/', views.page_edit_view, name='page_edit'),
    path('dashboard/pages/<uuid:page_id>/delete/', views.page_delete_view, name='page_delete'),
    path('dashboard/pages/<uuid:page_id>/builder/', views.page_builder_view, name='page_builder'),
    
    path('dashboard/navigation/', views.navigation_manager_view, name='navigation_manager'),
    path('dashboard/navigation/items/<uuid:item_id>/delete/', views.navigation_item_delete, name='navigation_item_delete'),
    
    path('dashboard/theme/', views.theme_editor_view, name='theme_editor'),
    path('dashboard/theme-store/', views.theme_store_view, name='theme_store'),
    path('dashboard/theme-store/install/<uuid:version_id>/', views.install_theme_view, name='install_theme'),
    
    path('dashboard/assets/', views.asset_library_view, name='asset_library'),
    path('dashboard/assets/<uuid:asset_id>/delete/', views.asset_delete_view, name='asset_delete'),
    
    path('dashboard/forms/builder/', views.form_builder_view, name='form_builder'),
    path('dashboard/forms/submissions/', views.form_submissions_view, name='form_submissions'),

    # Editor Actions (API-like)
    path('editor/sections/<uuid:section_id>/edit/', views.edit_section_view, name='edit_section'),
    path('editor/sections/add/<uuid:revision_id>/<uuid:version_id>/', views.section_add_view, name='section_add'),
    path('editor/sections/<uuid:section_id>/delete/', views.section_delete_view, name='section_delete'),
    path('editor/sections/<uuid:section_id>/reorder/<str:direction>/', views.section_reorder_view, name='section_reorder'),
    path('editor/revisions/<uuid:revision_id>/publish/', views.publish_action_view, name='publish_action'),
    
    # Preview (Internal to Builder)
    path('preview/<slug:slug>/', views.preview_page_view, name='preview_page'),

    # ==========================================
    # 2. CATCH-ALL ROUTES (Must come LAST)
    # ==========================================
    # Public Pages (The Live Website)
    path('', views.public_page_view, name='public_home'),
    path('<slug:slug>/', views.public_page_view, name='public_page'),
]