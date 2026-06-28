from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from apps.saas_core.models.base import LumoBaseModel

# ==============================================================================
# USER MANAGER (Email as Primary Identifier)
# ==============================================================================
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('The Email field must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('account_status', AccountStatus.ACTIVE)
        return self.create_user(email, password, **extra_fields)

# ==============================================================================
# ENUMS (Rule: Never use Boolean for Status)
# ==============================================================================
class AccountStatus(models.TextChoices):
    PENDING_VERIFICATION = 'PENDING', _('Pending Verification')
    ACTIVE = 'ACTIVE', _('Active')
    SUSPENDED = 'SUSPENDED', _('Suspended')

# ==============================================================================
# IDENTITY MODELS
# ==============================================================================
class User(AbstractUser, LumoBaseModel):
    """
    Global Identity Model. 
    Users exist at the platform level, NOT the tenant level.
    """
    username = None  # We strictly use Email for SaaS login
    email = models.EmailField(_('email address'), unique=True, db_index=True)
    
    account_status = models.CharField(
        max_length=30, 
        choices=AccountStatus.choices, 
        default=AccountStatus.PENDING_VERIFICATION,
        db_index=True
    )
    
    # Security Tracking (Foundation for Lumo Brain)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    failed_login_attempts = models.PositiveIntegerField(default=0)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        db_table = 'lumo_identity_user'
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def __str__(self):
        return self.email


# ==============================================================================
# PLATFORM REGISTRY (Global Metadata for Authorization)
# ==============================================================================

class Feature(LumoBaseModel):
    """
    Groups permissions and links to the future App Store / Module Registry.
    e.g., name="Company Management", code="company"
    """
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'lumo_feature_registry'

    def __str__(self):
        return self.name

class Permission(LumoBaseModel):
    """
    Atomic actions within a feature.
    e.g., feature=company, code="company.create"
    """
    feature = models.ForeignKey(Feature, on_delete=models.CASCADE, related_name='permissions')
    code = models.CharField(max_length=100, unique=True, db_index=True)
    name = models.CharField(max_length=150) # e.g., "Create Company"
    
    class Meta:
        db_table = 'lumo_permission_registry'

    def __str__(self):
        return self.code

# ==============================================================================
# IDENTITY MODELS (Tenant Scoped)
# ==============================================================================

class Role(LumoBaseModel):
    workspace = models.ForeignKey('saas_core.Workspace', on_delete=models.CASCADE, related_name='roles')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # 🟢 Only the new Relational RBAC Field remains
    permissions_m2m = models.ManyToManyField(Permission, blank=True, related_name='roles')
    
    is_system_default = models.BooleanField(default=False) 

    class Meta:
        db_table = 'lumo_identity_role'
        unique_together = [('workspace', 'name')] 
        indexes = [
            models.Index(fields=['workspace', 'is_deleted']),
        ]

    def __str__(self):
        return f"{self.name} - {self.workspace_id}"
    
    def soft_delete(self, user=None):
        if self.is_system_default:
            raise ValueError("System default roles cannot be deleted.")
        super().soft_delete(user)