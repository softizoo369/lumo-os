from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import IntegrityError
from django.http import HttpResponse
from django.db.models import Prefetch
from apps.saas_core.models.subscription import SubscriptionPlan, PlanPrice
from apps.saas_core.models.finance import SubscriptionOrder, PaymentTransaction, TransactionStatus, PaymentAccount, OrderStatus, BillingProfile, Invoice
from apps.saas_core.services.workspace_service import WorkspaceService
from apps.saas_core.services.usage_service import UsageService
from apps.saas_core.services.billing_engine import BillingEngine
from apps.saas_core.services.audit_service import AuditService
from apps.saas_core.services.order_service import OrderService
from apps.saas_core.services.billing_profile_service import BillingProfileService
from apps.saas_core.services.stripe_service import StripeService
from apps.saas_core.services.invoice_service import InvoiceService
from apps.saas_core.forms.billing_forms import BillingProfileForm
from apps.saas_core.decorators import require_permission

@login_required(login_url='/auth/login/')
@require_permission('billing.read')
def billing_dashboard(request):
    workspace = WorkspaceService.get_current_workspace(request)
    try:
        active_sub = workspace.subscription
    except:
        active_sub = None
        
    usage = UsageService.get_current_usage(workspace)
    invoices = Invoice.objects.filter(workspace=workspace).order_by('-created_at')[:5]
    
    context = {
        'subscription': active_sub,
        'usage': usage,
        'workspace': workspace,
        'invoices': invoices
    }
    return render(request, 'saas_core/billing/dashboard.html', context)

from apps.saas_core.models.settings import GlobalConfiguration

@login_required(login_url='/auth/login/')
def subscription_plans(request):
    """Displays all active and public subscription plans adhering to SaaS Constitution v1."""
    workspace = WorkspaceService.get_current_workspace(request)
    subscription = getattr(workspace, 'subscription', None)
    
    from apps.saas_core.services.usage_service import UsageService
    usage = UsageService.get_current_usage(workspace)
    
    # 🟢 SaaS Constitution: Global Config
    global_config = GlobalConfiguration.get_config()
    
    active_prices = PlanPrice.objects.filter(is_active=True, is_archived=False)
    
    # 🟢 ENTERPRISE QUERY: Only Public Plans, Explicitly Ordered!
    plans = SubscriptionPlan.objects.filter(is_active=True, is_public=True).prefetch_related(
        Prefetch('prices', queryset=active_prices)
    ).order_by('sort_order')
    
    context = {
        'workspace': workspace,
        'subscription': subscription,
        'usage': usage,
        'plans': plans,
        'global_config': global_config
    }
    return render(request, 'saas_core/billing/subscription_plans.html', context)

@login_required(login_url='/auth/login/')
@require_permission('billing.update')
def checkout_summary(request, price_id):
    workspace = WorkspaceService.get_current_workspace(request)
    price = get_object_or_404(PlanPrice, id=price_id, is_active=True, is_archived=False)
    
    subscription = workspace.subscription
    billing_calc = BillingEngine.calculate_proration(subscription, price)
    
    if request.method == 'POST':
        try:
            order = OrderService.create_order(workspace, price, request.user)
            
            # 🟢 Redirect logic based on auto-complete
            if order.status == OrderStatus.COMPLETED:
                messages.success(request, "Plan updated successfully! Your excess credit has been added to your workspace wallet.")
                return redirect('saas_core:billing_dashboard')
            else:
                messages.info(request, "Order generated securely. Please complete the payment.")
                return redirect('saas_core:pay_order', order_id=order.id)
                
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('saas_core:subscription_plans')
            
    return render(request, 'saas_core/billing/checkout.html', {
        'price': price, 'plan': price.plan, 'workspace': workspace, 'billing_calc': billing_calc
    })

