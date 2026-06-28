import hashlib
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from apps.saas_core.models.invitation import WorkspaceInvitation, InvitationStatus
from apps.saas_core.models.tenant import WorkspaceMember
from apps.saas_core.services.audit_service import AuditService

User = get_user_model()

class InvitationAcceptanceService:
    """
    Handles the secure redemption of invitation tokens.
    Enforces atomic transactions and race-condition safety.
    """

    @staticmethod
    def get_invitation(raw_token):
        """Validates the raw token by matching its SHA-256 hash."""
        token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
        return WorkspaceInvitation.objects.filter(
            token_hash=token_hash, 
            status=InvitationStatus.PENDING
        ).first()

    @staticmethod
    @transaction.atomic
    def accept(request, invitation, user=None, password=None, first_name='', last_name=''):
        """Processes the acceptance securely within a DB lock."""
        
        # 1. Pessimistic Lock to prevent double-clicking issues
        invitation = WorkspaceInvitation.objects.select_for_update().get(id=invitation.id)

        # 2. Expiration & Status Checks
        if invitation.status != InvitationStatus.PENDING:
            raise ValueError("This invitation has already been used or revoked.")
            
        if invitation.expires_at < timezone.now():
            invitation.status = InvitationStatus.EXPIRED
            invitation.save()
            raise ValueError("This invitation has expired. Please request a new one.")

        # 3. Handle User Identity (Create new if not provided)
        if not user:
            user = User.objects.create_user(
                email=invitation.email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )

        # 4. Create Workspace Member (If not already a member)
        member, created = WorkspaceMember.objects.get_or_create(
            workspace=invitation.workspace,
            user=user,
            defaults={'role': invitation.role}
        )
        
        # If member existed but was deleted, restore them and update role
        if not created and member.is_deleted:
            member.is_deleted = False
            member.role = invitation.role
            member.save()

        # 5. Finalize Invitation Status
        invitation.status = InvitationStatus.ACCEPTED
        invitation.accepted_at = timezone.now()
        invitation.accepted_by = user
        invitation.save()

        # 6. Audit Logging
        AuditService.log(
            request=request,
            workspace=invitation.workspace,
            action='invitation.accepted',
            resource_type='WorkspaceMember',
            resource_id=str(member.id),
            metadata={'email': user.email, 'role_assigned': invitation.role.name},
            status='SUCCESS'
        )

        return user