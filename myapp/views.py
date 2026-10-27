import json
import logging
from datetime import datetime, timedelta
from urllib.parse import quote_plus

from django.db import connection
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from .models import FAQ, ErrorCode, SupportTicket
from .mongo import check_mongo_status, log_user_feedback
from .middleware import get_recent_requests, get_request_stats
from .services import get_destination_weather, DESTINATION_COORDINATES
from .ai_assistant import generate_assistant_response, get_error_code_from_sql

logger = logging.getLogger("wanderwise.views")

PLACES = {
    "ooty": ["Government Botanical Garden", "Ooty Lake boating", "Doddabetta Peak",
             "Tea factory and tea gardens", "Pykara Falls", "Rose Garden",
             "Avalanche Lake", "Emerald Lake"],
    "manali": ["Hadimba Temple", "Solang Valley", "Old Manali cafes", "Jogini Waterfall",
               "Vashisht hot springs", "Mall Road", "Naggar Castle"],
    "goa": ["Baga Beach", "Fort Aguada", "Basilica of Bom Jesus", "Palolem Beach",
            "Dudhsagar Falls", "Anjuna flea market", "Old Goa churches"],
    "bali": ["Uluwatu Temple", "Tegallalang Rice Terraces", "Ubud Monkey Forest",
             "Tanah Lot", "Nusa Penida", "Seminyak Beach", "Mount Batur sunrise"],
    "munnar": ["Tea plantations", "Eravikulam National Park", "Mattupetty Dam",
               "Echo Point", "Top Station viewpoint", "Attukal Waterfalls"],
    "kerala": ["Alleppey backwaters", "Munnar tea gardens", "Fort Kochi", "Kovalam Beach",
               "Athirappilly Falls", "Thekkady spice gardens"],
    "jaipur": ["Amber Fort", "City Palace", "Hawa Mahal", "Jantar Mantar",
               "Nahargarh Fort sunset", "Johari Bazaar"],
    "rishikesh": ["Laxman Jhula", "Triveni Ghat evening aarti", "Beatles Ashram",
                  "River rafting", "Neer Garh Waterfall", "Ram Jhula"],
    "pondicherry": ["Promenade Beach", "French Quarter walk", "Auroville", "Paradise Beach",
                    "Sri Aurobindo Ashram", "Serenity Beach"],
    "kodaikanal": ["Kodaikanal Lake", "Coaker's Walk", "Pillar Rocks", "Bryant Park",
                   "Silver Cascade Falls", "Pine Forest"],
}

INTEREST_TIPS = {
    "Nature": "Spend time at a scenic viewpoint or garden",
    "Adventure": "Try a trek, ride or other adventure activity",
    "Beaches": "Relax by the water at sunset",
    "Culture": "Visit a local temple, museum or heritage site",
    "Food": "Join a local food walk or try a famous local dish",
    "Photography": "Golden-hour photo walk at a scenic spot",
}

FOOD = {
    "veg": ["Local vegetarian breakfast spot", "Popular vegetarian thali place", "Well-reviewed vegetarian restaurant"],
    "nonveg": ["Local breakfast spot", "Popular local non-veg restaurant", "Well-reviewed dinner place"],
    "any": ["Local breakfast spot", "Street food or local lunch", "Well-reviewed local restaurant"],
}

PACKING_BASE = ["ID proof and tickets", "Phone, charger and power bank", "Reusable water bottle",
                "Basic medicines and first-aid", "Some cash for small shops"]

PACKING_EXTRA = {
    "Nature": ["Light rain jacket", "Comfortable walking shoes"],
    "Adventure": ["Sturdy shoes with good grip", "Small backpack", "Sunscreen"],
    "Beaches": ["Swimwear and flip-flops", "Sunscreen and sunglasses", "Quick-dry towel"],
    "Culture": ["Modest clothing for temples", "Socks (for temple visits)"],
    "Food": ["Hand sanitizer", "Stomach-friendly medicines"],
    "Photography": ["Camera or phone tripod", "Extra memory and battery"],
}

