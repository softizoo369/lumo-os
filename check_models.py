from apps.lumo_sites.models import SiteKit
for f in SiteKit._meta.fields:
    print(f.name, f.__class__.__name__, f.null, f.blank)