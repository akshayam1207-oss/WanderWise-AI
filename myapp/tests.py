import json
from django.test import TestCase, Client
from myapp.models import FAQ, ErrorCode, SupportTicket
from myapp.services import get_destination_weather
from myapp.management.commands.seed_faqs import seed_database_faqs, seed_database_error_codes


class WanderWiseAssessmentTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Seed full set of 12 real FAQs and 8 Error Codes into test database
        seed_database_faqs()
        seed_database_error_codes()

    def test_pages_render_successfully(self):
        """Verifies at least 3 distinct pages render with status 200 and include chat widget."""
        routes = ["/", "/faq/", "/destinations/", "/health/", "/errors/", "/tickets/"]
        for route in routes:
            response = self.client.get(route)
            self.assertEqual(response.status_code, 200, f"Route {route} failed")
            # Verify chat widget is present on every page
            self.assertContains(response, "ww-chat-widget")
            self.assertContains(response, "Ask WanderWise AI")

    def test_faq_sql_storage_and_api(self):
        """Verifies at least 10 FAQs are stored in SQL database and accessible via API."""
        count = FAQ.objects.filter(is_active=True).count()
        self.assertGreaterEqual(count, 10, "Assessment requires at least 10 FAQs in SQL database")

        # HTML page render
        response = self.client.get("/faq/")
        self.assertEqual(response.status_code, 200)
        first_faq = FAQ.objects.filter(is_active=True).first()
        self.assertContains(response, first_faq.question)

        # REST API endpoint (/api/faqs/)
        api_res = self.client.get("/api/faqs/")
        self.assertEqual(api_res.status_code, 200)
        api_data = api_res.json()
        self.assertTrue(api_data.get("success"))
        self.assertGreaterEqual(api_data.get("count", 0), 10)

    def test_eight_error_codes_in_sql_and_api(self):
        """Verifies 8+ error codes stored in SQL database, accessible via API, and simulated."""
        count = ErrorCode.objects.count()
        self.assertGreaterEqual(count, 8, "Assessment requires 8+ error codes in SQL database")

        # REST API endpoint (/api/error-codes/)
        api_res = self.client.get("/api/error-codes/")
        self.assertEqual(api_res.status_code, 200)
        self.assertGreaterEqual(api_res.json().get("count", 0), 8)

        # Simulation for all 8 error codes
        required_codes = [400, 401, 403, 404, 429, 500, 503, 600]
        for code in required_codes:
            response = self.client.get(f"/test-error/{code}/")
            expected_status = 422 if code == 600 else code
            self.assertEqual(response.status_code, expected_status, f"Error simulation for {code} failed")
            self.assertContains(response, "Ask the Assistant", status_code=expected_status)

    def test_invalid_url_displays_custom_404(self):
        """Verifies testing an invalid URL displays custom 404 page with Ask the Assistant."""
        response = self.client.get("/this-page-does-not-exist/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "404", status_code=404)
        self.assertContains(response, "Lost in Translation", status_code=404)
        self.assertContains(response, "Ask the Assistant", status_code=404)

    def test_support_ticket_crud_in_sql(self):
        """Verifies full CRUD operations on support tickets stored in SQL."""
        # 1. CREATE
        payload = {
            "name": "Jane Traveler",
            "email": "jane@example.com",
            "category": "Trip Planning Issue",
            "subject": "Question regarding Ooty budget",
            "message": "Can I adjust the accommodation split for family homestays?"
        }
        create_res = self.client.post(
            "/api/support-ticket/",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(create_res.status_code, 200)
        data = create_res.json()
        ticket_id = data.get("ticket_id")
        self.assertTrue(ticket_id.startswith("WW-TCK-"))

        # 2. READ (GET)
        read_res = self.client.get(f"/api/support-ticket/?ticket_id={ticket_id}")
        self.assertEqual(read_res.status_code, 200)
        ticket_data = read_res.json().get("ticket")
        self.assertEqual(ticket_data["name"], "Jane Traveler")
        self.assertEqual(ticket_data["status"], "OPEN")

        # 3. UPDATE (PUT/PATCH)
        update_res = self.client.post(
            "/api/support-ticket/",
            data=json.dumps({"action": "update", "ticket_id": ticket_id, "status": "RESOLVED"}),
            content_type="application/json"
        )
        self.assertEqual(update_res.status_code, 200)
        updated_ticket = SupportTicket.objects.get(ticket_id=ticket_id)
        self.assertEqual(updated_ticket.status, "RESOLVED")

        # 4. DELETE
        del_res = self.client.post(
            "/api/support-ticket/",
            data=json.dumps({"action": "delete", "ticket_id": ticket_id}),
            content_type="application/json"
        )
        self.assertEqual(del_res.status_code, 200)
        self.assertFalse(SupportTicket.objects.filter(ticket_id=ticket_id).exists())

    def test_ai_assistant_faq_answering(self):
        """Verifies AI assistant answers queries grounded in SQL FAQs."""
        response = self.client.post(
            "/api/chat/",
            data=json.dumps({"message": "Is WanderWise free to use?"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("free", data.get("reply", "").lower())

    def test_ai_assistant_error_code_explanation(self):
        """Verifies AI assistant explains the required error codes from SQL."""
        # 404 test
        response_404 = self.client.post(
            "/api/chat/",
            data=json.dumps({"message": "What does error code 404 mean?"}),
            content_type="application/json"
        )
        self.assertEqual(response_404.status_code, 200)
        self.assertIn("404", response_404.json().get("reply", ""))

        # Site-specific WW-600 test
        response_600 = self.client.post(
            "/api/chat/",
            data=json.dumps({"message": "Explain error WW-600"}),
            content_type="application/json"
        )
        self.assertEqual(response_600.status_code, 200)
        self.assertIn("WW-600", response_600.json().get("reply", ""))

    def test_third_party_api_timeout_and_fallback(self):
        """Verifies third-party API timeout and fallback mechanism."""
        fallback_data = get_destination_weather("Ooty", timeout_seconds=1.0, force_timeout=True)
        self.assertTrue(fallback_data["is_fallback"])
        self.assertIn("WanderWise Fallback", fallback_data["source"])
        self.assertIsNotNone(fallback_data["temperature"])

        response = self.client.get("/api/weather/?destination=Ooty&force_timeout=true")
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertTrue(json_data["is_fallback"])

    def test_feedback_api(self):
        """Verifies feedback logging."""
        response = self.client.post(
            "/api/feedback/",
            data=json.dumps({"session_id": "test-session", "rating": 5, "comment": "Great answer!"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))

    def test_health_check_endpoint(self):
        """Verifies health check page and JSON API."""
        response = self.client.get("/health/?format=json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertTrue(data["sql_database"]["connected"])
        self.assertEqual(data["sql_database"]["error_codes_stored"], 8)
        self.assertIn("request_stats", data)