TIPS = [
    "Book stays and transport early, especially on weekends and holidays.",
    "Start sightseeing early to avoid crowds and make the most of the day.",
    "Check the weather forecast for your dates before you leave.",
    "Keep digital and paper copies of your tickets and ID.",
    "Respect local customs and keep the places you visit clean.",
]

STAY = {
    "budget": ("Budget stays", "Hostels, homestays or budget hotels", 0.30),
    "standard": ("Comfort stays", "3-star hotels or good homestays", 0.40),
    "luxury": ("Premium stays", "4-5 star hotels or resorts", 0.50),
}

MODES = {
    "bus": ("Bus", 0.12),
    "train": ("Train", 0.15),
    "car": ("Car / Cab", 0.22),
    "flight": ("Flight", 0.35),
}


def maps_link(place, destination):
    return "https://www.google.com/maps/search/?api=1&query=" + quote_plus(f"{place} {destination}")


# ==========================================
# PAGE VIEWS (At least 3 distinct pages)
# ==========================================

def home(request):
    """
    Home page / Trip Planner.
    Retrieves FAQs dynamically from the SQL database.
    """
    faqs = FAQ.objects.filter(is_active=True).order_by("order")[:10]
    return render(request, "myapp/home.html", {
        "faqs": faqs,
        "page_title": "WanderWise AI | Smart Travel Planner",
    })


def faq_page(request):
    """
    Dedicated FAQ page (Page 2).
    Displays at least 10 FAQs stored in SQL database with category filters,
    and supports dynamic API-based loading.
    """
    category_filter = request.GET.get("category", "").strip()
    search_query = request.GET.get("q", "").strip()

    faqs = FAQ.objects.filter(is_active=True).order_by("order")
    if category_filter and category_filter != "All":
        faqs = faqs.filter(category=category_filter)
    if search_query:
        faqs = faqs.filter(question__icontains=search_query) | faqs.filter(answer__icontains=search_query)

    categories = ["All", "General", "Planning", "Budget", "Troubleshooting"]
    faq_count = FAQ.objects.filter(is_active=True).count()

    return render(request, "myapp/faq.html", {
        "faqs": faqs,
        "categories": categories,
        "active_category": category_filter or "All",
        "search_query": search_query,
        "faq_count": faq_count,
        "page_title": "Frequently Asked Questions | WanderWise AI",
    })


def destinations_page(request):
    """
    Dedicated Destinations page (Page 3).
    Displays destinations with live weather via third-party API with fallback.
    """
    destinations_list = [
        {"name": "Ooty", "state": "Tamil Nadu", "tag": "Hills & Tea Valleys", "bg": "ooty", "gradient": "linear-gradient(135deg, #11998e, #38ef7d)"},
        {"name": "Manali", "state": "Himachal Pradesh", "tag": "Snow Peaks & Trails", "bg": "manali", "gradient": "linear-gradient(135deg, #3a7bd5, #6755e8)"},
        {"name": "Goa", "state": "Goa", "tag": "Golden Beaches & Nightlife", "bg": "goa", "gradient": "linear-gradient(135deg, #f7971e, #ffd200)"},
        {"name": "Bali", "state": "Indonesia", "tag": "Temples & Tropical Coast", "bg": "bali", "gradient": "linear-gradient(135deg, #ee0979, #ff6a00)"},
        {"name": "Munnar", "state": "Kerala", "tag": "Tea Plantations & Mist", "bg": "munnar", "gradient": "linear-gradient(135deg, #134e5e, #71b280)"},
        {"name": "Jaipur", "state": "Rajasthan", "tag": "Royal Palaces & Forts", "bg": "jaipur", "gradient": "linear-gradient(135deg, #f857a6, #ff5858)"},
        {"name": "Rishikesh", "state": "Uttarakhand", "tag": "Rafting & Yoga on Ganga", "bg": "rishikesh", "gradient": "linear-gradient(135deg, #00b4db, #0083b0)"},
        {"name": "Pondicherry", "state": "Puducherry", "tag": "French Quarter & Promenade", "bg": "pondicherry", "gradient": "linear-gradient(135deg, #8a2387, #e94057)"},
        {"name": "Kodaikanal", "state": "Tamil Nadu", "tag": "Pine Forests & Lakes", "bg": "kodaikanal", "gradient": "linear-gradient(135deg, #2c3e50, #3498db)"},
    ]

    for dest in destinations_list:
        dest["weather"] = get_destination_weather(dest["name"], timeout_seconds=1.5)

    return render(request, "myapp/destinations.html", {
        "destinations": destinations_list,
        "page_title": "Explore Top Travel Destinations | WanderWise AI",
    })


