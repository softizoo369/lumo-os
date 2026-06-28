# from apps.lumo_sites.models import TenantPage, PageRevision, SiteDomain

# print("========== RUNTIME EVIDENCE REPORT ==========")

# print("\n[1] ALL TENANT PAGES:")
# all_pages = TenantPage._base_manager.values('id', 'title', 'slug', 'site_id', 'workspace_id')
# for p in all_pages: print(p)

# print("\n[2] HOME PAGES (slug='home'):")
# home_pages = TenantPage._base_manager.filter(slug='home')
# if not home_pages.exists():
#     print("NO HOMEPAGE FOUND IN DATABASE.")
    
# for p in home_pages:
#     print(f"- Page ID: {p.id}")
#     print(f"  Site ID: {p.site_id}")
#     print(f"  Workspace ID: {p.workspace_id}")
#     print(f"  Title: {p.title}")
    
#     revisions = PageRevision._base_manager.filter(page=p)
#     print("  Revisions:")
#     if not revisions.exists():
#         print("    None")
#     for r in revisions:
#         print(f"    Revision ID: {r.id} | Status: {r.status} | Created: {r.created_at}")
        
#     drafts = revisions.filter(status='DRAFT').count()
#     published = revisions.filter(status='PUBLISHED').count()
#     archived = revisions.filter(status='ARCHIVED').count()
#     print(f"  Counts: DRAFT={drafts} | PUBLISHED={published} | ARCHIVED={archived}")

# print("\n[3] EXACT LOOKUPS FOR 'mycompany.local':")
# try:
#     domain = SiteDomain._base_manager.get(domain_name='mycompany.local')
#     site = domain.workspace.website
#     print(f"Target Site ID: {site.id}")
    
#     # Simulate: page = TenantPage._base_manager.filter(site=site, slug='home', is_deleted=False).first()
#     target_page = TenantPage._base_manager.filter(site=site, slug='home', is_deleted=False).first()
#     print(f"Exact Page Returned: {target_page.id if target_page else 'None'}")
    
#     target_rev = None
#     if target_page:
#         # Simulate: revision = PageRevision._base_manager.filter(page=page, status='PUBLISHED', is_deleted=False).order_by('-created_at').first()
#         target_rev = PageRevision._base_manager.filter(page=target_page, status='PUBLISHED', is_deleted=False).order_by('-created_at').first()
#         print(f"Exact Revision Returned: {target_rev.id if target_rev else 'None'}")
    
#     print("\n[4] VERDICT:")
#     if not target_page:
#         print("STATE: A. Homepage missing?")
#         print("EXECUTION BRANCH: Connected Successfully page (Returns HttpResponse '...Your domain is successfully connected!...')")
#     elif not target_rev:
#         print("STATE: B. Homepage exists but no published revision?")
#         print("EXECUTION BRANCH: Under Construction page (Returns HttpResponse '<h1>🚧 Under Construction</h1>')")
#     else:
#         print("STATE: C. Homepage and published revision both exist?")
#         print("EXECUTION BRANCH: Full Rendered Page (Returns render 'lumo_sites/layouts/base_tenant_site.html')")

# except Exception as e:
#     print(f"Error during trace: {e}")
    
# print("===========================================")


# import sys
# import traceback
# from django.template.loader import render_to_string
# from django.test import RequestFactory
# from apps.lumo_sites.models import PageRevision, TenantPageSection

# print("\n========== RUNTIME TRACE ==========")

# revision_id = 'bb9f1750-98e3-45ad-b1f9-85024d3ab7db'
# revision = PageRevision._base_manager.filter(id=revision_id).first()

# if not revision:
#     print(f"[HALT] Revision {revision_id} not found.")
#     sys.exit()

# page = revision.page
# site = page.site
# sections = TenantPageSection._base_manager.filter(revision=revision, is_visible=True, is_deleted=False).order_by('sort_order')

# print(f"\n[1] TenantPageSection count: {sections.count()}")

# request = RequestFactory().get(f"/{page.slug}")
# rendered_sections = ""

# print("\n[2] SECTION TRACE:")
# for sec in sections:
#     sec_type = sec.section_version.section.name
#     template_name = sec.section_version.html_template_path
#     print(f"\n--- Section ID: {sec.id} ---")
#     print(f"Type: {sec_type}")
#     print(f"Template: {template_name}")
    
#     context = {'data': sec.content_json, 'site': site, 'preset': site.active_preset, 'site_menu': None}
    
