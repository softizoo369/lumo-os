import json
from django.core.management.base import BaseCommand
from apps.lumo_sites.models import AtomicSection, AtomicSectionVersion, DataSourceType

class Command(BaseCommand):
    help = 'Seeds the database with core Enterprise Atomic Sections'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING("Starting Atomic Section Seeding..."))

        # 1. HERO SECTION
        hero, _ = AtomicSection.objects.get_or_create(
            code="section_hero", defaults={"name": "Hero Section", "category": "Header"}
        )
        AtomicSectionVersion.objects.update_or_create(
            section=hero, version_number="v1.0",
            defaults={
                "html_template_path": "lumo_sites/sections/hero/hero_v1.html",
                "capabilities": ["supports_background_image", "supports_dark_mode"],
                "is_i18n_enabled": True,
                "default_schema_json": {
                    "heading": {"type": "text", "label": "Main Headline", "required": True},
                    "subheading": {"type": "textarea", "label": "Sub Headline", "required": False},
                    "primary_button_text": {"type": "text", "label": "Button Text", "default": "Get Started"},
                    "primary_button_url": {"type": "url", "label": "Button Link", "default": "/contact"},
                    "background_image": {"type": "image", "label": "Background Image", "required": False}
                }
            }
        )

        # 2. CONTACT FORM (The CRM Bridge)
        contact, _ = AtomicSection.objects.get_or_create(
            code="section_contact_form", defaults={"name": "Contact & Form", "category": "Conversion"}
        )
        AtomicSectionVersion.objects.update_or_create(
            section=contact, version_number="v1.0",
            defaults={
                "html_template_path": "lumo_sites/sections/contact/form_v1.html",
                "capabilities": ["supports_container_width"],
                "is_i18n_enabled": True,
                "default_schema_json": {
                    "section_title": {"type": "text", "label": "Title", "default": "Contact Us"},
                    "description": {"type": "textarea", "label": "Description", "required": False},
                    "form_definition_id": {"type": "reference", "model": "lumo_sites.FormDefinition", "label": "Select Form", "required": True}
                }
            }
        )

        # 3. PRODUCT GRID (E-Commerce Bridge)
        products, _ = AtomicSection.objects.get_or_create(
            code="section_product_grid", defaults={"name": "Featured Products", "category": "Dynamic"}
        )
        AtomicSectionVersion.objects.update_or_create(
            section=products, version_number="v1.0",
            defaults={
                "html_template_path": "lumo_sites/sections/ecommerce/product_grid_v1.html",
                "data_source_type": DataSourceType.PRODUCTS,
                "capabilities": ["supports_dark_mode"],
                "is_i18n_enabled": True,
                "default_schema_json": {
                    "section_title": {"type": "text", "label": "Title", "default": "Featured Products"},
                    "item_limit": {"type": "number", "label": "Products to display", "default": 4},
                    "show_add_to_cart": {"type": "boolean", "label": "Show 'Add to Cart' button", "default": True}
                }
            }
        )

        self.stdout.write(self.style.SUCCESS("✅ Successfully seeded Core Atomic Sections!"))