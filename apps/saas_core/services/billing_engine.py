from django.utils import timezone
from decimal import Decimal
from apps.saas_core.models.subscription import WorkspaceSubscription, PlanPrice

class BillingEngine:
    """Enterprise Pricing Strategy & Proration Engine (With Wallet Integration)"""

    @staticmethod
    def calculate_proration(subscription: WorkspaceSubscription, new_price: PlanPrice) -> dict:
        now = timezone.now()
        workspace = subscription.workspace
        
        # 🟢 1. Fetch Wallet Balance
        from apps.saas_core.services.billing_profile_service import BillingProfileService
        profile = BillingProfileService.get_or_create_profile(workspace)
        wallet_balance = profile.wallet_balance

        # 🟢 2. Calculate Unused Plan Credit
        unused_credit = Decimal("0.00")
        if subscription.status == 'ACTIVE' and subscription.snapshot_price_amount:
            total_seconds = (subscription.current_period_end - subscription.current_period_start).total_seconds()
            unused_seconds = (subscription.current_period_end - now).total_seconds()
            if total_seconds > 0 and unused_seconds > 0:
                ratio = Decimal(str(unused_seconds)) / Decimal(str(total_seconds))
                unused_credit = subscription.snapshot_price_amount * ratio

        # 🟢 3. Combine Credits & Calculate Due
        total_credit = unused_credit + wallet_balance
        amount_due = new_price.amount - total_credit
        
        excess_credit = Decimal("0.00")

        if amount_due <= 0:
            excess_credit = abs(amount_due)  # Money left in wallet
            amount_due = Decimal("0.00")

        return {
            "is_upgrade": new_price.amount >= (subscription.snapshot_price_amount or Decimal("0.00")),
            "total_credit_applied": round(total_credit, 2),
            "new_cost": new_price.amount,
            "amount_due": round(amount_due, 2),
            "excess_credit": round(excess_credit, 2)
        }