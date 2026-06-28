import uuid
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
from django.utils.safestring import mark_safe

# Lumo OS Imports
from apps.identity.models import Role
from apps.saas_core.models.tenant import WorkspaceMember
from apps.saas_core.models.company import Company, CompanyAccess
from apps.saas_core.models.invitation import WorkspaceInvitation
from apps.saas_core.services.audit_service import AuditService
from apps.saas_core.services.workspace_service import WorkspaceService
from apps.saas_core.services.invitation_policy import InvitationPolicyService
from apps.saas_core.services.invitation_service import InvitationService
from apps.saas_core.decorators import require_permission

User = get_user_model()

@login_required(login_url='/auth/login/')
@require_permission('team.read')
def team_list(request):
    """Displays active members and pending invitations."""
    # 🟢 FIX: Passed 'request' to the service
    workspace = WorkspaceService.get_current_workspace(request)
    
    members = WorkspaceMember.objects.filter(workspace=workspace, is_deleted=False).select_related('user', 'role').order_by('created_at')
    pending_invites = WorkspaceInvitation.objects.filter(workspace=workspace, status='PENDING').order_by('-created_at')
    roles = Role.objects.filter(workspace=workspace, is_deleted=False)
    
    return render(request, 'saas_core/team/list.html', {
        'members': members,
        'pending_invites': pending_invites,
        'roles': roles
    })


@login_required(login_url='/auth/login/')
@require_permission('team.update')
def team_invite(request):
    """Handles the form submission from the Invite Modal."""
    # 🟢 FIX: Passed 'request' to the service
    workspace = WorkspaceService.get_current_workspace(request)
    
    if request.method == 'POST':
        email = request.POST.get('email')
        role_id = request.POST.get('role_id')
        role = get_object_or_404(Role, id=role_id, workspace=workspace)
        
        try:
            InvitationPolicyService.check_eligibility(workspace)
            invitation, raw_token = InvitationService.create_or_resend_invitation(
                request=request, workspace=workspace, email=email, role=role
            )
            
            invite_link = f"http://127.0.0.1:8000/invite/accept/{raw_token}/"
            
            html_msg = f"""
            <div class="mb-1">Invitation link generated for <strong>{email}</strong>:</div>
            <div class="d-flex align-items-center bg-white bg-opacity-25 border border-white border-opacity-25 rounded p-1 mt-2">
                <input type="text" id="link-{raw_token[:5]}" class="form-control form-control-sm border-0 shadow-none bg-transparent text-white" value="{invite_link}" readonly>
                <button type="button" class="btn btn-sm btn-light border-0 rounded text-primary fw-bold px-3 ms-1" onclick="copyInviteLink(this, 'link-{raw_token[:5]}')">
                    Copy
                </button>
            </div>
            <small class="text-warning mt-2 d-block" style="font-size:0.7rem;"><i class="bi bi-shield-lock-fill"></i> Raw link is never saved. Copy it now!</small>
            """
            messages.success(request, mark_safe(html_msg))
            
        except ValueError as e:
            messages.error(request, str(e))
            
    return redirect('saas_core:team_list')


@login_required(login_url='/auth/login/')
@require_permission('team.update')
def team_update(request, member_id):
    """Update a team member's role and company access."""
    # 🟢 FIX: Passed 'request' to the service
    workspace = WorkspaceService.get_current_workspace(request)
    
    member = get_object_or_404(WorkspaceMember, id=member_id, workspace=workspace, is_deleted=False)
    roles = Role.objects.filter(workspace=workspace, is_deleted=False)
    companies = Company.objects.filter(workspace_id=workspace.id, is_deleted=False).order_by('name')
    
    current_accesses = CompanyAccess.objects.filter(member=member, is_deleted=False).values_list('company_id', flat=True)
    current_access_ids = [str(uuid) for uuid in current_accesses]

    if request.method == 'POST':
        role_id = request.POST.get('role_id')
        if role_id:
            new_role = get_object_or_404(Role, id=role_id, workspace=workspace)
            member.role = new_role
            member.save()

        if not (member.role.is_system_default and member.role.name == 'OWNER'):
            selected_company_ids = request.POST.getlist('companies')
            CompanyAccess.objects.filter(member=member).exclude(company_id__in=selected_company_ids).update(is_deleted=True)
            
            for c_id in selected_company_ids:
                access = CompanyAccess._base_manager.filter(workspace_id=workspace.id, member=member, company_id=c_id).first()
                if access:
                    if getattr(access, 'is_deleted', False):
                        access.is_deleted = False
                        access.save()
                else:
                    CompanyAccess.objects.create(workspace_id=workspace.id, member=member, company_id=c_id)

        from apps.saas_core.policy_engine import PolicyEngine
        PolicyEngine.invalidate_cache(workspace.id, member.user.id)

        messages.success(request, f"Access settings updated for {member.user.email}.")
        return redirect('saas_core:team_list')

    return render(request, 'saas_core/team/update.html', {
        'member': member, 'roles': roles, 'companies': companies, 'current_access_ids': current_access_ids
    })


@login_required(login_url='/auth/login/')
@require_permission('team.remove')
def team_remove(request, member_id):
    """Remove a member from the workspace."""
    # 🟢 FIX: Passed 'request' to the service
    workspace = WorkspaceService.get_current_workspace(request)
    
    if request.method == 'POST':
        member = get_object_or_404(WorkspaceMember, id=member_id, workspace=workspace)
        
        if member.user == request.user:
            messages.error(request, "You cannot remove yourself from the workspace.")
        else:
            member.is_deleted = True
            member.save()
            messages.success(request, f"Member '{member.user.email}' has been removed.")
            
    return redirect('saas_core:team_list')


@login_required(login_url='/auth/login/')
@require_permission('team.update')
def team_add_manual(request):
    """Directly adds a user to the workspace without email invitation."""
    # 🟢 FIX: Passed 'request' to the service
    workspace = WorkspaceService.get_current_workspace(request)
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email').lower().strip()
        password = request.POST.get('password')
        role_id = request.POST.get('role_id')
        role = get_object_or_404(Role, id=role_id, workspace=workspace)

        try:
            InvitationPolicyService.check_eligibility(workspace)

            with transaction.atomic():
                user = User.objects.filter(email=email).first()
                if user:
                    member, created = WorkspaceMember.objects.get_or_create(workspace=workspace, user=user, defaults={'role': role})
                    if not created and member.is_deleted:
                        member.is_deleted = False
                        member.role = role
                        member.save()
                    elif not created:
                        raise ValueError(f"The user {email} is already in this workspace.")
                else:
                    if len(password) < 8:
                        raise ValueError("Password must be at least 8 characters long.")
                    user = User.objects.create_user(email=email, password=password, first_name=first_name, last_name=last_name)
                    WorkspaceMember.objects.create(workspace=workspace, user=user, role=role)

                AuditService.log(
                    request=request, workspace=workspace, action='team.add_manual',
                    resource_type='WorkspaceMember', resource_id=str(user.id),
                    metadata={'email': email, 'role': role.name}, status='SUCCESS'
                )

            messages.success(request, f"User {first_name} ({email}) has been added successfully!")
        except ValueError as e:
            messages.error(request, str(e))

    return redirect('saas_core:team_list')