from django.core.management.base import BaseCommand
from myapp.models import FAQ, ErrorCode

INITIAL_FAQS = [
    {
        "question": "Is WanderWise AI free to use?",
        "answer": "Yes, WanderWise AI is completely free to use. You can generate custom daily itineraries, budget estimates, packing lists, and map routes with no sign-up or credit card required.",
        "category": "General",
        "order": 1,
    },
    {
        "question": "Are the budget numbers exact?",
        "answer": "The budget figures provided by WanderWise are smart estimates calculated according to your travel style (Budget, Comfort, Luxury) and travel mode (Flight, Train, Bus, Car). Always check current rates for hotels and transport before booking.",
        "category": "Budget",
        "order": 2,
    },
    {
        "question": "Can I plan a trip to any destination?",
        "answer": "Yes! WanderWise AI supports any town, city, or country worldwide. Popular destinations like Ooty, Manali, Goa, Bali, Munnar, Jaipur, and Rishikesh have curated attractions, while other global destinations receive intelligent algorithmic recommendations.",
        "category": "Planning",
        "order": 3,
    },
    {
        "question": "Can I save my itinerary?",
        "answer": "Absolutely. On your itinerary results page, click 'Print / Save as PDF' to download a clean offline copy, or click 'Copy itinerary' to copy the day-by-day plan directly to your clipboard to share with friends.",
        "category": "Planning",
        "order": 4,
    },
    {
        "question": "How do I create a trip plan?",
        "answer": "Go to the 'Plan a Trip' section on the homepage, enter where you want to go, your total budget in rupees, duration in days, number of travelers, preferred travel style, transport mode, food preference, and interests, then click 'Plan My Journey'.",
        "category": "Planning",
        "order": 5,
    },
    {
        "question": "Can I change my travel dates?",
        "answer": "Yes. When filling out the planner form, select your desired Start Date. Your day-by-day schedule will automatically show the correct calendar dates and days of the week.",
        "category": "Planning",
        "order": 6,
    },
    {
        "question": "Can I select my preferred food?",
        "answer": "Yes, you can customize your meal preference by selecting Vegetarian, Non-vegetarian, or 'Any food'. Your itinerary will suggest breakfast, lunch, and dinner options matching your dietary preference.",
        "category": "Planning",
        "order": 7,
    },
    {
        "question": "Can I choose my travel budget?",
        "answer": "Yes, you can specify your total budget in rupees. WanderWise divides this proportionally across Accommodation, Food, Transportation, Activities, and Emergency/Shopping.",
        "category": "Budget",
        "order": 8,
    },
    {
        "question": "How do I view directions to attractions?",
        "answer": "Every attraction listed in your daily morning and afternoon itinerary includes a direct Google Maps link. Clicking it opens turn-by-turn directions and photos on Google Maps.",
        "category": "Planning",
        "order": 9,
    },
    {
        "question": "What should I do if trip planning fails?",
        "answer": "If trip planning fails or an error occurs, ensure that you entered a valid destination name, a positive budget, and at least 1 travel day. You can also click the 'Ask WanderWise AI' chat widget at the bottom-right or submit a support ticket for immediate help.",
        "category": "Troubleshooting",
        "order": 10,
    },
    {
        "question": "What do error codes like 404, 500, or WW-600 mean?",
        "answer": "HTTP 404 means the requested page or itinerary URL was not found. Error 500 indicates an unexpected server issue. WW-600 is our site-specific code for itinerary generation timeouts. You can ask our AI chat widget about any error code (400, 401, 403, 404, 429, 500, 503, WW-600) for instant troubleshooting.",
        "category": "Troubleshooting",
        "order": 11,
    },
    {
        "question": "How can I contact support or report an issue?",
        "answer": "You can open the AI chat widget on any page and type 'contact support' or click 'Create Support Ticket'. Enter your name, email, and issue details, and our team will get back to you promptly.",
        "category": "General",
        "order": 12,
    },
]

