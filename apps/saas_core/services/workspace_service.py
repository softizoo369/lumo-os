from apps.saas_core.models.tenant import Workspace, WorkspaceMember

class WorkspaceService:
    @staticmethod
    def get_current_workspace(request):
        if not request or not request.user.is_authenticated:
            return None
            
        if hasattr(request, 'workspace') and request.workspace:
            return request.workspace
            
        membership = WorkspaceMember.objects.filter(
            user=request.user, 
            is_deleted=False
        ).select_related('workspace').first()
        
        if membership:
            return membership.workspace
            
        return None