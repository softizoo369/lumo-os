from apps.saas_core.models.feature import PlanFeature

class FeatureService:
    @staticmethod
    def get_feature_details(workspace, feature_code: str):
        """Returns the PlanFeature object if the feature is enabled for the workspace's active plan."""
        try:
            active_sub = workspace.subscription
            if active_sub.status != 'ACTIVE':
                return None
        except:
            return None

        # Fetch the specific feature for this plan
        plan_feature = PlanFeature.objects.filter(
            plan=active_sub.plan,
            feature__code=feature_code,
            is_enabled=True
        ).first()
        return plan_feature

    @staticmethod
    def has_feature(workspace, feature_code: str) -> bool:
        """Simple boolean check if a feature is available."""
        return FeatureService.get_feature_details(workspace, feature_code) is not None