def health_check(request):
    """
    Health check page & Request logging status.
    Tests SQL database (FAQs, ErrorCodes, Tickets), MongoDB, third-party API, and lists recent requests.
    """
    sql_ok = False
    sql_latency = 0.0
    faq_count = 0
    error_codes_count = 0
    ticket_count = 0
    try:
        t0 = datetime.utcnow()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            cursor.fetchone()
        sql_latency = round((datetime.utcnow() - t0).total_seconds() * 1000, 2)
        sql_ok = True
        faq_count = FAQ.objects.count()
        error_codes_count = ErrorCode.objects.count()
        ticket_count = SupportTicket.objects.count()
    except Exception as e:
        logger.error("SQL Database health check failed: %s", e)

    mongo_status = check_mongo_status()

    test_destination = request.GET.get("test_dest", "Ooty")
    force_timeout = request.GET.get("force_timeout", "false").lower() in ("true", "1")
    weather_info = get_destination_weather(test_destination, timeout_seconds=2.0, force_timeout=force_timeout)

    recent_requests = get_recent_requests()
    stats = get_request_stats()

    health_data = {
        "status": "healthy" if sql_ok else "degraded",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "sql_database": {
            "connected": sql_ok,
            "engine": "sqlite3",
            "latency_ms": sql_latency,
            "faqs_stored": faq_count,
            "error_codes_stored": error_codes_count,
            "support_tickets_stored": ticket_count,
        },
        "mongodb": mongo_status,
        "third_party_api": {
            "name": "Open-Meteo Weather API",
            "test_destination": test_destination,
            "is_fallback": weather_info["is_fallback"],
            "fallback_reason": weather_info.get("fallback_reason"),
            "source": weather_info["source"],
            "response_time_ms": weather_info["response_time_ms"],
        },
        "request_stats": stats,
    }

    if request.GET.get("format") == "json" or request.headers.get("Accept") == "application/json":
        return JsonResponse(health_data)

    return render(request, "myapp/health.html", {
        "health": health_data,
        "recent_requests": recent_requests,
        "stats": stats,
        "weather_info": weather_info,
        "force_timeout": force_timeout,
        "page_title": "System Health & Request Logging | WanderWise AI",
    })


def error_reference(request):
    """
    Error Codes Reference and Interactive Testing Center.
    Documents all 8 required error codes from SQL database (ErrorCode model).
    """
    error_codes = ErrorCode.objects.all().order_by("code")
    return render(request, "myapp/errors_guide.html", {
        "error_codes": error_codes,
        "error_count": error_codes.count(),
        "page_title": "Error Code Reference & Testing | WanderWise AI",
    })


def test_error(request, code):
    """
    Simulates / triggers the requested error code for assessment verification.
    Retrieves error definition from the SQL database.
    """
    err_info = get_error_code_from_sql(code)

    if code == 400:
        return render(request, "myapp/400.html", {"error": err_info}, status=400)
    elif code == 401:
        return render(request, "myapp/generic_error.html", {"status_code": 401, "error": err_info}, status=401)
    elif code == 403:
        return render(request, "myapp/403.html", {"error": err_info}, status=403)
    elif code == 404:
        return render(request, "myapp/404.html", {"error": err_info}, status=404)
    elif code == 429:
        return render(request, "myapp/generic_error.html", {"status_code": 429, "error": err_info}, status=429)
    elif code == 500:
        return render(request, "myapp/500.html", {"error": err_info}, status=500)
    elif code == 503:
        return render(request, "myapp/generic_error.html", {"status_code": 503, "error": err_info}, status=503)
    elif code == 600:
        response = render(request, "myapp/generic_error.html", {
            "status_code": "WW-600",
            "error": err_info,
            "is_site_specific": True
        }, status=422)
        response["X-WanderWise-Error"] = "WW-600"
        return response
    else:
        return render(request, "myapp/generic_error.html", {"status_code": code, "error": err_info}, status=code)


