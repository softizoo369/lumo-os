from django.db import models
from django.utils import timezone
from apps.saas_core.models.base import LumoBaseModel
from apps.saas_core.models.tenant import Workspace

# 🟢 SAAS STATE MACHINE: Subscription Level
class SubscriptionStatus(models.TextChoices):
    TRIALING = "TRIALING", "Trialing"
    ACTIVE = "ACTIVE", "Active"
    PAST_DUE = "PAST_DUE", "Past Due" # Inside Grace Period
    CANCELED = "CANCELED", "Canceled" # User canceled, stops at period end
    EXPIRED = "EXPIRED", "Expired"
    PENDING_PAYMENT = "PENDING_PAYMENT", "Pending Payment"

class BillingCycle(models.TextChoices):
    MONTHLY = "MONTHLY", "Monthly"
    YEARLY = "YEARLY", "Yearly"
    LIFETIME = "LIFETIME", "Lifetime"

class SubscriptionPlan(LumoBaseModel):
    """The Master Plan Definition"""
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.TextField(null=True, blank=True)
    
    # 🟢 Commercial & Display Flags
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_default = models.BooleanField(default=False, help_text="Auto-assign on onboarding")
    is_popular = models.BooleanField(default=False, help_text="Highlight as Most Popular")
    is_public = models.BooleanField(default=True, help_text="Show on public pricing page")
    allow_signup = models.BooleanField(default=True, help_text="Allow direct checkout")
    requires_sales_contact = models.BooleanField(default=False, help_text="Hide price, show Contact Sales")
    
    # 🟢 Strategy Flags
    is_free_plan = models.BooleanField(default=False)
    is_trial_plan = models.BooleanField(default=False)
    trial_days = models.IntegerField(default=14, help_text="Number of free trial days")
    
    # Core Limits
    max_users = models.IntegerField(default=1)
    max_companies = models.IntegerField(default=1)
    max_customers = models.IntegerField(default=100)
    max_storage_mb = models.IntegerField(default=500)

    class Meta:
        db_table = 'lumo_subscription_plan'
        ordering = ['sort_order']
        constraints = [
            models.UniqueConstraint(fields=['is_default'], condition=models.Q(is_default=True), name='only_one_default_plan')
        ]

    def __str__(self):
        return self.name

class PlanPrice(LumoBaseModel):
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE, related_name='prices')
    currency = models.ForeignKey('core_masterdata.Currency', on_delete=models.PROTECT, related_name='plan_prices')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    billing_cycle = models.CharField(max_length=20, choices=BillingCycle.choices)
    is_active = models.BooleanField(default=True)
    is_archived = models.BooleanField(default=False)
    gateway_price_id = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'lumo_plan_price'
        constraints = [
            models.UniqueConstraint(fields=['plan', 'currency', 'billing_cycle'], condition=models.Q(is_active=True, is_archived=False), name='uniq_active_price_per_plan_currency_cycle')
        ]

    def __str__(self):
        return f"{self.plan.name} - {self.amount} {self.currency.code}/{self.billing_cycle}"

class WorkspaceSubscription(LumoBaseModel):
    workspace = models.OneToOneField(Workspace, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    price = models.ForeignKey(PlanPrice, on_delete=models.PROTECT, null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=SubscriptionStatus.choices, default=SubscriptionStatus.TRIALING)
    
    current_period_start = models.DateTimeField(default=timezone.now)
    current_period_end = models.DateTimeField()
    trial_end = models.DateTimeField(null=True, blank=True)
    
    snapshot_plan_name = models.CharField(max_length=100, null=True, blank=True)
    snapshot_plan_code = models.CharField(max_length=50, null=True, blank=True)
    snapshot_price_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    snapshot_currency_code = models.CharField(max_length=10, null=True, blank=True)
    snapshot_billing_cycle = models.CharField(max_length=20, null=True, blank=True)
    snapshot_taken_at = models.DateTimeField(auto_now_add=True)

    cancel_at_period_end = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(null=True, blank=True)
    gateway_provider = models.CharField(max_length=50, null=True, blank=True)
    gateway_subscription_id = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'lumo_workspace_subscription'
        indexes = [
            models.Index(fields=['workspace', 'status', 'current_period_end']),
        ]

    @property
    def is_valid(self):
        if self.status not in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING, SubscriptionStatus.PAST_DUE]:
            return False
        return timezone.now() <= self.current_period_end

    def save(self, *args, **kwargs):
        if self.plan and self.plan.code != self.snapshot_plan_code:
            self.snapshot_plan_name = self.plan.name
            self.snapshot_plan_code = self.plan.code
        if self.price:
            if self.snapshot_price_amount != self.price.amount or self.snapshot_billing_cycle != self.price.billing_cycle:
                self.snapshot_price_amount = self.price.amount
                self.snapshot_currency_code = self.price.currency.code
                self.snapshot_billing_cycle = self.price.billing_cycle
                self.snapshot_taken_at = timezone.now()
        super().save(*args, **kwargs)