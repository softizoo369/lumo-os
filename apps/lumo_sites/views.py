from django.db.models import Prefetch
import uuid
import hashlib
from django.shortcuts import get_object_or_404, render, redirect
from django.http import Http404, HttpResponse
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.template.loader import render_to_string
from django.db.models import Max
from django.contrib.auth.decorators import login_required

from apps.lumo_sites.services.cloudflare_service import CloudflareService
from apps.lumo_sites.models import (
    TenantSite, TenantPage, PageRevision, RevisionStatus, 
    TenantPageSection, SiteDomain, DomainVerification, DomainStatus, 
    SiteMenu, SiteMenuItem, FormDefinition, FormSubmission, 
    MediaAsset, ThemePreset, SiteKit, SiteKitVersion, SiteKitManifest,
    AtomicSectionVersion
)
from apps.lumo_sites.forms import (
    TenantPageForm, DynamicSchemaForm, SiteDomainForm, 
    SiteMenuItemForm, ThemePresetForm, FormDefinitionForm, MediaAssetForm
)
from apps.lumo_sites.rendering.engine import SiteRenderingEngine
from apps.lumo_sites.services.revisions import PageRevisionService
from apps.lumo_sites.services.publish_service import PublishService
from apps.saas_core.services.audit_service import AuditService
from apps.saas_core.services.workspace_service import WorkspaceService


# Helper function (can be placed at the top of views.py or inside a service)
def generate_empty_content_from_schema(schema_json):
    """
    Parses the AtomicSectionVersion schema and generates an empty data dictionary.
    Prevents schema metadata (like dicts for 'reference' fields) from being saved as data.
    """
    empty_data = {}
    if not isinstance(schema_json, dict):
        return empty_data
        
    for key, value in schema_json.items():
        if isinstance(value, dict):
            # If it's a field definition dict (e.g., {"type": "reference", ...})
            if value.get('type') == 'reference' or value.get('type') == 'image':
                empty_data[key] = ""  # Initialize with empty string, ready for UUID
            elif value.get('type') == 'boolean':
                empty_data[key] = value.get('default', False)
            elif value.get('type') == 'number':
                empty_data[key] = value.get('default', 0)
            else:
                empty_data[key] = value.get('default', "")
        else:
            # Fallback for simple key-value defaults
            empty_data[key] = value
            
    return empty_data

# =====================================================================
# 1. PUBLIC RENDERER (The Live Website)
# =====================================================================

def render_dynamic_page(request, site, slug, is_preview=False):
    # 🟢 1. Page Lookup (Bypass Manager)
    page = TenantPage._base_manager.filter(site=site, slug=slug, is_deleted=False).first()
    
    if not page and slug == 'home':
        return HttpResponse(
            "<div style='text-align:center; padding:100px; font-family:sans-serif;'>"
            "<h1 style='color:#0d6efd;'>🚀 Lumo OS</h1>"
            "<h2>Your domain is successfully connected!</h2>"
            "<p style='color:#6c757d;'>Please create a page with slug <b>'home'</b> to see it here.</p>"
            "</div>"
        )
    elif not page:
        return HttpResponse(
            f"<div style='text-align:center; padding:10vh 20px; font-family:sans-serif; background-color:#f8fafc; height:100vh;'>"
            f"<h1 style='color:#475569; font-size:5rem; margin-bottom:10px;'>404</h1>"
            f"<h2 style='color:#0f172a; font-weight:bold;'>Page Not Found</h2>"
            f"<p style='color:#64748b; margin-top:20px; font-size: 1.1rem;'>The page <code style='background:#e2e8f0; color:#dc2626; padding:4px 8px; border-radius:4px;'>/{slug}</code> does not exist on this website.</p>"
            f"<a href='/' style='display:inline-block; margin-top:30px; padding:12px 28px; background:#4f46e5; color:white; text-decoration:none; border-radius:50px; font-weight:bold;'>Go Back Home</a>"
            f"</div>",
            status=404
        )

    # 🟢 2. Unified Revision Lookup (PHASE 1 FIX)
    from apps.lumo_sites.services.revision_resolver import RevisionResolver
    revision = (
        RevisionResolver.get_latest_draft(page)
        if is_preview
        else RevisionResolver.get_latest_published(page)
    )
    
    if not revision:
        if is_preview:
            return HttpResponse("No draft revision found for this page.")
        return HttpResponse(
            "<div style='text-align:center; padding:100px; font-family:sans-serif;'>"
            "<h1>🚧 Under Construction</h1>"
            "<p style='color:#6c757d;'>This page hasn't been published yet.</p>"
            "</div>"
        )

    # 🟢 3. Menus Lookup
    menu_items_qs = SiteMenuItem._base_manager.filter(is_deleted=False).order_by('sort_order')
    
    main_menu = SiteMenu._base_manager.filter(site=site, name="Main Navigation", is_deleted=False).prefetch_related(
        Prefetch('items', queryset=menu_items_qs)
    ).first()
    
    footer_menu = SiteMenu._base_manager.filter(site=site, name="Footer Menu", is_deleted=False).prefetch_related(
        Prefetch('items', queryset=menu_items_qs)
    ).first()

    # 🟢 4. Sections Lookup
    sections = TenantPageSection._base_manager.filter(revision=revision, is_visible=True, is_deleted=False).order_by('sort_order')
    
    rendered_sections = ""
    for section in sections:
        template_path = section.section_version.html_template_path
        context = {
            'data': section.content_json, 
            'site': site, 
            'preset': site.active_preset,
            'site_menu': main_menu 
        }
        
        # 🟢 UUID Validation Fix applied here
        form_id = section.content_json.get('form_definition_id')
        if form_id and isinstance(form_id, str):
            from django.core.exceptions import ValidationError
            try:
                context['dynamic_form'] = FormDefinition._base_manager.get(id=form_id, site=site)
            except (FormDefinition.DoesNotExist, ValidationError, ValueError):
                pass
                
        try:
            rendered_sections += render_to_string(template_path, context, request=request)
        except Exception as e:
            rendered_sections += f"<div style='padding: 20px; background: #ffebee; color: #c62828; text-align: center;'>Error rendering section: {section.section_version.section.name}</div>"

    return render(request, 'lumo_sites/layouts/base_tenant_site.html', {
        'site': site, 'page': page, 'rendered_sections': rendered_sections, 
        'is_preview': is_preview, 'main_menu': main_menu, 'footer_menu': footer_menu
    })

