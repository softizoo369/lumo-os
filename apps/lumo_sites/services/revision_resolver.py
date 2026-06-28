from apps.lumo_sites.models import PageRevision, RevisionStatus

class RevisionResolver:
    """
    Enterprise Unified Revision Resolver.
    Ensures Builder, Preview, and Publish always target the exact same timeline.
    """
    @staticmethod
    def get_latest_draft(page):
        return (
            PageRevision._base_manager
            .filter(page=page, status=RevisionStatus.DRAFT, is_deleted=False)
            .order_by('-version_number')
            .first()
        )

    @staticmethod
    def get_latest_published(page):
        return (
            PageRevision._base_manager
            .filter(page=page, status=RevisionStatus.PUBLISHED, is_deleted=False)
            .order_by('-version_number')
            .first()
        )