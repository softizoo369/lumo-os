from django import forms

class RegistrationForm(forms.Form):
    company_name = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg', 
            'placeholder': 'e.g., Acme Corp',
            'autocomplete': 'organization'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control form-control-lg', 
            'placeholder': 'name@company.com',
            'autocomplete': 'email'
        })
    )
    password = forms.CharField(
        min_length=8,
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg', 
            'placeholder': 'Create a strong password',
            'autocomplete': 'new-password'
        })
    )