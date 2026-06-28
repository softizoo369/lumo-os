# apps/saas_core/forms/company_form.py
from django import forms
from django.core.validators import FileExtensionValidator
from apps.saas_core.models.company import Company
from apps.saas_core.validators import validate_image_size
from apps.saas_core.models.settings import WorkspacePreference
from apps.saas_core.models.settings import PaymentGatewayConfig



class CompanyForm(forms.ModelForm):
    # Enforce extensions and size limits securely on the server
    logo = forms.ImageField(
        required=False,
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp']),
            validate_image_size
        ],
        widget=forms.FileInput(attrs={'accept': 'image/jpeg, image/png, image/webp'})
    )

    class Meta:
        model = Company
        fields = [
            'name', 'legal_name', 'email', 'phone', 'logo', 
            'country', 'currency', 'timezone', 'industry', 'is_active'
        ]



class WorkspacePreferenceForm(forms.ModelForm):
    """Form for managing Tenant-specific Preferences"""
    class Meta:
        model = WorkspacePreference
        fields = ['invoice_prefix', 'timezone', 'date_format', 'reply_to_email']
        widgets = {
            'invoice_prefix': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. INV-2026-'}),
            'timezone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Asia/Dhaka'}),
            'date_format': forms.Select(choices=[
                ('YYYY-MM-DD', 'YYYY-MM-DD (e.g. 2026-12-31)'),
                ('DD-MM-YYYY', 'DD-MM-YYYY (e.g. 31-12-2026)'),
                ('MM/DD/YYYY', 'MM/DD/YYYY (e.g. 12/31/2026)')
            ], attrs={'class': 'form-select'}),
            'reply_to_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'billing@yourcompany.com'}),
        }



class PaymentGatewayConfigForm(forms.ModelForm):
    """Form for securely configuring Tenant Payment API Keys"""
    class Meta:
        model = PaymentGatewayConfig
        fields = ['gateway', 'is_active', 'is_test_mode', 'api_key', 'api_secret', 'webhook_secret']
        widgets = {
            'gateway': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input', 'style': 'transform: scale(1.2);'}),
            'is_test_mode': forms.CheckboxInput(attrs={'class': 'form-check-input', 'style': 'transform: scale(1.2);'}),
            'api_key': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. pk_test_12345 / Store ID'}),
            'api_secret': forms.PasswordInput(render_value=True, attrs={'class': 'form-control', 'placeholder': 'e.g. sk_test_12345 / Store Password'}),
            'webhook_secret': forms.PasswordInput(render_value=True, attrs={'class': 'form-control', 'placeholder': 'Webhook Signing Secret (Optional)'}),
        }