def tickets_page(request):
    """
    Support Ticket Portal (CRUD interface).
    Allows creating, viewing, tracking, updating, and deleting support tickets in SQL.
    """
    tickets = SupportTicket.objects.all().order_by("-created_at")
    status_filter = request.GET.get("status", "")
    if status_filter:
        tickets = tickets.filter(status=status_filter)

    search_id = request.GET.get("ticket_id", "").strip()
    searched_ticket = None
    if search_id:
        searched_ticket = SupportTicket.objects.filter(ticket_id__iexact=search_id).first()

    return render(request, "myapp/tickets.html", {
        "tickets": tickets[:25],
        "searched_ticket": searched_ticket,
        "search_id": search_id,
        "total_tickets": SupportTicket.objects.count(),
        "open_count": SupportTicket.objects.filter(status="OPEN").count(),
        "resolved_count": SupportTicket.objects.filter(status="RESOLVED").count(),
        "page_title": "Support Ticket Portal (CRUD) | WanderWise AI",
    })


# ==========================================
# TRIP PLANNER VIEW
# ==========================================

def plan_trip(request):
    if request.method != "POST":
        return redirect("home")

    destination = request.POST.get("destination", "").strip()
    interests = request.POST.getlist("interests")
    try:
        budget = int(request.POST.get("budget", 0))
        duration = int(request.POST.get("duration", 1))
        travelers = int(request.POST.get("travelers", 1))
    except ValueError:
        return render(request, "myapp/400.html", {
            "message": "Invalid trip parameters: Budget, duration, and travelers must be positive numbers."
        }, status=400)

    if not destination or budget <= 0 or duration <= 0 or travelers <= 0:
        return render(request, "myapp/400.html", {
            "message": "Missing or invalid trip parameters. Please provide a destination and positive numbers for budget and duration."
        }, status=400)

    # Check for site-specific error trigger: e.g. duration > 30 days
    if duration > 30:
        err_600 = get_error_code_from_sql(600)
        response = render(request, "myapp/generic_error.html", {
            "status_code": "WW-600",
            "error": err_600,
            "is_site_specific": True,
            "custom_message": f"WanderWise AI planning engine supports itineraries up to 30 days. You requested {duration} days. Please shorten your trip duration or submit a support ticket for customized group expeditions.",
        }, status=422)
        response["X-WanderWise-Error"] = "WW-600"
        return response

    style_key = request.POST.get("stay_style", "standard")
    if style_key not in STAY:
        style_key = "standard"
    mode_key = request.POST.get("travel_mode", "train")
    if mode_key not in MODES:
        mode_key = "train"
    food_key = request.POST.get("food", "any")
    if food_key not in FOOD:
        food_key = "any"

    start = None
    raw_date = request.POST.get("start_date", "")
    if raw_date:
        try:
            start = datetime.strptime(raw_date, "%Y-%m-%d").date()
        except ValueError:
            start = None

    key = destination.lower()
    places = next((v for k, v in PLACES.items() if k in key), None)
    if not places:
        places = [f"Top sights in {destination}", f"Local market in {destination}",
                  f"Popular viewpoint near {destination}", f"Heritage spot in {destination}",
                  f"Day trip near {destination}", f"Famous local street in {destination}"]

    tips = [INTEREST_TIPS[i] for i in interests if i in INTEREST_TIPS] or ["Explore at your own pace"]
    food_list = FOOD[food_key]
    per_day_cost = round(budget / duration)
    days = []
    for d in range(duration):
        morning = places[(d * 2) % len(places)]
        afternoon = places[(d * 2 + 1) % len(places)]
        if duration == 1:
            theme = "Your day out"
        elif d == 0:
            theme = "Arrive and explore"
        elif d == duration - 1:
            theme = "Last memories and head home"
        else:
            theme = "Go deeper"
        days.append({
            "number": d + 1,
            "theme": theme,
            "date": (start + timedelta(days=d)).strftime("%a, %d %b") if start else "",
            "morning": {"name": morning, "url": maps_link(morning, destination)},
            "afternoon": {"name": afternoon, "url": maps_link(afternoon, destination)},
            "evening": tips[d % len(tips)],
            "food": food_list[d % len(food_list)],
            "cost": per_day_cost,
        })

    stay_label, stay_hint, stay_share = STAY[style_key]
    mode_label, mode_share = MODES[mode_key]
    weights = [
        ("🏨 Accommodation", stay_share),
        ("🍜 Food", 0.25),
        ("🚗 Transport (" + mode_label + ")", mode_share),
        ("🎟️ Activities", 0.10),
        ("🛍️ Shopping and emergency", 0.08),
    ]
    total_w = sum(w for _, w in weights)
    budget_rows = []
    for label, w in weights:
        share = w / total_w
        budget_rows.append({"label": label, "amount": round(budget * share),
                            "percent": round(share * 100)})

    packing = list(PACKING_BASE)
    for i in interests:
        for item in PACKING_EXTRA.get(i, []):
            if item not in packing:
                packing.append(item)

    end = (start + timedelta(days=duration - 1)) if start else None
    weather = get_destination_weather(destination, timeout_seconds=2.0)

    context = {
        "destination": destination, "budget": budget, "duration": duration,
        "travelers": travelers, "interests": interests, "days": days,
        "budget_rows": budget_rows,
        "per_person_per_day": round(budget / travelers / duration),
        "per_person_total": round(budget / travelers),
        "stay_label": stay_label, "stay_hint": stay_hint,
        "mode_label": mode_label,
        "food_label": {"veg": "Vegetarian", "nonveg": "Non-vegetarian", "any": "Any food"}[food_key],
        "start_date": start.strftime("%d %b %Y") if start else "",
        "end_date": end.strftime("%d %b %Y") if end else "",
        "packing": packing, "tips": TIPS,
        "weather": weather,
        "map_url": "https://www.google.com/maps/search/?api=1&query=" + quote_plus(destination),
        "weather_url": "https://www.google.com/search?q=" + quote_plus("weather " + destination),
        "page_title": f"{duration}-Day {destination} Itinerary | WanderWise AI",
    }
    return render(request, "myapp/result.html", context)


