from django import forms
from apps.lumo_sites.models import ThemePreset, TenantPage, SiteDomain, SiteMenuItem
from apps.lumo_sites.models import MediaAsset
from apps.lumo_sites.models import FormDefinition

class DynamicSchemaForm(forms.Form):
    def __init__(self, schema, initial_content=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.schema = schema
        self.initial_content = initial_content or {}

        # 🟢 স্মার্ট ডিটেকশন: যদি স্কিমায় form_definition_id থাকে, তবে ডাটাবেস থেকে স্কিমা ফেচ করো
        if 'form_definition_id' in self.initial_content:
            try:
                form_def = FormDefinition.objects.get(id=self.initial_content['form_definition_id'])
                # ডাটাবেসের ফর্ম স্কিমা এখানে ইমপ্লিমেন্ট করুন
                self.add_form_fields(form_def.schema_json)
            except FormDefinition.DoesNotExist:
                pass
        else:
            self.add_fields_from_schema(schema)

    def add_fields_from_schema(self, schema_dict):
        # ফ্ল্যাটেনিং লজিক
        for key, value in schema_dict.items():
            # 🟢 SPRINT 5 FIX: Handle UUID/Reference types safely to prevent 500 crashes
            initial_val = self.initial_content.get(key, '')
            
            # Check if value is a dict (which means the raw schema got passed in by mistake)
            if isinstance(value, dict) and value.get('type') == 'reference':
                # If initial_val is also somehow the raw dict, clear it out to avoid UUID ValidationError
                if isinstance(initial_val, dict):
                    initial_val = ''
            
            self.fields[key] = forms.CharField(initial=initial_val)

    def add_form_fields(self, schema_list):
        # ফর্ম বিল্ডারের JSON Array (List of dicts) থেকে ফিল্ড বানানো
        for item in schema_list:
            field_name = item.get('name')
            # 🟢 SPRINT 5 FIX: Same safety check here
            initial_val = self.initial_content.get(field_name, '')
            if isinstance(initial_val, dict):
                initial_val = ''
                
            self.fields[field_name] = forms.CharField(
                label=item.get('label'),
                initial=initial_val,
                widget=forms.TextInput(attrs={'class': 'w-full p-2 border rounded'})
            )

    def get_unflattened_data(self):
        # সেভ করার জন্য ডেটা প্রসেসিং
        return self.cleaned_data


class ThemePresetForm(forms.ModelForm):
    class Meta:
        model = ThemePreset
        fields = ['primary_color', 'secondary_color', 'heading_font', 'body_font', 'border_radius']
        widgets = {
            'primary_color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color w-100'}),
            'secondary_color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color w-100'}),
            'heading_font': forms.Select(attrs={'class': 'form-select'}),
            'body_font': forms.Select(attrs={'class': 'form-select'}),
            'border_radius': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 8px or 0.5rem'}),
        }


class TenantPageForm(forms.ModelForm):
    # 🟢 SPRINT 1 FIX: Auto Navigation Feature
    add_to_main_nav = forms.BooleanField(
        required=False, 
        initial=True, 
        label="Add to Main Navigation"
    )
    
    class Meta:
        model = TenantPage
        fields = ['title', 'slug', 'seo_title', 'seo_description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. About Us'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. about-us'}),
            'seo_title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SEO Title (Max 60 chars)'}),
            'seo_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Meta description for Google search...'}),
        }


class SiteMenuItemForm(forms.ModelForm):
    class Meta:
        model = SiteMenuItem
        fields = ['label', 'url', 'sort_order']
        widgets = {
            'label': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. About Us'}),
            'url': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. /about-us or https://...'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control', 'value': 0}),
        }


class MediaAssetForm(forms.ModelForm):
    class Meta:
        model = MediaAsset
        fields = ['file_path', 'alt_text', 'is_public']
        widgets = {
            'file_path': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*,application/pdf'}),
            'alt_text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Company Logo'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input', 'style': 'transform: scale(1.3);'}),
        }


class SiteDomainForm(forms.ModelForm):
    class Meta:
        model = SiteDomain
        fields = ['domain_name', 'is_primary', 'is_subdomain'] 
        widgets = {
            'domain_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., www.brand.com or blog.brand.com'}),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_subdomain': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class FormDefinitionForm(forms.ModelForm):
    class Meta:
        model = FormDefinition
        fields = ['name', 'success_message', 'schema_json']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Contact Us Form'}),
            'success_message': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'schema_json': forms.Textarea(attrs={'class': 'form-control font-monospace', 'rows': 4, 'placeholder': '[{"field": "email", "type": "text"}]'}),
        }