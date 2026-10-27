import os
import re
import logging
from django.conf import settings
from .models import FAQ, SupportTicket
from .mongo import log_chat_interaction

logger = logging.getLogger("wanderwise.ai")

# Detailed explanations for the 8 required error codes
ERROR_CODE_KNOWLEDGE = {
    "400": {
        "title": "400 Bad Request",
        "category": "Client Error",
        "meaning": "The server could not understand the request due to malformed syntax, invalid parameters, or missing required fields.",
        "wanderwise_context": "On WanderWise, this commonly occurs if the trip planning form was submitted with negative numbers for budget/duration or missing destination information.",
        "solution": "1. Review your trip planner form inputs.\n2. Ensure budget is greater than ₹0 and duration is at least 1 day.\n3. Verify your destination name and try submitting again."
    },
    "401": {
        "title": "401 Unauthorized",
        "category": "Authentication Error",
        "meaning": "The requested resource requires valid user authentication or authentication has failed.",
        "wanderwise_context": "Occurs when attempting to view private saved itineraries, profile settings, or the admin portal without logging in.",
        "solution": "1. Log into your WanderWise account or admin portal.\n2. Verify your session cookie is active.\n3. If your session expired, re-authenticate to continue."
    },
    "403": {
        "title": "403 Forbidden",
        "category": "Authorization Error",
        "meaning": "The server understood the request, but refuses to authorize access. Unlike 401, re-authenticating will not make a difference.",
        "wanderwise_context": "Occurs when attempting to access restricted administrative endpoints, staff-only tools, or modify another traveler's itinerary.",
        "solution": "1. Check if you have proper permission levels.\n2. Return to the main WanderWise public pages.\n3. Contact support if you need elevated access."
    },
    "404": {
        "title": "404 Page Not Found",
        "category": "Client Error",
        "meaning": "The server cannot find the requested URL. The link may be broken, mistyped, or removed.",
        "wanderwise_context": "Occurs if an itinerary link has expired, or an invalid address such as /this-page-does-not-exist/ was opened.",
        "solution": "1. Check the URL for typographical errors.\n2. Return to the WanderWise Home page at '/'.\n3. Use the Trip Planner to generate a new itinerary."
    },
    "429": {
        "title": "429 Too Many Requests",
        "category": "Rate Limiting",
        "meaning": "The client has sent too many requests in a given amount of time (rate limit exceeded).",
        "wanderwise_context": "Protects WanderWise's AI trip generator and third-party APIs from automated bot traffic or rapid form spamming.",
        "solution": "1. Pause for 30–60 seconds before submitting another request.\n2. Avoid rapid repetitive clicks on the 'Plan My Journey' button.\n3. Try your search again after a brief pause."
    },
    "500": {
        "title": "500 Internal Server Error",
        "category": "Server Error",
        "meaning": "The server encountered an unexpected condition that prevented it from fulfilling the request.",
        "wanderwise_context": "Occurs if an unhandled backend exception happens during itinerary assembly, database queries, or template rendering.",
        "solution": "1. Refresh the page after a few moments.\n2. Check the WanderWise Health Check page at '/health/' to verify system status.\n3. If the problem persists, click 'Create Support Ticket' below so our team can resolve it."
    },
    "503": {
        "title": "503 Service Unavailable",
        "category": "Server Capacity / Maintenance",
        "meaning": "The server is currently unable to handle the request due to temporary overloading or maintenance.",
        "wanderwise_context": "Occurs if upstream generative AI services or meteorological APIs are momentarily experiencing outages or peak loads.",
        "solution": "1. Wait 1–2 minutes and retry your request.\n2. Check our Health Check dashboard for live external API availability.\n3. WanderWise will automatically activate fallback responses where available."
    },
    "600": {
        "title": "WW-600 Custom Code (AI Plan Generation Quota / Engine Timeout)",
        "category": "Site-Specific Error",
        "meaning": "WanderWise site-specific application code indicating an itinerary generation timeout or multi-destination complexity overload.",
        "wanderwise_context": "Triggers when a customized itinerary involves complex custom constraints or excessive dates that exceed real-time computation limits.",
        "solution": "1. Shorten the requested trip duration (e.g. 3–7 days for optimal planning).\n2. Select fewer simultaneous interest categories.\n3. Use our 'Create Support Ticket' feature to request a custom human-curated travel plan."
    },
}

