from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.core.exceptions import ValidationError
from core.context import get_workspace, set_workspace
from apps.saas_core.models.tenant import WorkspaceMember
from apps.saas_core.models.company import Company
from apps.saas_core.decorators import require_permission
from apps.saas_core.models.settings import GlobalConfiguration
from .forms import RegistrationForm
from .services import IdentityService

def register_view(request):
    """Handles User Registration and Smart B2B Onboarding Routing."""
    if request.user.is_authenticated and get_workspace():
        return redirect('saas_core:dashboard_home')
        
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            company_name = form.cleaned_data.get('company_name')
            
            try:
                # 1. Create User and Workspace
                result = IdentityService.register_tenant_owner(
                    email=email, password=password, company_name=company_name
                )
                
                # 2. Authenticate
                user = authenticate(request, username=email, password=password)
                if not user:
                    user = authenticate(request, email=email, password=password)
                    
                if user is not None:
                    login(request, user)
                    
                    # 3. Inject workspace into session
                    workspace_id = str(result['workspace'].id)
                    request.session['active_workspace_id'] = workspace_id
                    set_workspace(workspace_id)
                    
                    messages.success(request, f"Welcome! Let's set up your first workspace for '{result['workspace'].name}'.")
                    
                    # 🟢 SAAS CONSTITUTION: Route to Company Creation first!
                    global_config = GlobalConfiguration.get_config()
                    if global_config.allow_company_before_subscription:
                        return redirect('saas_core:company_create')
                    else:
                        return redirect('saas_core:subscription_plans')
                else:
                    messages.error(request, "Registration successful, but auto-login failed. Please login.")
                    return redirect('identity:login')
                    
            except ValidationError as e:
                if hasattr(e, 'message_dict'):
                    for field, errors in e.message_dict.items():
                        for error in errors:
                            messages.error(request, f"{error}")
                else:
                    for error in e.messages:
                        messages.error(request, error)
            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
    else:
        form = RegistrationForm()
        
    return render(request, 'identity/register.html', {'form': form})

def login_view(request):
    """Handles standard user login with intelligent State Machine routing."""
    if request.user.is_authenticated and get_workspace():
        return redirect('saas_core:dashboard_home')
        
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        user = authenticate(request, username=email, password=password)
        if not user:
            user = authenticate(request, email=email, password=password)
            
        if user is not None:
            login(request, user)
            
            membership = WorkspaceMember.objects.filter(user=user).first()
            if membership:
                workspace_id = str(membership.workspace_id)
                request.session['active_workspace_id'] = workspace_id
                set_workspace(workspace_id)
                
                # 🟢 INTELLIGENT ROUTING: Check Workspace State
                workspace = membership.workspace
                company_exists = Company.objects.filter(workspace_id=workspace.id, is_deleted=False).exists()
                
                try:
                    is_sub_valid = workspace.subscription.is_valid
                except:
                    is_sub_valid = False

                if not company_exists:
                    messages.info(request, "Please create your company profile to continue.")
                    return redirect('saas_core:company_create')
                elif not is_sub_valid and GlobalConfiguration.get_config().dashboard_requires_active_subscription:
                    messages.warning(request, "Please select a subscription plan to unlock your dashboard.")
                    return redirect('saas_core:subscription_plans')
                else:
                    messages.success(request, "Welcome back!")
                    return redirect('saas_core:dashboard_home')
            else:
                if user.is_superuser or user.is_staff:
                    result = IdentityService.create_workspace_for_user(user, "Lumo OS HQ")
                    workspace_id = str(result['workspace'].id)
                    request.session['active_workspace_id'] = workspace_id
                    set_workspace(workspace_id)
                    messages.success(request, "Welcome Admin! System HQ workspace auto-generated.")
                    return redirect('saas_core:dashboard_home')
                    
                messages.warning(request, "No workspace found. Please register your company.")
                return redirect('identity:register')
        else:
            messages.error(request, "Invalid email or password.")
            
    return render(request, 'identity/login.html')

def logout_view(request):
    """Safely logs out, flushes session, and redirects."""
    logout(request)
    messages.success(request, "You have been successfully logged out.")
    return redirect('identity:login')