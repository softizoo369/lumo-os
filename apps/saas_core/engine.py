from apps.saas_core.models.company import Company

class LumoBrain:
    """
    The Business Operating System With A Built-In Resource Control Brain.
    Centralized validation for limits, prerequisites, and features.
    """
    
    @staticmethod
    def can_create_company(workspace) -> dict:
        """Checks if the workspace has reached its company limit based on the active plan."""
        
        # 1. Check Subscription Status
        if not hasattr(workspace, 'subscription') or not workspace.subscription.is_active:
            return {
                "allowed": False,
                "redirect": "/upgrade/",
                "message": "You don't have an active subscription."
            }
            
        # 2. Check Resource Limit
        current_company_count = Company.objects.filter(workspace_id=workspace.id).count()
        max_allowed = workspace.subscription.plan.max_companies
        
        if current_company_count >= max_allowed:
            return {
                "allowed": False,
                "redirect": "/upgrade/",
                "message": f"Limit Reached! Your {workspace.subscription.plan.name} plan allows maximum {max_allowed} companies."
            }
            
        return {"allowed": True, "message": "Success"}