@login_required(login_url='/auth/login/')
@require_permission('billing.update')
def pay_order(request, order_id):
    workspace = WorkspaceService.get_current_workspace(request)
    order = get_object_or_404(SubscriptionOrder, id=order_id, workspace=workspace)
    
    if order.status != OrderStatus.PENDING:
        messages.warning(request, "This order has already been processed or is pending verification.")
        return redirect('saas_core:billing_dashboard')
        
    payment_accounts = PaymentAccount.objects.filter(is_active=True)
    if request.method == 'POST':
        transaction_id_input = request.POST.get('transaction_id')
        account_id_input = request.POST.get('account_id')
        sender_number = request.POST.get('sender_number')
        
        if PaymentTransaction.objects.filter(transaction_id=transaction_id_input).exists():
            messages.error(request, f"Transaction ID '{transaction_id_input}' has already been used.")
            return render(request, 'saas_core/billing/pay_order.html', {'order': order, 'accounts': payment_accounts})
            
        try:
            transaction = PaymentTransaction.objects.create(
                order=order,
                workspace=workspace,
                receiving_account_id=account_id_input,
                amount_paid=order.total_amount,
                sender_account_number=sender_number,
                transaction_id=transaction_id_input,
                proof_file=request.FILES.get('proof_file'),
                status=TransactionStatus.PENDING
            )
            order.status = OrderStatus.PROCESSING
            order.save()
            
            AuditService.log(
                request=request, workspace=workspace, action='payment.submitted',
                resource_type='PaymentTransaction', resource_id=str(transaction.id),
                metadata={'order_id': str(order.id), 'amount': float(order.total_amount), 'tx_id': transaction_id_input, 'gateway_account': account_id_input},
                status='SUCCESS'
            )
            messages.success(request, "Payment submitted successfully! Superadmin will verify shortly.")
            return redirect('saas_core:billing_dashboard')
            
        except IntegrityError:
            messages.error(request, "Database error: This order or transaction might already exist.")
            return render(request, 'saas_core/billing/pay_order.html', {'order': order, 'accounts': payment_accounts})
            
    return render(request, 'saas_core/billing/pay_order.html', {'order': order, 'accounts': payment_accounts})

@login_required(login_url='/auth/login/')
@require_permission('billing.update')
def process_automated_payment(request, order_id, gateway_code):
    """Entry point for Automated Payment Gateways (Stripe)."""
    workspace = WorkspaceService.get_current_workspace(request)
    order = get_object_or_404(SubscriptionOrder, id=order_id, workspace=workspace)
    
    if gateway_code.lower() == 'stripe':
        try:
            checkout_url = StripeService.create_checkout_session(request, order)
            return redirect(checkout_url)
        except Exception as e:
            messages.error(request, f"Payment gateway error: {str(e)}")
            return redirect('saas_core:pay_order', order_id=order.id)
            
    messages.info(request, f"{gateway_code.upper()} integration is coming next!")
    return redirect('saas_core:pay_order', order_id=order.id)

@login_required(login_url='/auth/login/')
@require_permission('billing.manage') 
def billing_profile_settings(request):
    workspace = WorkspaceService.get_current_workspace(request)
    if not workspace:
        messages.error(request, "Workspace not found.")
        return redirect('saas_core:dashboard_home')
        
    profile = BillingProfileService.get_or_create_profile(workspace=workspace)
    if request.method == 'POST':
        form = BillingProfileForm(request.POST, instance=profile)
        if form.is_valid():
            profile = form.save()
            AuditService.log(
                request=request, workspace=workspace, action='billing_profile.updated',
                resource_type='BillingProfile', resource_id=str(profile.id),
                metadata={'is_complete': profile.is_complete}, status='SUCCESS'
            )
            messages.success(request, "Legal billing profile updated successfully! Future invoices will use this data.")
            return redirect('saas_core:billing_profile_settings')
    else:
        form = BillingProfileForm(instance=profile)
    return render(request, 'saas_core/billing/profile_settings.html', {'form': form, 'is_complete': profile.is_complete})

@login_required(login_url='/auth/login/')
@require_permission('billing.read') 
def view_invoice(request, token):
    workspace = WorkspaceService.get_current_workspace(request)
    invoice = get_object_or_404(Invoice, public_token=token)
    
    if not request.user.is_superuser and invoice.workspace_id != workspace.id:
        AuditService.log(
            request=request, workspace=workspace, action='invoice.access_denied',
            resource_type='Invoice', resource_id=str(invoice.id), status='FAILED'
        )
        messages.error(request, "Access Denied: This invoice belongs to another workspace.")
        return redirect('saas_core:billing_dashboard')
        
    AuditService.log(
        request=request, workspace=workspace, action='invoice.viewed',
        resource_type='Invoice', resource_id=str(invoice.id), status='SUCCESS'
    )
    return render(request, 'saas_core/billing/invoice_detail.html', {'invoice': invoice})

@login_required(login_url='/auth/login/')
def download_invoice_pdf(request, invoice_id):
    workspace = WorkspaceService.get_current_workspace(request)
    invoice = get_object_or_404(Invoice, id=invoice_id, workspace=workspace)
    
    if not invoice.pdf_file:
        InvoiceService.generate_pdf(invoice)
        
    response = HttpResponse(invoice.pdf_file.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{invoice.invoice_number}.pdf"'
    return response