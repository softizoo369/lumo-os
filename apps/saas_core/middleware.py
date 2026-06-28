from django.shortcuts import redirect
from apps.lumo_sites.models import SiteDomain
from django.urls import resolve
from core.context import set_workspace, get_workspace
from apps.saas_core.models.tenant import Workspace, WorkspaceMember
from core.context import set_workspace

class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 🟢 SURGICAL FIX: Existing tenant context preserve (No Blind Reset)
        if not get_workspace():
            set_workspace(None)
            
        if request.user.is_authenticated:
            workspace_id = request.session.get('active_workspace_id')
            if not workspace_id:
                membership = WorkspaceMember.objects.filter(user=request.user).first()
                if membership:
                    workspace_id = str(membership.workspace_id)
                    request.session['active_workspace_id'] = workspace_id
            
            if workspace_id:
                set_workspace(workspace_id)
                
        return self.get_response(request)

class SaaSEnforcementMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 🔴 SUPER ADMIN VIP PASS
        if request.user.is_authenticated and (request.user.is_superuser or request.user.is_staff):
            return self.get_response(request)

        # 🔴 EXEMPTION: Identity & Admin apps
        try:
            url_name = resolve(request.path_info).url_name
            app_name = resolve(request.path_info).app_name
        except:
            url_name, app_name = None, None

        if app_name in ['identity', 'admin'] or url_name == 'workspace_locked':
            return self.get_response(request)

        # 🔴 ENFORCEMENT
        if request.user.is_authenticated:
            workspace_id = get_workspace()
            if workspace_id:
                workspace = Workspace.objects.filter(id=workspace_id).first()
                if workspace and workspace.status == 'SUSPENDED':
                    return redirect('saas_core:workspace_locked')

        return self.get_response(request)
    



class TenantRoutingMiddleware:
    """
    এই মিডলওয়্যারটি চেক করে ভিজিটর কোন ডোমেইন দিয়ে সাইটে ঢুকছে।
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(':')[0] 
        request.tenant_site = None 

        if host not in ['127.0.0.1', 'localhost', 'lumo-os.com']:
            try:
                domain_record = SiteDomain._base_manager.select_related('workspace__website').get(domain_name=host)
                
                if hasattr(domain_record.workspace, 'website'):
                    request.tenant_site = domain_record.workspace.website
                    
                    # 🟢 SURGICAL PATCH: Activate TenantManager for Public Visitors
                    # ডোমেইন অনুযায়ী ওয়ার্কস্পেস সেট করে দেওয়া হলো যাতে Public View-তে 404 না আসে
                    set_workspace(str(domain_record.workspace_id))
                    
            except SiteDomain.DoesNotExist:
                pass

        response = self.get_response(request)
        return response