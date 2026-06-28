import secrets
import hashlib
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from apps.saas_core.models.invitation import WorkspaceInvitation, InvitationStatus
from apps.saas_core.services.audit_service import AuditService

class InvitationService:
    """
    Enterprise Invitation Service.
    Handles secure token generation, hashing, and concurrent request protection.
    """
    INVITATION_EXPIRY_DAYS = 7

    @staticmethod
    def _generate_secure_token():
        """Generates a raw token for email and a SHA-256 hash for the DB."""
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
        return raw_token, token_hash

    @staticmethod
    def create_or_resend_invitation(request, workspace, email, role):
        email = email.lower().strip()
        
        # 🟢 Enterprise Standard: Atomic Transaction to prevent Race Conditions
        with transaction.atomic():
            
            # 1. Pessimistic Lock: Check if a pending invite already exists
            existing_invite = WorkspaceInvitation.objects.select_for_update().filter(
                workspace=workspace, 
                email=email, 
                status=InvitationStatus.PENDING
            ).first()

            # 2. Token Generation
            raw_token, token_hash = InvitationService._generate_secure_token()
            expiry_date = timezone.now() + timedelta(days=InvitationService.INVITATION_EXPIRY_DAYS)

            if existing_invite:
                # 🔄 RESEND POLICY: Update existing, don't create duplicate
                existing_invite.token_hash = token_hash
                existing_invite.role = role # Update role if admin changed their mind
                existing_invite.expires_at = expiry_date
                existing_invite.send_count += 1
                existing_invite.last_sent_at = timezone.now()
                existing_invite.save()
                
                invitation = existing_invite
                action_log = 'invitation.resent'
            else:
                # ✨ NEW INVITE POLICY
                invitation = WorkspaceInvitation.objects.create(
                    workspace=workspace,
                    email=email,
                    role=role,
                    token_hash=token_hash,
                    expires_at=expiry_date,
                    invited_by=request.user
                )
                action_log = 'invitation.created'

            # 3. Audit Logging
            AuditService.log(
                request=request,
                workspace=workspace,
                action=action_log,
                resource_type='WorkspaceInvitation',
                resource_id=str(invitation.id),
                metadata={'email': email, 'role_code': role.name, 'send_count': invitation.send_count},
                status='SUCCESS'
            )

            # 🔴 CRITICAL: Return the RAW TOKEN to the View layer so it can be emailed.
            # The raw token is NEVER saved in the database!
            return invitation, raw_token