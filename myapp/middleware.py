import time
import logging
from collections import deque
from datetime import datetime
from pathlib import Path
from django.conf import settings

logger = logging.getLogger("wanderwise.requests")

# Buffer for the recent 50 requests to display on the Health Check dashboard
RECENT_REQUESTS = deque(maxlen=50)

REQUEST_STATS = {
    "total": 0,
    "status_2xx": 0,
    "status_3xx": 0,
    "status_4xx": 0,
    "status_5xx": 0,
    "total_time_ms": 0.0,
    "start_time": datetime.utcnow().isoformat() + "Z",
}

LOG_DIR = settings.BASE_DIR / "data"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "requests.log"


def get_client_ip(request):
    """Safely extracts client IP even when running behind reverse proxies."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "127.0.0.1")


class RequestLoggingMiddleware:
    """
    Middleware to log every HTTP request and response with latency, status,
    and client information. Powers the Health Check dashboard.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.perf_counter()
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        response = self.get_response(request)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        status_code = response.status_code
        method = request.method
        path = request.path
        client_ip = get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "Unknown")[:80]

        # Update stats
        REQUEST_STATS["total"] += 1
        REQUEST_STATS["total_time_ms"] += duration_ms
        if 200 <= status_code < 300:
            REQUEST_STATS["status_2xx"] += 1
        elif 300 <= status_code < 400:
            REQUEST_STATS["status_3xx"] += 1
        elif 400 <= status_code < 500:
            REQUEST_STATS["status_4xx"] += 1
        elif status_code >= 500:
            REQUEST_STATS["status_5xx"] += 1

        log_entry = {
            "timestamp": timestamp,
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "client_ip": client_ip,
            "user_agent": user_agent,
        }

        RECENT_REQUESTS.appendleft(log_entry)

        # Log format string
        msg = f"[{timestamp}] {method} {path} -> {status_code} ({duration_ms}ms) from {client_ip}"
        if status_code >= 500:
            logger.error(msg)
        elif status_code >= 400:
            logger.warning(msg)
        else:
            logger.info(msg)

        # Append to log file
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except Exception:
            pass

        return response


def get_recent_requests():
    return list(RECENT_REQUESTS)


def get_request_stats():
    total = REQUEST_STATS["total"]
    avg_latency = round(REQUEST_STATS["total_time_ms"] / total, 2) if total > 0 else 0.0
    return {
        "total": total,
        "status_2xx": REQUEST_STATS["status_2xx"],
        "status_3xx": REQUEST_STATS["status_3xx"],
        "status_4xx": REQUEST_STATS["status_4xx"],
        "status_5xx": REQUEST_STATS["status_5xx"],
        "avg_latency_ms": avg_latency,
        "uptime_start": REQUEST_STATS["start_time"],
    }
