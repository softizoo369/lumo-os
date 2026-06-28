from django.test import TestCase, RequestFactory
from apps.lumo_sites.models import TenantSite, TenantPage, PageRevision, TenantPageSection, FormDefinition, RevisionStatus
from apps.lumo_sites.views import render_dynamic_page, preview_page_view, public_page_view
import uuid

class ReferenceResolverRegressionTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.site = TenantSite.objects.create(...)
        self.page = TenantPage.objects.create(site=self.site, slug='clinic', is_deleted=False)
        self.revision = PageRevision.objects.create(page=self.page, status=RevisionStatus.DRAFT, is_deleted=False)
        self.form = FormDefinition.objects.create(site=self.site, id=uuid.uuid4())
        
        self.section = TenantPageSection.objects.create(
            revision=self.revision,
            is_visible=True,
            is_deleted=False,
            content_json={}
        )

    def _render_with_content(self, content):
        self.section.content_json = content
        self.section.save()
        request = self.factory.get('/site/clinic/')
        # Use render_dynamic_page to test rendering pipeline resilience
        return render_dynamic_page(request, self.site, 'clinic', is_preview=True)

    def test_case_1_valid_uuid(self):
        # CASE 1: Expected Form Renders Successfully
        response = self._render_with_content({"form_definition_id": str(self.form.id)})
        self.assertEqual(response.status_code, 200)

    def test_case_2_empty_string(self):
        # CASE 2: No Crash on ""
        response = self._render_with_content({"form_definition_id": ""})
        self.assertEqual(response.status_code, 200)

    def test_case_3_none_value(self):
        # CASE 3: No Crash on None
        response = self._render_with_content({"form_definition_id": None})
        self.assertEqual(response.status_code, 200)

    def test_case_4_missing_key(self):
        # CASE 4: No Crash on missing key
        response = self._render_with_content({"other_key": "value"})
        self.assertEqual(response.status_code, 200)

    def test_case_5_corrupted_dict(self):
        # CASE 5: No Crash on nested dictionary
        response = self._render_with_content({"form_definition_id": {"type": "reference"}})
        self.assertEqual(response.status_code, 200)

    def test_case_6_preview_view_integration(self):
        # CASE 6: Full view integration
        self.section.content_json = {"form_definition_id": ""}
        self.section.save()
        request = self.factory.get('/site/preview/clinic/')
        request.tenant_site = self.site
        response = preview_page_view(request, slug='clinic')
        self.assertEqual(response.status_code, 200)

    def test_case_7_public_view_integration(self):
        # CASE 7: Full view integration (Published)
        self.revision.status = RevisionStatus.PUBLISHED
        self.revision.save()
        self.section.content_json = {"form_definition_id": ""}
        self.section.save()
        request = self.factory.get('/site/clinic/')
        request.tenant_site = self.site
        response = public_page_view(request, slug='clinic')
        self.assertEqual(response.status_code, 200)