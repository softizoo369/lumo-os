from django.db import models
from apps.saas_core.models.base import TenantAwareModel

class WorkspaceUsage(TenantAwareModel):
    """Tracks real-time usage via Signals to prevent costly .count() queries."""
    
    total_users = models.IntegerField(default=0)
    total_companies = models.IntegerField(default=0)
    total_customers = models.IntegerField(default=0)
    total_invoices = models.IntegerField(default=0)
    total_storage_mb = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    api_calls_this_month = models.IntegerField(default=0)
    
    last_recalculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'lumo_workspace_usage'