from django import forms
from apps.saas_core.models.subscription import SubscriptionPlan, PlanPrice
from apps.core_masterdata.models import Currency
from apps.saas_core.models.tenant import Workspace
from apps.saas_core.models.finance import TaxRate, PaymentGateway, PaymentAccount
from apps.saas_core.models.settings import GlobalConfiguration
from apps.saas_core.models.feature import Feature # 🟢 NEW IMPORT

class SubscriptionPlanForm(forms.ModelForm):
    """Enterprise Form for creating the Master Plan with Commercial Flags"""
    
    currency = forms.ModelChoiceField(
        queryset=Currency.objects.all(), 
        required=True, 
        empty_label="Select Base Currency",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    monthly_price = forms.DecimalField(
        max_digits=10, decimal_places=2, required=True, initial=0.00, min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 29.00'})
    )
    yearly_price = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0.00, min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 290.00'})
    )
    
    # 🟢 NEW: Dynamic Module Mapping Field
    features = forms.ModelMultipleChoiceField(
        queryset=Feature.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input feature-checkbox', 'style': 'transform: scale(1.2); cursor: pointer;'}),
        required=False,
        label="Unlocked Modules"
    )

    class Meta:
        model = SubscriptionPlan
        fields = [
            'name', 'code', 'description', 
            'max_users', 'max_companies', 'max_customers', 'max_storage_mb',
            'is_default', 'is_popular', 'is_public', 'allow_signup', 'requires_sales_contact',
            'is_free_plan', 'is_trial_plan', 'trial_days', 'is_active', 'sort_order'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Professional Plan'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. PRO_TIER'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'max_users': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'max_companies': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'max_customers': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'max_storage_mb': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input', 'style': 'transform: scale(1.3);'}),
            'is_popular': forms.CheckboxInput(attrs={'class': 'form-check-input', 'style': 'transform: scale(1.3);'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input', 'style': 'transform: scale(1.3);'}),
            'allow_signup': forms.CheckboxInput(attrs={'class': 'form-check-input', 'style': 'transform: scale(1.3);'}),
            'requires_sales_contact': forms.CheckboxInput(attrs={'class': 'form-check-input', 'style': 'transform: scale(1.3);'}),
            'is_free_plan': forms.CheckboxInput(attrs={'class': 'form-check-input', 'style': 'transform: scale(1.3);'}),
            'is_trial_plan': forms.CheckboxInput(attrs={'class': 'form-check-input', 'style': 'transform: scale(1.3);'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input', 'style': 'transform: scale(1.3);'}),
            'trial_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        monthly = cleaned_data.get('monthly_price')
        yearly = cleaned_data.get('yearly_price')
        if monthly is not None and monthly < 0:
            self.add_error('monthly_price', "Price cannot be negative.")
        if yearly is not None and yearly < 0:
            self.add_error('yearly_price', "Price cannot be negative.")
        return cleaned_data

# (বাকি ফর্মগুলো আগের মতোই থাকবে)

    def clean(self):
        cleaned_data = super().clean()
        monthly = cleaned_data.get('monthly_price')
        yearly = cleaned_data.get('yearly_price')
        if monthly is not None and monthly < 0:
            self.add_error('monthly_price', "Price cannot be negative.")
        if yearly is not None and yearly < 0:
            self.add_error('yearly_price', "Price cannot be negative.")
        return cleaned_data

class PlanPriceForm(forms.ModelForm):
    class Meta:
        model = PlanPrice
        fields = ['currency', 'amount', 'billing_cycle', 'is_active']
        widgets = {
            'currency': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'billing_cycle': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class GlobalConfigForm(forms.ModelForm):
    """Form for managing Superadmin Global SaaS Configuration"""
    class Meta:
        model = GlobalConfiguration
        fields = [
            'site_name', 'support_email', 'default_timezone', 'maintenance_mode',
            # 🟢 Added Constitution Rules
            'allow_company_before_subscription', 'dashboard_requires_active_subscription',
            'trial_enabled', 'grace_period_days', 'max_payment_retries'
        ]
        widgets = {
            'site_name': forms.TextInput(attrs={'class': 'form-control'}),
            'support_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'default_timezone': forms.TextInput(attrs={'class': 'form-control'}),
            'maintenance_mode': forms.CheckboxInput(attrs={'class': 'form-check-input', 'style': 'transform: scale(1.3);'}),
            
            'allow_company_before_subscription': forms.CheckboxInput(attrs={'class': 'form-check-input', 'style': 'transform: scale(1.3);'}),
            'dashboard_requires_active_subscription': forms.CheckboxInput(attrs={'class': 'form-check-input', 'style': 'transform: scale(1.3);'}),
            'trial_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input', 'style': 'transform: scale(1.3);'}),
            'grace_period_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_payment_retries': forms.NumberInput(attrs={'class': 'form-control'}),
        }

# ==========================================
# OTHER EXISTING FORMS (Unchanged)
# ==========================================
class TaxRateForm(forms.ModelForm):
    class Meta:
        model = TaxRate
        fields = ['name', 'country', 'state_province', 'percentage', 'effective_from', 'effective_to', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. BD VAT 15%'}),
            'country': forms.Select(attrs={'class': 'form-select select2-enable'}),
            'state_province': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional state/region'}),
            'percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'effective_from': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'effective_to': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class PaymentGatewayForm(forms.ModelForm):
    class Meta:
        model = PaymentGateway
        fields = ['name', 'code', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Stripe, bKash'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'STRIPE, BKASH'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class PaymentAccountForm(forms.ModelForm):
    class Meta:
        model = PaymentAccount
        fields = ['gateway', 'account_name', 'account_number', 'branch_name', 'routing_number', 'is_active']
        widgets = {
            'gateway': forms.Select(attrs={'class': 'form-select'}),
            'account_name': forms.TextInput(attrs={'class': 'form-control'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'branch_name': forms.TextInput(attrs={'class': 'form-control'}),
            'routing_number': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class WorkspaceForm(forms.ModelForm):
    class Meta:
        model = Workspace
        fields = ['name', 'domain', 'status', 'suspension_reason', 'timezone', 'currency']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'domain': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'suspension_reason': forms.Select(attrs={'class': 'form-select'}),
            'timezone': forms.TextInput(attrs={'class': 'form-control'}),
            'currency': forms.TextInput(attrs={'class': 'form-control'}),
        }