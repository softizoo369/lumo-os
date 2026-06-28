from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test, login_required
from django.utils import timezone
from datetime import timedelta
# Models
from apps.saas_core.models.subscription import SubscriptionPlan, PlanPrice, WorkspaceSubscription
from apps.saas_core.models.tenant import Workspace, WorkspaceStatus
from apps.saas_core.models.audit import AuditLog
from apps.saas_core.models.finance import PaymentTransaction, TransactionStatus
from apps.identity.models import Feature
from apps.core_masterdata.models import Currency
from apps.saas_core.models.finance import TaxRate, PaymentGateway, PaymentAccount
from apps.saas_core.forms.superadmin_forms import TaxRateForm, PaymentGatewayForm, PaymentAccountForm
from apps.saas_core.services.audit_service import AuditService
# Forms & Services
from apps.saas_core.forms.superadmin_forms import SubscriptionPlanForm, PlanPriceForm
from apps.saas_core.services.usage_service import UsageService
from apps.saas_core.services.payment_service import PaymentVerificationService
from apps.saas_core.models.settings import GlobalConfiguration
from apps.saas_core.services.settings_service import SettingsService
from apps.saas_core.forms.superadmin_forms import GlobalConfigForm
from apps.saas_core.models.subscription import SubscriptionPlan, WorkspaceSubscription, SubscriptionStatus
from apps.saas_core.services.audit_service import AuditService
from apps.saas_core.models.feature import Feature, PlanFeature




# Security check for Superadmin
def is_superadmin(user):
    return user.is_superuser

# ==========================================
# SUPERADMIN: PLAN & PRICING MANAGEMENT
# ==========================================

@user_passes_test(is_superadmin, login_url='/auth/login/')
def superadmin_plan_list(request):
    """Displays all SaaS plans and their pricing"""
    plans = SubscriptionPlan.objects.prefetch_related('prices__currency').all()
    return render(request, 'saas_core/superadmin/plan_list.html', {'plans': plans})

from apps.saas_core.services.subscription_service import SubscriptionService

@user_passes_test(is_superadmin, login_url='/auth/login/')
def superadmin_plan_create(request):
    """Creates a base Subscription Plan and maps selected modules."""
    if request.method == 'POST':
        form = SubscriptionPlanForm(request.POST)
        if form.is_valid():
            plan_data = {k: v for k, v in form.cleaned_data.items() if k not in ['currency', 'monthly_price', 'yearly_price', 'features']}
            pricing_data = {
                'currency': form.cleaned_data.get('currency'),
                'monthly_price': form.cleaned_data.get('monthly_price'),
                'yearly_price': form.cleaned_data.get('yearly_price')
            }
            
            plan = SubscriptionService.create_plan_with_prices(plan_data, pricing_data)
            
            # 🟢 SYNC FEATURES: Link unlocked modules to this plan
            features = form.cleaned_data.get('features')
            if features:
                for feature in features:
                    PlanFeature.objects.create(plan=plan, feature=feature, is_enabled=True)
            
            messages.success(request, f"Plan '{plan.name}' created successfully!")
            return redirect('saas_core:superadmin_plan_list')
    else:
        form = SubscriptionPlanForm()
    return render(request, 'saas_core/superadmin/plan_form.html', {'form': form, 'title': 'Create New SaaS Plan'})

