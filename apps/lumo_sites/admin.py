from django.contrib import admin
from .models import (
    SiteDomain, DomainVerification, MediaAsset,
    ThemePreset, AtomicSection, AtomicSectionVersion,
    SiteKit, SiteKitVersion, SiteKitManifest,
    TenantSite, TenantPage, PageRevision, TenantPageSection,
    SiteDeployment, SiteMenu, SiteMenuItem, FormDefinition, FormSubmission
)

# ==========================================
# 1. ATOMIC SECTIONS (The Lego Blocks)
# ==========================================
class AtomicSectionVersionInline(admin.StackedInline):
    model = AtomicSectionVersion
    extra = 0
    fields = ('version_number', 'html_template_path', 'data_source_type', 'is_i18n_enabled', 'capabilities', 'default_schema_json')
    
@admin.register(AtomicSection)
class AtomicSectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'category')
    search_fields = ('name', 'code', 'category')
    list_filter = ('category',)
    inlines = [AtomicSectionVersionInline]

@admin.register(AtomicSectionVersion)
class AtomicSectionVersionAdmin(admin.ModelAdmin):
    list_display = ('section', 'version_number', 'data_source_type')
    search_fields = ('section__name', 'section__code', 'version_number')
    list_filter = ('data_source_type', 'is_i18n_enabled')

# ==========================================
# 2. SITE KITS (The Blueprint Builder)
# ==========================================
class SiteKitManifestInline(admin.TabularInline):
    model = SiteKitManifest
    extra = 1
    # 🟢 শুধুমাত্র সেকশন ড্রপডাউন এবং সর্ট অর্ডার দেখাচ্ছি
    fields = ('section_version', 'default_sort_order') 
    ordering = ('default_sort_order',)

@admin.register(SiteKitVersion)
class SiteKitVersionAdmin(admin.ModelAdmin):
    list_display = ('kit', 'version_number', 'default_preset')
    list_filter = ('kit',)
    # 🟢 ফিক্স: মেইন ফর্ম থেকে অডিট ফিল্ডগুলো গায়েব করে দিচ্ছি!
    exclude = ('is_deleted', 'deleted_at', 'created_by', 'updated_by', 'deleted_by') 
    inlines = [SiteKitManifestInline]

@admin.register(SiteKit)
class SiteKitAdmin(admin.ModelAdmin):
    list_display = ('name', 'industry', 'is_premium', 'price')
    list_filter = ('is_premium', 'industry')
    search_fields = ('name',)

# ==========================================
# 3. THEME PRESETS (Decoration Layer)
# ==========================================
@admin.register(ThemePreset)
class ThemePresetAdmin(admin.ModelAdmin):
    list_display = ('name', 'primary_color', 'secondary_color', 'heading_font', 'body_font')
    search_fields = ('name',)

# ==========================================
# 4. TENANT MONITORING (User Sites)
# ==========================================
class TenantPageInline(admin.TabularInline):
    model = TenantPage
    extra = 0
    fields = ('title', 'slug', 'seo_title')

@admin.register(TenantSite)
class TenantSiteAdmin(admin.ModelAdmin):
    list_display = ('workspace', 'active_kit_version', 'active_preset')
    search_fields = ('workspace__name',)
    inlines = [TenantPageInline]

@admin.register(SiteDomain)
class SiteDomainAdmin(admin.ModelAdmin):
    list_display = ('domain_name', 'workspace', 'is_primary', 'is_subdomain', 'ssl_status')
    list_filter = ('is_primary', 'is_subdomain', 'ssl_status')
    search_fields = ('domain_name', 'workspace__name')

@admin.register(SiteDeployment)
class SiteDeploymentAdmin(admin.ModelAdmin):
    list_display = ('site', 'revision', 'status', 'deployed_at')
    list_filter = ('status',)

# ==========================================
# 5. FORMS & ASSETS
# ==========================================
@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = ('workspace', 'file_path', 'storage_provider', 'mime_type', 'is_public')
    list_filter = ('storage_provider', 'is_public')

@admin.register(FormDefinition)
class FormDefinitionAdmin(admin.ModelAdmin):
    list_display = ('name', 'site')
    search_fields = ('name', 'site__workspace__name')

@admin.register(FormSubmission)
class FormSubmissionAdmin(admin.ModelAdmin):
    list_display = ('form', 'created_at')
    list_filter = ('form',)