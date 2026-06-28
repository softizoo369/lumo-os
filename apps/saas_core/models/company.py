from django.db import models
from apps.saas_core.models.base import TenantAwareModel

class Company(TenantAwareModel):
    """Legal Entity Model for ERP"""
    name = models.CharField(max_length=255)
    legal_name = models.CharField(max_length=255, null=True, blank=True)
    registration_number = models.CharField(max_length=100, null=True, blank=True)
    vat_number = models.CharField(max_length=50, null=True, blank=True)
    
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)
    website = models.URLField(null=True, blank=True)
    logo = models.ImageField(upload_to='company_logos/', null=True, blank=True)
    address = models.TextField(null=True, blank=True)

    # Masterdata Relations
    industry = models.ForeignKey('core_masterdata.Industry', on_delete=models.SET_NULL, null=True)
    country = models.ForeignKey('core_masterdata.Country', on_delete=models.SET_NULL, null=True)
    currency = models.ForeignKey('core_masterdata.Currency', on_delete=models.SET_NULL, null=True)
    timezone = models.ForeignKey('core_masterdata.Timezone', on_delete=models.SET_NULL, null=True)

    # Settings
    date_format = models.CharField(max_length=20, default='YYYY-MM-DD')
    time_format = models.CharField(max_length=10, default='24H')
    fiscal_year_start = models.CharField(max_length=5, default='01-01', help_text="MM-DD")
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'lumo_company'
        ordering = ['-is_default', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=["workspace_id"],
                condition=models.Q(is_default=True, is_deleted=False),
                name="one_default_company_per_workspace"
            )
        ]

    def __str__(self):
        return self.name

class CompanyAccess(TenantAwareModel):
    """Data Access Control Layer"""
    member = models.ForeignKey('saas_core.WorkspaceMember', on_delete=models.CASCADE, related_name='company_accesses')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='accessible_members')
    is_primary = models.BooleanField(default=False)

    class Meta:
        db_table = 'lumo_company_access'
        unique_together = ('member', 'company')

    def __str__(self):
        return f"{self.member.user.email} -> {self.company.name}"