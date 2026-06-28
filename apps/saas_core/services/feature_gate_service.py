from apps.saas_core.models.tenant import Workspace, WorkspaceStatus
from apps.saas_core.services.usage_service import UsageService
from apps.saas_core.services.feature_service import FeatureService

class FeatureGateService:
    """Enterprise SaaS Enforcement Engine."""
    
    @staticmethod
    def check_workspace_access(workspace: Workspace) -> dict:
        """Global Gate: Checks if the workspace is allowed to access the SaaS."""
        if workspace.status == WorkspaceStatus.SUSPENDED:
            return {"allowed": False, "reason": "SUSPENDED", "message": "Your workspace has been suspended by administration."}
        if workspace.status == WorkspaceStatus.ARCHIVED:
            return {"allowed": False, "reason": "ARCHIVED", "message": "Your workspace is archived and read-only."}
        return {"allowed": True}

    @staticmethod
    def check_limit(workspace: Workspace, limit_name: str) -> dict:
        """Action Gate: Checks if a specific action is within dynamic limits."""
        try:
            active_sub = workspace.subscription
        except:
            active_sub = None
            
        plan_name = active_sub.plan.name if active_sub else "Free Tier"
        
        # Fetch dynamic limit
        feature_details = FeatureService.get_feature_details(workspace, limit_name)
        limit_value = feature_details.limit if feature_details and feature_details.limit else 1
        
        usage = UsageService.get_current_usage(workspace)
        usage_field = limit_name.replace('max_', 'total_')
        current_usage = getattr(usage, usage_field, 0)
        
        if current_usage >= limit_value:
            clean_name = limit_name.replace('max_', '').replace('_', ' ').title()
            return {
                "allowed": False, 
                "message": f"Upgrade Required: You have reached your limit of {limit_value} {clean_name} on the {plan_name}."
            }
        return {"allowed": True}