INITIAL_ERROR_CODES = [
    {
        "code": 400,
        "code_str": "400",
        "title": "Bad Request",
        "category": "Client Error",
        "meaning": "The server could not understand the request due to malformed syntax, invalid parameters, or missing required fields.",
        "wanderwise_context": "On WanderWise, this commonly occurs if the trip planning form was submitted with negative numbers for budget/duration or missing destination information.",
        "solution": "1. Review your trip planner form inputs.\n2. Ensure budget is greater than ₹0 and duration is at least 1 day.\n3. Verify your destination name and try submitting again.",
        "is_site_specific": False,
    },
    {
        "code": 401,
        "code_str": "401",
        "title": "Unauthorized",
        "category": "Authentication Error",
        "meaning": "The requested resource requires valid user authentication or authentication has failed.",
        "wanderwise_context": "Occurs when attempting to view private saved itineraries, profile settings, or the admin portal without logging in.",
        "solution": "1. Log into your WanderWise account or admin portal.\n2. Verify your session cookie is active.\n3. If your session expired, re-authenticate to continue.",
        "is_site_specific": False,
    },
    {
        "code": 403,
        "code_str": "403",
        "title": "Forbidden",
        "category": "Authorization Error",
        "meaning": "The server understood the request, but refuses to authorize access. Unlike 401, re-authenticating will not grant access.",
        "wanderwise_context": "Occurs when attempting to access restricted administrative endpoints, staff-only tools, or modify another traveler's itinerary.",
        "solution": "1. Check if you have proper permission levels.\n2. Return to the main WanderWise public pages.\n3. Contact support if you need elevated access.",
        "is_site_specific": False,
    },
    {
        "code": 404,
        "code_str": "404",
        "title": "Page Not Found",
        "category": "Client Error",
        "meaning": "The server cannot find the requested URL. The link may be broken, mistyped, or removed.",
        "wanderwise_context": "Occurs if an itinerary link has expired, or an invalid address such as /this-page-does-not-exist/ was opened.",
        "solution": "1. Check the URL for typographical errors.\n2. Return to the WanderWise Home page at '/'.\n3. Use the Trip Planner to generate a new itinerary.",
        "is_site_specific": False,
    },
    {
        "code": 429,
        "code_str": "429",
        "title": "Too Many Requests",
        "category": "Rate Limiting",
        "meaning": "The client has sent too many requests in a given amount of time (rate limit exceeded).",
        "wanderwise_context": "Protects WanderWise's AI trip generator and third-party APIs from automated bot traffic or rapid form spamming.",
        "solution": "1. Pause for 30–60 seconds before submitting another request.\n2. Avoid rapid repetitive clicks on the 'Plan My Journey' button.\n3. Try your search again after a brief pause.",
        "is_site_specific": False,
    },
    {
        "code": 500,
        "code_str": "500",
        "title": "Internal Server Error",
        "category": "Server Error",
        "meaning": "The server encountered an unexpected condition that prevented it from fulfilling the request.",
        "wanderwise_context": "Occurs if an unhandled backend exception happens during itinerary assembly, database queries, or template rendering.",
        "solution": "1. Refresh the page after a few moments.\n2. Check the WanderWise Health Check page at '/health/' to verify system status.\n3. If the problem persists, click 'Create Support Ticket' below so our team can resolve it.",
        "is_site_specific": False,
    },
    {
        "code": 503,
        "code_str": "503",
        "title": "Service Unavailable",
        "category": "Server Capacity / Maintenance",
        "meaning": "The server is currently unable to handle the request due to temporary overloading or maintenance.",
        "wanderwise_context": "Occurs if upstream generative AI services or meteorological APIs are momentarily experiencing outages or peak loads.",
        "solution": "1. Wait 1–2 minutes and retry your request.\n2. Check our Health Check dashboard for live external API availability.\n3. WanderWise will automatically activate fallback responses where available.",
        "is_site_specific": False,
    },
    {
        "code": 600,
        "code_str": "WW-600",
        "title": "Plan Quota Exceeded / AI Engine Timeout",
        "category": "Site-Specific Error",
        "meaning": "WanderWise site-specific application code indicating an itinerary duration limit exceeded (> 30 days) or multi-destination computational overload.",
        "wanderwise_context": "Triggers when a customized itinerary exceeds algorithmic bounds or when multi-city constraints overwhelm real-time route optimization.",
        "solution": "1. Shorten the requested trip duration (3–7 days recommended for optimal planning).\n2. Select fewer simultaneous interest categories.\n3. Click 'Create Support Ticket' to have our travel team prepare a custom group expedition plan.",
        "is_site_specific": True,
    },
]


def seed_database_faqs():
    """Seeds the initial 12 FAQs into SQL database if they don't already exist."""
    count = 0
    for item in INITIAL_FAQS:
        obj, created = FAQ.objects.get_or_create(
            question=item["question"],
            defaults={
                "answer": item["answer"],
                "category": item["category"],
                "order": item["order"],
                "is_active": True,
            }
        )
        if created:
            count += 1
    return count


def seed_database_error_codes():
    """Seeds the 8 required Error Codes into SQL database."""
    count = 0
    for item in INITIAL_ERROR_CODES:
        obj, created = ErrorCode.objects.get_or_create(
            code=item["code"],
            defaults={
                "code_str": item["code_str"],
                "title": item["title"],
                "category": item["category"],
                "meaning": item["meaning"],
                "wanderwise_context": item["wanderwise_context"],
                "solution": item["solution"],
                "is_site_specific": item["is_site_specific"],
            }
        )
        if created:
            count += 1
    return count


class Command(BaseCommand):
    help = "Seeds initial 12 FAQs and 8 Error Codes into SQL database"

    def handle(self, *args, **options):
        f_count = seed_database_faqs()
        e_count = seed_database_error_codes()
        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {f_count} FAQs and {e_count} Error Codes into SQL database."))
