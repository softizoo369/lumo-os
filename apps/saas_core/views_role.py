from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.identity.models import Role, Permission, Feature
from apps.saas_core.decorators import require_permission
from apps.saas_core.services.workspace_service import WorkspaceService
from apps.saas_core.policy_engine import PolicyEngine
from apps.saas_core.services.audit_service import AuditService

def _generate_matrix(role=None):
    active_perm_codes = set()
    if role:
        active_perm_codes = set(role.permissions_m2m.values_list('code', flat=True))

    features = Feature.objects.prefetch_related('permissions').all().order_by('id')
    
    matrix = []
    for feature in features:
        row = {'name': feature.name, 'code': feature.code, 'perms': {}}
        for action in ['create', 'read', 'update', 'delete']:
            row['perms'][action] = {'available': False, 'key': '', 'checked': False}

        for perm in feature.permissions.all():
            action_suffix = perm.code.split('.')[-1]
            if action_suffix in row['perms']:
                row['perms'][action_suffix] = {
                    'available': True,
                    'key': f"perm_{perm.code}",
                    'checked': perm.code in active_perm_codes 
                }
        matrix.append(row)
    return matrix

def _extract_permissions_from_post(post_data):
    selected_codes = []
    for key in post_data.keys():
        if key.startswith('perm_'):
            perm_code = key.replace('perm_', '')
            selected_codes.append(perm_code)
    return selected_codes

@login_required(login_url='/auth/login/')
def role_list(request):
    # 🟢 FIX: Passed 'request' to the service
    workspace = WorkspaceService.get_current_workspace(request)
    roles = Role.objects.filter(workspace=workspace, is_deleted=False).prefetch_related('role_members').order_by('created_at')
    return render(request, 'saas_core/role/list.html', {'roles': roles})

@login_required(login_url='/auth/login/')
@require_permission('role.create')
def role_create(request):
    # 🟢 FIX: Passed 'request' to the service
    workspace = WorkspaceService.get_current_workspace(request)
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        selected_codes = _extract_permissions_from_post(request.POST)
        
        if Role.objects.filter(workspace=workspace, name__iexact=name).exists():
            messages.error(request, f"Role '{name}' already exists.")
        else:
            role = Role.objects.create(workspace=workspace, name=name, description=description)
            perms_to_add = Permission.objects.filter(code__in=selected_codes)
            role.permissions_m2m.set(perms_to_add)
            
            AuditService.log(
                request=request, workspace=workspace, action='role.create',
                resource_type='Role', resource_id=role.id,
                metadata={'role_name': role.name, 'permissions_assigned': len(selected_codes)}, status='SUCCESS'
            )

            from apps.saas_core.services.notification_service import NotificationService
            NotificationService.send(
                recipient=request.user, workspace=workspace, title="New Role Created",
                message=f"You have successfully created the '{role.name}' role with {len(selected_codes)} permissions.",
                notif_type='SUCCESS', action_url=f"/settings/roles/{role.id}/edit/"
            )
            
            messages.success(request, "Role and permissions created successfully.")
            return redirect('saas_core:role_list')

    return render(request, 'saas_core/role/form.html', {'matrix': _generate_matrix(), 'is_edit': False})

@login_required(login_url='/auth/login/')
@require_permission('role.update')
def role_update(request, role_id):
    # 🟢 FIX: Passed 'request' to the service
    workspace = WorkspaceService.get_current_workspace(request)
    role = get_object_or_404(Role, id=role_id, workspace=workspace, is_deleted=False)
    
    if request.method == 'POST':
        if role.is_system_default:
            messages.error(request, "You cannot modify system default roles (e.g., OWNER).")
            return redirect('saas_core:role_list')

        role.name = request.POST.get('name')
        role.description = request.POST.get('description')
        role.save()
        
        selected_codes = _extract_permissions_from_post(request.POST)
        perms_to_add = Permission.objects.filter(code__in=selected_codes)
        role.permissions_m2m.set(perms_to_add)
        
        PolicyEngine.invalidate_cache(workspace.id)
        
        AuditService.log(
            request=request, workspace=workspace, action='role.update',
            resource_type='Role', resource_id=role.id,
            metadata={'role_name': role.name, 'permissions_assigned': len(selected_codes)}, status='SUCCESS'
        )

        messages.success(request, f"Role '{role.name}' updated successfully.")
        return redirect('saas_core:role_list')

    return render(request, 'saas_core/role/form.html', {'role': role, 'matrix': _generate_matrix(role), 'is_edit': True})

@login_required(login_url='/auth/login/')
@require_permission('role.delete')
def role_delete(request, role_id):
    # 🟢 FIX: Passed 'request' to the service
    workspace = WorkspaceService.get_current_workspace(request)
    if request.method == 'POST':
        role = get_object_or_404(Role, id=role_id, workspace=workspace)
        try:
            role_name = role.name
            role.soft_delete(user=request.user)
            
            AuditService.log(
                request=request, workspace=workspace, action='role.delete',
                resource_type='Role', resource_id=str(role.id),
                metadata={'deleted_role_name': role_name}, status='SUCCESS'
            )
            
            messages.success(request, f"Role '{role_name}' has been safely removed.")
        except ValueError as e:
            messages.error(request, str(e))
    return redirect('saas_core:role_list')