@user_passes_test(is_superadmin, login_url='/auth/login/')
def superadmin_plan_update(request, plan_id):
    """Updates a plan, pricing, and active module mappings."""
    plan = get_object_or_404(SubscriptionPlan, id=plan_id)
    
    monthly_obj = plan.prices.filter(billing_cycle='MONTHLY', is_archived=False, is_active=True).first()
    yearly_obj = plan.prices.filter(billing_cycle='YEARLY', is_archived=False, is_active=True).first()
    
    initial_data = {}
    if monthly_obj:
        initial_data['currency'] = monthly_obj.currency
        initial_data['monthly_price'] = monthly_obj.amount
    if yearly_obj:
        initial_data['yearly_price'] = yearly_obj.amount
        
    # 🟢 PRE-LOAD FEATURES: Get previously selected modules for this plan
    initial_data['features'] = Feature.objects.filter(planfeature__plan=plan, planfeature__is_enabled=True)

    if request.method == 'POST':
        form = SubscriptionPlanForm(request.POST, instance=plan)
        if form.is_valid():
            plan_data = {k: v for k, v in form.cleaned_data.items() if k not in ['currency', 'monthly_price', 'yearly_price', 'features']}
            pricing_data = {
                'currency': form.cleaned_data.get('currency'),
                'monthly_price': form.cleaned_data.get('monthly_price'),
                'yearly_price': form.cleaned_data.get('yearly_price')
            }
            
            SubscriptionService.update_plan_with_prices(plan, plan_data, pricing_data)
            
            # 🟢 HARD SYNC FEATURES: Remove old mappings and apply new ones
            PlanFeature.objects.filter(plan=plan).delete()
            features = form.cleaned_data.get('features')
            if features:
                for feature in features:
                    PlanFeature.objects.create(plan=plan, feature=feature, is_enabled=True)
            
            messages.success(request, f"Plan '{plan.name}' updated successfully!")
            return redirect('saas_core:superadmin_plan_list')
    else:
        form = SubscriptionPlanForm(instance=plan, initial=initial_data)
        
    return render(request, 'saas_core/superadmin/plan_form.html', {'form': form, 'title': 'Edit SaaS Plan', 'is_edit': True})

@user_passes_test(is_superadmin, login_url='/auth/login/')
def superadmin_price_add(request, plan_id):
    """Attaches a Price (Currency + Amount) to an existing Plan"""
    plan = get_object_or_404(SubscriptionPlan, id=plan_id)
    if request.method == 'POST':
        form = PlanPriceForm(request.POST)
        if form.is_valid():
            price = form.save(commit=False)
            price.plan = plan
            price.save()
            messages.success(request, f"Pricing added to {plan.name}!")
            return redirect('saas_core:superadmin_plan_list')
    else:
        form = PlanPriceForm()
        
    return render(request, 'saas_core/superadmin/price_form.html', {'form': form, 'plan': plan})

# ==========================================
# SUPERADMIN: WORKSPACE (TENANT) MANAGEMENT
# ==========================================

@user_passes_test(is_superadmin, login_url='/auth/login/')
def workspace_list(request):
    """List all registered workspaces/tenants with their current subscription plan."""
    workspaces = Workspace.objects.all().order_by('-created_at')
    
    workspace_data = []
    for ws in workspaces:
        try:
            active_sub = ws.subscription
        except:
            active_sub = None
            
        usage = UsageService.get_current_usage(ws)
        
        workspace_data.append({
            'workspace': ws,
            'plan': active_sub.plan if active_sub else None,
            'usage': usage,
        })
        
    return render(request, 'saas_core/superadmin/workspace_list.html', {'workspace_data': workspace_data})

@user_passes_test(is_superadmin, login_url='/auth/login/')
def workspace_toggle_status(request, workspace_id):
    """Toggle Workspace status between ACTIVE and SUSPENDED."""
    if request.method == 'POST':
        workspace = get_object_or_404(Workspace, id=workspace_id)
        action = request.POST.get('action')
        
        if action == 'suspend':
            workspace.status = WorkspaceStatus.SUSPENDED
            messages.warning(request, f"Workspace '{workspace.name}' has been SUSPENDED.")
        elif action == 'activate':
            workspace.status = WorkspaceStatus.ACTIVE
            messages.success(request, f"Workspace '{workspace.name}' is now ACTIVE.")
            
        workspace.save()
        
    return redirect('saas_core:superadmin_workspace_list')

# ==========================================
# SUPERADMIN: PAYMENT OPERATIONS CENTER
# ==========================================

