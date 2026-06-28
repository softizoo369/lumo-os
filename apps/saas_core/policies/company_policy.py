from django.urls import reverse
from apps.saas_core.services.usage_service import UsageService
from apps.saas_core.models.settings import GlobalConfiguration

class CompanyPolicy:
    """Rules and limitations regarding Company Creation."""

    @staticmethod
    def can_create(workspace) -> dict:
        global_config = GlobalConfiguration.get_config()
        current_usage = UsageService.get_current_usage(workspace)

        try:
            active_sub = workspace.subscription
        except:
            active_sub = None

        # 🟢 SCENARIO 1: NO ACTIVE SUBSCRIPTION (Applying SaaS Constitution)
        if not active_sub or not active_sub.is_valid:
            # Check if global config allows creating 1 company before payment
            if global_config.allow_company_before_subscription and current_usage.total_companies < 1:
                return {
                    "allowed": True, 
                    "message": "Proceed to create your first company profile."
                }
            else:
                return {
                    "allowed": False,
                    "redirect": reverse('saas_core:subscription_plans'), 
                    "message": "🔒 You need an active subscription to create more companies."
                }

        # 🟢 SCENARIO 2: ACTIVE SUBSCRIPTION (Enforcing Plan Limits)
        plan = active_sub.plan
        max_allowed_companies = plan.max_companies
        
        if current_usage.total_companies >= max_allowed_companies:
            return {
                "allowed": False,
                "redirect": reverse('saas_core:subscription_plans'),
                "message": f"Limit Reached! Your '{plan.name}' plan allows a maximum of {max_allowed_companies} company profiles. Please upgrade."
            }
            
        return {"allowed": True, "message": "Proceed to creation."}