#     try:
#         out = render_to_string(template_name, context, request=request)
#         print("Result: SUCCESS")
#         rendered_sections += out
#     except Exception as e:
#         print(f"Result: FAILED -> {type(e).__name__}: {str(e)}")

# print("\n[3] FINAL RENDER TRACE: lumo_sites/layouts/base_tenant_site.html")
# final_context = {
#     'site': site, 'page': page, 'rendered_sections': rendered_sections, 
#     'is_preview': False, 'main_menu': None, 'footer_menu': None
# }

# try:
#     final_out = render_to_string('lumo_sites/layouts/base_tenant_site.html', final_context, request=request)
#     print("Result: SUCCESS")
# except Exception as e:
#     print(f"Result: FATAL HALT -> {type(e).__name__}: {str(e)}")
#     print("\n[TRACEBACK]:")
#     traceback.print_exc(limit=2)
# print("===================================\n")


# from apps.lumo_sites.models import PageRevision, TenantPageSection

# page_id = '4757d45d-5539-42f7-af76-f8eb122c9df6'
# print(f"{'REV':<5} | {'STATUS':<10} | {'TOTAL SECTIONS':<15} | {'NULL WORKSPACE SECTIONS'}")
# print("-" * 60)

# for rev in PageRevision._base_manager.filter(page_id=page_id).order_by('version_number'):
#     total = TenantPageSection._base_manager.filter(revision=rev).count()
#     null_ws = TenantPageSection._base_manager.filter(revision=rev, workspace__isnull=True).count()
#     print(f"V{rev.version_number:<3} | {rev.status:<10} | {total:<15} | {null_ws}")


# from apps.lumo_sites.models import TenantPage, PageRevision, TenantPageSection

# print("========== SURGICAL DATA RECOVERY ==========")

# page_id = '4757d45d-5539-42f7-af76-f8eb122c9df6'
# page = TenantPage._base_manager.get(id=page_id)
# authoritative_workspace_id = page.workspace_id or page.site.workspace_id

# # ১. Source Revision (V2) খুঁজে বের করা
# source_rev = PageRevision._base_manager.filter(page=page, version_number=2).first()

# # ২. Target Draft (V5 বা বর্তমান ড্রাফট) খুঁজে বের করা
# target_draft = PageRevision._base_manager.filter(page=page, status='DRAFT').order_by('-version_number').first()

# if not source_rev:
#     print("❌ Error: Source Revision V2 not found.")
# elif not target_draft:
#     print("❌ Error: Active Draft not found. Please open the editor to generate a draft first.")
# else:
#     # V2 এর সেকশনগুলো বের করা
#     source_sections = TenantPageSection._base_manager.filter(revision=source_rev)
    
#     if source_sections.count() == 0:
#         print("❌ Error: Source Revision V2 has 0 sections. Cannot recover.")
#     else:
#         print(f"🔄 Found {source_sections.count()} sections in V2. Cloning to V{target_draft.version_number}...")
        
#         # টার্গেট ড্রাফটে আগে থেকে কোনো গার্বেজ সেকশন থাকলে ক্লিয়ার করা
#         TenantPageSection._base_manager.filter(revision=target_draft).delete()
        
#         restored_sections = []
#         for sec in source_sections:
#             restored_sections.append(TenantPageSection(
#                 workspace_id=authoritative_workspace_id,  # 🟢 THE CRITICAL FIX
#                 revision=target_draft,
#                 section_version=sec.section_version,
#                 sort_order=sec.sort_order,
#                 is_visible=sec.is_visible,
#                 content_json=sec.content_json.copy()
#             ))
            
#         # Bulk Insert
#         TenantPageSection.objects.bulk_create(restored_sections)
#         print(f"✅ SUCCESS! Sections restored to Draft V{target_draft.version_number} with valid Workspace ID.")
        
# print("============================================")


# from apps.lumo_sites.models import TenantPage, PageRevision, TenantPageSection
# import sys

# print("========== SAFE SURGICAL DATA RECOVERY ==========")

# page_id = '4757d45d-5539-42f7-af76-f8eb122c9df6'

# # 1. Extract Authoritative Data Source
# try:
#     page = TenantPage._base_manager.select_related('site').get(id=page_id)
#     authoritative_workspace_id = page.site.workspace_id
# except TenantPage.DoesNotExist:
#     print(f"❌ Error: Page {page_id} not found.")
#     sys.exit()

