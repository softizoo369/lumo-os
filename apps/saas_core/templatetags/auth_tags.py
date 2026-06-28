from django import template
from apps.saas_core.policy_engine import PolicyEngine
from apps.saas_core.services.workspace_service import WorkspaceService

register = template.Library()

@register.simple_tag(takes_context=True)
def has_permission(context, action_code):
    request = context.get('request')
    if not request or not request.user.is_authenticated:
        return False
        
    # 🟢 REQUIRED PATCH: Prevent AttributeError on public templates
    try:
        workspace = WorkspaceService.get_current_workspace(request)
    except AttributeError:
        return False
    
    if not workspace:
        return False
        
    return PolicyEngine.can(request.user, workspace, action_code)