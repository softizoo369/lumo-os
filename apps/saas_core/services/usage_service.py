from django.db.models import F, Sum
from apps.saas_core.models.usage import WorkspaceUsage
from core.context import system_context
from apps.saas_core.models.company import Company
from apps.saas_core.models.finance import PaymentTransaction, BillingProfile
from apps.lumo_sites.models import MediaAsset # 🟢 FIX: Added MediaAsset Import

class UsageService:
    @staticmethod
    def get_current_usage(workspace):
        """Fetches the usage safely and auto-heals any duplicate records."""
        with system_context():
            usages = WorkspaceUsage.objects.filter(workspace_id=workspace.id)
            
            if usages.exists():
                usage = usages.first()
                # Auto-heal duplicate records
                if usages.count() > 1:
                    WorkspaceUsage.objects.filter(workspace_id=workspace.id).exclude(id=usage.id).delete()
                return usage
            
            return WorkspaceUsage.objects.create(workspace_id=workspace.id)

    @staticmethod
    def increment_usage(workspace, field_name: str, amount: int = 1):
        """Atomically increment usage counters."""
        with system_context():
            UsageService.get_current_usage(workspace)
            WorkspaceUsage.objects.filter(workspace_id=workspace.id).update(
                **{field_name: F(field_name) + amount}
            )

    @staticmethod
    def decrement_usage(workspace, field_name: str, amount: int = 1):
        """Atomically decrement usage counters safely."""
        with system_context():
            UsageService.get_current_usage(workspace)
            WorkspaceUsage.objects.filter(
                workspace_id=workspace.id, 
                **{f"{field_name}__gt": 0}
            ).update(
                **{field_name: F(field_name) - amount}
            )

    @staticmethod
    def sync_workspace_storage(workspace):
        """Scans ALL tenant files (including Site Media) and accurately calculates MB usage."""
        total_bytes = 0
        
        with system_context():
            # 1. Calculate Company Logos
            for comp in Company.objects.filter(workspace_id=workspace.id).exclude(logo=''):
                try:
                    if comp.logo and hasattr(comp.logo, 'size'): total_bytes += comp.logo.size
                except Exception: pass

            # 2. Calculate Payment Proofs
            for pay in PaymentTransaction.objects.filter(workspace_id=workspace.id).exclude(proof_file=''):
                try:
                    if pay.proof_file and hasattr(pay.proof_file, 'size'): total_bytes += pay.proof_file.size
                except Exception: pass
                
            # 3. Calculate Tax Certificates
            for prof in BillingProfile.objects.filter(workspace__id=workspace.id).exclude(tax_exemption_certificate=''):
                try:
                    if prof.tax_exemption_certificate and hasattr(prof.tax_exemption_certificate, 'size'): 
                        total_bytes += prof.tax_exemption_certificate.size
                except Exception: pass

            # 🟢 4. FIX: Calculate Lumo Sites Media Assets (The biggest storage consumer)
            asset_query = MediaAsset.objects.filter(workspace_id=workspace.id).aggregate(total_kb=Sum('file_size_kb'))
            asset_kb = asset_query['total_kb'] or 0
            asset_bytes = float(asset_kb) * 1024 # Convert KB to Bytes

            # Convert Total Bytes to MB
            total_mb = (total_bytes + asset_bytes) / (1024 * 1024)
            
            usage = UsageService.get_current_usage(workspace)
            usage.total_storage_mb = round(total_mb, 2)
            usage.save(update_fields=['total_storage_mb'])