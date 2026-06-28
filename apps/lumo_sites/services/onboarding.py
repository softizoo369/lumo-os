from django.db import transaction
from apps.saas_core.models.tenant import Workspace
from apps.lumo_sites.models import SiteKitVersion
from apps.lumo_sites.services.provisioning import SiteProvisioningService

class WorkspaceOnboardingService:
    """
    Enterprise Orchestrator: Explicitly handles the entire lifecycle of a new client onboarding.
    No signals, no hidden magic. Everything happens in one strict transaction.
    """

    @staticmethod
    @transaction.atomic
    def onboard_new_client(owner_user, company_name, selected_kit_id=None):
        
        # 1. Create the Workspace (Tenant)
        workspace = Workspace.objects.create(
            name=company_name,
            # slug=slugify(company_name), # Assuming slug generation is handled
            # owner=owner_user
        )

        # 2. Create Subscription & Billing Setup
        # SubscriptionProvisioningService.setup_trial(workspace=workspace, plan="STARTER")

        # 3. Provision the Website Ecosystem (Calling our previously built service)
        kit_version = None
        if selected_kit_id:
            kit_version = SiteKitVersion.objects.filter(id=selected_kit_id).first()
        
        # Fallback to the default Kit if none selected
        if not kit_version:
            kit_version = SiteKitVersion.objects.first()

        if kit_version:
            SiteProvisioningService.provision_new_site(
                workspace=workspace, 
                active_kit_version=kit_version
            )

        # 4. Create Default Roles & Permissions
        # RoleProvisioningService.create_default_roles(workspace=workspace)

        # 5. Log the Audit Event
        # AuditLogger.log(action="WORKSPACE_ONBOARDED", workspace=workspace, user=owner_user)

        return workspace