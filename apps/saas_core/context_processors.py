from apps.saas_core.models.notification import Notification
from apps.saas_core.services.settings_service import SettingsService
from apps.saas_core.services.menu_service import MenuService
from apps.saas_core.services.workspace_service import WorkspaceService

def global_notifications(request):
    """Injects unread notifications into every template automatically."""
    if request.user.is_authenticated:
        unreads = Notification.objects.filter(
            recipient=request.user, 
            is_read=False
        ).order_by('-created_at')[:5]
        
        unread_count = Notification.objects.filter(
            recipient=request.user, 
            is_read=False
        ).count()
        
        return {
            'lumo_notifications': unreads,
            'lumo_unread_count': unread_count
        }
    return {}

def global_saas_settings(request):
    """
    Injects Global Settings and Dynamic Sidebar Menu into all templates.
    """
    sidebar_menu = []
    
    # 🟢 REQUIRED PATCH: Do not execute admin context logic on public website routes
    is_public_site_route = getattr(request, 'tenant_site', None) is not None
    
    if request.user.is_authenticated and not is_public_site_route:
        try:
            workspace = WorkspaceService.get_current_workspace(request)
            if workspace:
                sidebar_menu = MenuService.get_sidebar_for_user(request.user, workspace.id)
        except AttributeError:
            pass # Fail gracefully if workspace context is still missing
            
    try:
        config = SettingsService.get_global_config()
        return {
            'global_config': config,
            'sidebar_menu': sidebar_menu
        }
    except Exception:
        return {
            'global_config': None,
            'sidebar_menu': sidebar_menu
        }