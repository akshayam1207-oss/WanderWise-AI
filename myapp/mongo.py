import os
import json
import logging
from datetime import datetime
from pathlib import Path
from django.conf import settings

logger = logging.getLogger("wanderwise.mongo")

# Try importing pymongo
try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False
    logger.warning("pymongo is not installed. Falling back to local logging.")

FALLBACK_DIR = settings.BASE_DIR / "data"
FALLBACK_DIR.mkdir(exist_ok=True)


def get_mongo_client():
    """
    Returns a connected MongoClient or None.
    Uses a fast timeout so failing connections do not slow down web requests.
    """
    if not PYMONGO_AVAILABLE:
        return None

    mongo_uri = getattr(settings, "MONGO_URI", os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
    try:
        client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=1500,
            connectTimeoutMS=1500,
            socketTimeoutMS=1500,
        )
        # Test connection with ping
        client.admin.command("ping")
        return client
    except Exception as e:
        logger.debug("MongoDB connection not available: %s", e)
        return None


def get_mongo_db():
    client = get_mongo_client()
    if client:
        db_name = getattr(settings, "MONGO_DB_NAME", os.getenv("MONGO_DB_NAME", "wanderwise_db"))
        return client[db_name]
    return None


def log_chat_interaction(session_id, user_message, bot_response, metadata=None):
    """
    Stores chat log in MongoDB collection 'chat_logs'.
    Falls back to data/chat_logs_fallback.jsonl if MongoDB is unavailable.
    """
    record = {
        "session_id": session_id or "anonymous",
        "user_message": user_message,
        "bot_response": bot_response,
        "metadata": metadata or {},
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    db = get_mongo_db()
    if db is not None:
        try:
            res = db.chat_logs.insert_one(record)
            return {"success": True, "backend": "mongodb", "id": str(res.inserted_id)}
        except Exception as e:
            logger.error("Failed to insert chat log into MongoDB: %s", e)

    # Fallback to persistent JSONL log
    try:
        fallback_file = FALLBACK_DIR / "chat_logs_fallback.jsonl"
        with open(fallback_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        return {"success": True, "backend": "file_fallback"}
    except Exception as e:
        logger.error("Failed to write to chat log fallback file: %s", e)
        return {"success": False, "error": str(e)}


def log_user_feedback(session_id, rating, comment="", metadata=None):
    """
    Stores user feedback in MongoDB collection 'user_feedback'.
    Falls back to data/feedback_fallback.jsonl if MongoDB is unavailable.
    """
    record = {
        "session_id": session_id or "anonymous",
        "rating": rating,
        "comment": comment or "",
        "metadata": metadata or {},
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    db = get_mongo_db()
    if db is not None:
        try:
            res = db.user_feedback.insert_one(record)
            return {"success": True, "backend": "mongodb", "id": str(res.inserted_id)}
        except Exception as e:
            logger.error("Failed to insert feedback into MongoDB: %s", e)

    # Fallback to persistent JSONL log
    try:
        fallback_file = FALLBACK_DIR / "feedback_fallback.jsonl"
        with open(fallback_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        return {"success": True, "backend": "file_fallback"}
    except Exception as e:
        logger.error("Failed to write to feedback fallback file: %s", e)
        return {"success": False, "error": str(e)}


def check_mongo_status():
    """
    Pings MongoDB and returns diagnostic status dictionary for the Health Check page.
    """
    if not PYMONGO_AVAILABLE:
        return {
            "configured": False,
            "connected": False,
            "status": "PyMongo library missing",
            "chat_logs_count": 0,
            "feedback_count": 0,
        }

    mongo_uri = getattr(settings, "MONGO_URI", os.getenv("MONGO_URI", ""))
    masked_uri = "configured" if mongo_uri else "not set"
    if "@" in mongo_uri:
        # Mask credentials in URI
        parts = mongo_uri.split("@")
        masked_uri = "mongodb+srv://***@" + parts[-1]
    elif mongo_uri:
        masked_uri = mongo_uri

    start = datetime.utcnow()
    client = get_mongo_client()
    if client:
        latency = (datetime.utcnow() - start).total_seconds() * 1000
        db_name = getattr(settings, "MONGO_DB_NAME", os.getenv("MONGO_DB_NAME", "wanderwise_db"))
        db = client[db_name]
        try:
            chat_count = db.chat_logs.count_documents({})
            feedback_count = db.user_feedback.count_documents({})
        except Exception:
            chat_count = 0
            feedback_count = 0

        return {
            "configured": True,
            "connected": True,
            "status": "Connected & Operational",
            "latency_ms": round(latency, 2),
            "database": db_name,
            "uri": masked_uri,
            "chat_logs_count": chat_count,
            "feedback_count": feedback_count,
        }
    else:
        # Check fallback files
        fallback_chats = 0
        fallback_feedback = 0
        try:
            c_file = FALLBACK_DIR / "chat_logs_fallback.jsonl"
            if c_file.exists():
                fallback_chats = sum(1 for _ in open(c_file, "r", encoding="utf-8"))
            f_file = FALLBACK_DIR / "feedback_fallback.jsonl"
            if f_file.exists():
                fallback_feedback = sum(1 for _ in open(f_file, "r", encoding="utf-8"))
        except Exception:
            pass

        return {
            "configured": bool(mongo_uri),
            "connected": False,
            "status": "Offline (Standby mode - using resilient fallback buffer)",
            "uri": masked_uri,
            "chat_logs_count": fallback_chats,
            "feedback_count": fallback_feedback,
            "fallback_active": True,
        }
