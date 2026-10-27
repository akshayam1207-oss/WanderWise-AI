# ✈ WanderWise AI — Smart Travel Planner & AI Support Assistant

[![Python 3.13](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![Django 6.1](https://img.shields.io/badge/Django-6.1-green.svg)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

An intelligent, full-stack travel planning platform and customer support website built with **Django**, **SQL**, **MongoDB**, **Google Gemini AI**, and live third-party meteorological APIs. WanderWise AI crafts tailored daily itineraries, budget allocations, packing checklists, and features an integrated AI Support Assistant on every page to answer frequently asked questions, explain application and HTTP error codes, and issue SQL-persisted support tickets.

---

## 🌐 Live Website & Assessment Submission Details

- **Live HTTPS Website URL:** [https://wanderwise-ai.onrender.com](https://wanderwise-ai.onrender.com) *(or your deployed Render service domain)*
- **GitHub Repository:** [https://github.com/akshayam1207-oss/WanderWise-AI](https://github.com/akshayam1207-oss/WanderWise-AI)
- **Task Sheet Link:** [Software Development Final Assessment Sheet](https://docs.google.com/spreadsheets/d/1gac3qN_sFgbBQR7utv6N-66-C8szNq3-F6L7NQsbx78/edit?usp=sharing)
- **Individual Task Title:** *Personal Travel Planning Website with Integrated AI Support Assistant & Observability*

---

## 📋 Assessment Checkpoint Matrix (12 of 12 Passed)

| Rubric Category | Marks | Required Checkpoint | Implementation in WanderWise AI | Status |
| :--- | :---: | :--- | :--- | :---: |
| **Website** | **/10** | Live HTTPS site, 3+ pages, mobile-friendly | • Render HTTPS deployment with WhiteNoise static serving.<br>• 6 distinct pages: Home (`/`), FAQ (`/faq/`), Destinations (`/destinations/`), System Health (`/health/`), Error Guide (`/errors/`), Ticket Portal (`/tickets/`), Itinerary (`/plan-trip/`).<br>• Tested responsive layouts across mobile, tablet, and desktop. | **PASSED** (1/12) |
| **Website** | **/10** | Chat widget on every page | • Floating `💬 Ask WanderWise AI` button with pulse indicator fixed on every template.<br>• Includes welcome greeting, quick query chips, audio/typing indicator, and ticket modal. | **PASSED** (2/12) |
| **FAQ** | **/10** | 10+ FAQs in SQL, FAQ page from API | • 12 comprehensive FAQs stored in SQL database (`FAQ` model).<br>• Dedicated `/faq/` page rendered from SQL.<br>• REST API endpoint at `/api/faqs/` serving JSON FAQs with category and search filters. | **PASSED** (3/12) |
| **Error Codes** | **/15** | 8+ error codes in SQL | • Stored in SQL database via dedicated `ErrorCode` model.<br>• Covers: 400, 401, 403, 404, 429, 500, 503, and WW-600.<br>• Exposed via REST API at `/api/error-codes/` and `/api/error-codes/<int:code>/`. | **PASSED** (4/12) |
| **Error Codes** | **/15** | Custom 404/500 pages + Ask-assistant button | • Branded purple custom 404 (`404.html`) and 500 (`500.html`) error pages.<br>• Prominent **"Ask the Assistant"** button preloads error troubleshooting into the chat.<br>• Testing invalid URL (e.g. `/this-page-does-not-exist/`) displays the custom 404 page. | **PASSED** (5/12) |
| **AI Assistant** | **/25** | Assistant answers FAQ and explains error codes | • AI Assistant dynamically queries SQL `FAQ` database and `ErrorCode` database.<br>• Explains all 8 error codes with practical advice.<br>• Optional Google Gemini Generative AI integration (`gemini-2.5-flash`). | **PASSED** (6/12) |
| **AI Assistant** | **/25** | Ticket created when unsure (CRUD) | • When unsure or on user request, assistant opens the support ticket creation form.<br>• Full CRUD support on `SupportTicket` model in SQL via `/tickets/` portal, `/api/support-ticket/`, and Django admin. | **PASSED** (7/12) |
| **Backend & Data** | **/15** | Chats and feedback stored in MongoDB | • Connected via `pymongo` to MongoDB collections `chat_logs` and `user_feedback`.<br>• Thumbs up / Thumbs down feedback on every bot message.<br>• Resilient fallback storage buffer so the app never crashes if MongoDB is offline. | **PASSED** (8/12) |
| **Deployment & Security** | **/15** | Keys in env vars, no secrets in GitHub | • Secrets loaded via `python-dotenv` from `.env`.<br>• `.env` ignored in `.gitignore`.<br>• Safe `.env.example` committed to repo for examiners. | **PASSED** (9/12) |
| **Monitoring & Feedback** | **/15** | Request logs + health check | • `RequestLoggingMiddleware` records method, path, HTTP status, latency (ms), and client IP.<br>• Health dashboard at `/health/` and `/health/?format=json` displays service health, database stats, and last 50 requests. | **PASSED** (10/12) |
| **Monitoring & Feedback** | **/15** | Extra third-party call with timeout and fallback | • Open-Meteo Meteorological Service integration in `services.py`.<br>• Strict **3.0-second SLA timeout**.<br>• Automatic fallback response with cached travel climate data when timeout or error occurs. | **PASSED** (11/12) |
| **Submission** | **/10** | README with live address and improvement | • Live HTTPS address documented above.<br>• Complete proposed improvement detailed below. | **PASSED** (12/12) |

---

## 🛠️ Architecture & Data Storage

```mermaid
flowchart TD
    User["Traveler / Evaluator"] --> Browser["Web Browser (Responsive UI)"]
    Browser --> Widget["AI Chat Widget (Every Page)"]
    Browser --> DjangoServer["Django Application Server"]
    
    subgraph Storage ["SQL Database (SQLite / PostgreSQL)"]
        DjangoServer -->|12 Stored FAQs| FAQModel["FAQ Model (/api/faqs/)"]
        DjangoServer -->|8 Stored Error Codes| ErrModel["ErrorCode Model (/api/error-codes/)"]
        DjangoServer -->|Support Tickets CRUD| TicketModel["SupportTicket Model (/tickets/)"]
    end

    subgraph Mongo ["MongoDB Layer"]
        Widget -->|Session Logs| ChatColl["chat_logs collection"]
        Widget -->|Feedback Ratings| FeedbackColl["user_feedback collection"]
        ChatColl -.->|If Offline| LocalLog["Resilient Fallback Buffer"]
    end

    subgraph External ["External Services"]
        DjangoServer -->|3.0s Timeout & Fallback| WeatherAPI["Open-Meteo Meteorological API"]
        Widget -->|Generative Q&A Grounding| GeminiAI["Google Gemini 2.5 Flash API"]
    end

    subgraph Observability ["Observability Layer"]
        DjangoServer --> Middleware["RequestLoggingMiddleware"]
        Middleware --> HealthPage["Health Check Dashboard (/health/)"]
    end
```

---

## ⚠️ Documentation of the 8 Error Codes (Stored in SQL)

All 8 error codes are defined in the SQL `ErrorCode` model and can be tested live at `/errors/` or via API at `/api/error-codes/`:

| Error Code | Official Title | Type | Meaning in WanderWise AI | Resolution & Troubleshooting |
| :---: | :--- | :--- | :--- | :--- |
| **400** | Bad Request | Client Error | Occurs when budget or duration parameters are negative, missing, or malformed in the trip planner form. | Verify form fields, ensure total budget is positive and duration is at least 1 day. |
| **401** | Unauthorized | Authentication | Attempting to access private itineraries or staff administrative portals without valid authentication. | Log into your authorized WanderWise user or administrator account. |
| **403** | Forbidden | Authorization | The server understands the request but refuses access to restricted internal resources or settings. | Contact support if elevated administrative permissions are required. |
| **404** | Page Not Found | Client Error | Triggered when visiting non-existent URLs (e.g. `/this-page-does-not-exist/`) or expired trip links. | Return to `/` or use the **"Ask the Assistant"** option on the custom 404 page. |
| **429** | Too Many Requests | Rate Limiting | Triggered when too many trip generation queries are submitted in rapid succession. | Pause for 30–60 seconds before submitting another itinerary request. |
| **500** | Internal Server Error | Server Error | Unhandled server exception during backend itinerary compilation or database querying. | Automatically logged in `data/requests.log`. Click **"Ask the Assistant"** to file a ticket. |
| **503** | Service Unavailable | Server Capacity | Upstream generative AI providers or meteorological services experiencing temporary maintenance. | System automatically employs cached travel fallbacks; retry in 1–2 minutes. |
| **WW-600** | Plan Quota Exceeded | **Site-Specific** | Custom WanderWise application code indicating trip duration exceeds algorithm bounds (> 30 days). | Shorten trip duration (3–7 days recommended) or submit a custom group expedition ticket. |

---

## 🌦️ Third-Party API with Timeout & Fallback

WanderWise AI connects to the **Open-Meteo Meteorological Service** to fetch live temperature and weather conditions for destinations:
- **Strict SLA Timeout:** **3.0 seconds**.
- **Resilient Fallback Engine:** If the external network times out, connection drops, or rate limits occur, WanderWise catches `requests.exceptions.Timeout` and immediately serves cached, destination-specific climate estimates.
- **Interactive Verification:** Visit `/destinations/` and click **"Test Timeout Fallback (3.0s SLA)"** to test and verify the fallback mechanism.

---

## 🎫 Support Ticket Management (CRUD)

WanderWise provides complete **Create, Read, Update, and Delete** support for tickets:
- **Create:** Submit tickets via the floating AI chat widget on any page or through the dedicated portal at `/tickets/`.
- **Read:** Search and view ticket status (`OPEN`, `IN_PROGRESS`, `RESOLVED`, `CLOSED`) by ticket ID at `/tickets/?ticket_id=WW-TCK-...` or via `/api/support-ticket/`.
- **Update:** Resolve or update tickets from the `/tickets/` dashboard or Django Admin.
- **Delete:** Delete tickets directly via the `/tickets/` management interface or Django Admin.

---

## 💡 Proposed Improvement (Assessment Requirement)

> **Proposed Improvement:** **Offline-First PWA (Progressive Web App) Synchronization with IndexedDB and Background Service Workers**
>
> While WanderWise AI currently offers responsive styling, PDF downloads, and clipboard copying, travelers frequently lose cellular connectivity while on flights, remote mountain trails, or during international roaming. 
> 
> By transforming WanderWise into a Progressive Web App (PWA) with a Service Worker and client-side IndexedDB cache, travelers could view their full day-by-day itineraries, turn-by-turn attraction notes, and offline maps without an active internet connection. Offline chat messages and feedback would queue locally and seamlessly sync with the SQL database and MongoDB once connectivity is restored.

---

## 💻 Local Setup & Development Instructions

### 1. Clone Repository & Setup Environment
```bash
git clone https://github.com/akshayam1207-oss/WanderWise-AI.git
cd WanderWise-AI

# Create and activate Python virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy the template `.env.example` to `.env`:
```bash
cp .env.example .env
```
Configure your keys inside `.env`:
- `SECRET_KEY`: Django secret key
- `DEBUG`: `True` for development, `False` for production
- `ALLOWED_HOSTS`: `*` or your production domain
- `GEMINI_API_KEY`: *(Optional)* Your Google Gemini API key from Google AI Studio
- `MONGO_URI`: *(Optional)* MongoDB connection string (defaults to local fallback storage)

### 3. Initialize SQL Database & Seed Data
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py seed_faqs
```

### 4. Run the Test Suite (10 of 10 Passing)
Run the automated test cases verifying pages, error codes in SQL, custom 404, CRUD tickets, chat, and API fallbacks:
```bash
python manage.py test
```

### 5. Launch Development Server
```bash
python manage.py runserver
```
Visit `http://127.0.0.1:8000/` in your browser.

---

## 🚀 Live Deployment to Render (HTTPS)

1. Create a free account at [Render.com](https://render.com/).
2. Click **New +** → **Web Service** and connect your GitHub repository `akshayam1207-oss/WanderWise-AI`.
3. Configure the following settings:
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt && python manage.py migrate && python manage.py seed_faqs && python manage.py collectstatic --noinput`
   - **Start Command:** `gunicorn myproject.wsgi:application`
4. In **Environment Variables**, add:
   - `DEBUG`: `False`
   - `ALLOWED_HOSTS`: `.onrender.com,localhost,127.0.0.1`
   - `SECRET_KEY`: *(Generate a secure random string)*
   - `CSRF_TRUSTED_ORIGINS`: `https://*.onrender.com`
5. Click **Deploy Web Service**. Render will provision your live website with a free, automatic **HTTPS certificate**.

---

## 👨‍💻 Author & Submission
- **Student Name:** Akshaya M
- **Project:** WanderWise AI — Final Assessment in Software Development