def public_page_view(request, slug='home'):
    if hasattr(request, 'tenant_site') and request.tenant_site:
        site = request.tenant_site
    else:
        workspace = WorkspaceService.get_current_workspace(request)
        site = getattr(workspace, "website", None) if workspace else None
        
    if not site:
        return render(request, 'lumo_sites/errors/no_site.html')
    return render_dynamic_page(request, site, slug, is_preview=False)

def preview_page_view(request, slug='home'):
    workspace = WorkspaceService.get_current_workspace(request)
    site = getattr(workspace, "website", None) if workspace else None
    
    if not site:
        raise Http404("No tenant site found.")
    return render_dynamic_page(request, site, slug, is_preview=True)


# =====================================================================
# 2. EDITOR SYSTEM (Section Level Editor)
# =====================================================================
def unflatten_dict(flat_dict):
    result = {}
    for key, value in flat_dict.items():
        parts = key.split('.')
        d = result
        for part in parts[:-1]:
            if part not in d:
                d[part] = {}
            d = d[part]
        d[parts[-1]] = value
    return result

def edit_section_view(request, section_id):
    workspace = WorkspaceService.get_current_workspace(request)
    # 🟢 SECURED: IDOR patched by enforcing workspace boundary
    section = get_object_or_404(TenantPageSection, id=section_id, workspace=workspace)
    
    schema = section.section_version.default_schema_json
    initial_data = section.content_json if section.content_json else {}

    if request.method == 'POST':
        submitted_lock_version = int(request.POST.get('lock_version', 0))
        
        if section.lock_version != submitted_lock_version:
            messages.error(request, "⚠️ Conflict Detected! Another editor modified this section. Please refresh.")
            return redirect('lumo_sites:edit_section', section_id=section.id)
            
        form = DynamicSchemaForm(data=request.POST, schema=schema, initial_content=initial_data)
        
        if form.is_valid():
            section.content_json.update(unflatten_dict(form.cleaned_data))
            section.lock_version += 1 
            section.save()
            
            # 🟢 AUDIT LOG
            AuditService.log(
                request=request, workspace=section.workspace, action="SECTION_EDITED",
                resource_type="TenantPageSection", resource_id=str(section.id),
                metadata={"section_name": section.section_version.section.name, "page": section.revision.page.title}
            )
            
            messages.success(request, f"{section.section_version.section.name} updated successfully!")
            return redirect('lumo_sites:preview_page', slug=section.revision.page.slug)
    else:
        form = DynamicSchemaForm(schema=schema, initial_content=initial_data)

    return render(request, 'lumo_sites/editor/section_edit_form.html', {'form': form, 'section': section})


# =====================================================================
# 3. BUILDER DASHBOARD & PUBLISHING
# =====================================================================
# 🟢 SPRINT 3 FIX: Lightweight Dashboard (Only Pages, no inline sections)
def builder_dashboard_view(request):
    workspace = WorkspaceService.get_current_workspace(request)
    tenant_site = getattr(workspace, "website", None) if workspace else None
    
    if not tenant_site:
        messages.info(request, "👋 Welcome! Choose a theme to start building your website.")
        return redirect('lumo_sites:theme_store')  # 🟢 SaaS Onboarding Routing

    # 🟢 FIX: Ensure we only fetch pages that are NOT deleted
    pages = TenantPage.objects.filter(site=tenant_site, is_deleted=False).order_by('-created_at')
    
    dashboard_data = []
    for page in pages:
        draft_revision = PageRevisionService.get_or_create_draft(page)
        dashboard_data.append({'page': page, 'draft_revision': draft_revision})

    return render(request, 'lumo_sites/editor/dashboard.html', {'site': tenant_site, 'dashboard_data': dashboard_data})


