from django.db import models
from django.conf import settings
from apps.saas_core.models.base import LumoBaseModel

# 🟢 SAAS STATE MACHINE: Workspace Level
class WorkspaceStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    SUSPENDED = 'SUSPENDED', 'Suspended'

class SuspensionReason(models.TextChoices):
    PAYMENT_FAILURE = 'PAYMENT_FAILURE', 'Payment Failure'
    ABUSE = 'ABUSE', 'Policy Abuse / Terms Violation'
    ADMIN = 'ADMIN', 'Admin Action'

class Workspace(LumoBaseModel):
    name = models.CharField(max_length=255)
    domain = models.CharField(max_length=255, unique=True, db_index=True)
    
    status = models.CharField(
        max_length=20, 
        choices=WorkspaceStatus.choices, 
        default=WorkspaceStatus.ACTIVE,
        db_index=True
    )
    
    # 🟢 Added Suspension Reason
    suspension_reason = models.CharField(
        max_length=50, 
        choices=SuspensionReason.choices, 
        null=True, blank=True
    )
    
    timezone = models.CharField(max_length=50, default='UTC')
    currency = models.CharField(max_length=3, default='USD')

    @property
    def owner(self):
        """Returns the user who owns/created this workspace."""
        if hasattr(self, 'created_by') and self.created_by:
            return self.created_by
        first_member = self.members.select_related('user').first()
        return first_member.user if first_member else None

    class Meta:
        db_table = 'lumo_workspace'
        indexes = [
            models.Index(fields=['status', 'is_deleted']),
        ]

    def __str__(self):
        return self.name

class WorkspaceMember(LumoBaseModel):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, db_index=True, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='workspace_memberships')
    role = models.ForeignKey('identity.Role', on_delete=models.SET_NULL, null=True, related_name='role_members')

    class Meta:
        db_table = 'lumo_workspace_member'
        constraints = [
            models.UniqueConstraint(fields=['workspace', 'user'], name='unique_workspace_user')
        ]

    def __str__(self):
        return f"{self.user.email} -> {self.workspace.name}"