# Also support alias WW-001 or WW-600
ERROR_CODE_KNOWLEDGE["ww-600"] = ERROR_CODE_KNOWLEDGE["600"]
ERROR_CODE_KNOWLEDGE["ww-001"] = ERROR_CODE_KNOWLEDGE["600"]


def search_faqs_in_sql(query_text):
    """
    Searches FAQs stored in SQL database for matches against user query.
    """
    words = [w.lower().strip() for w in re.split(r'\W+', query_text) if len(w) > 2]
    if not words:
        return []

    faqs = list(FAQ.objects.filter(is_active=True))
    scored_faqs = []

    for faq in faqs:
        q_lower = faq.question.lower()
        a_lower = faq.answer.lower()
        score = 0

        # Exact phrase or strong word match
        if query_text.lower() in q_lower:
            score += 10

        for word in words:
            if word in q_lower:
                score += 3
            if word in a_lower:
                score += 1

        if score > 0:
            scored_faqs.append((score, faq))

    scored_faqs.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored_faqs]


def detect_error_code(query_text):
    """
    Checks if user is asking about any of the 8 required error codes.
    """
    text = query_text.lower()

    # Check for direct codes
    for code in ["400", "401", "403", "404", "429", "500", "503", "600"]:
        pattern = r'\b' + code + r'\b'
        if re.search(pattern, text):
            return code

    if "ww-600" in text or "ww600" in text or "ww-001" in text or "ww001" in text or "site-specific" in text or "custom error" in text:
        return "600"

    # Friendly synonyms
    if "bad request" in text:
        return "400"
    if "unauthorized" in text:
        return "401"
    if "forbidden" in text:
        return "403"
    if "not found" in text or "page missing" in text:
        return "404"
    if "too many requests" in text or "rate limit" in text:
        return "429"
    if "internal server" in text or "server error" in text:
        return "500"
    if "service unavailable" in text:
        return "503"

    return None


def ask_gemini_api(prompt_text, system_instruction):
    """
    Optional call to Google Gemini API if GEMINI_API_KEY is configured.
    Falls back gracefully if unavailable.
    """
    api_key = getattr(settings, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return None

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_text,
            config={
                "system_instruction": system_instruction,
                "temperature": 0.3,
            }
        )
        if response and response.text:
            return response.text.strip()
    except Exception as e:
        logger.warning("Gemini API call failed or timed out: %s. Using local knowledge engine.", e)
    return None