# 🟢 SPRINT 3: The Dedicated Page Builder Workspace
def page_builder_view(request, page_id):
    workspace = WorkspaceService.get_current_workspace(request)
    tenant_site = getattr(workspace, "website", None) if workspace else None
    
    if not tenant_site:
        messages.info(request, "👋 Welcome! Choose a theme to start building your website.")
        return redirect('lumo_sites:theme_store')  # 🟢 SaaS Onboarding Routing
        
    page = get_object_or_404(TenantPage, id=page_id, site=tenant_site, is_deleted=False)
    
    # 🟢 PHASE 1 FIX: Unified Draft Resolution
    from apps.lumo_sites.services.revision_resolver import RevisionResolver
    draft_revision = RevisionResolver.get_latest_draft(page)
    if not draft_revision:
        draft_revision = PageRevisionService.get_or_create_draft(page)
    
    # 🟢 FIX: Ensure we only fetch sections that are NOT deleted
    sections = TenantPageSection.objects.filter(revision=draft_revision, is_deleted=False).order_by('sort_order')
    
    # Fetch Atomic Sections for the Library Modal
    atomic_versions = AtomicSectionVersion.objects.select_related('section').order_by('section__category', 'section__name')
    
    context = {
        'site': tenant_site,
        'page': page,
        'draft_revision': draft_revision,
        'sections': sections,
        'atomic_versions': atomic_versions
    }
    return render(request, 'lumo_sites/editor/page_builder.html', context)

# 🟢 SPRINT 5 FIX: Unified Publish Pipeline
def publish_action_view(request, revision_id):
    workspace = WorkspaceService.get_current_workspace(request)
    
    # 🟢 PHASE 1 FIX: Unified Publisher Resolution
    from apps.lumo_sites.services.revision_resolver import RevisionResolver
    
    draft_revision = PageRevision._base_manager.filter(id=revision_id, is_deleted=False).first()
    if not draft_revision:
        # Fallback if template passed page_id by mistake
        page = TenantPage._base_manager.filter(id=revision_id, is_deleted=False).first()
        if page:
            draft_revision = RevisionResolver.get_latest_draft(page)

    if not draft_revision:
        messages.error(request, "Error: Revision not found. Could not publish.")
        return redirect('lumo_sites:builder_dashboard')
    
    # Auto-heal missing workspace in legacy data
    if not draft_revision.workspace_id and workspace:
        draft_revision.workspace = workspace
        draft_revision.save(update_fields=['workspace'])

    # 1. Promote the draft revision to PUBLISHED via PageRevisionService
    PageRevisionService.publish_revision(draft_revision)
    
    # 2. Trigger the PublishService to generate snapshots and clear cache
    success, message = PublishService.publish_page(draft_revision.page.id, user=request.user)

    if success:
        AuditService.log(
            request=request, workspace=draft_revision.workspace, action="PAGE_PUBLISHED",
            resource_type="PageRevision", resource_id=str(draft_revision.id),
            metadata={"page_title": draft_revision.page.title}
        )
        messages.success(request, f"🚀 {draft_revision.page.title} page has been published successfully!")
    else:
        messages.warning(request, f"Revision promoted, but snapshot/cache task failed: {message}")
        
    return redirect('lumo_sites:builder_dashboard')


def theme_editor_view(request):
    workspace = WorkspaceService.get_current_workspace(request)
    tenant_site = getattr(workspace, "website", None) if workspace else None
    
    if not tenant_site:
        messages.info(request, "👋 Welcome! Choose a theme to start building your website.")
        return redirect('lumo_sites:theme_store')

    active_preset = tenant_site.active_preset
    if request.method == 'POST':
        form = ThemePresetForm(request.POST, instance=active_preset)
        if form.is_valid():
            form.save()
            
            # 🟢 AUDIT LOG
            AuditService.log(
                request=request, workspace=tenant_site.workspace, action="THEME_UPDATED",
                resource_type="ThemePreset", resource_id=str(active_preset.id),
                metadata={"preset_name": active_preset.name}
            )
            messages.success(request, "🎨 Theme styling updated successfully!")
            return redirect('lumo_sites:theme_editor')
    else:
        form = ThemePresetForm(instance=active_preset)

    return render(request, 'lumo_sites/editor/theme_editor.html', {'form': form, 'site': tenant_site})



# ... (Keep existing imports at the top of your views.py) ...

