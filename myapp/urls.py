from django.urls import path
from . import views

urlpatterns = [
    # Pages (At least 3 distinct pages)
    path("", views.home, name="home"),
    path("faq/", views.faq_page, name="faq"),
    path("destinations/", views.destinations_page, name="destinations"),
    path("plan-trip/", views.plan_trip, name="plan_trip"),
    path("health/", views.health_check, name="health"),
    path("errors/", views.error_reference, name="errors"),
    path("tickets/", views.tickets_page, name="tickets"),
    path("test-error/<int:code>/", views.test_error, name="test_error"),

    # REST APIs (SQL Data, AI Assistant, MongoDB)
    path("api/faqs/", views.api_faqs, name="api_faqs"),
    path("api/error-codes/", views.api_error_codes, name="api_error_codes"),
    path("api/error-codes/<int:code>/", views.api_error_codes, name="api_error_code_detail"),
    path("api/chat/", views.api_chat, name="api_chat"),
    path("api/support-ticket/", views.api_support_ticket, name="api_support_ticket"),
    path("api/support-ticket/<str:ticket_id>/", views.api_support_ticket, name="api_support_ticket_detail"),
    path("api/feedback/", views.api_feedback, name="api_feedback"),
    path("api/weather/", views.api_weather, name="api_weather"),
    path("api/health/", views.health_check, name="api_health"),
]
