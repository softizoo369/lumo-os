import uuid
from django.db import models
from apps.saas_core.models.base import LumoBaseModel

class Menu(models.Model):
    """
    Layer 2: Database Menu Registry (Global Platform Data).
    These are the master menus. They are NOT tenant-specific.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=100, unique=True, help_text="e.g., crm_dashboard")
    
    icon = models.CharField(max_length=100, default="bi-circle")
    url = models.CharField(max_length=255, default="#")
    
    # Self-referencing ForeignKey for Sub-menus
    parent = models.ForeignKey(
        'self', 
        null=True, blank=True, 
        on_delete=models.CASCADE, 
        related_name='children'
    )
    
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    # Layer 4 Future-proofing: Which feature unlocks this menu?
    required_feature_code = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'lumo_menu_registry'
        ordering = ['sort_order']

    def __str__(self):
        return f"{self.name} ({self.code})"


class RoleMenuPermission(LumoBaseModel):
    """
    Layer 3: Permission Layer (Tenant-Specific via Role).
    Defines which Role inside a Workspace can see which Menu.
    """
    role = models.ForeignKey('identity.Role', on_delete=models.CASCADE, related_name='menu_permissions')
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE)
    can_view = models.BooleanField(default=True)

    class Meta:
        db_table = 'lumo_role_menu_permission'
        unique_together = ('role', 'menu') # A role can only have one permission record per menu

    def __str__(self):
        return f"{self.role.name} -> {self.menu.name}: {self.can_view}"