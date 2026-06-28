from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.saas_core.models.tenant import Workspace
from apps.saas_core.services.subscription_service import SubscriptionService
from core.context import system_context
from apps.saas_core.services.settings_service import SettingsService

@receiver(post_save, sender=Workspace)
def setup_new_workspace_subscription(sender, instance, created, **kwargs):
    """
    Triggers the Subscription Provisioning when a new Workspace is created.
    Delegates the strict Invariant validation to the SubscriptionService.
    """
    if created:
        with system_context():
            SubscriptionService.assign_default_plan(instance)

@receiver(post_save, sender=Workspace)
def initialize_workspace_dependencies(sender, instance, created, **kwargs):
    if created:
        with system_context():
            # 1. Assign Default Subscription Plan
            SubscriptionService.assign_default_plan(instance)
            
            # 2. 🟢 NEW: Initialize Tenant Preferences Automatically
            SettingsService.get_workspace_preferences(instance)