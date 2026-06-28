from django.db import models
from django.conf import settings
from apps.saas_core.models.base import LumoBaseModel
from apps.saas_core.models.tenant import Workspace
from django.urls import reverse, NoReverseMatch
# 🟢 FIX: কাস্টম TenantManager ইমপোর্ট
from core.managers import TenantManager 

class DataSourceType(models.TextChoices):
    MANUAL = 'MANUAL', 'Manual Input'
    PRODUCTS = 'PRODUCTS', 'E-commerce Products'
    POSTS = 'POSTS', 'Blog Posts'

class DomainStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending Verification'
    VERIFIED = 'VERIFIED', 'Verified & Active'
    FAILED = 'FAILED', 'Verification Failed'

class StorageProvider(models.TextChoices):
    LOCAL = 'LOCAL', 'Local Storage'
    S3 = 'S3', 'AWS S3'
    R2 = 'R2', 'Cloudflare R2'

class DeploymentStatus(models.TextChoices):
    QUEUED = 'QUEUED', 'Queued for Build'
    BUILDING = 'BUILDING', 'Building & Purging Cache'
    PUBLISHED = 'PUBLISHED', 'Live & Published'
    FAILED = 'FAILED', 'Deployment Failed'

class RevisionStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    PUBLISHED = 'PUBLISHED', 'Published (Live)'
    ARCHIVED = 'ARCHIVED', 'Archived'

# --- 1. DOMAIN LAYER ---
class SiteDomain(LumoBaseModel):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='domains')
    domain_name = models.CharField(max_length=255, unique=True, db_index=True)
    is_primary = models.BooleanField(default=False)
    is_subdomain = models.BooleanField(default=False)
    ssl_status = models.BooleanField(default=False)

    objects = TenantManager()

    class Meta:
        db_table = 'lumo_sites_domain'
        constraints = [models.UniqueConstraint(fields=['workspace'], condition=models.Q(is_primary=True), name='one_primary_domain')]

    def __str__(self):
        return self.domain_name

class DomainVerification(LumoBaseModel):
    domain = models.OneToOneField(SiteDomain, on_delete=models.CASCADE, related_name='verification')
    cloudflare_id = models.CharField(max_length=100, blank=True, null=True)
    ownership_txt_name = models.CharField(max_length=255, blank=True, null=True)
    ownership_txt_value = models.TextField(blank=True, null=True)
    ssl_txt_name = models.CharField(max_length=255, blank=True, null=True)
    ssl_txt_value = models.TextField(blank=True, null=True)
    verification_token = models.CharField(max_length=100, blank=True, null=True)
    dns_target = models.CharField(max_length=255, default="cname.lumo-os.com")
    status = models.CharField(max_length=20, choices=DomainStatus.choices, default=DomainStatus.PENDING)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'lumo_sites_domain_verification'

    def __str__(self):
        return f"Verify: {self.domain.domain_name}"

# --- 2. MEDIA & ASSET LIBRARY ---
class MediaAsset(LumoBaseModel):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='media_assets')
    file_path = models.FileField(upload_to='tenant_media/%Y/%m/')
    storage_provider = models.CharField(max_length=20, choices=StorageProvider.choices, default=StorageProvider.LOCAL)
    checksum = models.CharField(max_length=128, db_index=True)
    mime_type = models.CharField(max_length=100)
    file_size_kb = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_public = models.BooleanField(default=True)
    alt_text = models.CharField(max_length=255, blank=True, null=True)
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)

    objects = TenantManager()

    class Meta:
        db_table = 'lumo_sites_media'

    def __str__(self):
        return f"Media: {self.file_path.name}"

# --- 3. ATOMIC SECTIONS & THEMES ---
class ThemePreset(LumoBaseModel):
    name = models.CharField(max_length=100)
    primary_color = models.CharField(max_length=20, default="#000000")
    secondary_color = models.CharField(max_length=20, default="#ffffff")
    heading_font = models.CharField(max_length=100, default="Inter")
    body_font = models.CharField(max_length=100, default="Inter")
    border_radius = models.CharField(max_length=20, default="8px")
    
    class Meta:
        db_table = 'lumo_sites_theme_preset'

    def __str__(self):
        return self.name

