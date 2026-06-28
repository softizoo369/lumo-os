from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
import json

from apps.lumo_sites.models import SiteKit, SiteKitVersion, SiteKitManifest, ThemePreset
from apps.lumo_sites.forms_superadmin import SiteKitForm, SiteKitManifestForm

# শুধুমাত্র সুপার-অ্যাডমিন এই ভিউগুলো অ্যাক্সেস করতে পারবে
def is_superadmin(user):
    return user.is_authenticated and user.is_superuser

@user_passes_test(is_superadmin)
def superadmin_sitekit_list(request):
    """সবগুলো তৈরি করা মাস্টার থিম (SiteKits) দেখানোর ভিউ"""
    sitekits = SiteKit.objects.all().prefetch_related('versions')
    return render(request, 'lumo_sites/superadmin/sitekit_list.html', {'sitekits': sitekits})

@user_passes_test(is_superadmin)
def superadmin_sitekit_create(request):
    """নতুন একটি থিম (SiteKit) তৈরি করার ভিউ। এটি স্বয়ংক্রিয়ভাবে একটি Preset এবং Version 1.0 তৈরি করবে।"""
    if request.method == 'POST':
        form = SiteKitForm(request.POST)
        if form.is_valid():
            sitekit = form.save()
            
            # নতুন থিমের জন্য একটি ডিফল্ট কালার প্রিসেট তৈরি করা
            default_preset = ThemePreset.objects.create(
                name=f"{sitekit.name} Default Preset",
                primary_color="#4f46e5",
                secondary_color="#ffffff",
                heading_font="Inter",
                body_font="Inter"
            )
            
            # থিমের প্রথম ভার্সন (v1.0) তৈরি করা
            version = SiteKitVersion.objects.create(
                kit=sitekit,
                version_number="1.0",
                default_preset=default_preset
            )
            
            messages.success(request, f"🎉 '{sitekit.name}' থিমটি সফলভাবে তৈরি হয়েছে!")
            return redirect('lumo_sites:superadmin_sitekit_builder', version_id=version.id)
    else:
        form = SiteKitForm()
        
    return render(request, 'lumo_sites/superadmin/sitekit_form.html', {'form': form, 'title': 'Create New Theme (SiteKit)'})

@user_passes_test(is_superadmin)
def superadmin_sitekit_builder(request, version_id):
    """
    The True Engine: এই ভিউয়ের মাধ্যমে সুপার-অ্যাডমিন থিমের কোন পেজে 
    কোন সেকশন থাকবে তা ম্যাপ (Manifest) করবে।
    """
    version = get_object_or_404(SiteKitVersion, id=version_id)
    manifests = version.manifest.all()
    
    if request.method == 'POST':
        form = SiteKitManifestForm(request.POST)
        if form.is_valid():
            manifest = form.save(commit=False)
            manifest.kit_version = version
            
            # JSON ভ্যালিডেশন
            try:
                if type(manifest.starter_content_json) == str:
                    manifest.starter_content_json = json.loads(manifest.starter_content_json)
                manifest.save()
                messages.success(request, f"সেকশনটি সফলভাবে '{manifest.page_slug}' পেজে যুক্ত হয়েছে!")
                return redirect('lumo_sites:superadmin_sitekit_builder', version_id=version.id)
            except json.JSONDecodeError:
                messages.error(request, "Starter Content-এ ভ্যালিড JSON ফরম্যাট ব্যবহার করুন।")
    else:
        form = SiteKitManifestForm(initial={'page_slug': 'home', 'default_sort_order': manifests.count() + 1})
        
    return render(request, 'lumo_sites/superadmin/sitekit_builder.html', {
        'version': version,
        'manifests': manifests,
        'form': form
    })


from apps.lumo_sites.models import AtomicSection, AtomicSectionVersion
from apps.lumo_sites.forms_superadmin import AtomicSectionForm, AtomicSectionVersionForm

# =====================================================================
# ATOMIC SECTIONS (UI COMPONENTS) MANAGEMENT
# =====================================================================
@user_passes_test(is_superadmin)
def superadmin_section_list(request):
    """সবগুলো UI কম্পোনেন্ট দেখানোর ভিউ"""
    sections = AtomicSection.objects.all().prefetch_related('versions').order_by('category', 'name')
    return render(request, 'lumo_sites/superadmin/section_list.html', {'sections': sections})

@user_passes_test(is_superadmin)
def superadmin_section_create(request):
    """নতুন একটি UI কম্পোনেন্ট (Base Section) তৈরি করা"""
    if request.method == 'POST':
        form = AtomicSectionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ UI Component Section সফলভাবে তৈরি হয়েছে!")
            return redirect('lumo_sites:superadmin_section_list')
    else:
        form = AtomicSectionForm()
    return render(request, 'lumo_sites/superadmin/section_form.html', {'form': form, 'title': 'Create New UI Component'})

@user_passes_test(is_superadmin)
def superadmin_section_version_create(request, section_id):
    """একটি নির্দিষ্ট সেকশনের নতুন ভার্সন (HTML File Path) যুক্ত করা"""
    section = get_object_or_404(AtomicSection, id=section_id)
    if request.method == 'POST':
        form = AtomicSectionVersionForm(request.POST)
        if form.is_valid():
            version = form.save(commit=False)
            version.section = section
            try:
                # JSON Validation
                if type(version.default_schema_json) == str:
                    version.default_schema_json = json.loads(version.default_schema_json)
                version.save()
                messages.success(request, f"✅ Version {version.version_number} সফলভাবে {section.name}-এ যুক্ত হয়েছে!")
                return redirect('lumo_sites:superadmin_section_list')
            except json.JSONDecodeError:
                messages.error(request, "Starter Schema-তে ভ্যালিড JSON ফরম্যাট ব্যবহার করুন।")
    else:
        form = AtomicSectionVersionForm(initial={'default_schema_json': '{}'})
    return render(request, 'lumo_sites/superadmin/section_form.html', {'form': form, 'title': f'Add Version to {section.name}'})