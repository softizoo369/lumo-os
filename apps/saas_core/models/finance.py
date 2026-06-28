import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.saas_core.models.base import LumoBaseModel

class TaxRegistrationType(models.TextChoices):
    VAT = 'VAT', 'VAT Number'
    GST = 'GST', 'GST Number'
    EIN = 'EIN', 'Employer Identification Number (US)'
    ABN = 'ABN', 'Australian Business Number'
    OTHER = 'OTHER', 'Other'

# ==========================================
# 1. PAYMENT CONFIGURATION
# ==========================================
class PaymentGateway(LumoBaseModel):
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'lumo_finance_payment_gateway'

    def __str__(self):
        return self.name

class PaymentAccount(LumoBaseModel):
    gateway = models.ForeignKey('saas_core.PaymentGateway', on_delete=models.PROTECT, related_name='accounts')
    account_name = models.CharField(max_length=100, help_text="e.g., Lumo OS bKash Merchant")
    account_number = models.CharField(max_length=100)
    branch_name = models.CharField(max_length=100, null=True, blank=True)
    routing_number = models.CharField(max_length=50, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'lumo_finance_payment_account'

    def __str__(self):
        return f"{self.gateway.name} - {self.account_number}"

# ==========================================
# 2. BILLING PROFILE & TAX ENGINE
# ==========================================
class TaxRate(LumoBaseModel):
    name = models.CharField(max_length=50, help_text="e.g. BD VAT 15%")
    country = models.ForeignKey('core_masterdata.Country', on_delete=models.PROTECT)
    state_province = models.CharField(max_length=100, null=True, blank=True)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'lumo_finance_tax_rate'

    def __str__(self):
        return f"{self.name} ({self.percentage}%)"

class BillingProfile(LumoBaseModel):
    """Legal billing entity for a workspace."""
    workspace = models.OneToOneField('saas_core.Workspace', on_delete=models.CASCADE, related_name='billing_profile')
    legal_company_name = models.CharField(max_length=255)
    billing_email = models.EmailField()
    
    address_line = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    postal_code = models.CharField(max_length=20, null=True, blank=True)
    country = models.ForeignKey('core_masterdata.Country', on_delete=models.PROTECT, null=True, blank=True)
    
    tax_registration_type = models.CharField(max_length=20, choices=TaxRegistrationType.choices, null=True, blank=True)
    tax_registration_number = models.CharField(max_length=100, null=True, blank=True)
    is_tax_exempt = models.BooleanField(default=False)
    tax_exemption_certificate = models.FileField(upload_to='secure/tax_exemptions/%Y/%m/', null=True, blank=True)
    
    # 🟢 Enterprise Customer Wallet for Proration & Refunds
    wallet_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    @property
    def is_complete(self):
        return bool(self.legal_company_name and self.billing_email and self.country_id)

    class Meta:
        db_table = 'lumo_finance_billing_profile'

    def __str__(self):
        return self.legal_company_name or "Incomplete Profile"

# ==========================================
# 3. SUBSCRIPTION ORDER (Snapshot Strategy)
# ==========================================
class OrderStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending Payment'
    PROCESSING = 'PROCESSING', 'Processing Verification'
    COMPLETED = 'COMPLETED', 'Completed & Provisioned'
    REJECTED = 'REJECTED', 'Rejected'
    EXPIRED = 'EXPIRED', 'Expired'
    REFUNDED = 'REFUNDED', 'Refunded'
    CANCELED = 'CANCELED', 'Canceled'

class SubscriptionOrder(LumoBaseModel):
    workspace = models.ForeignKey('saas_core.Workspace', on_delete=models.CASCADE, related_name='orders')
    plan = models.ForeignKey('saas_core.SubscriptionPlan', on_delete=models.PROTECT)
    price = models.ForeignKey('saas_core.PlanPrice', on_delete=models.PROTECT)

    snapshot_plan_name = models.CharField(max_length=100, editable=False)
    snapshot_price_amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    snapshot_currency_code = models.CharField(max_length=10, editable=False)
    snapshot_billing_cycle = models.CharField(max_length=20, editable=False)
    
    snapshot_tax_name = models.CharField(max_length=100, null=True, blank=True, editable=False)
    snapshot_tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'), editable=False)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    proration_credit = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), editable=False)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), editable=False)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False)

    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    expires_at = models.DateTimeField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = 'lumo_finance_subscription_order'

# ==========================================
# 4. PAYMENT TRANSACTION
# ==========================================
class TransactionStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending Verification'
    VERIFIED = 'VERIFIED', 'Verified & Settled'
    FAILED = 'FAILED', 'Failed / Rejected'
    REFUNDED = 'REFUNDED', 'Refunded'
    PARTIALLY_REFUNDED = 'PARTIALLY_REFUNDED', 'Partially Refunded'
    DISPUTED = 'DISPUTED', 'Disputed'
    CHARGEBACK = 'CHARGEBACK', 'Chargeback'

class PaymentTransaction(LumoBaseModel):
    order = models.OneToOneField('saas_core.SubscriptionOrder', on_delete=models.CASCADE, related_name='transaction')
    workspace = models.ForeignKey('saas_core.Workspace', on_delete=models.CASCADE)
    receiving_account = models.ForeignKey('saas_core.PaymentAccount', on_delete=models.PROTECT)
    
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    sender_account_number = models.CharField(max_length=100)
    transaction_id = models.CharField(max_length=255, unique=True, db_index=True)
    proof_file = models.FileField(upload_to='secure/payment_proofs/%Y/%m/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=TransactionStatus.choices, default=TransactionStatus.PENDING)

    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_payments')
    verified_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='rejected_payments')
    rejected_at = models.DateTimeField(null=True, blank=True)
    admin_note = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'lumo_finance_payment_transaction'

# ==========================================
# 5. ENTERPRISE INVOICE DOMAIN
# ==========================================
class InvoiceStatus(models.TextChoices):
    DRAFT = 'DRAFT', _('Draft')
    ISSUED = 'ISSUED', _('Issued')
    PAID = 'PAID', _('Paid')
    PARTIALLY_PAID = 'PARTIALLY_PAID', _('Partially Paid')
    VOID = 'VOID', _('Void / Cancelled')
    REFUNDED = 'REFUNDED', _('Refunded / Credit Note')

class Invoice(LumoBaseModel):
    """Immutable Financial Record."""
    workspace = models.ForeignKey('saas_core.Workspace', on_delete=models.PROTECT, related_name='invoices')
    order = models.OneToOneField('saas_core.SubscriptionOrder', on_delete=models.PROTECT, related_name='invoice', null=True, blank=True)
    
    invoice_number = models.CharField(max_length=50, unique=True, db_index=True, editable=False)
    
    snapshot_company_name = models.CharField(max_length=255, editable=False)
    snapshot_billing_email = models.EmailField(editable=False)
    snapshot_billing_address = models.TextField(editable=False, null=True, blank=True)
    snapshot_tax_type = models.CharField(max_length=50, null=True, blank=True, editable=False) 
    snapshot_tax_id = models.CharField(max_length=100, null=True, blank=True, editable=False)
    
    snapshot_base_currency = models.CharField(max_length=3, default='USD', editable=False)
    snapshot_display_currency = models.CharField(max_length=3, editable=False)
    snapshot_exchange_rate = models.DecimalField(max_digits=10, decimal_places=6, default=Decimal('1.000000'), editable=False)
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), editable=False)
    
    status = models.CharField(max_length=20, choices=InvoiceStatus.choices, default=InvoiceStatus.DRAFT)
    pdf_file = models.FileField(upload_to='secure/invoices/%Y/%m/', null=True, blank=True)
    
    # 🟢 FIX: Delegated token generation to the DB model default
    public_token = models.CharField(max_length=128, unique=True, db_index=True, editable=False, default=uuid.uuid4)
    
    issued_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'lumo_finance_invoice'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.invoice_number} | {self.status}"