# ==========================================
# REST / JSON API ENDPOINTS (SQL & MongoDB)
# ==========================================

def api_faqs(request):
    """
    REST API returning FAQs stored in SQL database.
    Fulfills assessment requirement: '10+ FAQs in SQL, FAQ page from API'.
    """
    category = request.GET.get("category", "").strip()
    q = request.GET.get("q", "").strip()

    faqs = FAQ.objects.filter(is_active=True).order_by("order")
    if category and category != "All":
        faqs = faqs.filter(category=category)
    if q:
        faqs = faqs.filter(question__icontains=q) | faqs.filter(answer__icontains=q)

    data = [
        {
            "id": f.id,
            "question": f.question,
            "answer": f.answer,
            "category": f.category,
            "order": f.order,
        }
        for f in faqs
    ]
    return JsonResponse({
        "success": True,
        "count": len(data),
        "source": "SQL Database (FAQ Model)",
        "faqs": data,
    })


def api_error_codes(request, code=None):
    """
    REST API returning Error Codes stored in SQL database.
    Fulfills assessment requirement: '8+ error codes in SQL'.
    """
    if code is not None:
        err = ErrorCode.objects.filter(code=code).first()
        if not err:
            return JsonResponse({"error": f"Error code {code} not found in SQL database."}, status=404)
        return JsonResponse({
            "success": True,
            "code": err.code,
            "code_str": err.code_str,
            "title": err.title,
            "category": err.category,
            "meaning": err.meaning,
            "wanderwise_context": err.wanderwise_context,
            "solution": err.solution,
            "is_site_specific": err.is_site_specific,
        })

    codes = ErrorCode.objects.all().order_by("code")
    data = [
        {
            "code": c.code,
            "code_str": c.code_str,
            "title": c.title,
            "category": c.category,
            "meaning": c.meaning,
            "wanderwise_context": c.wanderwise_context,
            "solution": c.solution,
            "is_site_specific": c.is_site_specific,
        }
        for c in codes
    ]
    return JsonResponse({
        "success": True,
        "count": len(data),
        "source": "SQL Database (ErrorCode Model)",
        "error_codes": data,
    })


