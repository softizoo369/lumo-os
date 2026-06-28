import stripe
import logging
from decimal import Decimal
from datetime import timedelta
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.db import transaction, IntegrityError

from apps.saas_core.models.finance import (
    SubscriptionOrder, PaymentTransaction, TransactionStatus, 
    OrderStatus, InvoiceStatus, ProcessedWebhookEvent, PaymentAccount
)
from apps.saas_core.models.subscription import WorkspaceSubscription, SubscriptionStatus
from apps.saas_core.services.invoice_service import InvoiceService
from apps.saas_core.services.audit_service import AuditService

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY

class StripeService:
    """Enterprise Stripe Integration with Idempotent Webhook Processing"""

    @staticmethod
    def create_checkout_session(request, order):
        # Stripe expects amount in minimum currency units (Cents)
        amount_in_cents = int(order.total_amount * 100)
        
        domain_url = request.build_absolute_uri('/')[:-1]
        success_url = f"{domain_url}{reverse('saas_core:billing_dashboard')}?payment_status=success"
        cancel_url = f"{domain_url}{reverse('saas_core:pay_order', kwargs={'order_id': order.id})}?payment_status=canceled"

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': order.snapshot_currency_code.lower(),
                    'product_data': {
                        'name': f"Subscription: {order.snapshot_plan_name}",
                        'description': f"Lumo OS - {order.snapshot_billing_cycle.title()} Billing",
                    },
                    'unit_amount': amount_in_cents,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=str(order.id),
            customer_email=request.user.email,
            metadata={
                'workspace_id': str(order.workspace_id),
                'order_id': str(order.id)
            }
        )
        return session.url

    @staticmethod
    def process_webhook_event(payload, sig_header):
        """
        Securely processes Stripe webhooks with strict Idempotency and Signature Verification.
        """
        webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)
        
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except ValueError:
            logger.error("Stripe Webhook Error: Invalid payload")
            raise ValueError("Invalid payload")
        except stripe.error.SignatureVerificationError:
            logger.error("Stripe Webhook Error: Invalid signature")
            raise ValueError("Invalid signature")

        event_id = event['id']
        event_type = event['type']
        gateway_name = 'STRIPE'

        # 🟢 1. Absolute Idempotency using Database UNIQUE Constraint
        try:
            webhook_record = ProcessedWebhookEvent.objects.create(
                event_id=event_id,
                gateway_name=gateway_name,
                event_type=event_type,
                status='PROCESSING'
            )
        except IntegrityError:
            # Event already exists in DB, it means Stripe is retrying an already received event.
            logger.info(f"Webhook {event_id} already processed or processing. Ignoring duplicate.")
            return

        # 🟢 2. Process Specific Events
        try:
            if event_type == 'checkout.session.completed':
                session = event['data']['object']
                StripeService._handle_checkout_completed(session)
            
            # Mark as successfully processed
            webhook_record.status = 'PROCESSED'
            webhook_record.save(update_fields=['status'])

        except Exception as e:
            # 🟢 3. Failure Handling & Audit
            logger.exception(f"Error processing webhook {event_id}: {str(e)}")
            webhook_record.status = 'FAILED'
            webhook_record.error_message = str(e)
            webhook_record.save(update_fields=['status', 'error_message'])
            raise e

    @staticmethod
    @transaction.atomic
    def _handle_checkout_completed(session):
        """Handles the successful checkout session and provisions the SaaS account."""
        
        order_id = session.get('client_reference_id') or session.get('metadata', {}).get('order_id')
        if not order_id:
            raise ValueError("No order_id found in Stripe session payload.")

        # 🟢 Pessimistic Lock on Order to prevent manual verification clashes
        order = SubscriptionOrder.objects.select_for_update().get(id=order_id)
        workspace = order.workspace

        if order.status == OrderStatus.COMPLETED:
            return  # Already provisioned manually or via another hook

        amount_paid = Decimal(str(session.get('amount_total', 0))) / Decimal('100.00')
        payment_intent = session.get('payment_intent', f"auto_stripe_{session.get('id')}")
        customer_email = session.get('customer_details', {}).get('email', 'stripe_customer')

        # 🟢 Fetch the Platform's Stripe Receiving Account (Required by Foreign Key)
        stripe_account = PaymentAccount.objects.filter(gateway__code__iexact='STRIPE', is_active=True).first()
        if not stripe_account:
            raise ValueError("Superadmin has not configured a valid 'STRIPE' Payment Account in Finance Center.")

        # 1. Create Verified Transaction
        tx = PaymentTransaction.objects.create(
            order=order,
            workspace=workspace,
            receiving_account=stripe_account,
            amount_paid=amount_paid,
            sender_account_number=customer_email,
            transaction_id=payment_intent,
            status=TransactionStatus.VERIFIED,
            verified_at=timezone.now()
        )

        # 2. Update Order
        order.status = OrderStatus.COMPLETED
        order.save(update_fields=['status'])

        # 3. Activate Subscription
        now = timezone.now()
        sub, _ = WorkspaceSubscription.objects.get_or_create(workspace=workspace, defaults={'plan': order.plan})
        
        sub.plan = order.plan
        sub.price = order.price
        sub.status = SubscriptionStatus.ACTIVE
        sub.current_period_start = now
        days = 365 if order.price.billing_cycle == 'YEARLY' else 30
        sub.current_period_end = now + timedelta(days=days)
        sub.gateway_provider = 'STRIPE'
        sub.gateway_subscription_id = session.get('subscription')
        sub.save()

        # 4. Generate Enterprise Invoice
        invoice = InvoiceService.create_invoice_from_order(order)
        invoice.status = InvoiceStatus.PAID
        invoice.amount_paid = amount_paid
        invoice.paid_at = now
        invoice.issued_at = now
        invoice.save(update_fields=['status', 'amount_paid', 'paid_at', 'issued_at'])

        # 5. Audit Logging
        AuditService.log(
            request=None, workspace=workspace, action='payment.automated_success',
            resource_type='PaymentTransaction', resource_id=str(tx.id),
            metadata={'amount': str(amount_paid), 'invoice_number': invoice.invoice_number, 'gateway': 'STRIPE'},
            status='SUCCESS'
        )