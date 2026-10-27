from datetime import datetime, timedelta
from urllib.parse import quote_plus

from django.shortcuts import render, redirect

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


def home(request):
    return render(request, "myapp/home.html")


def maps_link(place, destination):
    return "https://www.google.com/maps/search/?api=1&query=" + quote_plus(f"{place} {destination}")


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
        return redirect("home")
    if not destination or budget <= 0 or duration <= 0 or travelers <= 0:
        return redirect("home")

    style_key = request.POST.get("stay_style", "standard")
    if style_key not in STAY:
        style_key = "standard"
    mode_key = request.POST.get("travel_mode", "train")
    if mode_key not in MODES:
        mode_key = "train"
    food_key = request.POST.get("food", "any")
    if food_key not in FOOD:
        food_key = "any"

    # Optional start date
    start = None
    raw_date = request.POST.get("start_date", "")
    if raw_date:
        try:
            start = datetime.strptime(raw_date, "%Y-%m-%d").date()
        except ValueError:
            start = None

    # Pick the attraction list
    key = destination.lower()
    places = next((v for k, v in PLACES.items() if k in key), None)
    if not places:
        places = [f"Top sights in {destination}", f"Local market in {destination}",
                  f"Popular viewpoint near {destination}", f"Heritage spot in {destination}",
                  f"Day trip near {destination}", f"Famous local street in {destination}"]

    # Day-by-day plan
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

    # Budget split
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

    # Packing list
    packing = list(PACKING_BASE)
    for i in interests:
        for item in PACKING_EXTRA.get(i, []):
            if item not in packing:
                packing.append(item)

    end = (start + timedelta(days=duration - 1)) if start else None

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
        "map_url": "https://www.google.com/maps/search/?api=1&query=" + quote_plus(destination),
        "weather_url": "https://www.google.com/search?q=" + quote_plus("weather " + destination),
    }
    return render(request, "myapp/result.html", context)