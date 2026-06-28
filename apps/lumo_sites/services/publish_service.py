import hashlib
from django.core.cache import cache
from django.template.loader import render_to_string
from apps.lumo_sites.models import FormDefinition, TenantPage, PagePublishedSnapshot, TenantPageSection, PageRevision, RevisionStatus
from django.core.exceptions import ValidationError

class PublishService:
    """
    Enterprise Publishing Engine.
    Converts JSON published sections into a final static HTML snapshot and handles cache invalidation.
    """
    
    @staticmethod
    def publish_page(page_id, user=None):
        try:
            page = TenantPage.objects.get(id=page_id)
            workspace = page.workspace
            site = page.site
            
            # 🟢 FIX 1: Query the PUBLISHED revision, not the page directly
            published_revision = PageRevision.objects.filter(
                page=page, status=RevisionStatus.PUBLISHED, is_deleted=False
            ).order_by('-updated_at').first()

            if not published_revision:
                return False, "No published revision found to generate snapshot."

            # 🟢 FIX 2: Use correct fields: 'revision', 'is_visible', and 'sort_order'
            sections = TenantPageSection.objects.filter(
                revision=published_revision, is_visible=True, is_deleted=False
            ).order_by('sort_order')
            
            rendered_sections_html = []
            page_data_backup = []
            
            for section in sections:
                # 🟢 FIX 3: Use current schema fields (content_json, html_template_path)
                context = {
                    'data': section.content_json, 
                    'site': site,
                    'preset': site.active_preset
                }
                
                # ─── ✅ PATCHED FORM RESOLVER ───
                # Safely extract form_definition_id – handle None or missing content_json
                form_id = section.content_json.get('form_definition_id') if section.content_json else None
                if form_id and isinstance(form_id, str):
                    try:
                        context['dynamic_form'] = FormDefinition._base_manager.get(id=form_id, site=site)
                    except (FormDefinition.DoesNotExist, ValidationError, ValueError):
                        # Silently ignore – form not found or invalid UUID – page still renders
                        pass
                # ──────────────────────────────

                template_name = section.section_version.html_template_path
                
                try:
                    # Optional: pass dummy request or empty context if render_to_string needs it
                    section_html = render_to_string(template_name, context)
                    rendered_sections_html.append(section_html)
                except Exception as template_err:
                    print(f"Template Error for {template_name}: {template_err}")
                    continue
                
                page_data_backup.append({
                    'id': str(section.id),
                    'section_code': section.section_version.section.code,
                    'content_json': section.content_json,
                    'sort_order': section.sort_order
                })

            full_body_html = "\n".join(rendered_sections_html)
            
            # 🟢 FIX 4: Assuming base_tenant_site.html is your base template
            # If you don't actually render the full layout in the snapshot, you can just save full_body_html
            try:
                final_html = render_to_string("lumo_sites/layouts/base_tenant_site.html", {
                    'page': page,
                    'site': site,
                    'rendered_sections': full_body_html
                })
            except Exception:
                # Fallback if base_tenant_site requires request object or specific context
                final_html = full_body_html
            
            checksum = hashlib.sha256(final_html.encode('utf-8')).hexdigest()
            
            snapshot, created = PagePublishedSnapshot.objects.get_or_create(
                page=page,
                defaults={'workspace': workspace}
            )
            
            snapshot.rendered_html = final_html
            snapshot.page_data_snapshot = page_data_backup
            if not created:
                snapshot.version += 1
            snapshot.published_by = user
            snapshot.checksum = checksum
            snapshot.save()
            
            # 5. Cache Invalidation
            PublishService._invalidate_page_cache(page)
            
            return True, "Page published and snapshot generated successfully!"
            
        except TenantPage.DoesNotExist:
            return False, "Page not found."
        except Exception as e:
            import traceback
            print("Publish Error:", traceback.format_exc())
            return False, str(e)

    @staticmethod
    def _invalidate_page_cache(page):
        """Clears the Redis cache for all domains associated with this site/page."""
        domains = page.site.workspace.domains.filter(is_deleted=False) # 🟢 FIX: Used related_name 'domains'
        slug = page.slug if page.slug != 'home' else ''
        
        for domain in domains:
            cache_key_page = f"page_html:{domain.domain_name}:{slug if slug else 'home'}"
            cache.delete(cache_key_page)
            print(f"Invalidated cache: {cache_key_page}")