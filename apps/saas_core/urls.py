from django.urls import path
from . import views, views_superadmin, views_team, views_role, views_billing, views_invitation, views_webhook

app_name = 'saas_core'

urlpatterns = [
    # Dashboard & General
    path('dashboard/', views.dashboard_home, name='dashboard_home'),
    path('locked/', views.workspace_locked, name='workspace_locked'),
    
    # Company Routes
    path('companies/', views.company_list, name='company_list'),
    path('companies/create/', views.company_create, name='company_create'),
    path('companies/<uuid:company_id>/edit/', views.company_update, name='company_update'),
    path('companies/<uuid:company_id>/delete/', views.company_delete, name='company_delete'),

    # Team Management
    path('settings/team/', views_team.team_list, name='team_list'),
    path('settings/team/invite/', views_team.team_invite, name='team_invite'),
    path('settings/team/add-manual/', views_team.team_add_manual, name='team_add_manual'),
    path('settings/team/<uuid:member_id>/remove/', views_team.team_remove, name='team_remove'),
    path('settings/team/<uuid:member_id>/edit/', views_team.team_update, name='team_update'),
    
    # Public Onboarding Route
    path('invite/accept/<str:token>/', views_invitation.accept_invite, name='accept_invite'),

    # Roles & Permissions
    path('settings/roles/', views_role.role_list, name='role_list'),
    path('settings/roles/create/', views_role.role_create, name='role_create'),
    path('settings/roles/<uuid:role_id>/edit/', views_role.role_update, name='role_update'),
    path('settings/roles/<uuid:role_id>/delete/', views_role.role_delete, name='role_delete'),
    
    # Audit Logs (Tenant)
    path('settings/audit-logs/', views.audit_log_list, name='audit_log_list'),

    # ==========================================
    # TENANT BILLING ROUTES
    # ==========================================
    path('settings/billing/', views_billing.billing_dashboard, name='billing_dashboard'),
    path('upgrade/', views_billing.subscription_plans, name='subscription_plans'), # 🟢 Correct Upgrade Route
    path('checkout/<uuid:price_id>/', views_billing.checkout_summary, name='checkout_summary'),
    path('order/<uuid:order_id>/pay/', views_billing.pay_order, name='pay_order'),
    path('order/<uuid:order_id>/pay/auto/<str:gateway_code>/', views_billing.process_automated_payment, name='process_automated_payment'),
    path('invoice/<uuid:invoice_id>/download/', views_billing.download_invoice_pdf, name='download_invoice_pdf'),
    path('settings/billing/profile/', views_billing.billing_profile_settings, name='billing_profile_settings'),
    
    # Webhook
    path('webhook/stripe/', views_webhook.stripe_webhook_receiver, name='stripe_webhook_receiver'),

    # ==========================================
    # SUPERADMIN ROUTES
    # ==========================================
    path('superadmin/plans/', views_superadmin.superadmin_plan_list, name='superadmin_plan_list'),
    path('superadmin/plans/create/', views_superadmin.superadmin_plan_create, name='superadmin_plan_create'),
    path('superadmin/plans/<uuid:plan_id>/edit/', views_superadmin.superadmin_plan_update, name='superadmin_plan_update'),
    
    path('superadmin/payments/', views_superadmin.superadmin_payment_list, name='superadmin_payment_list'),
    path('superadmin/payments/<uuid:transaction_id>/action/', views_superadmin.superadmin_payment_action, name='superadmin_payment_action'),
    
    path('superadmin/global-audit/', views_superadmin.superadmin_global_audit, name='superadmin_global_audit'),
    path('superadmin/module-registry/', views_superadmin.superadmin_module_registry, name='superadmin_module_registry'),
    
    path('superadmin/finance/', views_superadmin.superadmin_finance_center, name='superadmin_finance_center'),
    path('superadmin/finance/taxes/', views_superadmin.tax_rate_list, name='tax_rate_list'),
    path('superadmin/finance/taxes/create/', views_superadmin.tax_rate_create, name='tax_rate_create'),
    path('superadmin/finance/taxes/<uuid:tax_id>/edit/', views_superadmin.tax_rate_update, name='tax_rate_update'),
    path('superadmin/finance/taxes/<uuid:tax_id>/toggle/', views_superadmin.tax_rate_toggle, name='tax_rate_toggle'),
    
    path('superadmin/finance/gateways/', views_superadmin.payment_gateway_list, name='payment_gateway_list'),
    path('superadmin/finance/gateways/create/', views_superadmin.payment_gateway_create, name='payment_gateway_create'),
    path('superadmin/finance/gateways/<uuid:gateway_id>/edit/', views_superadmin.payment_gateway_update, name='payment_gateway_update'),
    path('superadmin/finance/gateways/<uuid:gateway_id>/toggle/', views_superadmin.payment_gateway_toggle, name='payment_gateway_toggle'),
    
    path('superadmin/finance/accounts/', views_superadmin.payment_account_list, name='payment_account_list'),
    path('superadmin/finance/accounts/create/', views_superadmin.payment_account_create, name='payment_account_create'),
    path('superadmin/finance/accounts/<uuid:account_id>/edit/', views_superadmin.payment_account_update, name='payment_account_update'),
    path('superadmin/finance/accounts/<uuid:account_id>/toggle/', views_superadmin.payment_account_toggle, name='payment_account_toggle'),
    
    path('superadmin/workspaces/', views_superadmin.superadmin_workspace_list, name='superadmin_workspace_list'),
    path('superadmin/workspaces/<uuid:workspace_id>/toggle/', views_superadmin.superadmin_workspace_toggle, name='superadmin_workspace_toggle'),
    path('superadmin/workspaces/<uuid:workspace_id>/edit/', views_superadmin.superadmin_workspace_update, name='superadmin_workspace_update'),
    path('superadmin/workspaces/<uuid:workspace_id>/delete/', views_superadmin.superadmin_workspace_delete, name='superadmin_workspace_delete'),
    
    path('superadmin/settings/', views_superadmin.superadmin_global_settings, name='superadmin_global_settings'),
    path('settings/preferences/', views.workspace_preferences, name='workspace_preferences'),
    path('settings/payments/', views.workspace_payment_settings, name='workspace_payment_settings'),
    path('settings/payments/<uuid:config_id>/edit/', views.workspace_payment_update, name='workspace_payment_update'),
    path('settings/payments/<uuid:config_id>/delete/', views.workspace_payment_delete, name='workspace_payment_delete'),

    path('superadmin/workspaces/<uuid:workspace_id>/provision/', views_superadmin.superadmin_workspace_provision, name='superadmin_workspace_provision'),
]