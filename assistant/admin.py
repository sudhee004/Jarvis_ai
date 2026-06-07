"""
Django admin configuration for the Jarvis AI Assistant.

Each model is registered with a custom ModelAdmin that provides:
  - list_display  : columns visible in the changelist
  - list_filter   : sidebar filter facets
  - search_fields : full-text search targets
  - readonly_fields / date_hierarchy where appropriate
  - inline editors for related objects

Access the admin at:  http://127.0.0.1:8000/admin/
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.timezone import localtime

from .models import (
    ActivityLog,
    ChatMessage,
    ChatSession,
    Note,
    Reminder,
    UserMemory,
    UserProfile,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _short(text, length=60):
    """Truncate text to `length` chars for display in changelist."""
    return text[:length] + '…' if len(text) > length else text


# ===========================================================================
# UserProfile
# ===========================================================================
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ('user', 'theme', 'preferred_language', 'timezone',
                     'voice_enabled', 'notifications_enabled',
                     'total_messages', 'total_sessions', 'created_at')
    list_filter   = ('theme', 'preferred_language', 'voice_enabled',
                     'notifications_enabled')
    search_fields = ('user__username', 'user__email', 'bio')
    readonly_fields = ('created_at', 'updated_at', 'total_messages', 'total_sessions')
    date_hierarchy  = 'created_at'

    fieldsets = (
        ('User', {
            'fields': ('user',),
        }),
        ('Display', {
            'fields': ('avatar', 'bio'),
        }),
        ('Preferences', {
            'fields': ('theme', 'preferred_language', 'timezone',
                       'voice_enabled', 'notifications_enabled'),
        }),
        ('Stats (read-only)', {
            'fields': ('total_messages', 'total_sessions'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


# ===========================================================================
# ChatMessage inline — shown inside ChatSession admin
# ===========================================================================
class ChatMessageInline(admin.TabularInline):
    model   = ChatMessage
    extra   = 0
    max_num = 50       # limit inline rows for performance
    readonly_fields  = ('role', 'content', 'token_count', 'is_flagged', 'created_at')
    fields           = ('role', 'content', 'token_count', 'is_flagged', 'created_at')
    can_delete       = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


# ===========================================================================
# ChatSession
# ===========================================================================
@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display    = ('title', 'user', 'status', 'message_count_display',
                       'total_tokens', 'last_message_at', 'created_at')
    list_filter     = ('status',)
    search_fields   = ('title', 'user__username', 'summary')
    readonly_fields = ('created_at', 'updated_at', 'last_message_at', 'total_tokens')
    date_hierarchy  = 'created_at'
    inlines         = [ChatMessageInline]

    fieldsets = (
        ('Session Info', {
            'fields': ('user', 'title', 'status'),
        }),
        ('Summary & Tokens', {
            'fields': ('summary', 'total_tokens'),
        }),
        ('Timestamps', {
            'fields': ('last_message_at', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Messages')
    def message_count_display(self, obj):
        count = obj.message_count()
        return format_html('<strong>{}</strong>', count)


# ===========================================================================
# ChatMessage
# ===========================================================================
@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display    = ('session_title', 'role', 'content_preview',
                       'token_count', 'is_flagged', 'created_at')
    list_filter     = ('role', 'is_flagged')
    search_fields   = ('content', 'session__title', 'session__user__username')
    readonly_fields = ('created_at',)
    date_hierarchy  = 'created_at'

    @admin.display(description='Session')
    def session_title(self, obj):
        return obj.session.title

    @admin.display(description='Content Preview')
    def content_preview(self, obj):
        return _short(obj.content)


# ===========================================================================
# Note
# ===========================================================================
@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display    = ('title', 'user', 'tags', 'is_pinned',
                       'is_archived', 'updated_at', 'created_at')
    list_filter     = ('is_pinned', 'is_archived')
    search_fields   = ('title', 'content', 'tags', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy  = 'created_at'
    list_editable   = ('is_pinned', 'is_archived')

    fieldsets = (
        ('Note', {
            'fields': ('user', 'session', 'title', 'content'),
        }),
        ('Organisation', {
            'fields': ('tags', 'is_pinned', 'is_archived'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


# ===========================================================================
# Reminder
# ===========================================================================
@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display    = ('title', 'user', 'remind_at', 'priority',
                       'status', 'is_recurring', 'overdue_badge', 'created_at')
    list_filter     = ('priority', 'status', 'is_recurring')
    search_fields   = ('title', 'description', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy  = 'remind_at'
    list_editable   = ('status', 'priority')

    fieldsets = (
        ('Reminder', {
            'fields': ('user', 'session', 'title', 'description'),
        }),
        ('Scheduling', {
            'fields': ('remind_at', 'priority', 'status',
                       'is_recurring', 'recurrence_rule', 'snoozed_until'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Overdue?', boolean=True)
    def overdue_badge(self, obj):
        return obj.is_overdue()


# ===========================================================================
# UserMemory
# ===========================================================================
@admin.register(UserMemory)
class UserMemoryAdmin(admin.ModelAdmin):
    list_display    = ('user', 'key', 'value_preview', 'category',
                       'confidence', 'is_active', 'updated_at')
    list_filter     = ('category', 'is_active')
    search_fields   = ('key', 'value', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy  = 'created_at'
    list_editable   = ('is_active',)

    fieldsets = (
        ('Memory Entry', {
            'fields': ('user', 'source_session', 'key', 'value', 'category'),
        }),
        ('AI Metadata', {
            'fields': ('confidence', 'is_active'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Value')
    def value_preview(self, obj):
        return _short(obj.value)


# ===========================================================================
# ActivityLog
# ===========================================================================
@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display    = ('created_at_local', 'user', 'action_badge',
                       'description_preview', 'ip_address')
    list_filter     = ('action',)
    search_fields   = ('user__username', 'description', 'ip_address')
    readonly_fields = ('user', 'action', 'description', 'metadata',
                       'ip_address', 'user_agent', 'created_at')
    date_hierarchy  = 'created_at'

    # ActivityLog is immutable — disable add/change/delete from admin
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        # Allow superusers to purge logs if needed
        return request.user.is_superuser

    @admin.display(description='Timestamp', ordering='created_at')
    def created_at_local(self, obj):
        return localtime(obj.created_at).strftime('%Y-%m-%d %H:%M:%S')

    @admin.display(description='Action')
    def action_badge(self, obj):
        colour_map = {
            'register':       '#63f0ff',
            'login':          '#4ade80',
            'logout':         '#94a3b8',
            'start_chat':     '#a855f7',
            'send_message':   '#a855f7',
            'create_note':    '#2dd4bf',
            'update_note':    '#2dd4bf',
            'delete_note':    '#f87171',
            'create_reminder':'#fb923c',
            'dismiss_reminder':'#fb923c',
        }
        colour = colour_map.get(obj.action, '#94a3b8')
        return format_html(
            '<span style="'
            'background:{};color:#080b14;'
            'padding:2px 8px;border-radius:999px;'
            'font-size:0.75rem;font-weight:700;">'
            '{}</span>',
            colour,
            obj.get_action_display(),
        )

    @admin.display(description='Description')
    def description_preview(self, obj):
        return _short(obj.description) if obj.description else '—'


# ---------------------------------------------------------------------------
# Customise the admin site header and title
# ---------------------------------------------------------------------------
admin.site.site_header = 'Jarvis AI — Admin Panel'
admin.site.site_title  = 'Jarvis AI Admin'
admin.site.index_title = 'Database Management'
