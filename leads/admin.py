"""
Israinsols Pipeline - Django Admin Configuration (Phase 2)

Admin panel se leads monitor kar sakte hain:
- Filter by status, source
- Search by title, description
- Bulk actions (Mark Contacted, Reject, Export CSV)
- ScrapeLog se dekh sakte hain ke scraper kab chala aur kya hua
"""
import csv
from django.contrib import admin
from django.http import HttpResponse
from django.utils.html import format_html
from .models import ScrapedLead, ScrapeLog, FAQ, AgencyLead


# ──────────────────────────────────────────────
# Custom Admin Actions
# ──────────────────────────────────────────────
def mark_as_contacted(modeladmin, request, queryset):
    """Bulk action: Mark selected leads as Contacted"""
    updated = queryset.update(status=ScrapedLead.Status.CONTACTED)
    modeladmin.message_user(request, f"✅ {updated} leads marked as Contacted.")
mark_as_contacted.short_description = "✅ Mark selected as Contacted"


def mark_as_rejected(modeladmin, request, queryset):
    """Bulk action: Mark selected leads as Rejected"""
    updated = queryset.update(status=ScrapedLead.Status.REJECTED)
    modeladmin.message_user(request, f"🔴 {updated} leads marked as Rejected.")
mark_as_rejected.short_description = "🔴 Mark selected as Rejected"


def export_leads_csv(modeladmin, request, queryset):
    """Bulk action: Export selected leads as CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="israinsols_leads.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Title', 'Budget', 'Tech Stack', 'URL', 'Source',
        'Status', 'Client', 'Country', 'Scraped At'
    ])

    for lead in queryset:
        writer.writerow([
            lead.title,
            lead.budget,
            lead.tech_stack_display,
            lead.url,
            lead.get_source_display(),
            lead.get_status_display(),
            lead.client_name,
            lead.client_country,
            lead.scraped_at.strftime('%Y-%m-%d %H:%M'),
        ])

    return response
export_leads_csv.short_description = "📥 Export selected as CSV"


# ──────────────────────────────────────────────
# ScrapedLead Admin
# ──────────────────────────────────────────────
@admin.register(ScrapedLead)
class ScrapedLeadAdmin(admin.ModelAdmin):
    list_display = [
        'status_badge',
        'title_short',
        'budget',
        'tech_stack_display_col',
        'source',
        'scraped_at',
        'status',
    ]
    list_filter = ['status', 'source', 'scraped_at']
    search_fields = ['title', 'description', 'client_name', 'tech_stack']
    list_editable = ['status']  # Inline status change
    list_per_page = 50
    date_hierarchy = 'scraped_at'
    readonly_fields = ['content_hash', 'scraped_at', 'updated_at', 'notified_at']
    actions = [mark_as_contacted, mark_as_rejected, export_leads_csv]

    fieldsets = (
        ('📋 Lead Information', {
            'fields': ('title', 'description', 'budget', 'tech_stack', 'url', 'source')
        }),
        ('👤 Client Details', {
            'fields': ('client_name', 'client_country', 'posted_date'),
            'classes': ('collapse',),
        }),
        ('📊 Status & Tracking', {
            'fields': ('status', 'notes', 'telegram_message_id'),
        }),
        ('🔧 System Fields', {
            'fields': ('content_hash', 'scraped_at', 'notified_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def status_badge(self, obj):
        colors = {
            'unnotified': '#3498db',
            'notified': '#f39c12',
            'contacted': '#27ae60',
            'rejected': '#e74c3c',
            'applied': '#9b59b6',
        }
        color = colors.get(obj.status, '#95a5a6')
        return format_html(
            '<span style="background:{}; color:white; padding:3px 10px; '
            'border-radius:12px; font-size:11px; font-weight:bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    def title_short(self, obj):
        title = obj.title[:60] + '...' if len(obj.title) > 60 else obj.title
        return format_html('<a href="{}" target="_blank">{}</a>', obj.url, title)
    title_short.short_description = 'Title'

    def tech_stack_display_col(self, obj):
        return obj.tech_stack_display or '—'
    tech_stack_display_col.short_description = 'Tech Stack'


# ──────────────────────────────────────────────
# ScrapeLog Admin
# ──────────────────────────────────────────────
@admin.register(ScrapeLog)
class ScrapeLogAdmin(admin.ModelAdmin):
    list_display = [
        'run_status', 'source', 'total_found', 'new_saved',
        'duplicates_skipped', 'duration_display', 'started_at'
    ]
    list_filter = ['run_status', 'source', 'started_at']
    readonly_fields = [
        'source', 'run_status', 'total_found', 'new_saved',
        'duplicates_skipped', 'error_message', 'duration_seconds', 'started_at'
    ]
    list_per_page = 50

    def duration_display(self, obj):
        return f"{obj.duration_seconds:.1f}s"
    duration_display.short_description = 'Duration'

    def has_add_permission(self, request):
        return False  # Logs are auto-generated, not manually created



# ──────────────────────────────────────────────
# FAQ Admin
# ──────────────────────────────────────────────
@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ['question', 'category', 'order', 'is_active', 'created_at']
    list_filter = ['is_active', 'category', 'created_at']
    search_fields = ['question', 'answer', 'category']
    list_editable = ['order', 'is_active']
    list_per_page = 20


# ──────────────────────────────────────────────
# AgencyLead Admin
# ──────────────────────────────────────────────
@admin.register(AgencyLead)
class AgencyLeadAdmin(admin.ModelAdmin):
    list_display = ['status_badge', 'full_name', 'service_interested', 'created_at']
    list_filter = ['status', 'service_interested', 'created_at']
    search_fields = ['full_name', 'email', 'phone', 'message']
    list_per_page = 20
    readonly_fields = ['created_at', 'updated_at']

    def status_badge(self, obj):
        colors = {
            'new': '#3498db',
            'contacted': '#27ae60',
            'qualified': '#9b59b6',
            'lost': '#e74c3c',
        }
        color = colors.get(obj.status, '#95a5a6')
        return format_html(
            '<span style="background:{}; color:white; padding:3px 10px; '
            'border-radius:12px; font-size:11px; font-weight:bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'


# ──────────────────────────────────────────────
# Admin Site Customization
# ──────────────────────────────────────────────
admin.site.site_header = '🚀 Israinsols Management'
admin.site.site_title = 'Israinsols Admin'
admin.site.index_title = 'Lead & FAQ Dashboard'