class InvoiceLineItem(LumoBaseModel):
    """Immutable Line Items linked to the Invoice"""
    invoice = models.ForeignKey('saas_core.Invoice', on_delete=models.CASCADE, related_name='line_items')
    description = models.CharField(max_length=255, editable=False)
    quantity = models.PositiveIntegerField(default=1, editable=False)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    is_tax = models.BooleanField(default=False, editable=False)

    class Meta:
        db_table = 'lumo_finance_invoice_line_item'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.invoice.invoice_number} - {self.description}"

class CreditNote(LumoBaseModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='credit_notes')
    credit_note_number = models.CharField(max_length=50, unique=True, editable=False)
    amount_credited = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    reason = models.TextField()
    issued_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to='secure/credit_notes/%Y/%m/', null=True, blank=True)

    class Meta:
        db_table = 'lumo_finance_credit_note'

    def __str__(self):
        return self.credit_note_number

class ProcessedWebhookEvent(LumoBaseModel):
    event_id = models.CharField(max_length=255, unique=True, db_index=True)
    gateway_name = models.CharField(max_length=50)
    event_type = models.CharField(max_length=100)
    status = models.CharField(max_length=20, default='PROCESSED')
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'lumo_finance_webhook_event'
        indexes = [
            models.Index(fields=['event_id', 'gateway_name']),
        ]