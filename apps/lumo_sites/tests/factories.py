# apps/lumo_sites/tests/factories.py
# All factories wrapped in system_context() to satisfy TenantManager
from core.managers import system_context
from apps.saas_core.models.tenant import Workspace
from apps.saas_core.models.subscription import SubscriptionPlan
from apps.lumo_sites.models import (
    TenantSite, TenantPage, PageRevision, TenantPageSection,
    ThemePreset, SiteKitVersion, AtomicSection, AtomicSectionVersion,
    SiteKit, RevisionStatus
)

def create_default_plan():
    
    with system_context():
        plan, _ = SubscriptionPlan.objects.get_or_create(
            code='default',
            defaults={
                'name': 'Default Plan',
                'is_active': True,
                'is_default': True,
                'is_public': True,
                'is_free_plan': True,
                'trial_days': 0,
                'max_users': 10,
                'max_companies': 1,
                'max_customers': 100,
                'max_storage_mb': 1024,
                'sort_order': 1,
            }
        )
        return plan

def create_workspace(name='Test Workspace', **kwargs):
    create_default_plan()
    with system_context():
        return Workspace.objects.create(name=name, **kwargs)

def create_site_kit(name='Default Kit', **kwargs):
    with system_context():
        return SiteKit.objects.create(name=name, **kwargs)

def create_themepreset(
    name='Default Theme',
    primary_color='#4f46e5',
    secondary_color='#ffffff',
    heading_font='Inter',
    body_font='Inter',
    border_radius='8px',
    **kwargs
):
    with system_context():
        return ThemePreset.objects.create(
            name=name,
            primary_color=primary_color,
            secondary_color=secondary_color,
            heading_font=heading_font,
            body_font=body_font,
            border_radius=border_radius,
            **kwargs
        )

def create_sitekitversion(
    version_number='1.0',
    default_preset=None,
    kit=None,
    **kwargs
):
    with system_context():
        if kit is None:
            kit = create_site_kit()
        if default_preset is None:
            default_preset = create_themepreset()
        return SiteKitVersion.objects.create(
            kit=kit,
            version_number=version_number,
            default_preset=default_preset,
            **kwargs
        )

def create_atomicsection(name='Hero', code='hero', category='standard', **kwargs):
    with system_context():
        return AtomicSection.objects.create(name=name, code=code, category=category, **kwargs)

def create_atomicsectionversion(
    section=None,
    version_number='1.0',
    html_template_path='sections/hero.html',
    data_source_type='json',
    capabilities=None,
    is_i18n_enabled=False,
    default_schema_json=None,
    **kwargs
):
    with system_context():
        if section is None:
            section = create_atomicsection()
        if capabilities is None:
            capabilities = {}
        if default_schema_json is None:
            default_schema_json = {}
        return AtomicSectionVersion.objects.create(
            section=section,
            version_number=version_number,
            html_template_path=html_template_path,
            data_source_type=data_source_type,
            capabilities=capabilities,
            is_i18n_enabled=is_i18n_enabled,
            default_schema_json=default_schema_json,
            **kwargs
        )

def create_tenantsite(
    workspace=None,
    site_name='Test Site',
    slug='test-site',
    active_preset=None,
    active_kit_version=None,
    preset_override_json=None,
    **kwargs
):
    with system_context():
        if workspace is None:
            workspace = create_workspace()
        if active_preset is None:
            active_preset = create_themepreset()
        if active_kit_version is None:
            active_kit_version = create_sitekitversion(default_preset=active_preset)
        if preset_override_json is None:
            preset_override_json = {}
        return TenantSite.objects.create(
            workspace=workspace,
            active_kit_version=active_kit_version,
            active_preset=active_preset,
            site_name=site_name,
            slug=slug,
            preset_override_json=preset_override_json,
            **kwargs
        )

def create_tenantpage(
    site=None,
    workspace=None,
    title='Test Page',
    slug='test-page',
    **kwargs
):
    with system_context():
        if site is None:
            site = create_tenantsite(workspace=workspace)
        if workspace is None:
            workspace = site.workspace
        return TenantPage.objects.create(
            site=site,
            workspace=workspace,
            title=title,
            slug=slug,
            **kwargs
        )

def create_pagerevision(
    page=None,
    workspace=None,
    version_number=1,
    status=RevisionStatus.DRAFT,
    **kwargs
):
    with system_context():
        if page is None:
            page = create_tenantpage()
        if workspace is None:
            workspace = page.workspace
        return PageRevision.objects.create(
            page=page,
            workspace=workspace,
            version_number=version_number,
            status=status,
            **kwargs
        )

def create_tenantpagesection(
    revision=None,
    section_version=None,
    workspace=None,
    sort_order=0,
    is_visible=True,
    content_json=None,
    lock_version=0,
    **kwargs
):
    with system_context():
        if revision is None:
            revision = create_pagerevision()
        if section_version is None:
            section_version = create_atomicsectionversion()
        if workspace is None:
            workspace = revision.workspace
        if content_json is None:
            content_json = {}
        return TenantPageSection.objects.create(
            revision=revision,
            section_version=section_version,
            workspace=workspace,
            sort_order=sort_order,
            is_visible=is_visible,
            content_json=content_json,
            lock_version=lock_version,
            **kwargs
        )

def create_published_revision_with_duplicates(page, version_number=1):
    with system_context():
        workspace = page.workspace
        section_version = create_atomicsectionversion()
        pub_rev = PageRevision.objects.create(
            page=page,
            workspace=workspace,
            version_number=version_number,
            status=RevisionStatus.PUBLISHED,
            is_deleted=False,
        )
        for order in [1, 1, 2]:
            TenantPageSection.objects.create(
                revision=pub_rev,
                section_version=section_version,
                workspace=workspace,
                sort_order=order,
                is_visible=True,
                is_deleted=False,
                content_json={},
                lock_version=0,
            )
        return pub_rev

def create_full_test_site():
    with system_context():
        workspace = create_workspace()
        site = create_tenantsite(workspace=workspace)
        page = create_tenantpage(site=site, workspace=workspace)
        return workspace, site, page
