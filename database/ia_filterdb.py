# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import logging
from struct import pack
import re
import base64
from pyrogram.file_id import FileId
from pymongo.errors import DuplicateKeyError
from umongo import Instance, Document, fields
from motor.motor_asyncio import AsyncIOMotorClient
from marshmallow.exceptions import ValidationError
from info import DATABASE_URI, DATABASE_NAME, COLLECTION_NAME, USE_CAPTION_FILTER, MAX_B_TN
from utils import get_settings, save_group_settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


client = AsyncIOMotorClient(DATABASE_URI)
db = client[DATABASE_NAME]
instance = Instance.from_db(db)

@instance.register
class Media(Document):
    file_id = fields.StrField(attribute='_id')
    file_ref = fields.StrField(allow_none=True)
    file_name = fields.StrField(required=True)
    file_size = fields.IntField(required=True)
    file_type = fields.StrField(allow_none=True)
    mime_type = fields.StrField(allow_none=True)
    caption = fields.StrField(allow_none=True)

    class Meta:
        indexes = ('$file_name', )
        collection_name = COLLECTION_NAME


async def save_file(media):
    """Save file in database"""

    # TODO: Find better way to get same file_id for same media to avoid duplicates
    file_id, file_ref = unpack_new_file_id(media.file_id)
    file_name = re.sub(r"(_|\-|\.|\+)", " ", str(media.file_name))
    try:
        file = Media(
            file_id=file_id,
            file_ref=file_ref,
            file_name=file_name,
            file_size=media.file_size,
            file_type=media.file_type,
            mime_type=media.mime_type,
            caption=media.caption.html if media.caption else None,
        )
    except ValidationError:
        logger.exception('Error occurred while saving file in database')
        return False, 2
    else:
        try:
            await file.commit()
        except DuplicateKeyError:      
            logger.warning(
                f'{getattr(media, "file_name", "NO_FILE")} is already saved in database'
            )

            return False, 0
        else:
            logger.info(f'{getattr(media, "file_name", "NO_FILE")} is saved to database')
            try:
                from utils import temp
                cleaned = clean_movie_title(file_name)
                if cleaned and len(cleaned) > 1:
                    temp.MOVIE_TITLES_CACHE.add(cleaned)
            except Exception as e:
                logger.error(f"Error adding saved file to cache: {e}")
            return True, 1



async def get_search_results(chat_id, query, file_type=None, max_results=10, offset=0, filter=False):
    """For given query return (results, next_offset)"""
    # Callers may explicitly pass a larger max_results (e.g. 100 for spell-check
    # secondary DB lookups). Only apply the group-settings cap when the caller
    # uses the default value of 10.
    caller_max = max_results
    if chat_id is not None:
        settings = await get_settings(int(chat_id))
        try:
            if settings['max_btn']:
                settings_max = 10
            else:
                settings_max = int(MAX_B_TN)
        except KeyError:
            await save_group_settings(int(chat_id), 'max_btn', False)
            settings = await get_settings(int(chat_id))
            if settings['max_btn']:
                settings_max = 10
            else:
                settings_max = int(MAX_B_TN)
        # Use whichever is larger: the caller's explicit request or the settings value
        max_results = max(caller_max, settings_max)
    query = query.strip()
    #if filter:
        #better ?
        #query = query.replace(' ', r'(\s|\.|\+|\-|_)')
        #raw_pattern = r'(\s|_|\-|\.|\+)' + query + r'(\s|_|\-|\.|\+)'
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = r'(\b|[\.\+\-_])' + re.escape(query) + r'(\b|[\.\+\-_])'
    else:
        raw_pattern = query.replace(' ', r'.*[\s\.\+\-_()]')
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except Exception as e:
        print(f"Regex compilation error: {e}")
        return []
    if USE_CAPTION_FILTER:
        filter = {'$or': [{'file_name': regex}, {'caption': regex}]}
    else:
        filter = {'file_name': regex}

    if file_type:
        filter['file_type'] = file_type

    total_results = await Media.count_documents(filter)
    next_offset = offset + max_results

    if next_offset > total_results:
        next_offset = ''

    cursor = Media.find(filter)
    # Sort by recent
    cursor.sort('$natural', -1)
    # Slice files according to offset and max results
    cursor.skip(offset).limit(max_results)
    # Get list of files
    files = await cursor.to_list(length=max_results)

    return files, next_offset, total_results

async def get_bad_files(query, file_type=None, filter=False):
    """For given query return (results, next_offset)"""
    query = query.strip()
    #if filter:
        #better ?
        #query = query.replace(' ', r'(\s|\.|\+|\-|_)')
        #raw_pattern = r'(\s|_|\-|\.|\+)' + query + r'(\s|_|\-|\.|\+)'
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = r'(\b|[\.\+\-_])' + query + r'(\b|[\.\+\-_])'
    else:
        raw_pattern = query.replace(' ', r'.*[\s\.\+\-_]')
    
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except:
        return []

    if USE_CAPTION_FILTER:
        filter = {'$or': [{'file_name': regex}, {'caption': regex}]}
    else:
        filter = {'file_name': regex}

    if file_type:
        filter['file_type'] = file_type

    total_results = await Media.count_documents(filter)

    cursor = Media.find(filter)
    # Sort by recent
    cursor.sort('$natural', -1)
    # Get list of files
    files = await cursor.to_list(length=total_results)

    return files, total_results

