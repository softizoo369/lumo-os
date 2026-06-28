from django import forms
from apps.lumo_sites.models import SiteKit, SiteKitManifest
from apps.lumo_sites.models import AtomicSection, AtomicSectionVersion

class SiteKitForm(forms.ModelForm):
    class Meta:
        model = SiteKit
        fields = ['name', 'industry', 'is_premium', 'price', 'required_plan']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Medicare Pro'}),
            'industry': forms.Select(attrs={'class': 'form-select'}),
            'is_premium': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '49.00'}),
            'required_plan': forms.Select(attrs={'class': 'form-select'}),
        }

class SiteKitManifestForm(forms.ModelForm):
    class Meta:
        model = SiteKitManifest
        fields = ['page_slug', 'section_version', 'starter_content_json', 'default_sort_order', 'is_required']
        widgets = {
            'page_slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., home, about-us'}),
            'section_version': forms.Select(attrs={'class': 'form-select'}),
            'starter_content_json': forms.Textarea(attrs={'class': 'form-control font-monospace', 'rows': 4, 'placeholder': '{"title": "Welcome to our clinic", "subtitle": "Best care..."}'}),
            'default_sort_order': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class AtomicSectionForm(forms.ModelForm):
    class Meta:
        model = AtomicSection
        fields = ['name', 'code', 'category']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'যেমন: Hero Section V1'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., hero_v1'}),
            'category': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Header, Content, Footer'}),
        }

class AtomicSectionVersionForm(forms.ModelForm):
    class Meta:
        model = AtomicSectionVersion
        fields = ['version_number', 'html_template_path', 'data_source_type', 'is_i18n_enabled', 'default_schema_json']
        widgets = {
            'version_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1.0'}),
            'html_template_path': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'lumo_sites/sections/hero/hero_v1.html'}),
            'data_source_type': forms.Select(attrs={'class': 'form-select'}),
            'is_i18n_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'default_schema_json': forms.Textarea(attrs={'class': 'form-control font-monospace', 'rows': 4, 'placeholder': '{"title": "Welcome", "subtitle": "..."}'}),
        }