# =====================================================================
# TASK 1: PAGE AUTO NAVIGATION (Update page_create_view)
# =====================================================================
def page_create_view(request):
    workspace = WorkspaceService.get_current_workspace(request)
    tenant_site = getattr(workspace, "website", None) if workspace else None
    
    if not tenant_site:
        return HttpResponse("No site provisioned for this workspace yet.")
        
    if request.method == 'POST':
        form = TenantPageForm(request.POST)
        if form.is_valid():
            new_page = form.save(commit=False)
            new_page.site = tenant_site
            new_page.save()
            PageRevision.objects.create(page=new_page, version_number=1, status=RevisionStatus.DRAFT)
            
            # 🟢 TASK 1 FIX: Auto-Navigation Logic
            # Note: This assumes 'add_to_main_nav' is added to TenantPageForm
            add_to_nav = form.cleaned_data.get('add_to_main_nav', False)
            if add_to_nav:
                main_menu, _ = SiteMenu.objects.get_or_create(
                    site=tenant_site, 
                    name="Main Navigation", 
                    defaults={'workspace': workspace}
                )
                normalized_slug = new_page.slug.strip("/")
                
                # Duplicate Prevention
                exists = SiteMenuItem.objects.filter(
                    menu=main_menu,
                    url__in=[normalized_slug, f"/{normalized_slug}"]
                ).exists()
                
                if not exists:
                    last_order = SiteMenuItem.objects.filter(menu=main_menu).aggregate(Max('sort_order'))['sort_order__max']
                    next_order = (last_order or 0) + 1
                    SiteMenuItem.objects.create(
                        menu=main_menu,
                        label=new_page.title,
                        url=f"/{normalized_slug}",
                        sort_order=next_order,
                        workspace=workspace
                    )

            # 🟢 AUDIT LOG
            AuditService.log(
                request=request, workspace=tenant_site.workspace, action="PAGE_CREATED",
                resource_type="TenantPage", resource_id=str(new_page.id),
                metadata={"page_title": new_page.title}
            )
            messages.success(request, f"📄 Page '{new_page.title}' created successfully!")
            return redirect('lumo_sites:builder_dashboard')
    else:
        form = TenantPageForm()
    return render(request, 'lumo_sites/editor/page_form.html', {'form': form, 'title': 'Create New Page'})


# =====================================================================
# TASK 2: SLUG CHANGE STABILIZATION (Update page_edit_view)
# =====================================================================
def page_edit_view(request, page_id):
    workspace = WorkspaceService.get_current_workspace(request)
    tenant_site = getattr(workspace, "website", None) if workspace else None
    
    if not tenant_site:
        return HttpResponse("No site provisioned for this workspace yet.")
        
    page = get_object_or_404(TenantPage, id=page_id, site=tenant_site)
    old_slug = page.slug.strip("/") # 🟢 TASK 2: Track old slug
    
    if request.method == 'POST':
        form = TenantPageForm(request.POST, instance=page)
        if form.is_valid():
            updated_page = form.save()
            new_slug = updated_page.slug.strip("/")
            
            # 🟢 TASK 2 FIX: Safely sync related menu URLs
            if old_slug != new_slug:
                SiteMenuItem.objects.filter(
                    menu__site=tenant_site,
                    url__in=[old_slug, f"/{old_slug}"]
                ).update(url=f"/{new_slug}")
            
            # 🟢 AUDIT LOG
            AuditService.log(
                request=request, workspace=tenant_site.workspace, action="PAGE_SEO_UPDATED",
                resource_type="TenantPage", resource_id=str(page.id),
                metadata={"page_title": updated_page.title}
            )
            messages.success(request, f"🚀 SEO settings for '{updated_page.title}' updated!")
            return redirect('lumo_sites:builder_dashboard')
    else:
        form = TenantPageForm(instance=page)
    return render(request, 'lumo_sites/editor/page_form.html', {'form': form, 'title': f'Edit Page & SEO: {page.title}'})


# =====================================================================
# TASK 3: PAGE DELETE (Add NEW page_delete_view)
# =====================================================================
# 🟢 TASK 3: New Page Delete View
def page_delete_view(request, page_id):
    workspace = WorkspaceService.get_current_workspace(request)
    tenant_site = getattr(workspace, "website", None) if workspace else None
    
    if not tenant_site:
        return redirect('lumo_sites:builder_dashboard')
        
    # 🟢 SECURITY: Verify ownership
    page = get_object_or_404(TenantPage, id=page_id, site=tenant_site)
    
    if request.method == 'POST':
        normalized_slug = page.slug.strip("/")
        page_title = page.title
        
        # 🟢 Clean up internal menu items ONLY (Protects external URLs)
        SiteMenuItem.objects.filter(
            menu__site=tenant_site,
            url__in=[normalized_slug, f"/{normalized_slug}"]
        ).delete()
        
        # Delete the page (Revisions and sections cascade automatically based on your models)
        page.delete() 
        
        AuditService.log(
            request=request, workspace=workspace, action="PAGE_DELETED",
            resource_type="TenantPage", resource_id=str(page_id),
            metadata={"page_title": page_title}
        )
        messages.success(request, f"🗑️ Page '{page_title}' deleted successfully.")
        
    return redirect('lumo_sites:builder_dashboard')