class AtomicSection(LumoBaseModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=50)

    class Meta:
        db_table = 'lumo_sites_atomic_section'

    def __str__(self):
        return self.name

class AtomicSectionVersion(LumoBaseModel):
    section = models.ForeignKey(AtomicSection, on_delete=models.CASCADE, related_name='versions')
    version_number = models.CharField(max_length=20)
    html_template_path = models.CharField(max_length=255)
    data_source_type = models.CharField(max_length=20, choices=DataSourceType.choices, default=DataSourceType.MANUAL)
    capabilities = models.JSONField(default=list, help_text='e.g., ["supports_background_image", "supports_dark_mode"]')
    is_i18n_enabled = models.BooleanField(default=True)
    default_schema_json = models.JSONField(default=dict)

    class Meta:
        db_table = 'lumo_sites_section_version'
        unique_together = ('section', 'version_number')

    def __str__(self):
        return f"{self.section.name} (v{self.version_number})"

# --- 4. SITE KITS ---
class SiteKit(LumoBaseModel):
    name = models.CharField(max_length=100)
    industry = models.ForeignKey('core_masterdata.Industry', on_delete=models.SET_NULL, null=True, blank=True)
    is_premium = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    required_plan = models.ForeignKey('saas_core.SubscriptionPlan', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'lumo_sites_kit'

    def __str__(self):
        return self.name

class SiteKitVersion(LumoBaseModel):
    kit = models.ForeignKey(SiteKit, on_delete=models.CASCADE, related_name='versions')
    version_number = models.CharField(max_length=20)
    default_preset = models.ForeignKey(ThemePreset, on_delete=models.PROTECT)

    class Meta:
        db_table = 'lumo_sites_kit_version'
        unique_together = ('kit', 'version_number')

    def __str__(self):
        return f"{self.kit.name} (v{self.version_number})"

class SiteKitManifest(LumoBaseModel):
    kit_version = models.ForeignKey(SiteKitVersion, on_delete=models.CASCADE, related_name='manifest')
    page_slug = models.CharField(max_length=100, default='home')
    section_version = models.ForeignKey(AtomicSectionVersion, on_delete=models.PROTECT)
    starter_content_json = models.JSONField(default=dict, blank=True)
    default_sort_order = models.IntegerField(default=0)
    is_required = models.BooleanField(default=True)

    class Meta:
        db_table = 'lumo_sites_kit_manifest'
        ordering = ['page_slug', 'default_sort_order'] 

    def __str__(self):
        return f"/{self.page_slug} -> {self.section_version.section.name}"

# --- 5. TENANT SITE & PUBLISHING PIPELINE ---
class TenantSite(LumoBaseModel):
    workspace = models.OneToOneField(Workspace, on_delete=models.CASCADE, related_name='website')
    active_kit_version = models.ForeignKey(SiteKitVersion, on_delete=models.PROTECT)
    active_preset = models.ForeignKey(ThemePreset, on_delete=models.PROTECT)
    preset_override_json = models.JSONField(default=dict, blank=True)
    google_analytics_id = models.CharField(max_length=50, blank=True, null=True)
    fb_pixel_id = models.CharField(max_length=50, blank=True, null=True)

    objects = TenantManager()

    class Meta:
        db_table = 'lumo_sites_tenant_site'

    def __str__(self):
        return f"Site: {self.workspace.name}"

class TenantPage(LumoBaseModel):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='tenant_pages', null=True)
    site = models.ForeignKey(TenantSite, on_delete=models.CASCADE, related_name='pages')
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, db_index=True)
    seo_title = models.CharField(max_length=255, blank=True, null=True)
    seo_description = models.TextField(blank=True, null=True)
    og_image = models.ForeignKey(MediaAsset, on_delete=models.SET_NULL, null=True, blank=True)

    objects = TenantManager()

    class Meta:
        db_table = 'lumo_sites_page'
        unique_together = ('site', 'slug')

    def __str__(self):
        return f"{self.title} ({self.site.workspace.name if self.site else 'No Site'})"
        
    def save(self, *args, **kwargs):
        if not self.workspace_id and self.site_id:
            self.workspace_id = self.site.workspace_id
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        # Dynamically returns correct path whether behind /site/ prefix or root domain
        return reverse('lumo_sites:public_page', kwargs={'slug': self.slug})

