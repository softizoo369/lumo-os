from django.db import transaction
from django.utils.text import slugify
from apps.lumo_sites.models import (
    TenantSite, TenantPage, PageRevision, TenantPageSection,
    SiteKitManifest, RevisionStatus, SiteMenu, SiteMenuItem, FormDefinition
)

# =====================================================================
# SECTION PLUGIN PROVISIONERS (The Strategy Pattern)
# =====================================================================
class BaseSectionProvisioner:
    """Base class for all section-specific provisioning logic."""
    @staticmethod
    def process(tenant_site, manifest_item, generated_content):
        return generated_content

class ContactFormProvisioner(BaseSectionProvisioner):
    """Handles the creation of forms specific to the kit's starter content."""
    @staticmethod
    def process(tenant_site, manifest_item, generated_content):
        # We look into the starter_content to see if a form schema is provided
        form_data = manifest_item.starter_content_json.get('form_config', {})
        
        form_name = form_data.get('name', f"{tenant_site.workspace.name} Contact Form")
        form_schema = form_data.get('schema', [
            {"name": "name", "type": "text", "required": True},
            {"name": "email", "type": "email", "required": True}
        ])

        # Create the dynamic form in the database
        new_form = FormDefinition.objects.create(
            site=tenant_site,
            name=form_name,
            schema_json=form_schema
        )
        
        # Inject the newly created Form ID into the section content
        generated_content["form_definition_id"] = str(new_form.id)
        return generated_content

class ProductGridProvisioner(BaseSectionProvisioner):
    """Future-proof handler for E-commerce product grids."""
    @staticmethod
    def process(tenant_site, manifest_item, generated_content):
        # Logic to auto-link a default product collection could go here
        generated_content["collection_id"] = "all"
        return generated_content


# 🟢 The Registry: Maps section codes to their specific plugins
PROVISIONING_PLUGINS = {
    "section_contact_form": ContactFormProvisioner,
    "section_product_grid": ProductGridProvisioner,
    # section_booking: BookingProvisioner, (Future)
}

# =====================================================================
# CORE ECOSYSTEM PROVISIONER (Orchestrator)
# =====================================================================
class SiteProvisioningService:
    """
    Enterprise Ecosystem Provisioner (Multi-Page & Plugin Driven).
    """

    @staticmethod
    @transaction.atomic
    def provision_new_site(workspace, active_kit_version):
        
        # 1. Core Tenant Site Creation
        tenant_site = TenantSite.objects.create(
            workspace=workspace,
            active_kit_version=active_kit_version,
            active_preset=active_kit_version.default_preset
        )

        # 2. Global Menu Provisioning
        header_menu = SiteMenu.objects.create(site=tenant_site, name="Main Header")
        footer_menu = SiteMenu.objects.create(site=tenant_site, name="Footer Legal")

        # 3. Fetch the Multi-Page Blueprint
        manifest_items = SiteKitManifest.objects.filter(
            kit_version=active_kit_version
        ).select_related('section_version__section').order_by('page_slug', 'default_sort_order')

        # Dictionary to keep track of created pages and their Draft revisions
        page_revisions_map = {}
        sections_to_create = []
        menu_items_to_create = []
        created_pages_set = set() # To track unique pages for the menu

        # 4. The Assembly Line (Processing the Blueprint)
        for item in manifest_items:
            slug = item.page_slug
            
            # --- Page & Revision Creation (Lazy Load) ---
            if slug not in page_revisions_map:
                page_title = slug.replace('-', ' ').title()
                if slug == 'home':
                    page_title = "Home"

                new_page = TenantPage.objects.create(
                    site=tenant_site,
                    title=page_title,
                    slug=slug,
                    seo_title=f"{page_title} - {workspace.name}"
                )
                
                new_revision = PageRevision.objects.create(
                    page=new_page,
                    version_number=1,
                    status=RevisionStatus.DRAFT
                )
                page_revisions_map[slug] = new_revision
                
                # Prepare Menu Items (We will bulk create them later)
                if slug not in created_pages_set:
                    menu_url = "/" if slug == 'home' else f"/{slug}"
                    menu_items_to_create.append(
                        SiteMenuItem(menu=header_menu, label=page_title, url=menu_url, sort_order=len(created_pages_set) + 1)
                    )
                    created_pages_set.add(slug)

            # --- Section Content Assembly ---
            current_revision = page_revisions_map[slug]
            section_code = item.section_version.section.code
            
            # Start with the starter content defined in the kit manifest
            generated_content = item.starter_content_json.copy()

            # 🟢 The Plugin Orchestrator: Route to specific provisioner if it exists
            handler_class = PROVISIONING_PLUGINS.get(section_code, BaseSectionProvisioner)
            generated_content = handler_class.process(tenant_site, item, generated_content)

            # Prepare the section for bulk creation
            section = TenantPageSection(
                revision=current_revision,
                section_version=item.section_version,
                sort_order=item.default_sort_order,
                is_visible=item.is_required,
                content_json=generated_content
            )
            sections_to_create.append(section)

        # 5. Database Commit (Bulk Inserts for Speed)
        if menu_items_to_create:
            SiteMenuItem.objects.bulk_create(menu_items_to_create)
            
        if sections_to_create:
            TenantPageSection.objects.bulk_create(sections_to_create)

        return tenant_site