def generate_assistant_response(user_message, session_id=None):
    """
    Main AI assistant engine.
    - Resolves error codes (400, 401, 403, 404, 429, 500, 503, WW-600)
    - Searches SQL database FAQs
    - Resolves travel advice & trip planner questions
    - Offers support ticket creation if cannot answer or on request
    - Logs conversation to MongoDB
    """
    msg = user_message.strip()
    msg_lower = msg.lower()

    response_data = {
        "reply": "",
        "source": "knowledge_base",
        "matched_faq": None,
        "error_code": None,
        "suggest_ticket": False,
        "quick_replies": [],
    }

    # 1. Check for Support Ticket request
    ticket_triggers = ["support ticket", "create ticket", "contact support", "talk to human", "complaint", "submit ticket", "helpdesk"]
    if any(t in msg_lower for t in ticket_triggers):
        response_data["reply"] = (
            "I'd be happy to help you create a support ticket for our travel engineering team. "
            "Please fill out the quick support ticket form below and we will get back to you promptly."
        )
        response_data["suggest_ticket"] = True
        response_data["source"] = "support_flow"
        response_data["quick_replies"] = ["Plan a trip", "Check FAQs", "Health Check"]
        # Log and return
        log_chat_interaction(session_id, user_message, response_data["reply"], metadata=response_data)
        return response_data

    # 2. Check for Error Code explanation
    detected_code = detect_error_code(msg)
    if detected_code:
        err = ERROR_CODE_KNOWLEDGE[detected_code]
        response_data["error_code"] = detected_code
        response_data["source"] = "error_code_engine"
        response_data["reply"] = (
            f"### ⚠️ Error {err['title']} ({err['category']})\n\n"
            f"**What it means:** {err['meaning']}\n\n"
            f"**In WanderWise:** {err['wanderwise_context']}\n\n"
            f"**Recommended action:**\n{err['solution']}"
        )
        if detected_code in ["500", "503", "600"]:
            response_data["suggest_ticket"] = True

        response_data["quick_replies"] = [
            "Explain Error 404",
            "Explain Error 500",
            "Explain WW-600",
            "Create Support Ticket",
        ]
        log_chat_interaction(session_id, user_message, response_data["reply"], metadata=response_data)
        return response_data

    # 3. Check SQL FAQ Database
    matched_faqs = search_faqs_in_sql(msg)
    if matched_faqs:
        best_faq = matched_faqs[0]
        response_data["matched_faq"] = best_faq.question
        response_data["source"] = "sql_faq_database"
        response_data["reply"] = f"**{best_faq.question}**\n\n{best_faq.answer}"

        # If there are related FAQs, mention them
        if len(matched_faqs) > 1:
            related_q = matched_faqs[1].question
            response_data["quick_replies"].append(related_q)
        response_data["quick_replies"].extend(["Plan a trip", "How to save itinerary?", "Explain error codes"])
        log_chat_interaction(session_id, user_message, response_data["reply"], metadata=response_data)
        return response_data

    # 4. Built-in travel queries
    if any(k in msg_lower for k in ["how do i plan", "how to plan", "create a trip", "start planning"]):
        response_data["reply"] = (
            "Planning a trip with WanderWise AI is fast and simple:\n\n"
            "1. Navigate to the **Trip Planner** section on our homepage.\n"
            "2. Enter your destination (like Ooty, Manali, Bali, or any place in the world).\n"
            "3. Select your travel dates, group size, and total budget.\n"
            "4. Choose your travel style (Budget, Comfort, Luxury) and food preferences.\n"
            "5. Click **'Plan My Journey'** and your AI itinerary will be ready in seconds!"
        )
        response_data["quick_replies"] = ["Where can I go?", "How to save itinerary?", "How does budget split work?"]
        log_chat_interaction(session_id, user_message, response_data["reply"], metadata=response_data)
        return response_data

    if any(k in msg_lower for k in ["destination", "where to go", "popular places", "suggest a place"]):
        response_data["reply"] = (
            "WanderWise AI supports travel planning worldwide! Popular curated destinations include:\n\n"
            "• **Ooty** (Tea gardens & misty hills)\n"
            "• **Manali** (Snow peaks & adventure sports)\n"
            "• **Goa** (Golden beaches, forts & coastal vibes)\n"
            "• **Bali** (Tropical temples, culture & beaches)\n"
            "• **Munnar, Jaipur, Rishikesh, Pondicherry, Kodaikanal**\n\n"
            "You can also type *any custom town or city* in the planner!"
        )
        response_data["quick_replies"] = ["Plan a trip to Ooty", "Plan a trip to Manali", "Plan a trip to Goa"]
        log_chat_interaction(session_id, user_message, response_data["reply"], metadata=response_data)
        return response_data

    # 5. Try Gemini Generative AI if API key is present
    gemini_reply = ask_gemini_api(
        prompt_text=f"User question: {user_message}\nProvide a friendly, helpful, concise answer specifically for WanderWise AI travel assistant.",
        system_instruction=(
            "You are WanderWise AI's friendly travel support assistant. WanderWise is a smart AI travel planner website "
            "that creates daily itineraries, budget breakdowns, packing checklists, and maps. "
            "Help the user with travel planning, navigating the site, explaining errors (400, 401, 403, 404, 429, 500, 503, WW-600), "
            "or offering to create a support ticket. Keep responses concise, warm, and formatted with markdown."
        )
    )
    if gemini_reply:
        response_data["reply"] = gemini_reply
        response_data["source"] = "gemini_generative_ai"
        response_data["quick_replies"] = ["Plan a trip", "Browse FAQs", "Contact Support"]
        log_chat_interaction(session_id, user_message, response_data["reply"], metadata=response_data)
        return response_data

    # 6. Fallback when AI assistant cannot answer
    response_data["reply"] = (
        "I'm sorry, I don't have enough specific information in my travel database to answer that completely. "
        "Would you like me to create a support ticket so our travel team can help you personally?"
    )
    response_data["suggest_ticket"] = True
    response_data["source"] = "fallback_unanswered"
    response_data["quick_replies"] = ["🎫 Yes, create ticket", "Browse FAQs", "Plan a trip", "Error code guide"]
    log_chat_interaction(session_id, user_message, response_data["reply"], metadata=response_data)
    return response_data
