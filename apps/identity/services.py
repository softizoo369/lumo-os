from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from apps.saas_core.models.tenant import Workspace, WorkspaceMember, WorkspaceStatus
from core.event_bus import event_bus

User = get_user_model()

class IdentityService:
    """
    Handles core Identity operations: Registration, Authentication, and User Management.
    """

    @staticmethod
    @transaction.atomic
    def register_tenant_owner(email: str, password: str, company_name: str) -> dict:
        email = email.lower().strip()

        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists.")

        # 1. Create User (Handling both Default Django User and Custom User safely)
        try:
            user = User.objects.create_user(email=email, password=password, username=email)
        except TypeError:
            user = User.objects.create_user(email=email, password=password)

        # 2. Delegate Workspace creation to the standalone method
        return IdentityService.create_workspace_for_user(user, company_name)

    @staticmethod
    @transaction.atomic
    def create_workspace_for_user(user, company_name: str) -> dict:
        """
        Creates a workspace for an existing user (Great for Superusers or second workspaces).
        """
        safe_domain = "".join(c for c in company_name.lower() if c.isalnum() or c == ' ')
        safe_domain = safe_domain.replace(' ', '-')
        unique_domain = f"{safe_domain}-{str(user.id)[:6]}"

        # 1. Create Workspace
        workspace = Workspace.objects.create(
            name=company_name,
            domain=unique_domain,
            status=WorkspaceStatus.ACTIVE
        )

        # 2. Assign Ownership Role
        from apps.identity.models import Role 
        owner_role, _ = Role.objects.get_or_create(
            workspace=workspace,
            name='OWNER',
            defaults={
                'is_system_default': True,
                'description': "Full access to the workspace."
            }
        )

        # 3. Create Membership
        WorkspaceMember.objects.create(
            workspace=workspace,
            user=user,
            role=owner_role
        )

        # 4. Trigger Events
        event_bus.publish(
            event_name='tenant_registered',
            payload={
                'user_id': str(user.id),
                'email': user.email,
                'workspace_id': str(workspace.id),
                'company_name': workspace.name,
                'domain': workspace.domain
            }
        )

        return {
            "user": user,
            "workspace": workspace
        }