@user_passes_test(is_superadmin, login_url='/auth/login/')
def superadmin_payment_list(request):
    """Enterprise Payment Operations Center."""
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = now - timedelta(hours=24)
    forty_eight_hours_ago = now - timedelta(hours=48)

    # 🟢 FIX: Removed 'workspace__owner' from select_related
    payments = PaymentTransaction.objects.select_related(
        'workspace', 'order', 'receiving_account__gateway', 'verified_by', 'rejected_by'
    ).order_by('-created_at')[:1000]

    pending_qs = [p for p in payments if p.status == TransactionStatus.PENDING]
    
    kpi_data = {
        'pending_total': len(pending_qs),
        'sla_24h': len([p for p in pending_qs if p.created_at < yesterday and p.created_at >= forty_eight_hours_ago]),
        'sla_48h': len([p for p in pending_qs if p.created_at < forty_eight_hours_ago]),
        'today_approved': len([p for p in payments if p.status == TransactionStatus.VERIFIED and p.verified_at and p.verified_at >= today_start]),
        'today_rejected': len([p for p in payments if p.status == TransactionStatus.FAILED and p.rejected_at and p.rejected_at >= today_start]),
    }

    return render(request, 'saas_core/superadmin/payment_list.html', {
        'payments': payments,
        'kpi': kpi_data,
        'title': 'Payment Operations Center'
    })

@user_passes_test(is_superadmin, login_url='/auth/login/')
def superadmin_payment_action(request, transaction_id):
    """Approves or rejects a payment."""
    if request.method == 'POST':
        action = request.POST.get('action')
        reason = request.POST.get('reason', '')
        
        try:
            if action == 'approve':
                PaymentVerificationService.approve_payment(transaction_id, request.user)
                messages.success(request, "Payment verified! Invoice generated and subscription activated.")
            elif action == 'reject':
                PaymentVerificationService.reject_payment(transaction_id, request.user, reason)
                messages.warning(request, "Payment rejected and order cancelled.")
        except Exception as e:
            messages.error(request, f"Error processing payment: {str(e)}")
            
    return redirect('saas_core:superadmin_payment_list')

# ==========================================
# SUPERADMIN: AUDIT & MODULES
# ==========================================

@user_passes_test(is_superadmin, login_url='/auth/login/')
def superadmin_global_audit(request):
    """Superadmin view to see ALL audit logs."""
    logs = AuditLog.objects.select_related('workspace', 'actor').order_by('-created_at')[:1000]
    return render(request, 'saas_core/superadmin/global_audit.html', {'logs': logs})

@user_passes_test(is_superadmin, login_url='/auth/login/')
def superadmin_module_registry(request):
    """Superadmin App Store / Module Registry Control Panel."""
    features = Feature.objects.prefetch_related('permissions').all().order_by('code')
    return render(request, 'saas_core/superadmin/module_registry.html', {'features': features})


# ==========================================
# SUPERADMIN: FINANCE CENTER (SEPARATED CRUD)
# ==========================================

# 🟢 THE FIX: Smart Redirect for the main Finance Center URL
@user_passes_test(is_superadmin, login_url='/auth/login/')
def superadmin_finance_center(request):
    """Redirects the legacy main route to the first tab (Tax Rates)."""
    return redirect('saas_core:tax_rate_list')

# --- TAX RATE CRUD ---
@user_passes_test(is_superadmin, login_url='/auth/login/')
def tax_rate_list(request):
    taxes = TaxRate.objects.select_related('country').all().order_by('-is_active', '-created_at')
    return render(request, 'saas_core/superadmin/finance/tax_list.html', {'taxes': taxes})

# ... (বাকি কোড যেমন আছে তেমনই থাকবে) ...

@user_passes_test(is_superadmin, login_url='/auth/login/')
def tax_rate_create(request):
    if request.method == 'POST':
        form = TaxRateForm(request.POST)
        if form.is_valid():
            tax = form.save()
            AuditService.log(request=request, workspace=None, action='tax_rate.created', resource_type='TaxRate', resource_id=str(tax.id), status='SUCCESS')
            messages.success(request, "Tax Rate configured successfully.")
            return redirect('saas_core:tax_rate_list')
    else:
        form = TaxRateForm()
    return render(request, 'saas_core/superadmin/finance/generic_form.html', {'form': form, 'title': 'Configure Tax Rate', 'back_url': 'saas_core:tax_rate_list'})