# # 2. Locate Source (V2) and Target (V5)
# source_rev = PageRevision._base_manager.filter(page=page, version_number=2).first()
# target_draft = PageRevision._base_manager.filter(page=page, status='DRAFT').order_by('-version_number').first()

# if not source_rev:
#     print("❌ Error: Source Revision V2 not found.")
# elif not target_draft:
#     print("❌ Error: Active Draft (V5) not found.")
# else:
#     source_sections = TenantPageSection._base_manager.filter(revision=source_rev)
    
#     if source_sections.count() == 0:
#         print("❌ Error: Source Revision V2 has 0 sections.")
#     else:
#         print(f"🔄 Cloning {source_sections.count()} sections from V2 to V{target_draft.version_number}...")
        
#         # 3. Idempotency Check: Purge existing sections on the target draft bypassing TenantManager
#         deleted_count, _ = TenantPageSection._base_manager.filter(revision=target_draft).delete()
#         if deleted_count > 0:
#             print(f"   Cleared {deleted_count} existing garbage sections from target draft.")
        
#         # 4. Prepare explicit section data
#         restored_sections = []
#         for sec in source_sections:
#             restored_sections.append(TenantPageSection(
#                 workspace_id=authoritative_workspace_id,  # Explicitly overriding NULL
#                 revision=target_draft,
#                 section_version_id=sec.section_version_id, 
#                 sort_order=sec.sort_order,
#                 is_visible=sec.is_visible,
#                 content_json=sec.content_json.copy()
#             ))
            
#         # 5. Safe Bulk Insert bypassing TenantManager
#         TenantPageSection._base_manager.bulk_create(restored_sections)
#         print(f"✅ SUCCESS! Sections restored to Draft V{target_draft.version_number} with authoritative workspace_id.")
        
# print("=================================================")


# from apps.lumo_sites.models import TenantPageSection, PageRevision

# draft = PageRevision._base_manager.filter(
#     page_id='4757d45d-5539-42f7-af76-f8eb122c9df6',
#     status='DRAFT'
# ).first()

# print("Draft:", draft.version_number)

# sections = TenantPageSection._base_manager.filter(revision=draft)

# print("Sections:", sections.count())

# for s in sections:
#     print(
#         s.id,
#         s.workspace_id,
#         s.section_version_id
#     )


# from apps.lumo_sites.models import PageRevision

# draft = PageRevision._base_manager.filter(
#     page_id='4757d45d-5539-42f7-af76-f8eb122c9df6',
#     status='DRAFT'
# ).first()

# draft.status = 'PUBLISHED'
# draft.save()

# from apps.lumo_sites.models import PageRevision, TenantPageSection

# for rev in PageRevision._base_manager.filter(
#     page_id='4757d45d-5539-42f7-af76-f8eb122c9df6'
# ).order_by('version_number'):

#     count = TenantPageSection._base_manager.filter(
#         revision=rev
#     ).count()

#     print(
#         rev.version_number,
#         rev.status,
#         count
#     )


# from apps.lumo_sites.models import SiteDomain, TenantPage, PageRevision

# domain = SiteDomain._base_manager.get(
#     domain_name='mycompany.local'
# )

# site = domain.workspace.website

# page = TenantPage._base_manager.filter(
#     site=site,
#     slug='home',
#     is_deleted=False
# ).first()

# revision = PageRevision._base_manager.filter(
#     page=page,
#     status='PUBLISHED',
#     is_deleted=False
# ).order_by('-created_at').first()

# print(page.id)
# print(revision.id)
# print(revision.version_number)


# from apps.lumo_sites.models import TenantPageSection, PageRevision

# rev = PageRevision._base_manager.get(
#     id='775ed383-bf6c-49d4-b536-d2e3c580bba4'
# )

# sec = TenantPageSection._base_manager.filter(
#     revision=rev
# ).first()

# print("Section:", sec.id)
# print("Workspace:", sec.workspace_id)
# print("Version:", sec.section_version_id)
# print("Content:", sec.content_json)
# print("Template:", sec.section_version.html_template_path)
# print("Name:", sec.section_version.section.name)

# from django.template.loader import get_template

# try:
#     get_template(
#         'lumo_sites/sections/ecommerce/product_grid_v1.html'
#     )
#     print("TEMPLATE EXISTS")
# except Exception as e:
#     print(type(e).__name__)
#     print(e)

# from django.template.loader import render_to_string
# from django.contrib.auth.models import AnonymousUser
# from django.test import RequestFactory

# request = RequestFactory().get("/")
# request.user = AnonymousUser()