# =====================================================================
# TASK 4: FOOTER MENU RECOVERY (Update navigation_manager_view)
# =====================================================================
def navigation_manager_view(request):
    workspace = WorkspaceService.get_current_workspace(request)
    tenant_site = getattr(workspace, "website", None) if workspace else None
    
    if not tenant_site:
        messages.info(request, "👋 Welcome! Choose a theme to start building your website.")
        return redirect('lumo_sites:theme_store')  # 🟢 SaaS Onboarding Routing

    # 🟢 TASK 4 FIX: Idempotent Recovery (Replaces the 'if not menus.exists():' block)
    SiteMenu.objects.get_or_create(site=tenant_site, name="Main Navigation", defaults={'workspace': workspace})
    SiteMenu.objects.get_or_create(site=tenant_site, name="Footer Menu", defaults={'workspace': workspace})
        
    menus = SiteMenu.objects.filter(site=tenant_site).prefetch_related('items')
    
    if request.method == 'POST':
        # ... (Keep the existing POST logic here unchanged) ...
        form = SiteMenuItemForm(request.POST)
        menu_id = request.POST.get('menu_id')
        target_menu = get_object_or_404(SiteMenu, id=menu_id, site=tenant_site)
        
        if form.is_valid():
            item = form.save(commit=False)
            item.menu = target_menu
            item.save()
            
            # 🟢 AUDIT LOG
            AuditService.log(
                request=request, workspace=tenant_site.workspace, action="MENU_LINK_ADDED",
                resource_type="SiteMenuItem", resource_id=str(item.id),
                metadata={"link_label": item.label, "menu_name": target_menu.name}
            )
            messages.success(request, f"🔗 Link '{item.label}' added to {target_menu.name}!")
            return redirect('lumo_sites:navigation_manager')
    else:
        form = SiteMenuItemForm()
    return render(request, 'lumo_sites/editor/navigation_manager.html', {'menus': menus, 'form': form, 'site': tenant_site})


# =====================================================================
# 4. DOMAIN MANAGEMENT
# =====================================================================
def domain_manager_view(request):
    workspace = WorkspaceService.get_current_workspace(request)
    domains = SiteDomain.objects.filter(workspace=workspace, is_deleted=False).select_related('verification').order_by('-created_at')
    
    if request.method == 'POST':
        form = SiteDomainForm(request.POST)
        if form.is_valid():
            domain = form.save(commit=False)
            domain.workspace = workspace
            domain.domain_name = domain.domain_name.replace('https://', '').replace('http://', '').strip('/')
            
            # গ্লোবাল ডাটাবেস চেক
            if SiteDomain._base_manager.filter(domain_name=domain.domain_name).exists():
                messages.error(request, f"The domain '{domain.domain_name}' is already registered in the system.")
                return redirect('lumo_sites:domain_manager')
            
            try:
                with transaction.atomic():
                    if domain.is_primary:
                        SiteDomain.objects.filter(workspace=workspace, is_primary=True, is_deleted=False).update(is_primary=False)
                    elif not SiteDomain.objects.filter(workspace=workspace, is_deleted=False).exists():
                        domain.is_primary = True
                        
                    domain.save()
                    
                    # 🟢 FIX: Manual Verification System
                    token = f"lumo-verify-{uuid.uuid4().hex[:16]}"
                    DomainVerification.objects.create(
                        domain=domain,
                        verification_token=token,
                        ownership_txt_name="_lumo-verify", 
                        ownership_txt_value=token,
                        dns_target="cname.lumo-os.com",
                        status=DomainStatus.PENDING
                    )
                    
                AuditService.log(
                    request=request, 
                    workspace=workspace, 
                    action="domain.added", 
                    resource_type="SiteDomain", 
                    resource_id=str(domain.id),
                    status="SUCCESS"
                )
                messages.success(request, f"Domain added! Please add the DNS records provided to verify your domain.")
                return redirect('lumo_sites:domain_manager')
                
            except Exception as e:
                messages.error(request, str(e))
    else:
        form = SiteDomainForm()

    # 🟢 SECURED: UI Consistency Map updated for Domain Card and Sidebar
    context = {
        'domains': domains, 
        'form': form,
        'domain_count': domains.count(),
        'active_menu': 'domains'
    }
    return render(request, 'lumo_sites/editor/domain_manager.html', context)


def domain_delete_view(request, domain_id):
    if request.method == 'POST':
        workspace = WorkspaceService.get_current_workspace(request)
        # 🟢 SECURED: IDOR patched by enforcing workspace boundary
        domain = get_object_or_404(SiteDomain, id=domain_id, workspace=workspace)
        domain_name = domain.domain_name
        domain_str_id = str(domain.id)
        
        domain.delete(hard=True) 
        
        AuditService.log(
            request=request, 
            workspace=workspace, 
            action="domain.deleted", 
            resource_type="SiteDomain", 
            resource_id=domain_str_id,
            metadata={"domain_name": domain_name},
            status="SUCCESS"
        )
        messages.warning(request, f"🗑️ Domain '{domain_name}' has been removed from the system.")
    return redirect('lumo_sites:domain_manager')


# =====================================================================
# 5. FORMS & MEDIA
# =====================================================================
def form_submissions_view(request):
    workspace = WorkspaceService.get_current_workspace(request)
    tenant_site = getattr(workspace, "website", None) if workspace else None
    
    if not tenant_site:
        return HttpResponse("No site provisioned for this workspace yet.")
        
    forms_list = FormDefinition.objects.filter(site=tenant_site).prefetch_related('submissions')
    active_form = forms_list.first()
    submissions = active_form.submissions.all().order_by('-created_at') if active_form else []
    return render(request, 'lumo_sites/editor/form_submissions.html', {'site': tenant_site, 'forms': forms_list, 'active_form': active_form, 'submissions': submissions})

