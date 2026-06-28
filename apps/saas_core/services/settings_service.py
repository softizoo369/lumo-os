from django.core.cache import cache
from apps.saas_core.models.settings import GlobalConfiguration, WorkspacePreference, PaymentGatewayConfig

class SettingsService:
    """
    Enterprise Settings Engine with Caching Layer.
    Ensures zero DB hits for repeated settings queries.
    """
    CACHE_TTL = 60 * 60 * 24  # Cache for 24 hours

    # ==========================================
    # GLOBAL SETTINGS METHODS
    # ==========================================
    @staticmethod
    def get_global_config():
        """Fetches Global Config with Caching."""
        cache_key = "global_saas_config"
        config = cache.get(cache_key)
        
        if not config:
            config = GlobalConfiguration.get_config()
            cache.set(cache_key, config, SettingsService.CACHE_TTL)
            
        return config

    @staticmethod
    def clear_global_cache():
        """Clears global cache (Call this automatically when Superadmin updates config)."""
        cache.delete("global_saas_config")

    # ==========================================
    # TENANT SETTINGS METHODS
    # ==========================================
    @staticmethod
    def get_workspace_preferences(workspace):
        """Fetches Tenant-specific settings with Caching."""
        if not workspace:
            return None
            
        cache_key = f"workspace_pref_{workspace.id}"
        prefs = cache.get(cache_key)
        
        if not prefs:
            # If a preference row doesn't exist yet, automatically create one with defaults
            prefs, created = WorkspacePreference.objects.get_or_create(workspace=workspace)
            cache.set(cache_key, prefs, SettingsService.CACHE_TTL)
            
        return prefs

    @staticmethod
    def clear_workspace_cache(workspace):
        """Clears specific workspace cache (Call this when a tenant updates their preferences)."""
        if workspace:
            cache.delete(f"workspace_pref_{workspace.id}")

    # ==========================================
    # INTEGRATION & PAYMENT METHODS
    # ==========================================
    @staticmethod
    def get_active_payment_gateways(workspace):
        """
        Returns all ACTIVE payment gateways for a specific tenant.
        We strictly do NOT cache payment credentials for security reasons.
        """
        if not workspace:
            return []
            
        return PaymentGatewayConfig.objects.filter(
            workspace=workspace, 
            is_active=True
        ).select_related('gateway')