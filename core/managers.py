from django.db import models
from django.core.exceptions import PermissionDenied
from core.context import get_workspace, is_system_override

class TenantManager(models.Manager):
    """
    Strict Manager that automatically filters data based on the active workspace.
    Prevents cross-tenant data leaks at the ORM level.
    """
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 1. System/Admin Override (e.g., Global analytics or Cron jobs)
        if is_system_override():
            return queryset
            
        # 2. Get active workspace from contextvars
        workspace_id = get_workspace()
        
        # 3. Strict Safety Net
        if not workspace_id:
            raise PermissionDenied(
                "CRITICAL: Attempted to access tenant data without an active workspace context. "
                "Ensure TenantMiddleware is running or use system_context() for background jobs."
            )
            
        # 4. Enforce Isolation
        return queryset.filter(workspace_id=workspace_id)