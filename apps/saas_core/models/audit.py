from django.db import models
from django.conf import settings
from apps.saas_core.models.base import LumoBaseModel

class AuditLog(LumoBaseModel):
    """
    Tracks 'Who did What, When, and Where'.
    Essential for SOC2 Compliance and debugging.
    """
    workspace = models.ForeignKey(
        'saas_core.Workspace', 
        on_delete=models.CASCADE, 
        related_name='audit_logs',
        db_index=True
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )

    action = models.CharField(max_length=100, db_index=True) # e.g., 'role.create', 'company.delete'
    resource_type = models.CharField(max_length=100) # e.g., 'Role', 'Company'
    resource_id = models.CharField(max_length=255) # UUID of the affected resource

    # Security Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

    # Context Data (e.g., old values, new values, or specific context)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'lumo_audit_log'
        ordering = ['-created_at']
        indexes = [
            # High-performance search composites
            models.Index(fields=['workspace', '-created_at']),
            models.Index(fields=['actor', '-created_at']),
            models.Index(fields=['action', '-created_at']),
        ]

    def __str__(self):
        return f"{self.actor} -> {self.action} on {self.resource_type}"