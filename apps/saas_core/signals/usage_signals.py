from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from apps.saas_core.models.tenant import Workspace, WorkspaceMember
from apps.saas_core.models.company import Company
from apps.saas_core.models.finance import PaymentTransaction, BillingProfile
from apps.lumo_sites.models import MediaAsset # 🟢 NEW IMPORT
from apps.saas_core.services.usage_service import UsageService
from core.context import system_context


def _get_workspace_safely(instance):
    """
    🟢 THE ACCURATE FIX: 
    Resolves the workspace relation including TenantAwareModel 
    which uses 'workspace_id' (UUIDField) instead of a direct ForeignKey.
    """
    if hasattr(instance, 'workspace'):
        return instance.workspace
    if hasattr(instance, 'tenant'):
        return instance.tenant
        
    # 🟢 NEW: Fetch Workspace securely if only workspace_id exists
    if hasattr(instance, 'workspace_id') and instance.workspace_id:
        return Workspace.objects.filter(id=instance.workspace_id).first()
        
    return None

@receiver(post_save, sender=WorkspaceMember)
def track_user_creation(sender, instance, created, **kwargs):
    """Tracks when a user is added to a workspace."""
    workspace = _get_workspace_safely(instance)
    if not workspace:
        return

    with system_context():
        if created and not getattr(instance, 'is_deleted', False):
            UsageService.increment_usage(workspace, 'total_users')
        elif not created and getattr(instance, 'tracker', None) and instance.tracker.has_changed('is_deleted'):
            if instance.is_deleted:
                UsageService.decrement_usage(workspace, 'total_users')
            else:
                UsageService.increment_usage(workspace, 'total_users')

@receiver(post_save, sender=Company)
def track_company_creation(sender, instance, created, **kwargs):
    """Tracks when a company is added to a workspace."""
    workspace = _get_workspace_safely(instance)
    if not workspace:
        return

    with system_context():
        if created and not getattr(instance, 'is_deleted', False):
            UsageService.increment_usage(workspace, 'total_companies')
        elif not created and getattr(instance, 'tracker', None) and instance.tracker.has_changed('is_deleted'):
            if instance.is_deleted:
                UsageService.decrement_usage(workspace, 'total_companies')
            else:
                UsageService.increment_usage(workspace, 'total_companies')
    
    UsageService.sync_workspace_storage(workspace)

# 🟢 THE MASTER STORAGE SIGNAL: Tracks all file-related models instantly
@receiver([post_save, post_delete], sender=PaymentTransaction)
@receiver([post_save, post_delete], sender=BillingProfile)
@receiver([post_save, post_delete], sender=MediaAsset) # 🟢 Watches Website Media Uploads/Deletes
@receiver([post_save, post_delete], sender=Company) # 🟢 Watches Logo Uploads
def track_file_uploads(sender, instance, **kwargs):
    """Automatically syncs storage MB whenever ANY file is uploaded or deleted."""
    workspace = _get_workspace_safely(instance)
    if workspace:
        UsageService.sync_workspace_storage(workspace)