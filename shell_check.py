# 1. Shell এ পেস্ট করো
# python manage.py shell

import inspect
from django.apps import apps

# ====== যে মডেলগুলো inspect করতে চাও ======
MODEL_NAMES = [
    "SubscriptionPlan",
    "Workspace",
    "ThemePreset",
    "SiteKitVersion",
    "AtomicSection",
    "AtomicSectionVersion",
    "TenantSite",
    "TenantPage",
    "PageRevision",
    "TenantPageSection",
]

# ====== ফ্যাক্টরি কোড জেনারেট ======
def generate_factories():
    lines = []
    lines.append("# apps/lumo_sites/tests/factories.py")
    lines.append("# Auto‑generated from real models – DO NOT EDIT MANUALLY")
    lines.append("")
    lines.append("from django.test import TestCase")
    lines.append("from apps.saas_core.models.tenant import Workspace")
    lines.append("from apps.saas_core.models.subscription import SubscriptionPlan")
    lines.append("from apps.lumo_sites.models import (")
    lines.append("    TenantSite, TenantPage, PageRevision, TenantPageSection,")
    lines.append("    ThemePreset, SiteKitVersion, AtomicSection, AtomicSectionVersion,")
    lines.append("    RevisionStatus")
    lines.append(")")
    lines.append("")

    # Helper to get field info
    def field_info(model):
        required = []
        optional = []
        for f in model._meta.fields:
            if f.auto_created:
                continue
            if f.name in ["id", "created_at", "updated_at"]:
                continue
            if f.null or f.blank or f.has_default():
                optional.append(f.name)
            else:
                required.append(f.name)
        return required, optional

    # Generate factory for each model
    for model_name in MODEL_NAMES:
        try:
            model = apps.get_model("lumo_sites", model_name)
        except LookupError:
            # maybe in saas_core
            try:
                model = apps.get_model("saas_core", model_name)
            except LookupError:
                continue

        req, opt = field_info(model)
        func_name = f"create_{model_name.lower()}"
        lines.append(f"def {func_name}({', '.join(req) if req else ''}, **kwargs):")
        lines.append(f'    """Factory for {model_name}"""')
        # Create instance with required fields + kwargs
        args = []
        for f in req:
            # Guess a default value based on field type
            field_obj = model._meta.get_field(f)
            if field_obj.is_relation:
                # ForeignKey – need related factory
                rel_model = field_obj.related_model.__name__
                if rel_model in MODEL_NAMES:
                    rel_factory = f"create_{rel_model.lower()}()"
                else:
                    rel_factory = f"# TODO: create {rel_model}"
                args.append(f"{f}={rel_factory}")
            else:
                # Try to guess a default
                if "char" in field_obj.__class__.__name__.lower():
                    args.append(f'{f}="{f}_default"')
                elif "int" in field_obj.__class__.__name__.lower():
                    args.append(f"{f}=0")
                elif "bool" in field_obj.__class__.__name__.lower():
                    args.append(f"{f}=False")
                else:
                    args.append(f"{f}=None  # TODO: set proper default")
        if args:
            lines.append(f"    defaults = {{ {', '.join(args)} }}")
        else:
            lines.append("    defaults = {}")
        lines.append("    defaults.update(kwargs)")
        lines.append(f"    return {model.__name__}.objects.create(**defaults)")
        lines.append("")

    # Special: create_default_plan to handle signals
    lines.append("def create_default_plan():")
    lines.append('    """Ensure default plan exists for signal handling"""')
    lines.append("    plan, _ = SubscriptionPlan.objects.get_or_create(")
    lines.append("        code='default',")
    lines.append("        defaults={")
    lines.append("            'name': 'Default Plan',")
    lines.append("            'is_active': True,")
    lines.append("            'is_default': True,")
    lines.append("            'is_public': True,")
    lines.append("            'is_free_plan': True,")
    lines.append("            'trial_days': 0,")
    lines.append("            'max_users': 10,")
    lines.append("            'max_companies': 1,")
    lines.append("            'max_customers': 100,")
    lines.append("            'max_storage_mb': 1024,")
    lines.append("            'sort_order': 1,")
    lines.append("        }")
    lines.append("    )")
    lines.append("    return plan")
    lines.append("")

    # Override create_workspace to ensure plan exists
    lines.append("def create_workspace(name='Test Workspace', **kwargs):")
    lines.append("    create_default_plan()")
    lines.append("    return Workspace.objects.create(name=name, **kwargs)")
    lines.append("")

    # Add a convenience function to create full site with all dependencies
    lines.append("def create_full_test_site():")
    lines.append("    workspace = create_workspace()")
    lines.append("    theme = create_themeset(workspace)    # you may need to adjust")
    lines.append("    kit = create_sitekitversion(workspace)")
    lines.append("    site = TenantSite.objects.create(")
    lines.append("        workspace=workspace,")
    lines.append("        site_name='Test Site',")
    lines.append("        slug='test-site',")
    lines.append("        active_theme=theme,")
    lines.append("        active_kit=kit,")
    lines.append("    )")
    lines.append("    page = TenantPage.objects.create(")
    lines.append("        workspace=workspace,")
    lines.append("        site=site,")
    lines.append("        title='Test Page',")
    lines.append("        slug='test-page',")
    lines.append("        is_deleted=False,")
    lines.append("    )")
    lines.append("    return workspace, site, page")
    lines.append("")

    return "\n".join(lines)

# ====== Print the factories.py content ======
print(generate_factories())