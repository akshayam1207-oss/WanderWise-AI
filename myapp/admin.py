from django.contrib import admin
from .models import FAQ, ErrorCode, SupportTicket


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("id", "question", "category", "order", "is_active", "created_at")
    list_filter = ("category", "is_active")
    search_fields = ("question", "answer")
    list_editable = ("order", "is_active")


@admin.register(ErrorCode)
class ErrorCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "code_str", "title", "category", "is_site_specific", "created_at")
    list_filter = ("category", "is_site_specific")
    search_fields = ("code_str", "title", "meaning", "wanderwise_context", "solution")


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ("ticket_id", "name", "email", "subject", "category", "status", "created_at")
    list_filter = ("status", "category", "created_at")
    search_fields = ("ticket_id", "name", "email", "subject", "message", "admin_notes")
    list_editable = ("status",)
    readonly_fields = ("ticket_id", "created_at", "updated_at")
