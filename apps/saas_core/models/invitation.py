from django.db import models
from django.db.models import Q
from django.conf import settings
from apps.saas_core.models.base import LumoBaseModel

# 🟢 1. Invitation State Enum Class (Type Safety & No Magic Strings)
class InvitationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    ACCEPTED = "ACCEPTED", "Accepted"
    EXPIRED = "EXPIRED", "Expired"
    REVOKED = "REVOKED", "Revoked"

class WorkspaceInvitation(LumoBaseModel):
    """
    Enterprise-grade Workspace Invitation Model.
    Handles identity, state machine, and DB-level constraints.
    """
    workspace = models.ForeignKey(
        'saas_core.Workspace', 
        on_delete=models.CASCADE, 
        related_name='invitations'
    )
    email = models.EmailField(db_index=True)
    
    # 🟢 Role ID Snapshot (To be validated during acceptance)
    role = models.ForeignKey(
        'identity.Role', 
        on_delete=models.CASCADE,
        related_name='invitations'
    )
    
    # 🟢 Security (Token Hash instead of Raw Token)
    token_hash = models.CharField(max_length=128, unique=True, db_index=True)
    status = models.CharField(
        max_length=20, 
        choices=InvitationStatus.choices, 
        default=InvitationStatus.PENDING,
        db_index=True
    )
    expires_at = models.DateTimeField()
    
    # 🟢 Tracking & Audit
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='sent_invites'
    )
    accepted_at = models.DateTimeField(null=True, blank=True)
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='accepted_invites'
    )
    
    # 🟢 Delivery & Metrics (Enhancement #8)
    send_count = models.IntegerField(default=1)
    last_sent_at = models.DateTimeField(auto_now_add=True)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    last_email_error = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'lumo_workspace_invitation'
        ordering = ['-created_at']
        
        # 🟢 2 & 3. Database-Level Pending Invite Protection
        constraints = [
            models.UniqueConstraint(
                fields=['workspace', 'email'],
                condition=Q(status='PENDING'),
                name='unique_pending_invite_per_workspace'
            )
        ]
        
        # High-performance indexes for background jobs and UI
        indexes = [
            models.Index(fields=['workspace', 'status']),
            models.Index(fields=['email', 'status']),
        ]

    def __str__(self):
        return f"{self.email} -> {self.workspace.company_name} ({self.status})"