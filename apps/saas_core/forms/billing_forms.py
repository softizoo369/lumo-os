from django import forms
from apps.saas_core.models.finance import BillingProfile

class BillingProfileForm(forms.ModelForm):
    class Meta:
        model = BillingProfile
        fields = [
            'legal_company_name', 'billing_email', 
            'address_line', 'city', 'state', 'postal_code', 'country',
            'tax_registration_type', 'tax_registration_number'
        ]
        widgets = {
            'legal_company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Lumo Technologies Ltd.'}),
            'billing_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'billing@company.com'}),
            'address_line': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '123 Tech Street, Floor 5'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dhaka'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dhaka Division'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1212'}),
            'country': forms.Select(attrs={'class': 'form-select select2-enable'}),
            'tax_registration_type': forms.Select(attrs={'class': 'form-select'}),
            'tax_registration_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter TIN, BIN, or VAT Number'}),
        }