def form_builder_view(request):
    workspace = WorkspaceService.get_current_workspace(request)
    tenant_site = getattr(workspace, "website", None) if workspace else None
    
    if not tenant_site:
        return HttpResponse("No site provisioned for this workspace yet.")
        
    forms = FormDefinition.objects.filter(site=tenant_site)
    if request.method == 'POST':
        form = FormDefinitionForm(request.POST)
        if form.is_valid():
            new_form = form.save(commit=False)
            new_form.site = tenant_site
            new_form.save()
            
            # 🟢 AUDIT LOG
            AuditService.log(
                request=request, workspace=tenant_site.workspace, action="FORM_CREATED",
                resource_type="FormDefinition", resource_id=str(new_form.id),
                metadata={"form_name": new_form.name}
            )
            messages.success(request, "Form created successfully!")
            return redirect('lumo_sites:form_builder')
    else:
        form = FormDefinitionForm(initial={'schema_json': '[]'})
    return render(request, 'lumo_sites/editor/form_builder.html', {'forms': forms, 'form': form})


def asset_library_view(request):
    workspace = WorkspaceService.get_current_workspace(request)
    tenant_site = getattr(workspace, "website", None) if workspace else None
    
    if not workspace:
        return HttpResponse("No workspace found.")
        
    assets = MediaAsset.objects.filter(workspace=workspace).order_by('-created_at')
    
    if request.method == 'POST':
        form = MediaAssetForm(request.POST, request.FILES)
        if form.is_valid():
            asset = form.save(commit=False)
            asset.workspace = workspace
            uploaded_file = request.FILES.get('file_path')
            
            if uploaded_file:
                # 1. Safely calculate checksum BEFORE anything else
                file_hash = hashlib.md5()
                for chunk in uploaded_file.chunks():
                    file_hash.update(chunk)
                asset.checksum = file_hash.hexdigest()
                uploaded_file.seek(0) # Reset pointer
                
                # 2. Extract reliable MIME type and size
                # Fallback to python's mimetypes if content_type is unreliable
                import mimetypes
                guessed_mime, _ = mimetypes.guess_type(uploaded_file.name)
                
                asset.mime_type = uploaded_file.content_type or guessed_mime or 'application/octet-stream'
                asset.file_size_kb = uploaded_file.size / 1024
                
            asset.save()
            
            # 🟢 AUDIT LOG
            AuditService.log(
                request=request, workspace=workspace, action="ASSET_UPLOADED",
                resource_type="MediaAsset", resource_id=str(asset.id),
                metadata={"file_name": uploaded_file.name}
            )
            messages.success(request, f"🖼️ Asset '{uploaded_file.name}' uploaded successfully!")
            return redirect('lumo_sites:asset_library')
    else:
        form = MediaAssetForm(initial={'is_public': True})

    return render(request, 'lumo_sites/editor/asset_library.html', {'assets': assets, 'form': form, 'site': tenant_site})

def asset_delete_view(request, asset_id):
    if request.method == 'POST':
        workspace = WorkspaceService.get_current_workspace(request)
        # 🟢 SECURED: IDOR patched by enforcing workspace boundary
        asset = get_object_or_404(MediaAsset, id=asset_id, workspace=workspace)
        asset_name = asset.file_path.name.split('/')[-1]
        
        asset.delete()
        
        # 🟢 AUDIT LOG
        AuditService.log(
            request=request, workspace=workspace, action="ASSET_DELETED",
            resource_type="MediaAsset", resource_id=None,
            metadata={"file_name": asset_name}
        )
        messages.warning(request, f"🗑️ Asset '{asset_name}' deleted.")
    return redirect('lumo_sites:asset_library')


# =====================================================================
# 6. NAVIGATION MENUS
# =====================================================================
def navigation_manager_view(request):
    workspace = WorkspaceService.get_current_workspace(request)
    tenant_site = getattr(workspace, "website", None) if workspace else None
    
    if not tenant_site:
        return HttpResponse("No site provisioned for this workspace yet.")
        
    menus = SiteMenu.objects.filter(site=tenant_site).prefetch_related('items')
    
    # 🟢 FIX 1: Auto-provision default menus if missing (Prevents Blank Page)
    if not menus.exists():
        with transaction.atomic():
            SiteMenu.objects.create(workspace=workspace, site=tenant_site, name="Main Navigation")
            SiteMenu.objects.create(workspace=workspace, site=tenant_site, name="Footer Menu")
        menus = SiteMenu.objects.filter(site=tenant_site).prefetch_related('items')
    
    if request.method == 'POST':
        # ... (বাকি কোড অপরিবর্তিত থাকবে)
        form = SiteMenuItemForm(request.POST)
        menu_id = request.POST.get('menu_id')
        target_menu = get_object_or_404(SiteMenu, id=menu_id, site=tenant_site)
        
        if form.is_valid():
            item = form.save(commit=False)
            item.menu = target_menu
            item.save()
            
            # 🟢 AUDIT LOG
            AuditService.log(
                request=request, workspace=tenant_site.workspace, action="MENU_LINK_ADDED",
                resource_type="SiteMenuItem", resource_id=str(item.id),
                metadata={"link_label": item.label, "menu_name": target_menu.name}
            )
            messages.success(request, f"🔗 Link '{item.label}' added to {target_menu.name}!")
            return redirect('lumo_sites:navigation_manager')
    else:
        form = SiteMenuItemForm()
    return render(request, 'lumo_sites/editor/navigation_manager.html', {'menus': menus, 'form': form, 'site': tenant_site})

