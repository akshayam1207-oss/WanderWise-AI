from django.core.management.base import BaseCommand
from myapp.models import FAQ

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


class Command(BaseCommand):
    help = "Seeds initial 12 FAQs into SQL database"

    def handle(self, *args, **options):
        count = seed_database_faqs()
        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {count} FAQs into SQL database."))
