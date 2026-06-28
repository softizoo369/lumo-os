from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from apps.lumo_sites.models import TenantPageSection, FormDefinition
from django.core.exceptions import ValidationError


class SiteRenderingEngine:
    """
    Enterprise Rendering Engine: Converts JSON Content + HTML Templates 
    into a production-ready website string.
    """

    @staticmethod
    def render_revision(revision, tenant_site):
        """
        Takes a specific PageRevision (Draft or Published) and renders the full HTML.
        """
        # 🟢 N+1 Query Protection: We fetch the section and its version in a single query
        sections = (
            TenantPageSection.objects
            .filter(revision=revision, is_visible=True)
            .select_related('section_version', 'section_version__section')
            .order_by('sort_order')
        )

        rendered_fragments = []

        for section in sections:
            template_path = section.section_version.html_template_path
            
            # The Data Context passed to Jinja
            context = {
                'data': section.content_json,
                'site': tenant_site,
                'preset': tenant_site.active_preset,
            }
            
            # ─── ✅ PATCHED FORM RESOLVER ───
            # Safely extract form_definition_id – handle None or missing content_json
            form_id = section.content_json.get('form_definition_id') if section.content_json else None
            if form_id and isinstance(form_id, str):
                try:
                    context['dynamic_form'] = FormDefinition.objects.get(id=form_id)
                except (FormDefinition.DoesNotExist, ValidationError, ValueError):
                    # Silently ignore – form not found or invalid UUID – page still renders
                    pass
            # ──────────────────────────────
            
            try:
                # Render the individual atomic section
                fragment = render_to_string(template_path, context)
                rendered_fragments.append(fragment)
            except Exception as e:
                # 🟢 Enterprise Fail-Safe: If one section crashes, don't crash the whole site!
                error_comment = f"<!-- Error rendering section: {str(e)} -->"
                rendered_fragments.append(error_comment)

        # Stitch all sections together into one block of HTML
        return mark_safe("".join(rendered_fragments))