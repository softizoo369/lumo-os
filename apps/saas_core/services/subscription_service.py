import logging
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from apps.saas_core.models.subscription import SubscriptionPlan, WorkspaceSubscription, SubscriptionStatus, PlanPrice
from apps.saas_core.models.tenant import Workspace
from core.context import system_context

logger = logging.getLogger(__name__)

class SubscriptionService:
    @staticmethod
    def assign_default_plan(workspace: Workspace):
        """
        Enterprise Bootstrap Logic:
        Assigns the designated Default Plan to a newly created workspace.
        STRICT INVARIANT: A Workspace MUST have a Plan. If no plan exists, it fails loudly.
        """
        with system_context():
            # 1. 🟢 Look for the explicitly marked Default Plan
            default_plan = SubscriptionPlan.objects.filter(is_default=True, is_active=True).first()

            # 2. 🟡 Fallback: If no default is set, grab the first active plan to prevent crash
            if not default_plan:
                default_plan = SubscriptionPlan.objects.filter(is_active=True).order_by('sort_order').first()

            # 3. 🔴 FAIL LOUDLY: If the database has absolutely NO plans (Seed data missing)
            if not default_plan:
                error_msg = f"SYSTEM BOOTSTRAP FAILED: No active SubscriptionPlan found for Workspace '{workspace.name}'."
                logger.critical(error_msg)
                # Raising this inside the post_save signal will rollback the Workspace creation!
                # This perfectly protects our Invariant (No Plan = No Workspace).
                raise ValueError("System Configuration Error: No default subscription plan exists in the system. Please contact support.")

            # 4. Calculate Trial Period based on the Plan's settings
            trial_days = default_plan.trial_days if default_plan.trial_days is not None else 14
            end_date = timezone.now() + timedelta(days=trial_days)

            # 5. Create the valid Subscription (plan is GUARANTEED, price is legally None)
            sub, created = WorkspaceSubscription.objects.get_or_create(
                workspace=workspace,
                defaults={
                    'plan': default_plan,
                    'price': None, 
                    'status': SubscriptionStatus.TRIALING,
                    'current_period_start': timezone.now(),
                    'current_period_end': end_date,
                    'trial_end': end_date
                }
            )
            return sub

    @staticmethod
    @transaction.atomic
    def set_default_plan(plan):
        """Safely ensures only one plan is default using atomic transaction."""
        SubscriptionPlan.objects.exclude(id=plan.id).update(is_default=False)
        plan.is_default = True
        plan.save(update_fields=['is_default'])

    @staticmethod
    def _sync_immutable_prices(plan, currency, monthly_price, yearly_price):
        """
        Enterprise SaaS Pattern: Immutable Pricing.
        Archives old pricing if changed, creates a new active pricing record.
        Prevents ghost states and preserves historical invoice accuracy.
        """
        if currency and monthly_price is not None:
            current_monthly = PlanPrice.objects.filter(plan=plan, billing_cycle='MONTHLY', is_archived=False, is_active=True).first()
            if not current_monthly or current_monthly.amount != monthly_price or current_monthly.currency != currency:
                if current_monthly:
                    current_monthly.is_archived = True
                    current_monthly.is_active = False
                    current_monthly.save(update_fields=['is_archived', 'is_active'])
                PlanPrice.objects.create(plan=plan, currency=currency, amount=monthly_price, billing_cycle='MONTHLY', is_active=True)

        if currency and yearly_price is not None and yearly_price > 0:
            current_yearly = PlanPrice.objects.filter(plan=plan, billing_cycle='YEARLY', is_archived=False, is_active=True).first()
            if not current_yearly or current_yearly.amount != yearly_price or current_yearly.currency != currency:
                if current_yearly:
                    current_yearly.is_archived = True
                    current_yearly.is_active = False
                    current_yearly.save(update_fields=['is_archived', 'is_active'])
                PlanPrice.objects.create(plan=plan, currency=currency, amount=yearly_price, billing_cycle='YEARLY', is_active=True)

    @staticmethod
    @transaction.atomic
    def create_plan_with_prices(plan_data, pricing_data):
        """Domain-driven plan creation."""
        is_default = plan_data.pop('is_default', False)
        
        # Create base plan
        plan = SubscriptionPlan.objects.create(**plan_data)
        
        if is_default:
            SubscriptionService.set_default_plan(plan)
            
        SubscriptionService._sync_immutable_prices(
            plan, pricing_data.get('currency'), pricing_data.get('monthly_price'), pricing_data.get('yearly_price')
        )
        return plan

    @staticmethod
    @transaction.atomic
    def update_plan_with_prices(plan, plan_data, pricing_data):
        """Domain-driven plan update."""
        is_default = plan_data.pop('is_default', False)
        
        # Update base plan properties
        for key, value in plan_data.items():
            setattr(plan, key, value)
        plan.save()

        # Handle Default Flag Safely
        if is_default:
            SubscriptionService.set_default_plan(plan)
        elif plan.is_default and not is_default:
            plan.is_default = False
            plan.save(update_fields=['is_default'])

        # Sync Prices immutably
        SubscriptionService._sync_immutable_prices(
            plan, pricing_data.get('currency'), pricing_data.get('monthly_price'), pricing_data.get('yearly_price')
        )
        return plan