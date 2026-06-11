"""
Movie Request Tracking Database

Stores user movie requests and allows notifying users when the movie is uploaded.
"""

from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import re
import difflib
import logging
from info import DATABASE_URI, DATABASE_NAME

logger = logging.getLogger(__name__)

_req_client = AsyncIOMotorClient(DATABASE_URI)
_req_db = _req_client[DATABASE_NAME]
_requests_col = _req_db["movie_requests"]


async def save_movie_request(user_id: int, user_first_name: str, user_mention: str, movie_name: str) -> str:
    """
    Save a movie request. Returns the inserted _id as a string.
    """
    doc = {
        "user_id": user_id,
        "user_first_name": user_first_name,
        "user_mention": user_mention,  # HTML mention e.g. <a href='tg://user?id=123'>Name</a>
        "movie_name": movie_name,
        "timestamp": datetime.utcnow(),
        "fulfilled": False,
    }
    result = await _requests_col.insert_one(doc)
    return str(result.inserted_id)


async def fetch_and_mark_pending_requests(file_name: str):
    """
    Return all unfulfilled requests whose movie_name fuzzy-matches the uploaded file_name,
    and atomically marks them as fulfilled. This prevents duplicate notifications
    when multiple files are uploaded concurrently.
    """
    from database.ia_filterdb import clean_movie_title
    cleaned_file = _clean(clean_movie_title(file_name))

    matching = []
    ids_to_mark = []
    
    cursor = _requests_col.find({"fulfilled": False})
    async for req in cursor:
        req_clean = _clean(req.get("movie_name", ""))
        ratio = difflib.SequenceMatcher(None, req_clean, cleaned_file).ratio()
        if ratio >= 0.75:
            matching.append(req)
            ids_to_mark.append(req["_id"])
            
    if not ids_to_mark:
        return []
        
    result = await _requests_col.update_many(
        {"_id": {"$in": ids_to_mark}, "fulfilled": False},
        {"$set": {"fulfilled": True}}
    )
    
    # If no documents were modified, another concurrent task already fulfilled them
    if result.modified_count == 0:
        return []
        
    return matching


async def get_request_by_id(request_id: str):
    """Fetch a single request document by its string _id."""
    from bson import ObjectId
    try:
        return await _requests_col.find_one({"_id": ObjectId(request_id)})
    except Exception:
        return None


def _clean(title: str) -> str:
    """Normalize a movie title for fuzzy comparison."""
    t = re.sub(r'\s*\(\d{4}\)', '', title or "").strip().lower()
    t = re.sub(r'[^a-z0-9\s]', '', t)
    return re.sub(r'\s+', ' ', t).strip()
