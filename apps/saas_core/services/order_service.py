from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from apps.saas_core.models.finance import SubscriptionOrder, OrderStatus, InvoiceStatus
from apps.saas_core.models.subscription import SubscriptionStatus
from apps.saas_core.services.billing_engine import BillingEngine
from apps.saas_core.services.audit_service import AuditService
from apps.saas_core.services.usage_service import UsageService
from apps.saas_core.services.invoice_service import InvoiceService
from apps.saas_core.services.billing_profile_service import BillingProfileService

class OrderService:
    @staticmethod
    @transaction.atomic
    def create_order(workspace, price, user):
        usage = UsageService.get_current_usage(workspace)
        new_plan = price.plan
        
        limit_errors = []
        if usage.total_users > new_plan.max_users: limit_errors.append("Team Members")
        if usage.total_companies > new_plan.max_companies: limit_errors.append("Companies")
        if usage.total_storage_mb > new_plan.max_storage_mb: limit_errors.append("Storage")
        if limit_errors:
            raise ValueError(f"Cannot downgrade to '{new_plan.name}'. Remove excess resources first.")

        existing_order = SubscriptionOrder.objects.filter(workspace=workspace, status=OrderStatus.PENDING).first()
        if existing_order:
            existing_order.status = OrderStatus.EXPIRED
            existing_order.save()

        subscription = workspace.subscription
        billing_calc = BillingEngine.calculate_proration(subscription, price)

        # 🟢 1. Create Order
        order = SubscriptionOrder.objects.create(
            workspace=workspace,
            plan=price.plan,
            price=price,
            snapshot_plan_name=price.plan.name,
            snapshot_price_amount=price.amount,
            snapshot_currency_code=price.currency.code,
            snapshot_billing_cycle=price.billing_cycle,
            subtotal=price.amount,
            proration_credit=billing_calc['total_credit_applied'], # Used both plan time + wallet
            tax_amount=Decimal("0.00"),
            total_amount=billing_calc['amount_due'],
            status=OrderStatus.PENDING,
            expires_at=timezone.now() + timedelta(hours=72),
            created_by=user
        )

        # 🟢 2. Update Wallet Balance Immediately (Locking the funds)
        profile = BillingProfileService.get_or_create_profile(workspace)
        profile.wallet_balance = billing_calc['excess_credit']
        profile.save(update_fields=['wallet_balance'])

        # 🟢 3. ZERO-DOLLAR AUTO-COMPLETE LOGIC
        if billing_calc['amount_due'] <= 0:
            order.status = OrderStatus.COMPLETED
            order.save(update_fields=['status'])
            
            # Force Subscription to ACTIVE
            subscription.plan = price.plan
            subscription.price = price
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.current_period_start = timezone.now()
            days = 365 if price.billing_cycle == 'YEARLY' else 30
            subscription.current_period_end = timezone.now() + timedelta(days=days)
            subscription.save()
            
            # Generate PAID invoice automatically
            invoice = InvoiceService.create_invoice_from_order(order)
            invoice.status = InvoiceStatus.PAID
            invoice.amount_paid = order.total_amount
            invoice.paid_at = timezone.now()
            invoice.issued_at = timezone.now()
            invoice.save()
            
            AuditService.log(None, workspace, 'order.auto_completed', 'SubscriptionOrder', str(order.id), status='SUCCESS', actor=user)
            return order

        # 🟢 4. Normal Paid Flow
        if subscription.status != SubscriptionStatus.ACTIVE:
            subscription.status = SubscriptionStatus.PENDING_PAYMENT
            subscription.save()

        AuditService.log(None, workspace, 'order.created', 'SubscriptionOrder', str(order.id), status='SUCCESS', actor=user)
        return order