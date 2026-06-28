from django.db import transaction
from django.utils import timezone
from apps.saas_core.models.finance import PaymentTransaction, TransactionStatus, OrderStatus, InvoiceStatus
from apps.saas_core.models.subscription import WorkspaceSubscription, SubscriptionStatus
from apps.saas_core.services.invoice_service import InvoiceService
from apps.saas_core.services.audit_service import AuditService

class PaymentVerificationService:
    """Enterprise Service for Handling Manual and Automated Payment Verifications."""

    @staticmethod
    @transaction.atomic
    def approve_payment(transaction_id, user):
        """
        Approves a payment, provisions the subscription, and generates the final PAID invoice.
        """
        tx = PaymentTransaction.objects.select_related('order', 'workspace').get(id=transaction_id)
        
        # Idempotency: 
        if tx.status == TransactionStatus.VERIFIED:
            return tx

        order = tx.order
        workspace = tx.workspace
        now = timezone.now()

        # 1. Update Transaction Status
        tx.status = TransactionStatus.VERIFIED
        tx.verified_by = user
        tx.verified_at = now
        tx.save(update_fields=['status', 'verified_by', 'verified_at'])

        # 2. Update Order Status
        order.status = OrderStatus.COMPLETED
        order.save(update_fields=['status'])

        # 3. Provision / Extend Subscription
        sub, created = WorkspaceSubscription.objects.get_or_create(
            workspace=workspace,
            defaults={'plan': order.plan, 'price': order.price, 'current_period_end': order.expires_at}
        )
        
        sub.plan = order.plan
        sub.price = order.price
        sub.status = SubscriptionStatus.ACTIVE
        sub.current_period_end = order.expires_at
        
        if created or not sub.current_period_start:
            sub.current_period_start = now
            
        sub.save()

        # 4. Generate Enterprise Invoice & Mark as PAID
        invoice = InvoiceService.create_invoice_from_order(order)
        invoice.status = InvoiceStatus.PAID
        invoice.amount_paid = order.total_amount
        invoice.paid_at = now
        invoice.issued_at = now
        invoice.save(update_fields=['status', 'amount_paid', 'paid_at', 'issued_at'])

        # 5. Audit Trail (Log for Security & Compliance)
        actor_name = user.email if user else "System Auto"
        AuditService.log(
            request=None,
            workspace=workspace,
            actor=user,
            action='payment.approved',
            resource_type='PaymentTransaction',
            resource_id=str(tx.id),
            metadata={
                'amount': str(tx.amount_paid), 
                'invoice_number': invoice.invoice_number,
                'verified_by': actor_name
            }
        )
        return tx

    @staticmethod
    @transaction.atomic
    def reject_payment(transaction_id, user, reason):
        """Rejects a pending payment and logs the reason."""
        tx = PaymentTransaction.objects.select_related('order', 'workspace').get(id=transaction_id)
        
        if tx.status != TransactionStatus.PENDING:
            raise ValueError("Only PENDING transactions can be rejected.")

        now = timezone.now()
        
        tx.status = TransactionStatus.FAILED
        tx.rejected_by = user
        tx.rejected_at = now
        tx.admin_note = reason
        tx.save(update_fields=['status', 'rejected_by', 'rejected_at', 'admin_note'])

        order = tx.order
        order.status = OrderStatus.REJECTED
        order.save(update_fields=['status'])

        AuditService.log(
            request=None,
            workspace=tx.workspace,
            actor=user,
            action='payment.rejected',
            resource_type='PaymentTransaction',
            resource_id=str(tx.id),
            metadata={'reason': reason}
        )
        return tx