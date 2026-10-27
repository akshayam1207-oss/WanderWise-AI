import uuid
from django.db import models


class FAQ(models.Model):
    """
    Frequently Asked Questions stored in SQL database.
    Retrieved dynamically on the FAQ page and used by the AI assistant.
    """
    CATEGORY_CHOICES = [
        ("General", "General"),
        ("Planning", "Trip Planning"),
        ("Budget", "Budget & Pricing"),
        ("Troubleshooting", "Troubleshooting & Errors"),
    ]

    question = models.CharField(max_length=300)
    answer = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="General")
    order = models.PositiveIntegerField(default=0, help_text="Ordering index for display")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return self.question


class ErrorCode(models.Model):
    """
    Error codes stored in SQL database (Assessment Requirement: 8+ error codes in SQL).
    Provides knowledge for AI assistant explanations, custom error views, and API lookup.
    """
    code = models.IntegerField(unique=True, help_text="Status code number (e.g. 400, 404, 600)")
    code_str = models.CharField(max_length=20, help_text="Display string (e.g. '400', 'WW-600')")
    title = models.CharField(max_length=150)
    category = models.CharField(max_length=60, default="Client Error")
    meaning = models.TextField()
    wanderwise_context = models.TextField()
    solution = models.TextField()
    is_site_specific = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        verbose_name = "Error Code"
        verbose_name_plural = "Error Codes"

    def __str__(self):
        return f"[{self.code_str}] {self.title}"


class SupportTicket(models.Model):
    """
    Support tickets stored in SQL database.
    Supports full CRUD operations (Create, Read, Update, Delete).
    Created when AI assistant cannot answer or user requests support.
    """
    STATUS_CHOICES = [
        ("OPEN", "Open"),
        ("IN_PROGRESS", "In Progress"),
        ("RESOLVED", "Resolved"),
        ("CLOSED", "Closed"),
    ]

    ticket_id = models.CharField(max_length=30, unique=True, editable=False)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    category = models.CharField(max_length=60, default="General Inquiry")
    message = models.TextField()
    admin_notes = models.TextField(blank=True, default="", help_text="Internal staff notes")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="OPEN")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Support Ticket"
        verbose_name_plural = "Support Tickets"

    def save(self, *args, **kwargs):
        if not self.ticket_id:
            short_id = uuid.uuid4().hex[:6].upper()
            self.ticket_id = f"WW-TCK-{short_id}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.ticket_id}] {self.subject} ({self.status})"
