import random
import secrets
import weasyprint
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from apps.saas_core.models.finance import Invoice, InvoiceLineItem, InvoiceStatus

class InvoiceService:
    """Enterprise Invoice Generation & Management Service"""

    @staticmethod
    def generate_invoice_number():
        """Generates a 100% collision-free invoice number"""
        date_str = timezone.now().strftime('%y%m%d')
        while True:
            random_digits = str(random.randint(1000, 9999))
            invoice_number = f"INV-{date_str}-{random_digits}"
            if not Invoice.objects.filter(invoice_number=invoice_number).exists():
                return invoice_number

    @staticmethod
    @transaction.atomic
    def create_invoice_from_order(order):
        """Creates a formal invoice from a subscription order safely."""
        
        # 1. Fetch Legal Billing Info to prevent NULL constraint crashes
        billing_profile = getattr(order.workspace, 'billing_profile', None)
        company_name = billing_profile.legal_company_name if billing_profile and billing_profile.legal_company_name else order.workspace.name
        billing_email = billing_profile.billing_email if billing_profile and billing_profile.billing_email else order.workspace.owner.email

        # 2. Create the Master Invoice
        inv_number = InvoiceService.generate_invoice_number()
        secure_token = secrets.token_urlsafe(32)

        invoice = Invoice.objects.create(
            workspace=order.workspace,
            invoice_number=inv_number,
            public_token=secure_token,
            snapshot_company_name=company_name,
            snapshot_billing_email=billing_email,
            status=InvoiceStatus.DRAFT,
            subtotal=order.subtotal,
            tax_amount=order.tax_amount,
            total_amount=order.total_amount,
            snapshot_display_currency=order.snapshot_currency_code,
            due_date=timezone.now() + timezone.timedelta(days=7)
        )

        # 3. Create the Main Line Item
        InvoiceLineItem.objects.create(
            invoice=invoice,
            description=f"Subscription: {order.snapshot_plan_name} ({order.snapshot_billing_cycle})",
            quantity=1,
            unit_price=order.subtotal,
            amount=order.subtotal
        )

        # 4. Create Negative Line Item for Proration Credit
        if order.proration_credit and order.proration_credit > 0:
            InvoiceLineItem.objects.create(
                invoice=invoice,
                description="Unused Proration/Wallet Credit Applied",
                quantity=1,
                unit_price=-abs(order.proration_credit),
                amount=-abs(order.proration_credit)
            )

        return invoice

    @staticmethod
    def generate_pdf(invoice):
        """Generates a pixel-perfect PDF using WeasyPrint from an HTML template."""
        
        # 1. Render the HTML template with dynamic invoice data
        context = {'invoice': invoice}
        html_string = render_to_string('saas_core/billing/pdf/invoice_template.html', context)
        
        # 2. Generate PDF via WeasyPrint
        pdf_file = weasyprint.HTML(string=html_string).write_pdf()
        
        # 3. Save as a TRUE PDF to the Django FileField
        invoice.pdf_file.save(f"{invoice.invoice_number}.pdf", ContentFile(pdf_file), save=True)
        
        return invoice.pdf_file