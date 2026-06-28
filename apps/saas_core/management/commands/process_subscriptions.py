from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from apps.saas_core.models.subscription import WorkspaceSubscription, SubscriptionStatus
from apps.saas_core.models.tenant import WorkspaceStatus
from apps.saas_core.services.audit_service import AuditService
from core.context import system_context

class Command(BaseCommand):
    help = 'SaaS Heartbeat: Runs daily to check and expire past-due subscriptions.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Starting SaaS Heartbeat: Checking for expired subscriptions..."))
        
        now = timezone.now()
        
        # 🟢 Find subscriptions that are ACTIVE but their period has ended
        with system_context():
            for sub_obj in expired_subs:
                with transaction.atomic():
                    # 🟢 THE SECURE FIX: Lock the row and re-evaluate the condition
                    sub = WorkspaceSubscription.objects.select_for_update().get(id=sub_obj.id)
                    
                    if sub.current_period_end >= timezone.now() or sub.status != SubscriptionStatus.ACTIVE:
                        # Someone paid or status changed while the cronjob was running in the background
                        continue
                        
                    workspace = sub.workspace
                    
                    # 1. Update Subscription Status
                    sub.status = SubscriptionStatus.PAST_DUE
                    sub.save(update_fields=['status'])
                    
                    # 2. Lock/Suspend the Workspace
                    workspace.status = WorkspaceStatus.SUSPENDED
                    workspace.save(update_fields=['status'])
                    
                    # 2. Lock/Suspend the Workspace
                    workspace.status = WorkspaceStatus.SUSPENDED
                    workspace.save(update_fields=['status'])
                    
                    # 3. Enterprise Audit Log
                    AuditService.log(
                        request=None, 
                        workspace=workspace, 
                        action='subscription.auto_expired',
                        resource_type='WorkspaceSubscription', 
                        resource_id=str(sub.id),
                        metadata={'expired_on': str(sub.current_period_end)}, 
                        status='SUCCESS'
                    )
                    
                    count += 1
                    self.stdout.write(self.style.WARNING(f"Locked Workspace: {workspace.name} (Subscription Expired)"))
        
        self.stdout.write(self.style.SUCCESS(f"Heartbeat complete! {count} workspaces have been auto-suspended."))