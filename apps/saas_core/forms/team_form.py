from django import forms
from apps.identity.models import Role
from apps.saas_core.models.tenant import WorkspaceMember

class TeamInviteForm(forms.Form):
    email = forms.EmailField(
        label="Colleague's Work Email",
        widget=forms.EmailInput(attrs={'placeholder': 'name@company.com'})
    )
    role = forms.ModelChoiceField(
        queryset=Role.objects.none(),
        empty_label="Select a Role",
        label="Assign Role"
    )

    def __init__(self, workspace, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 🔴 শুধুমাত্র বর্তমান ওয়ার্কস্পেসের রোলগুলো দেখাবে
        self.fields['role'].queryset = Role.objects.filter(workspace=workspace, is_deleted=False)