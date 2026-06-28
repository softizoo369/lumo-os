from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, get_user_model
from apps.saas_core.services.invitation_acceptance import InvitationAcceptanceService

User = get_user_model()

def accept_invite(request, token):
    """Public onboarding view for accepting invitations."""
    # 1. Validate Token
    invitation = InvitationAcceptanceService.get_invitation(token)
    
    if not invitation:
        messages.error(request, "Invalid, expired, or already used invitation link.")
        return redirect('identity:login')

    # 2. Identify if user already has an account
    user_exists = User.objects.filter(email=invitation.email).exists()

    if request.method == 'POST':
        password = request.POST.get('password')
        
        try:
            if user_exists:
                # Existing User Flow: Authenticate first
                user = authenticate(email=invitation.email, password=password)
                if not user:
                    raise ValueError("Incorrect password for your existing account.")
                
                InvitationAcceptanceService.accept(request, invitation, user=user)
            else:
                # New User Flow: Create account
                first_name = request.POST.get('first_name', '')
                last_name = request.POST.get('last_name', '')
                
                if len(password) < 8:
                    raise ValueError("Password must be at least 8 characters long.")
                    
                user = InvitationAcceptanceService.accept(
                    request, invitation, password=password, 
                    first_name=first_name, last_name=last_name
                )
            
            # Auto-login after successful acceptance
            login(request, user)
            messages.success(request, f"Welcome to {invitation.workspace.name}!")
            return redirect('saas_core:dashboard_home')
            
        except ValueError as e:
            messages.error(request, str(e))

    return render(request, 'saas_core/team/accept_invite.html', {
        'invitation': invitation,
        'user_exists': user_exists
    })