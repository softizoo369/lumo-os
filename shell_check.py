# shell_check.py

from apps.lumo_sites.models import SiteDomain

print("MODEL:", SiteDomain)

print("\nMANAGERS:")
for m in SiteDomain._meta.managers:
    print(
        m.name,
        type(m)
    )


# shell_check.py

from apps.lumo_sites.models import SiteDomain

print("DEFAULT MANAGER:")
print(SiteDomain.objects)

print("\nBASE MANAGER:")
print(SiteDomain._base_manager)

print("\nCOUNT:")

try:
    print(
        SiteDomain._base_manager.count()
    )
except Exception as e:
    print("ERROR:", e)