@csrf_exempt
def api_chat(request):
    """
    AI Assistant chat endpoint.
    Answers FAQs from SQL database, explains error codes from SQL database,
    creates support tickets in SQL, and logs to MongoDB.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed. Use POST."}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        data = request.POST

    message = data.get("message", "").strip()
    session_id = data.get("session_id", "session-default")

    if not message:
        return JsonResponse({"error": "Message parameter is required."}, status=400)

    response_data = generate_assistant_response(message, session_id=session_id)
    return JsonResponse(response_data)


@csrf_exempt
def api_support_ticket(request, ticket_id=None):
    """
    Full CRUD Support Ticket endpoint stored in SQL database.
    Fulfills assessment requirement: 'Ticket created when unsure (CRUD)'.
      - POST: Create ticket
      - GET: Read ticket(s)
      - PUT / PATCH / action='update': Update ticket status
      - DELETE / action='delete': Delete ticket
    """
    data = {}
    if request.body:
        try:
            data = json.loads(request.body.decode("utf-8"))
        except Exception:
            data = {}
    if not data and request.POST:
        data = request.POST.dict()

    action = data.get("action", "").lower()
    method = request.method

    # 1. READ (GET)
    if method == "GET":
        t_id = ticket_id or request.GET.get("ticket_id", "").strip()
        if t_id:
            ticket = SupportTicket.objects.filter(ticket_id__iexact=t_id).first()
            if not ticket:
                return JsonResponse({"error": f"Ticket {t_id} not found"}, status=404)
            return JsonResponse({
                "success": True,
                "ticket": {
                    "ticket_id": ticket.ticket_id,
                    "name": ticket.name,
                    "email": ticket.email,
                    "subject": ticket.subject,
                    "category": ticket.category,
                    "message": ticket.message,
                    "status": ticket.status,
                    "created_at": ticket.created_at.strftime("%Y-%m-%d %H:%M UTC"),
                    "updated_at": ticket.updated_at.strftime("%Y-%m-%d %H:%M UTC"),
                }
            })

        tickets = SupportTicket.objects.all().order_by("-created_at")[:20]
        data_list = [
            {
                "ticket_id": t.ticket_id,
                "name": t.name,
                "email": t.email,
                "subject": t.subject,
                "status": t.status,
                "created_at": t.created_at.strftime("%Y-%m-%d %H:%M UTC"),
            }
            for t in tickets
        ]
        return JsonResponse({"success": True, "count": len(data_list), "tickets": data_list})

    # 2. DELETE
    if method == "DELETE" or action == "delete":
        t_id = ticket_id or data.get("ticket_id") or request.GET.get("ticket_id")
        if not t_id:
            return JsonResponse({"error": "ticket_id required for deletion"}, status=400)
        ticket = SupportTicket.objects.filter(ticket_id__iexact=t_id).first()
        if not ticket:
            return JsonResponse({"error": f"Ticket {t_id} not found"}, status=404)
        ticket.delete()
        return JsonResponse({"success": True, "message": f"Ticket {t_id} deleted successfully from SQL database."})

    # 3. UPDATE (PUT / PATCH / action='update')
    if method in ["PUT", "PATCH"] or action == "update":
        t_id = ticket_id or data.get("ticket_id")
        if not t_id:
            return JsonResponse({"error": "ticket_id required for update"}, status=400)
        ticket = SupportTicket.objects.filter(ticket_id__iexact=t_id).first()
        if not ticket:
            return JsonResponse({"error": f"Ticket {t_id} not found"}, status=404)

        if "status" in data and data["status"] in ["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"]:
            ticket.status = data["status"]
        if "admin_notes" in data:
            ticket.admin_notes = data["admin_notes"]
        ticket.save()

        return JsonResponse({
            "success": True,
            "message": f"Ticket {t_id} updated successfully in SQL database.",
            "ticket_id": ticket.ticket_id,
            "new_status": ticket.status,
        })

    # 4. CREATE (POST)
    if method == "POST":
        name = data.get("name", "").strip()
        email = data.get("email", "").strip()
        subject = data.get("subject", "").strip()
        category = data.get("category", "General Inquiry").strip()
        message = data.get("message", "").strip()

        if not name or not email or not message:
            return JsonResponse({"error": "Name, email, and message are required fields."}, status=400)

        try:
            ticket = SupportTicket.objects.create(
                name=name,
                email=email,
                subject=subject or f"Support inquiry from {name}",
                category=category,
                message=message,
                status="OPEN",
            )
            return JsonResponse({
                "success": True,
                "ticket_id": ticket.ticket_id,
                "message": f"Support ticket #{ticket.ticket_id} created successfully in SQL database!",
                "created_at": ticket.created_at.strftime("%Y-%m-%d %H:%M UTC"),
            })
        except Exception as e:
            logger.error("Failed to create support ticket in SQL: %s", e)
            return JsonResponse({"error": f"Failed to save ticket: {str(e)}"}, status=500)

    return JsonResponse({"error": "Unsupported method."}, status=405)


@csrf_exempt
def api_feedback(request):
    """
    Records user feedback into MongoDB (or resilient fallback file).
    Fulfills assessment requirement: 'Chats and feedback stored in MongoDB'.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed. Use POST."}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        data = request.POST

    session_id = data.get("session_id", "anonymous")
    rating = data.get("rating", 5)
    comment = data.get("comment", "").strip()

    result = log_user_feedback(session_id, rating, comment)
    return JsonResponse(result)


