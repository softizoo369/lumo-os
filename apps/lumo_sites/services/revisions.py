from django.db import transaction
from apps.lumo_sites.models import PageRevision, TenantPageSection, RevisionStatus
from collections import Counter

class PageRevisionService:
    """
    Enterprise Content Management Engine
    """

    @staticmethod
    @transaction.atomic
    def get_or_create_draft(page):
        """
        Fetch existing draft, or clone from published revision with safe ordering.
        """
        print("\n" + "="*80)
        print("🚀 GET_OR_CREATE_DRAFT CALLED")
        print(f"   PAGE ID: {page.id}")
        print("="*80 + "\n")

        # 1. Check existing draft
        existing_draft = PageRevision.objects.filter(
            page=page,
            status=RevisionStatus.DRAFT,
            is_deleted=False
        ).order_by('-version_number').first()

        existing_drafts_qs = PageRevision.objects.filter(
            page=page,
            status=RevisionStatus.DRAFT,
            is_deleted=False
        )
        print("EXISTING DRAFTS =", list(existing_drafts_qs.values_list("id", "version_number")))

        if existing_draft:
            print(f"✅ Returning existing draft: {existing_draft.id} (v{existing_draft.version_number})")
            return existing_draft

        # 2. Find source revision (published first, then fallback)
        published_rev = PageRevision.objects.filter(
            page=page,
            status=RevisionStatus.PUBLISHED,
            is_deleted=False
        ).order_by('-version_number').first()

        if not published_rev:
            published_rev = PageRevision.objects.filter(
                page=page,
                is_deleted=False
            ).order_by('-version_number').first()

        if not published_rev:
            raise ValueError(f"No existing revisions found for page: {page.title}")

        # ----- SOURCE REVISION LOGGING (Smoking Gun) -----
        print("\n📂 SOURCE REVISION")
        print(f"   ID: {published_rev.id}")
        print(f"   Version: {published_rev.version_number}")
        print(f"   Status: {published_rev.status}")

        old_sections = TenantPageSection._base_manager.filter(
            revision=published_rev,
            is_deleted=False
        ).order_by("sort_order")

        source_orders = list(old_sections.values_list("sort_order", flat=True))
        print(f"   SOURCE ORDERS = {source_orders}")

        # Check duplicates in source
        c = Counter(source_orders)
        for k, v in c.items():
            if v > 1:
                print(f"   ⚠️ DUPLICATE IN SOURCE: order {k} appears {v} times")

        # 3. Create new draft revision
        new_draft = PageRevision.objects.create(
            page=page,
            version_number=published_rev.version_number + 1,
            status=RevisionStatus.DRAFT,
            workspace=page.workspace,
        )
        print(f"\n🆕 NEW DRAFT CREATED: {new_draft.id} (v{new_draft.version_number})")

        # 4. Clone sections with REINDEXED sort_order (THE PERMANENT FIX)
        new_sections = []
        for idx, section in enumerate(old_sections, start=1):  # ← start from 1
            new_sections.append(
                TenantPageSection(
                    workspace=section.workspace,
                    revision=new_draft,
                    section_version=section.section_version,
                    sort_order=idx,  # ← NEW ORDER, guaranteed unique
                    is_visible=section.is_visible,
                    content_json=section.content_json.copy(),
                )
            )

        # ----- Log what will be inserted -----
        new_orders = [s.sort_order for s in new_sections]
        print(f"\n📋 ORDERS TO INSERT = {new_orders}")
        c2 = Counter(new_orders)
        for k, v in c2.items():
            if v > 1:
                print(f"⚠️ DUPLICATE BEFORE INSERT (should NOT happen): {k} appears {v} times")

        # 5. Bulk insert
        if new_sections:
            TenantPageSection.objects.bulk_create(new_sections)
            print(f"✅ Cloned {len(new_sections)} sections with reindexed sort_order.")
        else:
            print("ℹ️ No sections to clone.")

        print("\n" + "="*80 + "\n")
        return new_draft

    @staticmethod
    @transaction.atomic
    def publish_revision(target_revision):
        """
        Publish the target revision and archive others.
        """
        print("\n" + "="*80)
        print("📤 PUBLISH_REVISION CALLED")
        print(f"   TARGET: {target_revision.id} (v{target_revision.version_number})")
        print("="*80 + "\n")

        if target_revision.status == RevisionStatus.PUBLISHED:
            print("ℹ️ Already published, returning.")
            return target_revision

        page = target_revision.page

        # Archive old published
        archived_pub = PageRevision.objects.filter(
            page=page,
            status=RevisionStatus.PUBLISHED
        ).update(status=RevisionStatus.ARCHIVED)
        print(f"📦 Archived {archived_pub} previous published revisions.")

        # Archive other drafts (keep only target)
        archived_drafts = PageRevision.objects.filter(
            page=page,
            status=RevisionStatus.DRAFT
        ).exclude(id=target_revision.id).update(status=RevisionStatus.ARCHIVED)
        print(f"🗑️ Archived {archived_drafts} orphan drafts.")

        # Promote target
        target_revision.status = RevisionStatus.PUBLISHED
        target_revision.save()
        print(f"✅ Revision {target_revision.id} promoted to PUBLISHED.")

        return target_revision