@user_passes_test(is_superadmin, login_url='/auth/login/')
def tax_rate_update(request, tax_id):
    tax = get_object_or_404(TaxRate, id=tax_id)
    if request.method == 'POST':
        form = TaxRateForm(request.POST, instance=tax)
        if form.is_valid():
            form.save()
            AuditService.log(request=request, workspace=None, action='tax_rate.updated', resource_type='TaxRate', resource_id=str(tax.id), status='SUCCESS')
            messages.success(request, f"Tax Rate '{tax.name}' updated successfully.")
            return redirect('saas_core:tax_rate_list')
    else:
        form = TaxRateForm(instance=tax)
    return render(request, 'saas_core/superadmin/finance/generic_form.html', {'form': form, 'title': 'Edit Tax Rate', 'back_url': 'saas_core:tax_rate_list'})

@user_passes_test(is_superadmin, login_url='/auth/login/')
def tax_rate_toggle(request, tax_id):
    tax = get_object_or_404(TaxRate, id=tax_id)
    if request.method == 'POST':
        tax.is_active = not tax.is_active
        tax.save()
        action = 'activated' if tax.is_active else 'deactivated'
        AuditService.log(request=request, workspace=None, action=f'tax_rate.{action}', resource_type='TaxRate', resource_id=str(tax.id), status='SUCCESS')
        messages.success(request, f"Tax Rate '{tax.name}' has been {action}.")
    return redirect('saas_core:tax_rate_list')


# --- PAYMENT GATEWAY CRUD ---
@user_passes_test(is_superadmin, login_url='/auth/login/')
def payment_gateway_list(request):
    gateways = PaymentGateway.objects.all().order_by('-is_active', 'name')
    return render(request, 'saas_core/superadmin/finance/gateway_list.html', {'gateways': gateways})

@user_passes_test(is_superadmin, login_url='/auth/login/')
def payment_gateway_create(request):
    if request.method == 'POST':
        form = PaymentGatewayForm(request.POST)
        if form.is_valid():
            gateway = form.save()
            AuditService.log(request=request, workspace=None, action='payment_gateway.created', resource_type='PaymentGateway', resource_id=str(gateway.id), status='SUCCESS')
            messages.success(request, "Payment Gateway added successfully.")
            return redirect('saas_core:payment_gateway_list')
    else:
        form = PaymentGatewayForm()
    return render(request, 'saas_core/superadmin/finance/generic_form.html', {'form': form, 'title': 'Add Payment Gateway', 'back_url': 'saas_core:payment_gateway_list'})

@user_passes_test(is_superadmin, login_url='/auth/login/')
def payment_gateway_update(request, gateway_id):
    gateway = get_object_or_404(PaymentGateway, id=gateway_id)
    if request.method == 'POST':
        form = PaymentGatewayForm(request.POST, instance=gateway)
        if form.is_valid():
            form.save()
            AuditService.log(request=request, workspace=None, action='payment_gateway.updated', resource_type='PaymentGateway', resource_id=str(gateway.id), status='SUCCESS')
            messages.success(request, f"Gateway '{gateway.name}' updated successfully.")
            return redirect('saas_core:payment_gateway_list')
    else:
        form = PaymentGatewayForm(instance=gateway)
    return render(request, 'saas_core/superadmin/finance/generic_form.html', {'form': form, 'title': 'Edit Payment Gateway', 'back_url': 'saas_core:payment_gateway_list'})

@user_passes_test(is_superadmin, login_url='/auth/login/')
def payment_gateway_toggle(request, gateway_id):
    gateway = get_object_or_404(PaymentGateway, id=gateway_id)
    if request.method == 'POST':
        gateway.is_active = not gateway.is_active
        gateway.save()
        action = 'activated' if gateway.is_active else 'deactivated'
        AuditService.log(request=request, workspace=None, action=f'payment_gateway.{action}', resource_type='PaymentGateway', resource_id=str(gateway.id), status='SUCCESS')
        messages.success(request, f"Gateway '{gateway.name}' has been {action}.")
    return redirect('saas_core:payment_gateway_list')


