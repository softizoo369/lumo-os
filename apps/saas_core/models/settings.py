# apps/saas_core/models/settings.py
from django.db import models
from apps.saas_core.models.base import LumoBaseModel
from apps.saas_core.models.tenant import Workspace

# ==========================================
# 1. GLOBAL SYSTEM CONFIGURATION (THE CONSTITUTION)
# ==========================================
# apps/saas_core/models/settings.py
class GlobalConfiguration(LumoBaseModel):
    """
    Singleton Model: Controls the fundamental behavior of the entire SaaS platform.
    """
    # Core Identity
    site_name = models.CharField(max_length=100, default="Lumo OS")
    support_email = models.EmailField(default="support@lumodigital.co")
    default_timezone = models.CharField(max_length=50, default="Asia/Dhaka") # Kept explicitly as CharField
    maintenance_mode = models.BooleanField(default=False)
    
    # 🟢 PHASE 1 ADDITION: Platform Domain Routing (Additive)
    base_domain = models.CharField(max_length=255, default="lumodigital.co", help_text="e.g., lumodigital.co")
    app_domain = models.CharField(max_length=255, default="app.lumodigital.co", help_text="e.g., app.lumodigital.co")
    api_domain = models.CharField(max_length=255, default="api.lumodigital.co")
    media_domain = models.CharField(max_length=255, default="media.lumodigital.co")
    cdn_domain = models.CharField(max_length=255, default="cdn.lumodigital.co")
    portal_prefix = models.CharField(max_length=50, default="portal", help_text="e.g., 'portal' -> portal.sauda.com")

    # 🟢 SAAS CONSTITUTION v1 SETTINGS
    allow_company_before_subscription = models.BooleanField(default=True, help_text="Allow creating 1 company before paying.")
    dashboard_requires_active_subscription = models.BooleanField(default=True, help_text="Lock dashboard if no active plan.")
    trial_enabled = models.BooleanField(default=False, help_text="Global switch to enable/disable trials.")
    grace_period_days = models.IntegerField(default=7, help_text="Days before suspension after payment fails.")
    max_payment_retries = models.IntegerField(default=3, help_text="Dunning engine retry limit.")

    class Meta:
        db_table = 'lumo_global_config'
        verbose_name = 'Global Configuration'

    def save(self, *args, **kwargs):
        """Forces Singleton behavior (always ID 1)"""
        self.pk = 1 
        # 🟢 Safely clean domains without breaking existing logic
        for field in ['base_domain', 'app_domain', 'api_domain', 'media_domain', 'cdn_domain']:
            val = getattr(self, field, "")
            if val:
                val = val.replace('https://', '').replace('http://', '').strip('/')
                setattr(self, field, val)
        super().save(*args, **kwargs)

    @classmethod
    def get_config(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f"Global Config: {self.site_name}"

# ==========================================
# 2. WORKSPACE PREFERENCE
# ==========================================
class WorkspacePreference(LumoBaseModel):
    workspace = models.OneToOneField(Workspace, on_delete=models.CASCADE, related_name='preferences')
    invoice_prefix = models.CharField(max_length=10, default="INV-", help_text="e.g. INV-2026-")
    timezone = models.CharField(max_length=50, default="Asia/Dhaka")
    date_format = models.CharField(max_length=20, default="YYYY-MM-DD")
    theme_color = models.CharField(max_length=20, default="default")
    reply_to_email = models.EmailField(blank=True, null=True, help_text="Custom email for sending invoices")

    class Meta:
        db_table = 'lumo_workspace_preference'

    def __str__(self):
        return f"Preferences for {self.workspace.name}"

# ==========================================
# 3. PAYMENT GATEWAY CREDENTIALS
# ==========================================
class PaymentGatewayConfig(LumoBaseModel):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='gateway_credentials')
    gateway = models.ForeignKey('saas_core.PaymentGateway', on_delete=models.CASCADE, related_name='tenant_configs')
    
    is_active = models.BooleanField(default=False)
    is_test_mode = models.BooleanField(default=True)

    api_key = models.CharField(max_length=255, blank=True, null=True)
    api_secret = models.CharField(max_length=255, blank=True, null=True)
    webhook_secret = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'lumo_payment_gateway_config'
        constraints = [
            models.UniqueConstraint(fields=['workspace', 'gateway'], name='unique_workspace_gateway_config')
        ]

    def __str__(self):
        mode = "TEST" if self.is_test_mode else "LIVE"
        return f"{self.gateway.name} ({mode}) - {self.workspace.name}"