def navigation_item_delete(request, item_id):
    if request.method == 'POST':
        workspace = WorkspaceService.get_current_workspace(request)
        # 🟢 SECURED: IDOR patched by enforcing workspace boundary
        item = get_object_or_404(SiteMenuItem, id=item_id, workspace=workspace)
        menu_name = item.menu.name
        label = item.label
        
        item.delete()
        
        # 🟢 AUDIT LOG
        AuditService.log(
            request=request, workspace=workspace, action="MENU_LINK_DELETED",
            resource_type="SiteMenuItem", resource_id=None,
            metadata={"link_label": label, "menu_name": menu_name}
        )
        messages.warning(request, f"🗑️ Link removed from {menu_name}.")
    return redirect('lumo_sites:navigation_manager')


# =====================================================================
# 7. THEME STORE (Marketplace)
# =====================================================================

@login_required(login_url='/login/')
def theme_store_view(request):
    sitekits = SiteKit.objects.all().prefetch_related('versions')
    return render(request, 'lumo_sites/editor/theme_store.html', {'sitekits': sitekits})

@transaction.atomic
def install_theme_view(request, version_id):
    # 🟢 SECURED: Deterministic Workspace Provisioning
    workspace = WorkspaceService.get_current_workspace(request)
    if not workspace:
        messages.error(request, "No active workspace found.")
        return redirect('saas_core:dashboard_home')
        
    version = get_object_or_404(SiteKitVersion, id=version_id)
    
    tenant_site, created = TenantSite.objects.get_or_create(
        workspace=workspace,
        defaults={'active_kit_version': version, 'active_preset': version.default_preset}
    )
    
    if not created:
        tenant_site.active_kit_version = version
        tenant_site.active_preset = version.default_preset
        tenant_site.save()
        
    manifests = version.manifest.all()
    for m in manifests:
        # 🟢 FIX 1: _base_manager ব্যবহার করে Tenant Filter বাইপাস করা হলো যাতে Legacy ডেটা দেখা যায় 
        page, p_created = TenantPage._base_manager.get_or_create(
            site=tenant_site, 
            slug=m.page_slug,
            defaults={
                'title': m.page_slug.replace('-', ' ').title(),
                'workspace': workspace
            }
        )
        
        # 🟢 Self-Healing: পেজটি আগে থেকে থাকলে এবং workspace ফাঁকা থাকলে আপডেট করে দেওয়া
        if not p_created and not page.workspace_id:
            page.workspace = workspace
            page.save(update_fields=['workspace'])

        # 🟢 FIX 2: Revision-এর ক্ষেত্রেও একই লজিক
        revision, r_created = PageRevision._base_manager.get_or_create(
            page=page, 
            status=RevisionStatus.DRAFT, 
            defaults={
                'version_number': 1,
                'workspace': workspace
            }
        )
        
        if not r_created and not revision.workspace_id:
            revision.workspace = workspace
            revision.save(update_fields=['workspace'])

        # পুরানো সেকশন ক্লিয়ার করে নতুন থিমের সেকশন বসানো
        TenantPageSection._base_manager.filter(revision=revision).delete()
        
        TenantPageSection.objects.create(
            revision=revision, 
            section_version=m.section_version, 
            sort_order=m.default_sort_order,
            is_visible=m.is_required, 
            content_json=m.starter_content_json,
            workspace=workspace
        )
        
    # 🟢 AUDIT LOG
    AuditService.log(
        request=request, 
        workspace=workspace, 
        action="theme.installed",
        resource_type="SiteKitVersion", 
        resource_id=str(version.id),
        status="SUCCESS"
    )
    messages.success(request, f"🚀 '{version.kit.name}' থিমটি সফলভাবে ইনস্টল হয়েছে!")
    return redirect('lumo_sites:builder_dashboard')


def domain_verify_action_view(request, domain_id):
    if request.method == 'POST':
        workspace = WorkspaceService.get_current_workspace(request)
        domain = get_object_or_404(SiteDomain, id=domain_id, workspace=workspace)
        
        # Cloudflare/DNS Verification Logic
        is_verified = CloudflareService.verify_domain(domain)
        if is_verified:
            domain.status = DomainStatus.VERIFIED
            domain.save()
            messages.success(request, "Domain verified successfully!")
        else:
            messages.error(request, "DNS records not found. Please wait a few minutes.")
            
    return redirect('lumo_sites:domain_manager')

from django.db.models import Max