async def get_file_details(query):
    filter = {'file_id': query}
    cursor = Media.find(filter)
    filedetails = await cursor.to_list(length=1)
    return filedetails


def encode_file_id(s: bytes) -> str:
    r = b""
    n = 0

    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0

            r += bytes([i])

    return base64.urlsafe_b64encode(r).decode().rstrip("=")


def encode_file_ref(file_ref: bytes) -> str:
    return base64.urlsafe_b64encode(file_ref).decode().rstrip("=")


def unpack_new_file_id(new_file_id):
    """Return file_id, file_ref"""
    decoded = FileId.decode(new_file_id)
    file_id = encode_file_id(
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash
        )
    )
    file_ref = encode_file_ref(decoded.file_reference)
    return file_id, file_ref


CLEAN_KEYWORDS = [
    r'\b(19|20)\d{2}\b', # Years (e.g., 2022, 1999)
    r'\b\d{3,4}p\b', # Resolutions (e.g., 720p, 1080p, 2160p)
    r'\b(s|season)\s*\d+\b', # Seasons (e.g., S01, Season 2)
    r'\b(e|episode)\s*\d+\b', # Episodes (e.g., E01, Episode 4)
    r'\b(hindi|tamil|telugu|kannada|malayalam|english|bengali|marathi|gujarati|punjabi|dubbed|multi|dual|org|original)\b', # Languages
    r'\b(web-dl|webrip|web|hdr|hdrip|bluray|brrip|dvdrip|hdtv|rip|tc|cam|pre-dvd|dvd)\b', # Sources
    r'\b(x264|x265|hevc|h264|h265|aac|dd5\.1|ddp5\.1|ddp|ac3|mp3|dts|esub|sub|subtitles)\b', # Codecs/Audio/Subs
]

def clean_movie_title(filename):
    name = filename
    if '.' in name:
        name = name.rsplit('.', 1)[0]
    name = re.sub(r'[_.\-+\[\]()]', ' ', name)
    
    # Extract year if present
    year_match = re.search(r'\b(19|20)\d{2}\b', name)
    year_str = f" ({year_match.group(0)})" if year_match else ""
    
    earliest_idx = len(name)
    for pattern in CLEAN_KEYWORDS:
        match = re.search(pattern, name, re.IGNORECASE)
        if match:
            earliest_idx = min(earliest_idx, match.start())
            
    title = name[:earliest_idx].strip()
    title = re.sub(r'^[xX]\s*', '', title)
    title = re.sub(r'\s+', ' ', title)
    return f"{title.title()}{year_str}"

async def load_movie_titles_cache():
    from utils import temp
    if temp.LOADING_CACHE:
        return
    temp.LOADING_CACHE = True
    import time
    start_time = time.time()
    try:
        cursor = Media.find({}, {"file_name": 1})
        async for doc in cursor:
            fname = doc.get("file_name") if isinstance(doc, dict) else getattr(doc, "file_name", None)
            if fname:
                cleaned = clean_movie_title(fname)
                if cleaned and len(cleaned) > 1:
                    temp.MOVIE_TITLES_CACHE.add(cleaned)
        logger.info(f"Loaded {len(temp.MOVIE_TITLES_CACHE)} unique movie titles into cache in {time.time() - start_time:.2f}s.")
    except Exception as e:
        logger.exception(f"Error loading movie titles cache: {e}")
    finally:
        temp.LOADING_CACHE = False

async def find_similar_titles(query_str):
    from utils import temp
    import difflib
    import re
    
    query_clean = clean_movie_title(query_str)
    if not query_clean:
        return []
        
    query_clean_no_year = re.sub(r'\s*\(\d{4}\)', '', query_clean).strip().lower()
        
    if not temp.MOVIE_TITLES_CACHE:
        if temp.LOADING_CACHE:
            return []
        try:
            temp.LOADING_CACHE = True
            cursor = Media.find({}, {"file_name": 1})
            async for doc in cursor:
                fname = doc.get("file_name") if isinstance(doc, dict) else getattr(doc, "file_name", None)
                if fname:
                    cleaned = clean_movie_title(fname)
                    if cleaned and len(cleaned) > 1:
                        temp.MOVIE_TITLES_CACHE.add(cleaned)
        except Exception as e:
            logger.error(f"Fallback loading cache failed: {e}")
        finally:
            temp.LOADING_CACHE = False
            
    candidates = list(temp.MOVIE_TITLES_CACHE)
    
    # Map cleaned lower title without year to its original cached title
    candidates_map = {}
    for cand in candidates:
        cand_no_year = re.sub(r'\s*\(\d{4}\)', '', cand).strip().lower()
        if cand_no_year:
            # Keep the one with year if there are duplicates
            if cand_no_year not in candidates_map or '(' in cand:
                candidates_map[cand_no_year] = cand
                
    # Perform fuzzy search on candidates without year
    matches_no_year = difflib.get_close_matches(query_clean_no_year, list(candidates_map.keys()), n=4, cutoff=0.6)
    
    # Map back to original titles
    matches = [candidates_map[m] for m in matches_no_year if m in candidates_map]
    
    # Substring matches search
    if not matches:
        for cand_no_year, original in candidates_map.items():
            if query_clean_no_year in cand_no_year or cand_no_year in query_clean_no_year:
                matches.append(original)
                if len(matches) >= 4:
                    break
                    
    seen = set()
    unique_matches = []
    for m in matches:
        if m.lower() not in seen:
            seen.add(m.lower())
            unique_matches.append(m)
            
    return unique_matches[:4]