# --- PAYMENT ACCOUNT CRUD ---
@user_passes_test(is_superadmin, login_url='/auth/login/')
def payment_account_list(request):
    accounts = PaymentAccount.objects.select_related('gateway').all().order_by('-is_active', 'gateway__name')
    return render(request, 'saas_core/superadmin/finance/account_list.html', {'accounts': accounts})

@user_passes_test(is_superadmin, login_url='/auth/login/')
def payment_account_create(request):
    if request.method == 'POST':
        form = PaymentAccountForm(request.POST)
        if form.is_valid():
            account = form.save()
            AuditService.log(request=request, workspace=None, action='payment_account.created', resource_type='PaymentAccount', resource_id=str(account.id), status='SUCCESS')
            messages.success(request, "Payment Account configured successfully.")
            return redirect('saas_core:payment_account_list')
    else:
        form = PaymentAccountForm()
    return render(request, 'saas_core/superadmin/finance/generic_form.html', {'form': form, 'title': 'Add Payment Account', 'back_url': 'saas_core:payment_account_list'})

@user_passes_test(is_superadmin, login_url='/auth/login/')
def payment_account_update(request, account_id):
    account = get_object_or_404(PaymentAccount, id=account_id)
    if request.method == 'POST':
        form = PaymentAccountForm(request.POST, instance=account)
        if form.is_valid():
            form.save()
            AuditService.log(request=request, workspace=None, action='payment_account.updated', resource_type='PaymentAccount', resource_id=str(account.id), status='SUCCESS')
            messages.success(request, "Payment Account updated successfully.")
            return redirect('saas_core:payment_account_list')
    else:
        form = PaymentAccountForm(instance=account)
    return render(request, 'saas_core/superadmin/finance/generic_form.html', {'form': form, 'title': 'Edit Payment Account', 'back_url': 'saas_core:payment_account_list'})

@user_passes_test(is_superadmin, login_url='/auth/login/')
def payment_account_toggle(request, account_id):
    account = get_object_or_404(PaymentAccount, id=account_id)
    if request.method == 'POST':
        account.is_active = not account.is_active
        account.save()
        action = 'activated' if account.is_active else 'deactivated'
        AuditService.log(request=request, workspace=None, action=f'payment_account.{action}', resource_type='PaymentAccount', resource_id=str(account.id), status='SUCCESS')
        messages.success(request, f"Account '{account.account_name}' has been {action}.")
    return redirect('saas_core:payment_account_list')


from apps.saas_core.models.tenant import Workspace

# ==========================================
# SUPERADMIN: TENANT MANAGER (GLOBAL CONTROL)
# ==========================================
@user_passes_test(is_superadmin, login_url='/auth/login/')
def superadmin_workspace_list(request):
    """God-mode view of all SaaS Tenants with Provisioning Data."""
    workspaces = Workspace.objects.select_related('billing_profile').all().order_by('-created_at')
    plans = SubscriptionPlan.objects.filter(is_active=True) # 🟢 Preload plans for modal
    
    return render(request, 'saas_core/superadmin/workspace_list.html', {
        'workspaces': workspaces,
        'plans': plans
    })

@user_passes_test(is_superadmin, login_url='/auth/login/')
def superadmin_workspace_provision(request, workspace_id):
    """Directly assigns a custom/enterprise plan bypassing the payment gateway."""
    workspace = get_object_or_404(Workspace, id=workspace_id)
    
    if request.method == 'POST':
        plan_id = request.POST.get('plan_id')
        cycle = request.POST.get('billing_cycle', 'MONTHLY')
        
        plan = get_object_or_404(SubscriptionPlan, id=plan_id)
        price = plan.prices.filter(billing_cycle=cycle, is_active=True, is_archived=False).first()
        
        if not price:
            messages.error(request, f"No active {cycle} pricing found for {plan.name}.")
            return redirect('saas_core:superadmin_workspace_list')
            
        # Direct Provisioning
        sub, _ = WorkspaceSubscription.objects.get_or_create(workspace=workspace, defaults={'plan': plan})
        sub.plan = plan
        sub.price = price
        sub.status = SubscriptionStatus.ACTIVE
        sub.current_period_start = timezone.now()
        
        days = 365 if cycle == 'YEARLY' else 30
        sub.current_period_end = timezone.now() + timedelta(days=days)
        sub.gateway_provider = 'MANUAL_ADMIN_PROVISION'
        sub.save()
        
        AuditService.log(request, workspace, 'admin.plan_provisioned', 'WorkspaceSubscription', str(sub.id), status='SUCCESS', actor=request.user)
        messages.success(request, f"Custom provision successful: {plan.name} assigned to {workspace.name}.")
        
    return redirect('saas_core:superadmin_workspace_list')

