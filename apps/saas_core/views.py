from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from apps.saas_core.middleware import TenantRoutingMiddleware
from apps.saas_core.forms.company_form import CompanyForm
from apps.saas_core.models.company import Company
from apps.saas_core.models.tenant import WorkspaceMember
from apps.saas_core.models.audit import AuditLog
from apps.saas_core.policies.company_policy import CompanyPolicy
from apps.saas_core.services.menu_service import MenuService
from apps.saas_core.services.workspace_service import WorkspaceService
from apps.saas_core.services.company_access_service import CompanyAccessService
from apps.saas_core.decorators import require_permission
from apps.saas_core.services.settings_service import SettingsService
from apps.saas_core.forms.company_form import WorkspacePreferenceForm
from apps.saas_core.models.settings import PaymentGatewayConfig, GlobalConfiguration
from apps.saas_core.forms.company_form import PaymentGatewayConfigForm

@login_required(login_url='/auth/login/')
def dashboard_home(request):
    """SaaS Dashboard Home with Constitution Enforcement."""
    workspace = WorkspaceService.get_current_workspace(request)
    
    if not workspace:
        return redirect('identity:register')

    # 🟢 SAAS CONSTITUTION ENFORCEMENT: Lock Dashboard
    global_config = GlobalConfiguration.get_config()
    if global_config.dashboard_requires_active_subscription:
        sub = getattr(workspace, 'subscription', None)
        # If no subscription or subscription is strictly invalid
        if not sub or not sub.is_valid:
            messages.warning(request, "🔒 Please select a plan to unlock your workspace dashboard.")
            return redirect('saas_core:subscription_plans')

    membership = WorkspaceMember.objects.filter(
        user=request.user, 
        workspace=workspace,
        is_deleted=False
    ).select_related('role').first()
    
    if not membership:
        return redirect('identity:register')

    sidebar_menu = MenuService.get_sidebar_for_user(
        user=request.user, 
        workspace_id=workspace.id
    )
    
    context = {
        'workspace': workspace,
        'role': membership.role,
        'user': request.user,
        'sidebar_menu': sidebar_menu,
        'subscription_status': workspace.subscription.status if hasattr(workspace, 'subscription') else 'None', 
    }
    return render(request, 'saas_core/dashboard.html', context)

@login_required(login_url='/auth/login/')
@require_permission('company.read')
def company_list(request):
    workspace = WorkspaceService.get_current_workspace(request)
    if not workspace:
        return redirect('identity:register')

    member = WorkspaceMember.objects.filter(workspace=workspace, user=request.user, is_deleted=False).first()
    companies = CompanyAccessService.get_accessible_companies(member).order_by('-is_default', '-created_at')
    
    try:
        subscription = workspace.subscription
    except:
        subscription = None

    context = {
        'companies': companies,
        'subscription': subscription
    }
    return render(request, 'saas_core/company/list.html', context)

