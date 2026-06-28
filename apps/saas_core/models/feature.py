from django.db import models
from apps.saas_core.models.base import LumoBaseModel

class Feature(LumoBaseModel):
    """Global Registry of all Lumo OS Features (e.g., 'crm', 'advanced_reports')"""
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'lumo_feature'

    def __str__(self):
        return self.code

class PlanFeature(LumoBaseModel):
    """Maps Features to Subscription Plans with boolean flags or numeric limits."""
    plan = models.ForeignKey('saas_core.SubscriptionPlan', on_delete=models.CASCADE, related_name='plan_features')
    feature = models.ForeignKey(Feature, on_delete=models.CASCADE)
    
    is_enabled = models.BooleanField(default=True)
    limit = models.IntegerField(null=True, blank=True, help_text="Optional numeric limit specific to this feature")

    class Meta:
        db_table = 'lumo_plan_feature'
        unique_together = ('plan', 'feature')