# try:
#     html = render_to_string(
#         "lumo_sites/sections/ecommerce/product_grid_v1.html",
#         {
#             "data": {},
#             "site": None,
#             "preset": None,
#             "site_menu": None,
#         },
#         request=request,
#     )

#     print("SUCCESS")
#     print(len(html))

# except Exception as e:
#     import traceback
#     traceback.print_exc()


# from apps.lumo_sites.models import TenantPage, PageRevision

# page = TenantPage._base_manager.filter(slug='clinic').first()

# print("PAGE:", page)

# for rev in PageRevision._base_manager.filter(page=page):
#     print(
#         rev.version_number,
#         rev.status
#     )


# from apps.lumo_sites.models import TenantPage, PageRevision, TenantPageSection

# page = TenantPage._base_manager.get(slug='clinic')

# published = PageRevision._base_manager.filter(
#     page=page,
#     status='PUBLISHED'
# ).first()

# print("Revision:", published.id)

# sections = TenantPageSection._base_manager.filter(
#     revision=published
# )

# print("Sections:", sections.count())

# for s in sections:
#     print(
#         s.id,
#         s.section_version.section.name
#     )

# from apps.lumo_sites.models import SiteMenuItem

# for item in SiteMenuItem._base_manager.all():
#     print(
#         item.title,
#         item.url,
#         item.page_id if hasattr(item, "page_id") else None
#     )

# from apps.lumo_sites.models import SiteMenuItem

# for item in SiteMenuItem._base_manager.all():
#     print(item.__dict__)

# from apps.lumo_sites.models import SiteMenuItem

# item = SiteMenuItem._base_manager.get(
#     label="About Us"
# )

# item.url = "/site/about-us/"
# item.save()

# print(item.url)

# from apps.lumo_sites.models import SiteMenuItem


# SiteMenuItem._base_manager.filter(
#     label="About Us"
# ).update(
#     url="/site/about-us/"
# )

# from apps.lumo_sites.models import SiteMenuItem

# item = SiteMenuItem.objects.filter(label="Clinics").first()

# print(item.url)

# from apps.lumo_sites.models import TenantPageSection
# import json

# print("=== STARTING LUMO OS CMS RECOVERY ===")

# # --- Phase 3: Fix Orphaned Sections (Workspace Loss) ---
# print("\n[Phase 3] Auditing Orphaned Sections...")
# orphaned_sections = TenantPageSection._base_manager.filter(workspace__isnull=True)
# orphan_count = orphaned_sections.count()
# print(f"Found {orphan_count} sections with NULL workspace_id.")

# if orphan_count > 0:
#     fixed_count = 0
#     for section in orphaned_sections:
#         if section.revision and section.revision.workspace_id:
#             # Restore the workspace from the parent revision
#             section.workspace_id = section.revision.workspace_id
#             section.save(update_fields=['workspace_id'])
#             fixed_count += 1
#     print(f"✅ Successfully restored workspace_id for {fixed_count} sections.")


# # --- Phase 4: Fix Schema Corruption in content_json ---
# print("\n[Phase 4] Auditing Schema Corruption in Data Payload...")
# # We use _base_manager to check ALL sections, including published/deleted ones
# all_sections = TenantPageSection._base_manager.all()
# corrupted_count = 0
# repaired_count = 0

# for section in all_sections:
#     content = section.content_json
#     needs_save = False
    
#     if isinstance(content, dict):
#         for key, value in list(content.items()):
#             # Detect if a value is actually a schema definition dictionary
#             if isinstance(value, dict) and 'type' in value:
#                 print(f"⚠️ Corruption found in Section ID: {section.id}, Field: {key}")
#                 # Repair it by resetting it to an empty string (user will need to re-select the form/image)
#                 content[key] = ""
#                 needs_save = True
#                 corrupted_count += 1
                
#     if needs_save:
#         section.content_json = content
#         section.save(update_fields=['content_json'])
#         repaired_count += 1

# print(f"Found {corrupted_count} corrupted fields.")
# print(f"✅ Successfully repaired {repaired_count} sections.")
# print("\n=== RECOVERY COMPLETE ===")

# from apps.lumo_sites.models import TenantPageSection

# for s in TenantPageSection._base_manager.all():
#     if 'form_definition_id' in (s.content_json or {}):
#         print(
#             s.id,
#             type(s.content_json['form_definition_id']),
#             s.content_json['form_definition_id']
#         )


# from apps.lumo_sites.models import TenantPageSection

