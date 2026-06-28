# apps/lumo_sites/tests/test_revision_engine.py
from django.test import TestCase
from django.db import IntegrityError
from apps.lumo_sites.models import PageRevision, RevisionStatus, TenantPageSection
from apps.lumo_sites.services.revisions import PageRevisionService
from .factories import (
    create_full_test_site,
    create_published_revision_with_duplicates,
    create_pagerevision,
)

# 🔧 যদি real system_context না পাওয়া যায়, তাহলে একটি ডামি বানাই
try:
    from core.managers import system_context
except ImportError:
    # ডামি কনটেক্সট ম্যানেজার – টেস্টের জন্য কোনো কাজ করে না
    from contextlib import contextmanager
    @contextmanager
    def system_context():
        yield

class RevisionEngineTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        with system_context():
            cls.workspace, cls.site, cls.page = create_full_test_site()

    def test_clone_reindexes_duplicate_sort_order(self):
        with system_context():
            create_published_revision_with_duplicates(self.page)
            draft = PageRevisionService.get_or_create_draft(self.page)
            orders = (
                TenantPageSection.objects
                .filter(revision=draft, is_deleted=False)
                .order_by('sort_order')
                .values_list('sort_order', flat=True)
            )
            self.assertEqual(list(orders), [1, 2, 3])

    def test_unique_draft_constraint(self):
        with system_context():
            PageRevision.objects.create(
                workspace=self.workspace,
                page=self.page,
                version_number=1,
                status=RevisionStatus.DRAFT,
                is_deleted=False,
            )
            with self.assertRaises(IntegrityError):
                PageRevision.objects.create(
                    workspace=self.workspace,
                    page=self.page,
                    version_number=2,
                    status=RevisionStatus.DRAFT,
                    is_deleted=False,
                )

    def test_publish_archives_other_drafts(self):
        with system_context():
            draft1 = create_pagerevision(page=self.page, version_number=1, status=RevisionStatus.DRAFT)
            draft2 = create_pagerevision(page=self.page, version_number=2, status=RevisionStatus.DRAFT)
            PageRevisionService.publish_revision(draft2)
            draft1.refresh_from_db()
            self.assertEqual(draft1.status, RevisionStatus.ARCHIVED)
            draft2.refresh_from_db()
            self.assertEqual(draft2.status, RevisionStatus.PUBLISHED)