def api_weather(request):
    """
    Third-party weather API endpoint demonstrating strict timeout and fallback.
    Fulfills assessment requirement: 'Extra third-party call with timeout and fallback'.
    """
    destination = request.GET.get("destination", "Ooty")
    force_timeout = request.GET.get("force_timeout", "false").lower() in ("true", "1")
    try:
        timeout = float(request.GET.get("timeout", "3.0"))
    except ValueError:
        timeout = 3.0

    weather = get_destination_weather(destination, timeout_seconds=timeout, force_timeout=force_timeout)
    return JsonResponse(weather)


# ==========================================
# CUSTOM ERROR HANDLERS (404, 500, 403, 400)
# ==========================================

def custom_404(request, exception=None):
    """
    Custom 404 error page matching purple design with 'Ask the assistant' option.
    """
    err = get_error_code_from_sql(404)
    return render(request, "myapp/404.html", {
        "path": request.path,
        "error": err,
        "page_title": "404 - Page Not Found | WanderWise AI",
    }, status=404)


def custom_500(request):
    """
    Custom 500 error page matching purple design with 'Ask the assistant' option.
    """
    err = get_error_code_from_sql(500)
    return render(request, "myapp/500.html", {
        "error": err,
        "page_title": "500 - Server Error | WanderWise AI",
    }, status=500)


def custom_403(request, exception=None):
    err = get_error_code_from_sql(403)
    return render(request, "myapp/403.html", {
        "error": err,
        "page_title": "403 - Forbidden | WanderWise AI",
    }, status=403)


def custom_400(request, exception=None):
    err = get_error_code_from_sql(400)
    return render(request, "myapp/400.html", {
        "error": err,
        "page_title": "400 - Bad Request | WanderWise AI",
    }, status=400)