@login_required(login_url='identity:login')
@require_permission('company.create')
def company_create(request):
    workspace = WorkspaceService.get_current_workspace(request)
    if not workspace:
        messages.error(request, "No active workspace found.")
        return redirect("identity:register")

    decision = CompanyPolicy.can_create(workspace)
    if not decision['allowed']:
        messages.error(request, decision['message'])
        return redirect(decision['redirect'])

    if request.method == 'POST':
        form = CompanyForm(request.POST, request.FILES)
        if form.is_valid():
            company = form.save(commit=False)
            company.workspace_id = workspace.id
            company.save()
            messages.success(request, f"Entity '{company.name}' created successfully.")
            return redirect('saas_core:company_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}")
            messages.error(request, "Please correct the errors below.")
    else:
        form = CompanyForm()

    context = {'form': form, 'workspace': workspace}
    return render(request, 'saas_core/company/create.html', context)

@login_required(login_url='identity:login')
@require_permission('company.update')
def company_update(request, company_id):
    workspace = WorkspaceService.get_current_workspace(request)
    if not workspace:
        return redirect("identity:register")

    company = get_object_or_404(Company, id=company_id, workspace_id=workspace.id, is_deleted=False)

    if request.method == 'POST':
        form = CompanyForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, f"Entity '{company.name}' updated successfully.")
            return redirect('saas_core:company_list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CompanyForm(instance=company)

    context = {'form': form, 'company': company, 'workspace': workspace}
    return render(request, 'saas_core/company/update.html', context)

@login_required(login_url='identity:login')
@require_permission('company.delete')
def company_delete(request, company_id):
    workspace = WorkspaceService.get_current_workspace(request)
    if not workspace:
        messages.error(request, "No active workspace found.")
        return redirect('saas_core:dashboard_home')

    company = get_object_or_404(Company, id=company_id, workspace_id=workspace.id, is_deleted=False)
    company.is_deleted = True
    company.save()
    
    messages.success(request, f"Entity '{company.name}' has been moved to trash.")
    return redirect('saas_core:company_list')

@login_required(login_url='identity:login')
def workspace_locked(request):
    return render(request, 'saas_core/locked.html')

@login_required(login_url='/auth/login/')
@require_permission('audit.read')
def audit_log_list(request):
    workspace = WorkspaceService.get_current_workspace(request)
    logs = AuditLog.objects.filter(workspace=workspace).select_related('actor').order_by('-created_at')[:500]
    return render(request, 'saas_core/audit/list.html', {'logs': logs})

@login_required(login_url='/auth/login/')
@require_permission('company.update') 
def workspace_preferences(request):
    workspace = WorkspaceService.get_current_workspace(request)
    if not workspace:
        return redirect('identity:register')

    prefs = SettingsService.get_workspace_preferences(workspace)
    if request.method == 'POST':
        form = WorkspacePreferenceForm(request.POST, instance=prefs)
        if form.is_valid():
            form.save()
            SettingsService.clear_workspace_cache(workspace)
            
            from apps.saas_core.services.audit_service import AuditService
            AuditService.log(
                request=request, workspace=workspace, action='preferences.updated',
                resource_type='WorkspacePreference', resource_id=str(prefs.id), status='SUCCESS'
            )
            messages.success(request, "Workspace preferences updated successfully!")
            return redirect('saas_core:workspace_preferences')
    else:
        form = WorkspacePreferenceForm(instance=prefs)

    return render(request, 'saas_core/settings/preferences.html', {
        'form': form,
        'workspace': workspace
    })

@login_required(login_url='/auth/login/')
def workspace_payment_settings(request):
    workspace = WorkspaceService.get_current_workspace(request)
    if not workspace:
        return redirect('identity:register')

    if request.method == 'POST':
        form = PaymentGatewayConfigForm(request.POST)
        if form.is_valid():
            config = form.save(commit=False)
            config.workspace = workspace
            
            if PaymentGatewayConfig.objects.filter(workspace=workspace, gateway=config.gateway).exists():
                messages.error(request, f"Configuration for {config.gateway.name} already exists. Please update it instead.")
            else:
                config.save()
                messages.success(request, f"{config.gateway.name} API Keys configured successfully!")
                return redirect('saas_core:workspace_payment_settings')
    else:
        form = PaymentGatewayConfigForm()

    configured_gateways = PaymentGatewayConfig.objects.filter(workspace=workspace).select_related('gateway')
    return render(request, 'saas_core/settings/payment_settings.html', {
        'form': form,
        'configured_gateways': configured_gateways,
        'workspace': workspace
    })

@login_required(login_url='/auth/login/')
def workspace_payment_update(request, config_id):
    workspace = WorkspaceService.get_current_workspace(request)
    config = get_object_or_404(PaymentGatewayConfig, id=config_id, workspace=workspace)

    if request.method == 'POST':
        form = PaymentGatewayConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, f"{config.gateway.name} API credentials updated successfully!")
            return redirect('saas_core:workspace_payment_settings')
    else:
        form = PaymentGatewayConfigForm(instance=config)

    return render(request, 'saas_core/settings/payment_settings_edit.html', {
        'form': form,
        'config': config,
        'workspace': workspace
    })

@login_required(login_url='/auth/login/')
def workspace_payment_delete(request, config_id):
    workspace = WorkspaceService.get_current_workspace(request)
    config = get_object_or_404(PaymentGatewayConfig, id=config_id, workspace=workspace)
    
    if request.method == 'POST':
        gateway_name = config.gateway.name
        config.delete()
        messages.success(request, f"{gateway_name} configuration has been removed.")
        
    return redirect('saas_core:workspace_payment_settings')