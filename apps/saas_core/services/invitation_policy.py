from apps.saas_core.models.tenant import WorkspaceMember
from apps.saas_core.models.invitation import WorkspaceInvitation, InvitationStatus
from apps.saas_core.services.usage_service import UsageService

class InvitationPolicyService:
    """Enforces business rules and billing limits before an invitation is sent."""
    
    @staticmethod
    def check_eligibility(workspace):
        if getattr(workspace, 'is_deleted', False):
            raise ValueError("Invitations cannot be sent. This workspace is currently deleted or inactive.")
            
        # 🟢 THE FIX: Fetch dynamic limit from the Active Plan
        try:
            active_sub = workspace.subscription
            plan_limit = active_sub.plan.max_users
            plan_name = active_sub.plan.name
        except:
            plan_limit = 1
            plan_name = "Free Tier"
            
        # 🟢 THE FIX: Check accurate usage (Current + Pending)
        current_usage = UsageService.get_current_usage(workspace)
        pending_invites = WorkspaceInvitation.objects.filter(workspace=workspace, status=InvitationStatus.PENDING).count()
        
        total_allocated_seats = current_usage.total_users + pending_invites
        
        if total_allocated_seats >= plan_limit:
            raise ValueError(f"Limit reached! Your '{plan_name}' plan allows a maximum of {plan_limit} users. Please upgrade to invite more.")
            
        return True