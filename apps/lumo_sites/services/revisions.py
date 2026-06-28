import logging
from django.db import transaction
from apps.lumo_sites.models import PageRevision, TenantPageSection, RevisionStatus

logger = logging.getLogger(__name__)

class PageRevisionService:

    @staticmethod
    @transaction.atomic
    def get_or_create_draft(page):
        # 1. Check existing draft
        existing_draft = PageRevision.objects.filter(
            page=page,
            status=RevisionStatus.DRAFT,
            is_deleted=False
        ).order_by('-version_number').first()

        if existing_draft:
            return existing_draft

        # 2. Find source (published or latest)
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
            raise ValueError(f"No revisions for page: {page.title}")

        # 3. Create new draft
        new_draft = PageRevision.objects.create(
            page=page,
            version_number=published_rev.version_number + 1,
            status=RevisionStatus.DRAFT,
            workspace=page.workspace,
        )

        # 4. Clone sections with REINDEXED sort_order (THE FIX)
        old_sections = TenantPageSection._base_manager.filter(
            revision=published_rev,
            is_deleted=False
        ).order_by('sort_order')

        new_sections = []
        for idx, section in enumerate(old_sections, start=1):
            new_sections.append(
                TenantPageSection(
                    workspace=section.workspace,
                    revision=new_draft,
                    section_version=section.section_version,
                    sort_order=idx,          # ← নতুন sequential order
                    is_visible=section.is_visible,
                    content_json=section.content_json.copy(),
                )
            )

        if new_sections:
            TenantPageSection.objects.bulk_create(new_sections)
            logger.info(f"Cloned {len(new_sections)} sections for draft {new_draft.id}")

        return new_draft

    @staticmethod
    @transaction.atomic
    def publish_revision(target_revision):
        if target_revision.status == RevisionStatus.PUBLISHED:
            return target_revision

        page = target_revision.page

        # Archive old published
        PageRevision.objects.filter(
            page=page,
            status=RevisionStatus.PUBLISHED
        ).update(status=RevisionStatus.ARCHIVED)

        # Archive other drafts (keep only target)
        PageRevision.objects.filter(
            page=page,
            status=RevisionStatus.DRAFT
        ).exclude(id=target_revision.id).update(status=RevisionStatus.ARCHIVED)

        # Promote target
        target_revision.status = RevisionStatus.PUBLISHED
        target_revision.save()

        logger.info(f"Published revision {target_revision.id} for page {page.id}")
        return target_revision