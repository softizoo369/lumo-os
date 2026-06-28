from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from apps.saas_core.services.workspace_service import WorkspaceService
from apps.saas_core.services.feature_gate_service import FeatureGateService
from apps.saas_core.policy_engine import PolicyEngine
from apps.saas_core.services.audit_service import AuditService

def enforce_limit(limit_name):
    """
    Decorator to prevent actions if a workspace has reached its plan limit.
    Usage: @enforce_limit('max_companies')
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # 🟢 FIX: Passed 'request' down to the service
            workspace = WorkspaceService.get_current_workspace(request)
            
            if workspace:
                check = FeatureGateService.check_limit(workspace, limit_name)
                if not check['allowed']:
                    messages.warning(request, check['message'])
                    return redirect('saas_core:company_list') # Redirect back with error
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator



def require_permission(action_code):
    """
    Enterprise SaaS Decorator.
    Blocks view execution and LOGS FAILED ATTEMPTS if PolicyEngine denies access.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # 🟢 FIX: Passed 'request' down to the service (This was causing the TypeError)
            workspace = WorkspaceService.get_current_workspace(request)
            
            if not PolicyEngine.can(request.user, workspace, action_code):
                # 🔴 AUDIT: Record the malicious or unauthorized attempt
                AuditService.log(
                    request=request,
                    workspace=workspace,
                    action='permission.denied',
                    resource_type='PolicyEngine',
                    resource_id=action_code,
                    metadata={'attempted_action': action_code},
                    status='FAILED'
                )
                
                messages.error(request, "Access Denied: You do not have permission to perform this action.")
                return redirect('saas_core:dashboard_home') 
                
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def audit_action(action, resource_type):
    """
    Declarative Audit Decorator for standard views.
    Usage: @audit_action(action="company.delete", resource_type="Company")
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            response = view_func(request, *args, **kwargs)
            
            # Log only on successful POST requests (avoid logging simple page loads)
            if request.method == 'POST' and response.status_code in [200, 302]:
                # 🟢 FIX: Passed 'request' down to the service
                workspace = WorkspaceService.get_current_workspace(request)
                
                AuditService.log(
                    request=request,
                    workspace=workspace,
                    action=action,
                    resource_type=resource_type,
                    status='SUCCESS'
                )
            return response
        return _wrapped_view
    return decorator