class PageRevision(LumoBaseModel):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='page_revisions', null=True)
    page = models.ForeignKey(TenantPage, on_delete=models.CASCADE, related_name='revisions')
    version_number = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=RevisionStatus.choices, default=RevisionStatus.DRAFT)
    
    objects = TenantManager()
          

    class Meta:
        db_table = 'lumo_sites_page_revision'
        constraints = [
            models.UniqueConstraint(
                fields=["page"],
                condition=models.Q(status='DRAFT', is_deleted=False),
                name="unique_draft_per_page"
            ),
            models.UniqueConstraint(
                fields=["page"],
                condition=models.Q(status='PUBLISHED', is_deleted=False),
                name="unique_published_per_page"
            )
        ]

    def __str__(self):
        return f"{self.page.title} - Rev {self.version_number} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.workspace_id and self.page_id:
            page_workspace_id = getattr(self.page, 'workspace_id', None) or TenantPage.objects.filter(id=self.page_id).values_list('workspace_id', flat=True).first()
            self.workspace_id = page_workspace_id
        super().save(*args, **kwargs)
    
    

class TenantPageSection(LumoBaseModel):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='page_sections', null=True)
    revision = models.ForeignKey(PageRevision, on_delete=models.CASCADE, related_name='sections')
    section_version = models.ForeignKey(AtomicSectionVersion, on_delete=models.PROTECT)
    sort_order = models.IntegerField(default=0)
    is_visible = models.BooleanField(default=True)
    content_json = models.JSONField(default=dict)
    lock_version = models.IntegerField(default=1)

    objects = TenantManager()

    class Meta:
        db_table = 'lumo_sites_page_section'  # 🟢 FIX: The missing line restored!
        ordering = ['sort_order']
        constraints = [
            models.UniqueConstraint(
                fields=['revision', 'sort_order'],
                condition=models.Q(is_deleted=False),
                name='unique_sort_order_per_revision'
            )
        ]

    def __str__(self):
        return f"{self.section_version.section.name} (Order: {self.sort_order})"
        
    def save(self, *args, **kwargs):
        if not self.workspace_id and self.revision_id:
            rev_workspace_id = getattr(self.revision, 'workspace_id', None) or PageRevision.objects.filter(id=self.revision_id).values_list('workspace_id', flat=True).first()
            self.workspace_id = rev_workspace_id
        super().save(*args, **kwargs)

class SiteDeployment(LumoBaseModel):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='deployments', null=True)
    site = models.ForeignKey(TenantSite, on_delete=models.CASCADE, related_name='deployments')
    revision = models.ForeignKey(PageRevision, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=DeploymentStatus.choices, default=DeploymentStatus.QUEUED)
    triggered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    deployed_at = models.DateTimeField(null=True, blank=True)
    error_log = models.TextField(blank=True, null=True)

    objects = TenantManager()

    class Meta:
        db_table = 'lumo_sites_deployment'

    def __str__(self):
        return f"Deploy: {self.site.workspace.name if self.site else 'Unknown'} ({self.status})"
        
    def save(self, *args, **kwargs):
        if not self.workspace_id and self.site_id:
            self.workspace_id = self.site.workspace_id
        super().save(*args, **kwargs)

# --- 6. NAVIGATION & FORMS ---
class SiteMenu(LumoBaseModel):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='site_menus', null=True)
    site = models.ForeignKey(TenantSite, on_delete=models.CASCADE, related_name='menus')
    name = models.CharField(max_length=50)

    objects = TenantManager()

    class Meta:
        db_table = 'lumo_sites_menu'

    def __str__(self):
        return f"{self.name} ({self.site.workspace.name if self.site else 'Unknown'})"
        
    def save(self, *args, **kwargs):
        if not self.workspace_id and self.site_id:
            self.workspace_id = self.site.workspace_id
        super().save(*args, **kwargs)

