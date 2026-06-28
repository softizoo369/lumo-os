from django.db import transaction
from apps.saas_core.models.finance import BillingProfile

class BillingProfileService:
    """Enterprise Service for managing Tenant Billing Profiles securely."""

    @staticmethod
    def get_or_create_profile(workspace):
        """
        Safely fetches or creates a billing profile preventing race conditions.
        Avoids silent data pollution by NOT pre-filling legal entity names with operational workspace names.
        """
        with transaction.atomic():
            # 🟢 Gap 3 Fix: select_for_update() + atomic prevents IntegrityError race conditions
            profile, created = BillingProfile.objects.select_for_update().get_or_create(
                workspace=workspace,
                defaults={
                    # 🟢 Gap 4 Fix: No silent data pollution. Leave blank to force explicit completion.
                    'legal_company_name': '',
                    'billing_email': ''
                }
            )
        return profile