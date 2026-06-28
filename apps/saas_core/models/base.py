import uuid
from django.db import models
from django.utils import timezone
from core.managers import TenantManager

class SoftDeleteManager(TenantManager):
    """Overrides the default manager to hide soft-deleted records."""
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

class LumoBaseModel(models.Model):
    """
    Absolute Base Model: Handles ID, Timestamps, Audit tracking, and Soft Delete.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Soft Delete Standard
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    # Basic Audit (Who did what - ID references to avoid circular imports)
    created_by_id = models.UUIDField(null=True, blank=True)
    updated_by_id = models.UUIDField(null=True, blank=True)
    deleted_by_id = models.UUIDField(null=True, blank=True)

    class Meta:
        abstract = True

    def delete(self, user_id=None, hard=False):
        """Override delete to perform Soft Delete by default."""
        if hard:
            super().delete()
        else:
            self.is_deleted = True
            self.deleted_at = timezone.now()
            if user_id:
                self.deleted_by_id = user_id
            self.save()

    def restore(self):
        """Restore a soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by_id = None
        self.save()


class TenantAwareModel(LumoBaseModel):
    """
    Tenant Base Model: Handles Workspace Isolation + Everything in LumoBaseModel.
    """
    workspace_id = models.UUIDField(db_index=True)
    
    # 1. Default manager (Isolated + Soft Delete filtered)
    objects = SoftDeleteManager()
    
    # 2. Manager for finding deleted items (e.g., Recycle Bin)
    deleted_objects = TenantManager()
    
    # 3. Super Admin manager (Bypasses everything)
    all_objects = models.Manager()

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['workspace_id', 'is_deleted']),
        ]