class SiteMenuItem(LumoBaseModel):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='menu_items', null=True)
    menu = models.ForeignKey(SiteMenu, on_delete=models.CASCADE, related_name='items')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    label = models.CharField(max_length=100)
    url = models.CharField(max_length=255)
    sort_order = models.IntegerField(default=0)

    objects = TenantManager()

    class Meta:
        db_table = 'lumo_sites_menu_item'
        ordering = ['sort_order']

    def __str__(self):
        return self.label
        
    def save(self, *args, **kwargs):
        # 🟢 DUPLICATE METHOD & HARDCODED BUG REMOVED
        if not self.workspace_id and self.menu_id:
            menu_workspace_id = getattr(self.menu, 'workspace_id', None) or SiteMenu.objects.filter(id=self.menu_id).values_list('workspace_id', flat=True).first()
            self.workspace_id = menu_workspace_id
        super().save(*args, **kwargs)

    @property
    def href(self):
        """
        🟢 SPRINT 1 FIX (OPTIMIZED): Smartly resolves stored strings to absolute paths.
        Completely eliminates N+1 query vulnerability by parsing and reversing in memory.
        """
        url_str = (self.url or "").strip()
        
        # 1. Bypass absolute URIs (External links, mailto, tel, anchors)
        if url_str.startswith(('http://', 'https://', 'mailto:', 'tel:', '#')):
            return url_str
            
        # 2. Extract clean slug
        clean_slug = url_str.strip('/')
        if not clean_slug:
            return "/"
            
        # 3. Optimistic Django Namespace Routing
        try:
            return reverse('lumo_sites:public_page', kwargs={'slug': clean_slug})
        except NoReverseMatch:
            # Fallback if URL isn't meant for public_page namespace
            return f"/{clean_slug}"

class FormDefinition(LumoBaseModel):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='form_definitions', null=True)
    site = models.ForeignKey(TenantSite, on_delete=models.CASCADE, related_name='forms')
    name = models.CharField(max_length=100)
    schema_json = models.JSONField(default=list) 
    success_message = models.TextField(default="Thank you! We have received your submission.")

    objects = TenantManager()

    class Meta:
        db_table = 'lumo_sites_form'

    def __str__(self):
        return f"{self.name} ({self.site.workspace.name if self.site else 'Unknown'})"
        
    def save(self, *args, **kwargs):
        if not self.workspace_id and self.site_id:
            self.workspace_id = self.site.workspace_id
        super().save(*args, **kwargs)

class FormSubmission(LumoBaseModel):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='form_submissions', null=True)
    form = models.ForeignKey(FormDefinition, on_delete=models.CASCADE, related_name='submissions')
    submitted_data_json = models.JSONField(default=dict)

    objects = TenantManager()

    class Meta:
        db_table = 'lumo_sites_form_submission'

    def __str__(self):
        return f"Submission for {self.form.name if self.form else 'Unknown'}"
        
    def save(self, *args, **kwargs):
        if not self.workspace_id and self.form_id:
            form_workspace_id = getattr(self.form, 'workspace_id', None) or FormDefinition.objects.filter(id=self.form_id).values_list('workspace_id', flat=True).first()
            self.workspace_id = form_workspace_id
        super().save(*args, **kwargs)

class PagePublishedSnapshot(LumoBaseModel):
    page = models.OneToOneField('TenantPage', on_delete=models.CASCADE, related_name='published_snapshot')
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    rendered_html = models.TextField(blank=True, null=True)
    page_data_snapshot = models.JSONField(default=dict)
    version = models.PositiveIntegerField(default=1)
    published_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    checksum = models.CharField(max_length=64, blank=True, null=True)
    
    class Meta:
        db_table = 'lumo_sites_page_snapshot'
        
    def __str__(self):
        return f"Snapshot v{self.version}: {self.page.title}"