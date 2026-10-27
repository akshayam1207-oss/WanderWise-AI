from django.contrib import admin
from .models import FAQ, SupportTicket


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("id", "question", "category", "order", "is_active", "created_at")
    list_filter = ("category", "is_active")
    search_fields = ("question", "answer")
    list_editable = ("order", "is_active")


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ("ticket_id", "name", "email", "subject", "category", "status", "created_at")
    list_filter = ("status", "category", "created_at")
    search_fields = ("ticket_id", "name", "email", "subject", "message")
    readonly_fields = ("ticket_id", "created_at", "updated_at")
