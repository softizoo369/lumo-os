from django.db import models
from apps.saas_core.models.base import LumoBaseModel
from apps.saas_core.models.tenant import Workspace

class SubscriptionPlan(LumoBaseModel):
    """Defines the limitations and feature flags for different pricing tiers."""
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True, help_text="e.g., STARTER, BUSINESS, ENTERPRISE")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # 🛑 Resource Limits (The core of Lumo Brain)
    max_users = models.IntegerField(default=1)
    max_companies = models.IntegerField(default=1)
    max_customers = models.IntegerField(default=100)
    max_invoices = models.IntegerField(default=50)
    max_storage_mb = models.IntegerField(default=500)

    # 🚀 Feature Flags
    features = models.JSONField(default=dict, help_text='e.g., {"crm_enabled": true, "advanced_reports": false}')

    class Meta:
        db_table = 'lumo_subscription_plan'

    def __str__(self):
        return self.name

class WorkspaceSubscription(LumoBaseModel):
    """Links a Workspace to a specific Subscription Plan."""
    workspace = models.OneToOneField(Workspace, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.RESTRICT)
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'lumo_workspace_subscription'