# 🟢 SPRINT 3: The Dedicated Page Builder Workspace
def page_builder_view(request, page_id):
    workspace = WorkspaceService.get_current_workspace(request)
    tenant_site = getattr(workspace, "website", None) if workspace else None
    
    if not tenant_site:
        return redirect('lumo_sites:builder_dashboard')
        
    page = get_object_or_404(TenantPage, id=page_id, site=tenant_site, is_deleted=False)
    
    # STRICT RULE: Always work on the Draft Revision
    draft_revision = PageRevisionService.get_or_create_draft(page)
    
    # 🟢 FIX: Ensure we only fetch sections that are NOT deleted
    sections = TenantPageSection.objects.filter(revision=draft_revision, is_deleted=False).order_by('sort_order')
    
    # Fetch Atomic Sections for the Library Modal
    atomic_versions = AtomicSectionVersion.objects.select_related('section').order_by('section__category', 'section__name')
    
    context = {
        'site': tenant_site,
        'page': page,
        'draft_revision': draft_revision,
        'sections': sections,
        'atomic_versions': atomic_versions
    }
    return render(request, 'lumo_sites/editor/page_builder.html', context)

# 🟢 SPRINT 3: The Section CRUD Link (Add Section)
def section_add_view(request, revision_id, version_id):
    workspace = WorkspaceService.get_current_workspace(request)
    
    if request.method == 'POST':
        revision = get_object_or_404(PageRevision, id=revision_id, workspace=workspace, status=RevisionStatus.DRAFT)
        version = get_object_or_404(AtomicSectionVersion, id=version_id)
        
        last_order = TenantPageSection.objects.filter(revision=revision).aggregate(Max('sort_order'))['sort_order__max']
        next_order = (last_order or 0) + 1
        
        # 🟢 PHASE 1 FIX: Generate safe skeleton instead of copying raw schema
        safe_content_json = generate_empty_content_from_schema(version.default_schema_json)
        
        new_section = TenantPageSection.objects.create(
            workspace=workspace,
            revision=revision,
            section_version=version,
            sort_order=next_order,
            is_visible=True,
            content_json=safe_content_json # Use the safe skeleton
        )
        
        AuditService.log(
            request=request, workspace=workspace, action="SECTION_ADDED",
            resource_type="TenantPageSection", resource_id=str(new_section.id),
            metadata={"section_name": version.section.name, "page_id": str(revision.page.id)}
        )
        
        messages.success(request, f"✨ '{version.section.name}' added successfully!")
        return redirect('lumo_sites:page_builder', page_id=revision.page.id)
        
    return redirect('lumo_sites:builder_dashboard')

# 🟢 SPRINT 4: Section Delete
def section_delete_view(request, section_id):
    workspace = WorkspaceService.get_current_workspace(request)
    
    if request.method == 'POST':
        # SECURITY: Ensure section belongs to current workspace
        section = get_object_or_404(TenantPageSection, id=section_id, workspace=workspace)
        page_id = section.revision.page.id
        section_name = section.section_version.section.name
        
        # Delete the section (LumoBaseModel will handle soft delete automatically)
        section.delete()
        
        AuditService.log(
            request=request, workspace=workspace, action="SECTION_DELETED",
            resource_type="TenantPageSection", resource_id=str(section_id),
            metadata={"section_name": section_name, "page_id": str(page_id)}
        )
        
        messages.warning(request, f"🗑️ Section '{section_name}' has been removed from the page.")
        return redirect('lumo_sites:page_builder', page_id=page_id)
        
    return redirect('lumo_sites:builder_dashboard')


# 🟢 SPRINT 4: Section Reorder (Move Up/Down)
def section_reorder_view(request, section_id, direction):
    workspace = WorkspaceService.get_current_workspace(request)
    
    if request.method == 'POST':
        current_section = get_object_or_404(TenantPageSection, id=section_id, workspace=workspace)
        revision = current_section.revision
        page_id = revision.page.id
        
        adjacent_section = None
        
        # Find the adjacent section safely using relative ordering
        if direction == 'up':
            adjacent_section = TenantPageSection.objects.filter(
                revision=revision, sort_order__lt=current_section.sort_order, is_deleted=False
            ).order_by('-sort_order').first()
        elif direction == 'down':
            adjacent_section = TenantPageSection.objects.filter(
                revision=revision, sort_order__gt=current_section.sort_order, is_deleted=False
            ).order_by('sort_order').first()
            
        if adjacent_section:
            with transaction.atomic():
                # 🟢 PHASE 4 FIX: 3-Step Swap to prevent UniqueConstraint violation
                orig_current_order = current_section.sort_order
                orig_adjacent_order = adjacent_section.sort_order
                
                # Step 1: Temporarily "park" current_section out of the way
                current_section.sort_order = -9999
                current_section.save(update_fields=['sort_order'])
                
                # Step 2: Move adjacent_section safely into the vacated spot
                adjacent_section.sort_order = orig_current_order
                adjacent_section.save(update_fields=['sort_order'])
                
                # Step 3: Move current_section into its final intended spot
                current_section.sort_order = orig_adjacent_order
                current_section.save(update_fields=['sort_order'])
                
            messages.success(request, f"↕️ Section flow updated.")
            
        return redirect('lumo_sites:page_builder', page_id=page_id)
        
    return redirect('lumo_sites:builder_dashboard')