# null_workspace_qs = TenantPageSection._base_manager.filter(workspace__isnull=True)
# print(f"TOTAL BAD WORKSPACES: {null_workspace_qs.count()}")

# from apps.lumo_sites.models import TenantPageSection
# import json

# clinic_sections = TenantPageSection._base_manager.filter(revision__page__slug="clinic").order_by('-revision_id')

# print(f"\nTOTAL CLINIC SECTIONS FOUND: {clinic_sections.count()}\n")

# for s in clinic_sections:
#     print(f"Section ID  : {s.id}")
#     print(f"Revision ID : {s.revision_id}")
#     print(f"Workspace ID: {s.workspace_id}  <--- (CHECK IF NULL)")
    
#     content = s.content_json or {}
#     form_val = content.get('form_definition_id', 'MISSING')
    
#     print(f"Form Def ID : {form_val}  <--- (Type: {type(form_val)})")
#     print("-" * 60)

# from apps.lumo_sites.models import TenantPageSection

# bad_sections = TenantPageSection._base_manager.filter(workspace__isnull=True)
# fixed = 0

# for section in bad_sections:
#     if section.revision and section.revision.workspace_id:
#         section.workspace_id = section.revision.workspace_id
#         section.save(update_fields=['workspace_id'])
#         fixed += 1

# print(f"✅ Successfully recovered {fixed} orphaned sections!")

# from apps.lumo_sites.models import TenantPage, PageRevision, RevisionStatus

# page = TenantPage._base_manager.get(slug="clinic")

# # 1. Builder which revision is it editing? (Based on version_number)
# builder_draft = PageRevision._base_manager.filter(page=page, status=RevisionStatus.DRAFT).order_by('-version_number').first()

# # 2. Preview which revision is it rendering? (Based on created_at)
# preview_draft = PageRevision._base_manager.filter(page=page, status=RevisionStatus.DRAFT).order_by('-created_at').first()

# # 3. Live which revision is it rendering?
# live_published = PageRevision._base_manager.filter(page=page, status=RevisionStatus.PUBLISHED).order_by('-created_at').first()

# print(f"Builder Draft ID:   {builder_draft.id if builder_draft else 'NONE'} (v{builder_draft.version_number if builder_draft else 'N/A'})")
# print(f"Preview Draft ID:   {preview_draft.id if preview_draft else 'NONE'} (v{preview_draft.version_number if preview_draft else 'N/A'})")
# print(f"Live Published ID:  {live_published.id if live_published else 'NONE'} (v{live_published.version_number if live_published else 'N/A'})")

# from apps.lumo_sites.models import PageRevision

# for r in PageRevision._base_manager.filter(
#     page__slug="portfolio"
# ).order_by("-version_number"):
#     print(
#         r.version_number,
#         r.status
#     )

# from apps.lumo_sites.models import TenantPageSection

# sections = TenantPageSection._base_manager.filter(
#     revision__page__slug="portfolio",
#     revision__status="PUBLISHED"
# ).order_by("sort_order")

# for s in sections:
#     print(
#         s.sort_order,
#         s.is_visible,
#         s.section_version.title if hasattr(s.section_version, "title") else s.section_version_id
#     )

# from apps.lumo_sites.models import TenantPage, PageRevision, TenantPageSection

# page = TenantPage._base_manager.get(slug="clinic")

# for rev in PageRevision._base_manager.filter(page=page).order_by("-version_number"):
#     print("\nREVISION:", rev.version_number, rev.status)

#     sections = TenantPageSection._base_manager.filter(
#         revision=rev
#     ).order_by("sort_order")

#     for s in sections:
#         print(
#             s.sort_order,
#             s.id,
#             s.section_version_id
#         )


# from apps.lumo_sites.models import PageRevision

# for r in PageRevision._base_manager.order_by("-version_number")[:5]:
#     print(
#         r.version_number,
#         r.status,
#         r.id
#     )

# from apps.lumo_sites.models import TenantPageSection

# for s in TenantPageSection._base_manager.filter(
#     revision__version_number=10
# ).order_by("sort_order"):

#     print(
#         "SECTION:",
#         s.id,
#         "SORT:",
#         s.sort_order,
#         "VISIBLE:",
#         s.is_visible,
#         "DELETED:",
#         s.is_deleted,
#         "VERSION:",
#         s.section_version_id,
#         "WORKSPACE:",
#         s.workspace_id
#     )

# from apps.lumo_sites.models import TenantPageSection

# for s in TenantPageSection._base_manager.filter(
#     revision__version_number=11
# ).order_by("sort_order"):