@user_passes_test(is_superadmin, login_url='/auth/login/')
def superadmin_workspace_toggle(request, workspace_id):
    """
    The 'Kill Switch': Suspends or Reactivates a Tenant Workspace.
    """
    workspace = get_object_or_404(Workspace, id=workspace_id)
    
    if request.method == 'POST':
        # Assuming you have 'ACTIVE' and 'SUSPENDED' in WorkspaceStatus choices
        # If your status uses different string values, adjust them here
        if workspace.status == 'ACTIVE':
            workspace.status = 'SUSPENDED'
            action_msg = "Suspended"
        else:
            workspace.status = 'ACTIVE'
            action_msg = "Reactivated"
            
        workspace.save()
        
        # 🟢 Enterprise Audit Trail
        AuditService.log(
            request=request, 
            workspace=workspace, 
            action=f'workspace.{action_msg.lower()}', 
            resource_type='Workspace', 
            resource_id=str(workspace.id), 
            status='SUCCESS'
        )
        
        if workspace.status == 'SUSPENDED':
            messages.warning(request, f"Workspace '{workspace.name}' has been SUSPENDED. Users can no longer access it.")
        else:
            messages.success(request, f"Workspace '{workspace.name}' has been safely Reactivated.")
            
    return redirect('saas_core:superadmin_workspace_list')


@user_passes_test(is_superadmin, login_url='/auth/login/')
def superadmin_global_settings(request):
    """Handles global SaaS configuration updates safely."""
    # Fetch the singleton config object
    config = GlobalConfiguration.get_config()
    
    if request.method == 'POST':
        form = GlobalConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            # 🟢 CRITICAL: Clear the global cache so the system uses the fresh settings immediately
            SettingsService.clear_global_cache() 
            messages.success(request, "Global SaaS settings updated successfully!")
            return redirect('saas_core:superadmin_global_settings')
    else:
        form = GlobalConfigForm(instance=config)
        
    return render(request, 'saas_core/superadmin/global_settings.html', {
        'form': form,
        'title': 'Global SaaS Configuration'
    })

from apps.saas_core.forms.superadmin_forms import WorkspaceForm

@user_passes_test(is_superadmin, login_url='/auth/login/')
def superadmin_workspace_update(request, workspace_id):
    """Superadmin Edit Workspace Details"""
    workspace = get_object_or_404(Workspace, id=workspace_id)
    if request.method == 'POST':
        form = WorkspaceForm(request.POST, instance=workspace)
        if form.is_valid():
            form.save()
            messages.success(request, f"Workspace '{workspace.name}' updated successfully.")
            return redirect('saas_core:superadmin_workspace_list')
    else:
        form = WorkspaceForm(instance=workspace)

    return render(request, 'saas_core/superadmin/finance/generic_form.html', {
        'form': form,
        'title': f"Edit Workspace: {workspace.name}",
        'back_url': 'saas_core:superadmin_workspace_list'
    })

@user_passes_test(is_superadmin, login_url='/auth/login/')
def superadmin_workspace_delete(request, workspace_id):
    """Superadmin Delete/Archive Workspace"""
    workspace = get_object_or_404(Workspace, id=workspace_id)
    if request.method == 'POST':
        ws_name = workspace.name
        workspace.is_deleted = True
        workspace.status = 'ARCHIVED'
        workspace.save()
        messages.success(request, f"Workspace '{ws_name}' has been archived and removed from the active list.")
    return redirect('saas_core:superadmin_workspace_list')