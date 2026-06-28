from django.contrib import admin
from apps.saas_core.models import (
    GlobalConfiguration, WorkspacePreference, PaymentGatewayConfig,
    Workspace, WorkspaceMember, WorkspaceUsage,
    SubscriptionPlan, PlanPrice, WorkspaceSubscription,
    PaymentGateway, PaymentAccount, TaxRate, BillingProfile,
    SubscriptionOrder, PaymentTransaction, ProcessedWebhookEvent,
    Invoice, InvoiceLineItem,
    Company, CompanyAccess,
    AuditLog, WorkspaceInvitation
)

# ==========================================
# 1. SYSTEM SETTINGS
# ==========================================
@admin.register(GlobalConfiguration)
class GlobalConfigurationAdmin(admin.ModelAdmin):
    list_display = ('site_name', 'support_email', 'maintenance_mode', 'trial_enabled')
    
    def has_add_permission(self, request):
        # Singleton: Prevent adding more than 1 config
        if self.model.objects.exists():
            return False
        return super().has_add_permission(request)

@admin.register(WorkspacePreference)
class WorkspacePreferenceAdmin(admin.ModelAdmin):
    list_display = ('workspace', 'invoice_prefix', 'timezone', 'theme_color')
    search_fields = ('workspace__name',)

# ==========================================
# 2. TENANT & WORKSPACE
# ==========================================
class WorkspaceMemberInline(admin.TabularInline):
    model = WorkspaceMember
    extra = 0

@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'domain', 'status', 'created_at')
    list_filter = ('status', 'is_deleted')
    search_fields = ('name', 'domain')
    inlines = [WorkspaceMemberInline]

@admin.register(WorkspaceUsage)
class WorkspaceUsageAdmin(admin.ModelAdmin):
    list_display = ('workspace_id', 'total_users', 'total_companies', 'total_storage_mb', 'last_recalculated_at')

# ==========================================
# 3. SUBSCRIPTION & PRICING PLANS
# ==========================================
class PlanPriceInline(admin.TabularInline):
    model = PlanPrice
    extra = 1

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active', 'is_public', 'is_popular', 'sort_order')
    list_filter = ('is_active', 'is_public', 'is_popular', 'requires_sales_contact')
    search_fields = ('name', 'code')
    inlines = [PlanPriceInline]

@admin.register(WorkspaceSubscription)
class WorkspaceSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('workspace', 'plan', 'status', 'current_period_end', 'is_valid')
    list_filter = ('status', 'cancel_at_period_end')
    search_fields = ('workspace__name',)

# ==========================================
# 4. FINANCE & BILLING
# ==========================================
@admin.register(SubscriptionOrder)
class SubscriptionOrderAdmin(admin.ModelAdmin):
    list_display = ('workspace', 'snapshot_plan_name', 'total_amount', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('workspace__name', 'snapshot_plan_name')

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'workspace', 'amount_paid', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('transaction_id', 'workspace__name')

class InvoiceLineItemInline(admin.TabularInline):
    model = InvoiceLineItem
    extra = 0

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'workspace', 'total_amount', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('invoice_number', 'workspace__name')
    inlines = [InvoiceLineItemInline]

@admin.register(PaymentGateway)
class PaymentGatewayAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active')

@admin.register(PaymentAccount)
class PaymentAccountAdmin(admin.ModelAdmin):
    list_display = ('gateway', 'account_name', 'account_number', 'is_active')

@admin.register(BillingProfile)
class BillingProfileAdmin(admin.ModelAdmin):
    list_display = ('legal_company_name', 'workspace', 'billing_email', 'country')
    search_fields = ('legal_company_name', 'workspace__name')

# ==========================================
# 5. AUDIT & LOGS
# ==========================================
@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'actor', 'resource_type', 'created_at')
    list_filter = ('action', 'resource_type')
    search_fields = ('action', 'actor__email', 'resource_id')
    readonly_fields = ('action', 'actor', 'resource_type', 'resource_id', 'metadata', 'ip_address', 'user_agent')

@admin.register(ProcessedWebhookEvent)
class ProcessedWebhookEventAdmin(admin.ModelAdmin):
    list_display = ('event_id', 'gateway_name', 'event_type', 'status')
    list_filter = ('status', 'gateway_name')
    search_fields = ('event_id',)