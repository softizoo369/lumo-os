from collections import Counter

from apps.lumo_sites.models import (
PageRevision,
TenantPageSection,
)

print("\n" + "="*80)
print("GLOBAL REVISION AUDIT")
print("="*80)

for rev in PageRevision._base_manager.all().order_by("page_id", "version_number"):

    orders = list(
        TenantPageSection._base_manager
        .filter(
            revision=rev,
            is_deleted=False
        )
        .values_list(
            "sort_order",
            flat=True
        )
    )

    dupes = [
        k
        for k,v in Counter(orders).items()
        if v > 1
    ]

    if dupes:
        print(
            "\nCORRUPT REVISION:",
            rev.id,
            "PAGE:",
            rev.page_id,
            "VERSION:",
            rev.version_number,
            "STATUS:",
            rev.status
        )

        print("ORDERS =", orders)


    print("\nAUDIT COMPLETE")