#     print(
#         "SECTION:",
#         s.id,
#         "SORT:",
#         s.sort_order,
#         "VISIBLE:",
#         s.is_visible,
#         "DELETED:",
#         s.is_deleted,
#         "VERSION:",
#         s.section_version_id,
#         "WORKSPACE:",
#         s.workspace_id
#     )

# from apps.lumo_sites.models import TenantPageSection

# for s in TenantPageSection._base_manager.order_by(
#     "revision__version_number",
#     "sort_order"
# ):
#     print(
#         "REV:",
#         s.revision.version_number,
#         "| STATUS:",
#         s.revision.status,
#         "| SORT:",
#         s.sort_order,
#         "| SECTION:",
#         s.id,
#         "| VERSION:",
#         s.section_version_id
#     )

# from apps.lumo_sites.models import TenantPage

# page = TenantPage._base_manager.get(slug="clinic")

# print("PAGE:", page.id)

# for rev in page.revisions.all().order_by("-version_number"):
#     print(
#         rev.version_number,
#         rev.status,
#         rev.id
#     )

# from apps.lumo_sites.models import TenantPageSection

# for s in TenantPageSection._base_manager.filter(
#     section_version_id="b62e7940-89bb-4570-bcb1-e0806409849d"
# ):
#     print(
#         s.id,
#         s.revision.version_number,
#         s.revision.status,
#         s.sort_order
#     )

# from apps.lumo_sites.models import PageRevision, TenantPageSection

# draft = PageRevision._base_manager.get(version_number=11)

# print("Draft:", draft.id)

# for s in TenantPageSection._base_manager.filter(
#     revision=draft
# ).order_by("sort_order"):
#     print(
#         s.id,
#         s.sort_order,
#         s.is_deleted,
#         s.is_visible,
#         s.workspace_id,
#         s.section_version_id
#     )

# from apps.lumo_sites.models import PageRevision, TenantPageSection

# draft = PageRevision._base_manager.get(version_number=11)

# print(
#     TenantPageSection._base_manager.filter(
#         revision=draft
#     ).count()
# )

# print(
#     TenantPageSection._base_manager.filter(
#         revision=draft,
#         is_deleted=False
#     ).count()
# )

# print(
#     TenantPageSection._base_manager.filter(
#         revision=draft,
#         is_deleted=False,
#         is_visible=True
#     ).count()
# )


# from apps.lumo_sites.models import PageRevision, TenantPageSection

# for rev in PageRevision._base_manager.all():
#     orders = list(
#         TenantPageSection._base_manager.filter(
#             revision=rev,
#             is_deleted=False
#         ).values_list('sort_order', flat=True)
#     )

#     if len(orders) != len(set(orders)):
#         print(
#             "DUPLICATE FOUND",
#             rev.version_number,
#             rev.status,
#             orders
#         )

# from apps.lumo_sites.models import PageRevision, TenantPageSection

# rev_id = "d04c0509-eaf1-4950-b94d-00ae26772390"

# rev = PageRevision._base_manager.get(id=rev_id)

# print("REVISION")
# print(rev.id)
# print(rev.version_number)
# print(rev.status)

# print("\nSECTIONS")

# for s in TenantPageSection._base_manager.filter(
#     revision=rev
# ).order_by(
#     'sort_order',
#     'id'
# ):
#     print(
#         s.id,
#         "SORT=", s.sort_order,
#         "VISIBLE=", s.is_visible,
#         "DELETED=", s.is_deleted,
#         "VERSION=", s.section_version_id
#     )

# from collections import Counter

# from apps.lumo_sites.models import (
#     PageRevision,
#     TenantPageSection
# )

# rev_id = "d04c0509-eaf1-4950-b94d-00ae26772390"

# orders = list(
#     TenantPageSection._base_manager.filter(
#         revision_id=rev_id,
#         is_deleted=False
#     ).values_list(
#         'sort_order',
#         flat=True
#     )
# )

# print("ORDERS =", orders)

# counter = Counter(orders)

# for k, v in counter.items():
#     if v > 1:
#         print(
#             "DUPLICATE",
#             k,
#             "COUNT",
#             v
#         )

from apps.lumo_sites.models import (
    PageRevision,
    RevisionStatus
)

page_id = "46b1d0c9-a348-4a2e-9e84-dba35960c7f8"

for r in PageRevision._base_manager.filter(
    page_id=page_id
).order_by(
    '-version_number'
):
    print(
        r.version_number,
        r.status,
        r.id
    )