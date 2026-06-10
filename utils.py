# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import logging, asyncio, os, re, random, pytz, aiohttp, requests, string, json, http.client
from info import *
from imdb import Cinemagoer 
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram import enums
from pyrogram.errors import *
from typing import Union
from Script import script
from datetime import datetime, date
from typing import List
from database.users_chats_db import db
from database.join_reqs import JoinReqs
from bs4 import BeautifulSoup
from shortzy import Shortzy

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
join_db = JoinReqs
BTN_URL_REGEX = re.compile(r"(\[([^\[]+?)\]\((buttonurl|buttonalert):(?:/{0,2})(.+?)(:same)?\))")

imdb = Cinemagoer() 
TOKENS = {}
VERIFIED = {}
BANNED = {}
SECOND_SHORTENER = {}
SMART_OPEN = '“'
SMART_CLOSE = '”'
START_CHAR = ('\'', '"', SMART_OPEN)

# temp db for banned 
class temp(object):
    BANNED_USERS = []
    BANNED_CHATS = []
    ME = None
    CURRENT=int(os.environ.get("SKIP", 2))
    CANCEL = False
    MELCOW = {}
    U_NAME = None
    B_NAME = None
    GETALL = {}
    SHORT = {}
    SETTINGS = {}
    IMDB_CAP = {}
    MOVIE_TITLES_CACHE = set()
    LOADING_CACHE = False


async def pub_is_subscribed(bot, query, channel):
    btn = []
    for id in channel:
        chat = await bot.get_chat(int(id))
        try:
            await bot.get_chat_member(id, query.from_user.id)
        except UserNotParticipant:
            btn.append(
                [InlineKeyboardButton(f'Join {chat.title}', url=chat.invite_link)]
            )
        except Exception as e:
            pass
    return btn

async def is_subscribed(bot, query):
    if REQUEST_TO_JOIN_MODE == True and join_db().isActive():
        try:
            user = await join_db().get_user(query.from_user.id)
            if user and user["user_id"] == query.from_user.id:
                return True
            else:
                try:
                    user_data = await bot.get_chat_member(AUTH_CHANNEL, query.from_user.id)
                except UserNotParticipant:
                    pass
                except Exception as e:
                    logger.exception(e)
                else:
                    if user_data.status != enums.ChatMemberStatus.BANNED:
                        return True
        except Exception as e:
            logger.exception(e)
            return False
    else:
        try:
            user = await bot.get_chat_member(AUTH_CHANNEL, query.from_user.id)
        except UserNotParticipant:
            pass
        except Exception as e:
            logger.exception(e)
        else:
            if user.status != enums.ChatMemberStatus.BANNED:
                return True
        return False

async def get_poster(query, bulk=False, id=False, file=None):
    if not id:
        query = (query.strip()).lower()
        # Extract year in parentheses if present, e.g. "kantara (2022)" -> year="2022", title="kantara"
        year_match = re.search(r'\((19|20)\d{2}\)', query)
        if year_match:
            year = year_match.group(0)[1:-1]
            title = re.sub(r'\s*\((19|20)\d{2}\)', '', query).strip()
        else:
            title = query
            year = re.findall(r'[1-2]\d{3}$', query, re.IGNORECASE)
            if year:
                year = list_to_str(year[:1])
                title = (query.replace(year, "")).strip()
            elif file is not None:
                year = re.findall(r'[1-2]\d{3}', file, re.IGNORECASE)
                if year:
                    year = list_to_str(year[:1]) 
            else:
                year = None
        try:
            movieid = await asyncio.to_thread(imdb.search_movie, title.lower(), results=10)
        except Exception as e:
            logger.error(f"IMDb search error in get_poster: {e}")
            return None
        if not movieid:
            return None
        if year:
            filtered=list(filter(lambda k: str(k.get('year')) == str(year), movieid))
            if not filtered:
                filtered = movieid
        else:
            filtered = movieid
        movieid=list(filter(lambda k: k.get('kind') in ['movie', 'tv series'], filtered))
        if not movieid:
            movieid = filtered
        if bulk:
            return movieid
        movieid = movieid[0].movieID
    else:
        movieid = query
    try:
        movie = await asyncio.to_thread(imdb.get_movie, movieid)
    except Exception as e:
        logger.error(f"IMDb get_movie error in get_poster: {e}")
        return None
    if not movie:
        return None
    if movie.get("original air date"):
        date = movie["original air date"]
    elif movie.get("year"):
        date = movie.get("year")
    else:
        date = "N/A"
    plot = ""
    if not LONG_IMDB_DESCRIPTION:
        plot = movie.get('plot')
        if plot and len(plot) > 0:
            plot = plot[0]
    else:
        plot = movie.get('plot outline')
    if plot and len(plot) > 800:
        plot = plot[0:800] + "..."

    return {
        'title': movie.get('title'),
        'votes': movie.get('votes'),
        "aka": list_to_str(movie.get("akas")),
        "seasons": movie.get("number of seasons"),
        "box_office": movie.get('box office'),
        'localized_title': movie.get('localized title'),
        'kind': movie.get("kind"),
        "imdb_id": f"tt{movie.get('imdbID')}",
        "cast": list_to_str(movie.get("cast")),
        "runtime": list_to_str(movie.get("runtimes")),
        "countries": list_to_str(movie.get("countries")),
        "certificates": list_to_str(movie.get("certificates")),
        "languages": list_to_str(movie.get("languages")),
        "director": list_to_str(movie.get("director")),
        "writer":list_to_str(movie.get("writer")),
        "producer":list_to_str(movie.get("producer")),
        "composer":list_to_str(movie.get("composer")) ,
        "cinematographer":list_to_str(movie.get("cinematographer")),
        "music_team": list_to_str(movie.get("music department")),
        "distributors": list_to_str(movie.get("distributors")),
        'release_date': date,
        'year': movie.get('year'),
        'genres': list_to_str(movie.get("genres")),
        'poster': movie.get('full-size cover url'),
        'plot': plot,
        'rating': str(movie.get("rating")),
        'url':f'https://www.imdb.com/title/tt{movieid}'
    }

async def broadcast_messages(user_id, message):
    try:
        await message.copy(chat_id=user_id)
        return True, "Success"
    except FloodWait as e:
        await asyncio.sleep(e.x)
        return await broadcast_messages(user_id, message)
    except InputUserDeactivated:
        await db.delete_user(int(user_id))
        logging.info(f"{user_id}-Removed from Database, since deleted account.")
        return False, "Deleted"
    except UserIsBlocked:
        logging.info(f"{user_id} -Blocked the bot.")
        return False, "Blocked"
    except PeerIdInvalid:
        await db.delete_user(int(user_id))
        logging.info(f"{user_id} - PeerIdInvalid")
        return False, "Error"
    except Exception as e:
        return False, "Error"

async def broadcast_messages_group(chat_id, message):
    try:
        kd = await message.copy(chat_id=chat_id)
        try:
            await kd.pin()
        except:
            pass
        return True, "Success"
    except FloodWait as e:
        await asyncio.sleep(e.x)
        return await broadcast_messages_group(chat_id, message)
    except Exception as e:
        return False, "Error"
    
async def search_gagala(text):
    usr_agent = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/61.0.3163.100 Safari/537.36'
        }
    text = text.replace(" ", '+')
    url = f'https://www.google.com/search?q={text}'
    response = requests.get(url, headers=usr_agent)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    titles = soup.find_all( 'h3' )
    return [title.getText() for title in titles]

async def get_settings(group_id):
    settings = temp.SETTINGS.get(group_id)
    if not settings:
        settings = await db.get_settings(group_id)
        temp.SETTINGS[group_id] = settings
    return settings
    
async def save_group_settings(group_id, key, value):
    current = await get_settings(group_id)
    current[key] = value
    temp.SETTINGS[group_id] = current
    await db.update_settings(group_id, current)
    
def get_size(size):
    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    size = float(size)
    i = 0
    while size >= 1024.0 and i < len(units):
        i += 1
        size /= 1024.0
    return "%.2f %s" % (size, units[i])

def split_list(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]  

def get_file_id(msg: Message):
    if msg.media:
        for message_type in (
            "photo",
            "animation",
            "audio",
            "document",
            "video",
            "video_note",
            "voice",
            "sticker"
        ):
            obj = getattr(msg, message_type)
            if obj:
                setattr(obj, "message_type", message_type)
                return obj

def extract_user(message: Message) -> Union[int, str]:
    user_id = None
    user_first_name = None
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        user_first_name = message.reply_to_message.from_user.first_name

    elif len(message.command) > 1:
        if (
            len(message.entities) > 1 and
            message.entities[1].type == enums.MessageEntityType.TEXT_MENTION
        ):
           
            required_entity = message.entities[1]
            user_id = required_entity.user.id
            user_first_name = required_entity.user.first_name
        else:
            user_id = message.command[1]
            # don't want to make a request -_-
            user_first_name = user_id
        try:
            user_id = int(user_id)
        except ValueError:
            pass
    else:
        user_id = message.from_user.id
        user_first_name = message.from_user.first_name
    return (user_id, user_first_name)

def list_to_str(k):
    if not k:
        return "N/A"
    elif len(k) == 1:
        return str(k[0])
    elif MAX_LIST_ELM:
        k = k[:int(MAX_LIST_ELM)]
        return ' '.join(f'{elem}, ' for elem in k)
    else:
        return ' '.join(f'{elem}, ' for elem in k)

def last_online(from_user):
    time = ""
    if from_user.is_bot:
        time += "🤖 Bot :("
    elif from_user.status == enums.UserStatus.RECENTLY:
        time += "Recently"
    elif from_user.status == enums.UserStatus.LAST_WEEK:
        time += "Within the last week"
    elif from_user.status == enums.UserStatus.LAST_MONTH:
        time += "Within the last month"
    elif from_user.status == enums.UserStatus.LONG_AGO:
        time += "A long time ago :("
    elif from_user.status == enums.UserStatus.ONLINE:
        time += "Currently Online"
    elif from_user.status == enums.UserStatus.OFFLINE:
        time += from_user.last_online_date.strftime("%a, %d %b %Y, %H:%M:%S")
    return time

def split_quotes(text: str) -> List:
    if not any(text.startswith(char) for char in START_CHAR):
        return text.split(None, 1)
    counter = 1  # ignore first char -> is some kind of quote
    while counter < len(text):
        if text[counter] == "\\":
            counter += 1
        elif text[counter] == text[0] or (text[0] == SMART_OPEN and text[counter] == SMART_CLOSE):
            break
        counter += 1
    else:
        return text.split(None, 1)

    # 1 to avoid starting quote, and counter is exclusive so avoids ending
    key = remove_escapes(text[1:counter].strip())
    # index will be in range, or `else` would have been executed and returned
    rest = text[counter + 1:].strip()
    if not key:
        key = text[0] + text[0]
    return list(filter(None, [key, rest]))

def gfilterparser(text, keyword):
    if "buttonalert" in text:
        text = (text.replace("\n", "\\n").replace("\t", "\\t"))
    buttons = []
    note_data = ""
    prev = 0
    i = 0
    alerts = []
    for match in BTN_URL_REGEX.finditer(text):
        # Check if btnurl is escaped
        n_escapes = 0
        to_check = match.start(1) - 1
        while to_check > 0 and text[to_check] == "\\":
            n_escapes += 1
            to_check -= 1

        # if even, not escaped -> create button
        if n_escapes % 2 == 0:
            note_data += text[prev:match.start(1)]
            prev = match.end(1)
            if match.group(3) == "buttonalert":
                # create a thruple with button label, url, and newline status
                if bool(match.group(5)) and buttons:
                    buttons[-1].append(InlineKeyboardButton(
                        text=match.group(2),
                        callback_data=f"gfilteralert:{i}:{keyword}"
                    ))
                else:
                    buttons.append([InlineKeyboardButton(
                        text=match.group(2),
                        callback_data=f"gfilteralert:{i}:{keyword}"
                    )])
                i += 1
                alerts.append(match.group(4))
            elif bool(match.group(5)) and buttons:
                buttons[-1].append(InlineKeyboardButton(
                    text=match.group(2),
                    url=match.group(4).replace(" ", "")
                ))
            else:
                buttons.append([InlineKeyboardButton(
                    text=match.group(2),
                    url=match.group(4).replace(" ", "")
                )])

        else:
            note_data += text[prev:to_check]
            prev = match.start(1) - 1
    else:
        note_data += text[prev:]

    try:
        return note_data, buttons, alerts
    except:
        return note_data, buttons, None

def parser(text, keyword):
    if "buttonalert" in text:
        text = (text.replace("\n", "\\n").replace("\t", "\\t"))
    buttons = []
    note_data = ""
    prev = 0
    i = 0
    alerts = []
    for match in BTN_URL_REGEX.finditer(text):
        # Check if btnurl is escaped
        n_escapes = 0
        to_check = match.start(1) - 1
        while to_check > 0 and text[to_check] == "\\":
            n_escapes += 1
            to_check -= 1

        # if even, not escaped -> create button
        if n_escapes % 2 == 0:
            note_data += text[prev:match.start(1)]
            prev = match.end(1)
            if match.group(3) == "buttonalert":
                # create a thruple with button label, url, and newline status
                if bool(match.group(5)) and buttons:
                    buttons[-1].append(InlineKeyboardButton(
                        text=match.group(2),
                        callback_data=f"alertmessage:{i}:{keyword}"
                    ))
                else:
                    buttons.append([InlineKeyboardButton(
                        text=match.group(2),
                        callback_data=f"alertmessage:{i}:{keyword}"
                    )])
                i += 1
                alerts.append(match.group(4))
            elif bool(match.group(5)) and buttons:
                buttons[-1].append(InlineKeyboardButton(
                    text=match.group(2),
                    url=match.group(4).replace(" ", "")
                ))
            else:
                buttons.append([InlineKeyboardButton(
                    text=match.group(2),
                    url=match.group(4).replace(" ", "")
                )])

        else:
            note_data += text[prev:to_check]
            prev = match.start(1) - 1
    else:
        note_data += text[prev:]

    try:
        return note_data, buttons, alerts
    except:
        return note_data, buttons, None

def remove_escapes(text: str) -> str:
    res = ""
    is_escaped = False
    for counter in range(len(text)):
        if is_escaped:
            res += text[counter]
            is_escaped = False
        elif text[counter] == "\\":
            is_escaped = True
        else:
            res += text[counter]
    return res

def humanbytes(size):
    if not size:
        return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: ' ', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'

async def get_shortlink(chat_id, link):
    settings = await get_settings(chat_id) #fetching settings for group
    if 'shortlink' in settings.keys():
        URL = settings['shortlink']
        API = settings['shortlink_api']
    else:
        URL = SHORTLINK_URL
        API = SHORTLINK_API
    if URL.startswith("shorturllink") or URL.startswith("terabox.in") or URL.startswith("urlshorten.in"):
        URL = SHORTLINK_URL
        API = SHORTLINK_API
    if URL == "api.shareus.io":
        url = f'https://{URL}/easy_api'
        params = {
            "key": API,
            "link": link,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, raise_for_status=True, ssl=False) as response:
                    data = await response.text()
                    return data
        except Exception as e:
            logger.error(e)
            return link
    else:
        shortzy = Shortzy(api_key=API, base_site=URL)
        link = await shortzy.convert(link)
        return link
    
async def get_tutorial(chat_id):
    settings = await get_settings(chat_id) #fetching settings for group
    if 'tutorial' in settings.keys():
        if settings['is_tutorial']:
            TUTORIAL_URL = settings['tutorial']
        else:
            TUTORIAL_URL = TUTORIAL
    else:
        TUTORIAL_URL = TUTORIAL
    return TUTORIAL_URL
        
async def get_verify_shorted_link(link, url, api):
    API = api
    URL = url
    if URL == "api.shareus.io":
        url = f'https://{URL}/easy_api'
        params = {
            "key": API,
            "link": link,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, raise_for_status=True, ssl=False) as response:
                    data = await response.text()
                    return data
        except Exception as e:
            logger.error(e)
            return link
    else:
        shortzy = Shortzy(api_key=API, base_site=URL)
        link = await shortzy.convert(link)
        return link
        
async def check_token(bot, userid, token):
    user = await bot.get_users(userid)
    if not await db.is_user_exist(user.id):
        await db.add_user(user.id, user.first_name)
        await bot.send_message(LOG_CHANNEL, script.LOG_TEXT_P.format(user.id, user.mention))
    if user.id in TOKENS.keys():
        TKN = TOKENS[user.id]
        if token in TKN.keys():
            is_used = TKN[token]
            if is_used == True:
                return False
            else:
                return True
    else:
        return False

async def get_token(bot, userid, link):
    user = await bot.get_users(userid)
    if not await db.is_user_exist(user.id):
        await db.add_user(user.id, user.first_name)
        await bot.send_message(LOG_CHANNEL, script.LOG_TEXT_P.format(user.id, user.mention))
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=7))
    TOKENS[user.id] = {token: False}
    link = f"{link}verify-{user.id}-{token}"
    shortened_verify_url = await get_verify_shorted_link(link, VERIFY_SHORTLINK_URL, VERIFY_SHORTLINK_API)
    if VERIFY_SECOND_SHORTNER == True:
        snd_link = await get_verify_shorted_link(shortened_verify_url, VERIFY_SND_SHORTLINK_URL, VERIFY_SND_SHORTLINK_API)
        return str(snd_link)
    else:
        return str(shortened_verify_url)

async def verify_user(bot, userid, token):
    user = await bot.get_users(userid)
    if not await db.is_user_exist(user.id):
        await db.add_user(user.id, user.first_name)
        await bot.send_message(LOG_CHANNEL, script.LOG_TEXT_P.format(user.id, user.mention))
    TOKENS[user.id] = {token: True}
    tz = pytz.timezone('Asia/Kolkata')
    today = date.today()
    VERIFIED[user.id] = str(today)

async def check_verification(bot, userid):
    user = await bot.get_users(userid)
    if not await db.is_user_exist(user.id):
        await db.add_user(user.id, user.first_name)
        await bot.send_message(LOG_CHANNEL, script.LOG_TEXT_P.format(user.id, user.mention))
    tz = pytz.timezone('Asia/Kolkata')
    today = date.today()
    if user.id in VERIFIED.keys():
        EXP = VERIFIED[user.id]
        years, month, day = EXP.split('-')
        comp = date(int(years), int(month), int(day))
        if comp<today:
            return False
        else:
            return True
    else:
        return False  
    
async def send_all(bot, userid, files, ident, chat_id, user_name, query):
    settings = await get_settings(chat_id)
    if 'is_shortlink' in settings.keys():
        ENABLE_SHORTLINK = settings['is_shortlink']
    else:
        await save_group_settings(message.chat.id, 'is_shortlink', False)
        ENABLE_SHORTLINK = False
    try:
        if ENABLE_SHORTLINK:
            for file in files:
                title = file.file_name
                size = get_size(file.file_size)
                if not await db.has_premium_access(userid) and SHORTLINK_MODE == True:
                    await bot.send_message(chat_id=userid, text=f"<b>Hᴇʏ ᴛʜᴇʀᴇ {user_name} 👋🏽 \n\n✅ Sᴇᴄᴜʀᴇ ʟɪɴᴋ ᴛᴏ ʏᴏᴜʀ ғɪʟᴇ ʜᴀs sᴜᴄᴄᴇssғᴜʟʟʏ ʙᴇᴇɴ ɢᴇɴᴇʀᴀᴛᴇᴅ ᴘʟᴇᴀsᴇ ᴄʟɪᴄᴋ ᴅᴏᴡɴʟᴏᴀᴅ ʙᴜᴛᴛᴏɴ\n\n🗃️ Fɪʟᴇ Nᴀᴍᴇ : {title}\n🔖 Fɪʟᴇ Sɪᴢᴇ : {size}</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📤 Dᴏᴡɴʟᴏᴀᴅ 📥", url=await get_shortlink(chat_id, f"https://telegram.me/{temp.U_NAME}?start=files_{file.file_id}"))]]))
        else:
            for file in files:
                    f_caption = file.caption
                    title = file.file_name
                    size = get_size(file.file_size)
                    if CUSTOM_FILE_CAPTION:
                        try:
                            f_caption = CUSTOM_FILE_CAPTION.format(file_name='' if title is None else title,
                                                                    file_size='' if size is None else size,
                                                                    file_caption='' if f_caption is None else f_caption)
                        except Exception as e:
                            print(e)
                            f_caption = f_caption
                    if f_caption is None:
                        f_caption = f"{title}"
                    await bot.send_cached_media(
                        chat_id=userid,
                        file_id=file.file_id,
                        caption=f_caption,
                        protect_content=True if ident == "filep" else False,
                        reply_markup=InlineKeyboardMarkup(
                            [
                                [
                                InlineKeyboardButton('Sᴜᴘᴘᴏʀᴛ Gʀᴏᴜᴘ', url=GRP_LNK),
                                InlineKeyboardButton('Uᴘᴅᴀᴛᴇs Cʜᴀɴɴᴇʟ', url=CHNL_LNK)
                            ],[
                                InlineKeyboardButton("Bᴏᴛ Oᴡɴᴇʀ", url="t.me/creatorrio")
                                ]
                            ]
                        )
                    )
    except UserIsBlocked:
        await query.answer('Uɴʙʟᴏᴄᴋ ᴛʜᴇ ʙᴏᴛ ᴍᴀʜɴ !', show_alert=True)
    except PeerIdInvalid:
        await query.answer('Hᴇʏ, Sᴛᴀʀᴛ Bᴏᴛ Fɪʀsᴛ Aɴᴅ Cʟɪᴄᴋ Sᴇɴᴅ Aʟʟ', show_alert=True)
    except Exception as e:
        await query.answer('Hᴇʏ, Sᴛᴀʀᴛ Bᴏᴛ Fɪʀsᴛ Aɴᴅ Cʟɪᴄᴋ Sᴇɴᴅ Aʟʟ', show_alert=True)
        
async def get_cap(settings, remaining_seconds, files, query, total_results, search):
    if settings["imdb"]:
        IMDB_CAP = temp.IMDB_CAP.get(query.from_user.id)
        if IMDB_CAP:
            cap = IMDB_CAP
            cap+="<b>\n\n<u>🍿 Your Movie Files 👇</u></b>\n\n"
            for file in files:
                cap += f"<b>📁 <a href='https://telegram.me/{temp.U_NAME}?start=files_{file.file_id}'>[{get_size(file.file_size)}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file.file_name.split()))}\n\n</a></b>"
        else:
            imdb = await get_poster(search, file=(files[0]).file_name) if settings["imdb"] else None
            if imdb:
                TEMPLATE = script.IMDB_TEMPLATE_TXT
                cap = TEMPLATE.format(
                    qurey=search,
                    title=imdb['title'],
                    votes=imdb['votes'],
                    aka=imdb["aka"],
                    seasons=imdb["seasons"],
                    box_office=imdb['box_office'],
                    localized_title=imdb['localized_title'],
                    kind=imdb['kind'],
                    imdb_id=imdb["imdb_id"],
                    cast=imdb["cast"],
                    runtime=imdb["runtime"],
                    countries=imdb["countries"],
                    certificates=imdb["certificates"],
                    languages=imdb["languages"],
                    director=imdb["director"],
                    writer=imdb["writer"],
                    producer=imdb["producer"],
                    composer=imdb["composer"],
                    cinematographer=imdb["cinematographer"],
                    music_team=imdb["music_team"],
                    distributors=imdb["distributors"],
                    release_date=imdb['release_date'],
                    year=imdb['year'],
                    genres=imdb['genres'],
                    poster=imdb['poster'],
                    plot=imdb['plot'],
                    rating=imdb['rating'],
                    url=imdb['url'],
                    **locals()
                )
                cap+="<b>\n\n<u>🍿 Your Movie Files 👇</u></b>\n\n"
                for file in files:
                    cap += f"<b>📁 <a href='https://telegram.me/{temp.U_NAME}?start=files_{file.file_id}'>[{get_size(file.file_size)}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file.file_name.split()))}\n\n</a></b>"
            else:
                cap = f"<b>Tʜᴇ Rᴇꜱᴜʟᴛꜱ Fᴏʀ ☞ {search}\n\nRᴇǫᴜᴇsᴛᴇᴅ Bʏ ☞ {query.from_user.mention}\n\nʀᴇsᴜʟᴛ sʜᴏᴡ ɪɴ ☞ {remaining_seconds} sᴇᴄᴏɴᴅs\n\nᴘᴏᴡᴇʀᴇᴅ ʙʏ ☞ : {query.message.chat.title}\n\n⚠️ ᴀꜰᴛᴇʀ 5 ᴍɪɴᴜᴛᴇꜱ ᴛʜɪꜱ ᴍᴇꜱꜱᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴅᴇʟᴇᴛᴇᴅ 🗑️\n\n</b>"
                cap+="<b><u>🍿 Your Movie Files 👇</u></b>\n\n"
                for file in files:
                    cap += f"<b>📁 <a href='https://telegram.me/{temp.U_NAME}?start=files_{file.file_id}'>[{get_size(file.file_size)}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file.file_name.split()))}\n\n</a></b>"
    else:
        cap = f"<b>Tʜᴇ Rᴇꜱᴜʟᴛꜱ Fᴏʀ ☞ {search}\n\nRᴇǫᴜᴇsᴛᴇᴅ Bʏ ☞ {query.from_user.mention}\n\nʀᴇsᴜʟᴛ sʜᴏᴡ ɪɴ ☞ {remaining_seconds} sᴇᴄᴏɴᴅs\n\nᴘᴏᴡᴇʀᴇᴅ ʙʏ ☞ : {query.message.chat.title} \n\n⚠️ ᴀꜰᴛᴇʀ 5 ᴍɪɴᴜᴛᴇꜱ ᴛʜɪꜱ ᴍᴇꜱꜱᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴅᴇʟᴇᴛᴇᴅ 🗑️\n\n</b>"
        cap+="<b><u>🍿 Your Movie Files 👇</u></b>\n\n"
        for file in files:
            cap += f"<b>📁 <a href='https://telegram.me/{temp.U_NAME}?start=files_{file.file_id}'>[{get_size(file.file_size)}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file.file_name.split()))}\n\n</a></b>"
    return cap


async def get_seconds(time_string):
    def extract_value_and_unit(ts):
        value = ""
        unit = ""
        index = 0
        while index < len(ts) and ts[index].isdigit():
            value += ts[index]
            index += 1
        unit = ts[index:]
        if value:
            value = int(value)
        return value, unit
    value, unit = extract_value_and_unit(time_string)
    if unit == 's':
        return value
    elif unit == 'min':
        return value * 60
    elif unit == 'hour':
        return value * 3600
    elif unit == 'day':
        return value * 86400
    elif unit == 'month':
        return value * 86400 * 30
    elif unit == 'year':
        return value * 86400 * 365
    else:
        return 0


async def check_ott_status(movie_title):
    import aiohttp
    import ssl
    import re
    from urllib.parse import quote
    from datetime import datetime
    from info import TMDB_API_KEY
    
    # Extract year if present, e.g. "Kantara (2022)" -> name="Kantara", year=2022
    year_match = re.search(r'\((19|20)\d{2}\)', movie_title)
    target_year = None
    if year_match:
        target_year = int(year_match.group(0)[1:-1])
        clean_name = re.sub(r'\s*\((19|20)\d{2}\)', '', movie_title).strip()
    else:
        clean_name = movie_title.strip()
    
    # Only attempt TMDb if the user provided their own API key
    keys_to_try = [TMDB_API_KEY] if TMDB_API_KEY else []
    
    for api_key in keys_to_try:
        if not api_key:
            continue
        url = f"https://api.themoviedb.org/3/search/multi?api_key={api_key}&query={quote(clean_name)}"
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, timeout=5) as response:
                    if response.status != 200:
                        continue
                    data = await response.json()
                    results = data.get("results")
                    if not results:
                        return await check_imdb_ott_status(movie_title, fallback_on_error_only=False)
                        
                    first = results[0]
                    if target_year:
                        for item in results:
                            item_year_str = item.get("release_date") or item.get("first_air_date")
                            if item_year_str and item_year_str.startswith(str(target_year)):
                                first = item
                                break
                                
                    media_type = first.get("media_type")
                    display_name = first.get("title") or first.get("name") or clean_name
                    
                    if media_type == "movie":
                        movie_id = first.get("id")
                        release_date_str = first.get("release_date")
                        if not release_date_str:
                            return "NOT_RELEASED", display_name
                            
                        try:
                            release_date = datetime.strptime(release_date_str, "%Y-%m-%d").date()
                        except ValueError:
                            return "RELEASED", display_name
                            
                        today = datetime.now().date()
                        if release_date > today:
                            return "NOT_RELEASED", display_name
                            
                        rd_url = f"https://api.themoviedb.org/3/movie/{movie_id}/release_dates?api_key={api_key}"
                        async with session.get(rd_url, timeout=5) as rd_resp:
                            if rd_resp.status == 200:
                                rd_data = await rd_resp.json()
                                rd_results = rd_data.get("results", [])
                                
                                has_digital = False
                                digital_date = None
                                theatrical_date = None
                                
                                for country_data in rd_results:
                                    for rd in country_data.get("release_dates", []):
                                        rd_type = rd.get("type")
                                        rd_date_str = rd.get("release_date")
                                        if not rd_date_str:
                                            continue
                                        try:
                                            parsed_date = datetime.strptime(rd_date_str[:10], "%Y-%m-%d").date()
                                        except ValueError:
                                            continue
                                            
                                        if rd_type == 4:
                                            has_digital = True
                                            if digital_date is None or parsed_date < digital_date:
                                                digital_date = parsed_date
                                        elif rd_type in [2, 3]:
                                            if theatrical_date is None or parsed_date < theatrical_date:
                                                theatrical_date = parsed_date
                                                
                                if has_digital and digital_date:
                                    if digital_date <= today:
                                        return "RELEASED", display_name
                                    else:
                                        return "NOT_RELEASED", display_name
                                        
                                theatrical_to_use = theatrical_date or release_date
                                if theatrical_to_use:
                                    days_diff = (today - theatrical_to_use).days
                                    if days_diff >= 60:
                                        return "RELEASED", display_name
                                    else:
                                        return "NOT_RELEASED", display_name
                                        
                        return "RELEASED", display_name
                        
                    elif media_type == "tv":
                        first_air_date_str = first.get("first_air_date")
                        if not first_air_date_str:
                            return "NOT_RELEASED", display_name
                        try:
                            first_air_date = datetime.strptime(first_air_date_str, "%Y-%m-%d").date()
                        except ValueError:
                            return "RELEASED", display_name
                        if first_air_date > datetime.now().date():
                            return "NOT_RELEASED", display_name
                        else:
                            return "RELEASED", display_name
                            
        except Exception as e:
            logger.error(f"Error checking OTT status on TMDB with key {api_key}: {e}")
        
    return await check_imdb_ott_status(movie_title, fallback_on_error_only=True)


async def check_imdb_ott_status(movie_title, fallback_on_error_only=True):
    from utils import imdb as cinemagoer
    import re
    from datetime import datetime
    
    # Extract year if present
    year_match = re.search(r'\((19|20)\d{2}\)', movie_title)
    target_year = None
    if year_match:
        target_year = int(year_match.group(0)[1:-1])
        clean_name = re.sub(r'\s*\((19|20)\d{2}\)', '', movie_title).strip()
    else:
        clean_name = movie_title.strip()
        
    def parse_imdb_date(date_str):
        if not date_str:
            return None
        # Remove country suffix in parentheses, e.g. "04 Jun 2026 (India)" -> "04 Jun 2026"
        date_str = re.sub(r'\(.*?\)', '', str(date_str)).strip()
        formats = [
            "%d %b %Y",    # "04 Jun 2026"
            "%d %B %Y",    # "04 June 2026"
            "%Y-%m-%d",    # "2026-06-04"
            "%b %d, %Y",   # "Jun 04, 2026"
            "%B %d, %Y",   # "June 04, 2026"
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        return None

    try:
        movies = await asyncio.wait_for(
            asyncio.to_thread(cinemagoer.search_movie, clean_name, results=5),
            timeout=10.0
        )
        if movies:
            first = movies[0]
            if target_year:
                for m in movies:
                    if m.get('year') == target_year:
                        first = m
                        break
            movie = await asyncio.wait_for(
                asyncio.to_thread(cinemagoer.get_movie, first.movieID),
                timeout=10.0
            )
            kind = movie.get('kind')
            display_name = movie.get('title') or clean_name
            
            # Check if we have a parsed date from 'original air date'
            air_date_str = movie.get('original air date')
            parsed_date = parse_imdb_date(air_date_str)
            
            if parsed_date:
                today = datetime.now().date()
                if parsed_date > today:
                    return "NOT_RELEASED", display_name
                elif kind == 'tv series':
                    return "RELEASED", display_name
                else:
                    # For movies, theatrical-to-OTT window (45 days)
                    days_diff = (today - parsed_date).days
                    if days_diff >= 45:
                        return "RELEASED", display_name
                    else:
                        return "NOT_RELEASED", display_name
            
            # Fallback to year check
            year = movie.get('year')
            if year:
                current_year = datetime.now().year
                if year > current_year:
                    return "NOT_RELEASED", display_name
                elif year < current_year:
                    return "RELEASED", display_name
                else:
                    # Current year without specific release date
                    return "NOT_RELEASED", display_name
            
            return "RELEASED", display_name
        else:
            # Fallback heuristic using the year in the query/title
            year_match = re.search(r'\b(19|20)\d{2}\b', movie_title)
            if year_match:
                year = int(year_match.group(0))
                current_year = datetime.now().year
                if year >= current_year:
                    return "NOT_RELEASED", clean_name
                else:
                    return "RELEASED", clean_name
            return "NOT_FOUND", clean_name
    except Exception as e:
        logger.error(f"IMDb fallback OTT check failed: {e}")
        # Fallback heuristic using the year in the query/title on exception
        year_match = re.search(r'\b(19|20)\d{2}\b', movie_title)
        if year_match:
            year = int(year_match.group(0))
            current_year = datetime.now().year
            if year >= current_year:
                return "NOT_RELEASED", clean_name
            else:
                return "RELEASED", clean_name
        return "NOT_FOUND", clean_name


async def get_web_suggestions(query_str):
    try:
        return await asyncio.wait_for(_get_web_suggestions_impl(query_str), timeout=12.0)
    except asyncio.TimeoutError:
        logger.error(f"get_web_suggestions timed out for query: {query_str}")
        return []
    except Exception as e:
        logger.error(f"get_web_suggestions failed: {e}")
        return []


async def _get_web_suggestions_impl(query_str):
    import aiohttp
    import ssl
    from urllib.parse import quote
    from info import TMDB_API_KEY
    
    clean_name = query_str.strip()
    suggestions = []
    
    # Helper: search OMDb by query string
    async def omdb_search(query, session):
        for omdb_key in ["trilogy", "b9bd48a6"]:
            try:
                url = f"https://www.omdbapi.com/?s={quote(query)}&apikey={omdb_key}"
                async with session.get(url, timeout=6) as response:
                    if response.status == 200:
                        data = await response.json(content_type=None)
                        if data.get("Response") == "True":
                            results = []
                            for item in data.get("Search", []):
                                title = item.get("Title")
                                year_raw = item.get("Year", "")
                                year = year_raw.split("\u2013")[0].split("-")[0].strip() if year_raw else ""
                                year_str = f" ({year})" if year and year.isdigit() else ""
                                if title:
                                    results.append(f"{title}{year_str}")
                            return results
            except Exception as e:
                logger.error(f"OMDb error key={omdb_key}: {e}")
        return []
    
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        
        # Tier 1: TMDb (user's own key - best fuzzy matching)
        if TMDB_API_KEY:
            try:
                url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_API_KEY}&query={quote(clean_name)}"
                async with session.get(url, timeout=6) as response:
                    if response.status == 200:
                        data = await response.json()
                        for item in data.get("results", []):
                            media_type = item.get("media_type")
                            if media_type in ["movie", "tv"]:
                                title = item.get("title") or item.get("name")
                                year = item.get("release_date") or item.get("first_air_date")
                                year_str = f" ({year[:4]})" if year else ""
                                if title:
                                    sug = f"{title}{year_str}"
                                    if sug not in suggestions:
                                        suggestions.append(sug)
                                    if len(suggestions) >= 4:
                                        break
            except Exception as e:
                logger.error(f"TMDb suggestions error: {e}")
        
        # Tier 2: OMDb direct search
        if len(suggestions) < 2:
            try:
                direct = await omdb_search(clean_name, session)
                for sug in direct:
                    if sug not in suggestions:
                        suggestions.append(sug)
                    if len(suggestions) >= 4:
                        break
            except Exception as e:
                logger.error(f"OMDb direct search error: {e}")
        # Tier 2.5: Google Autocomplete (handles new/unindexed releases like "Peddi" and "Karuppu 2026")
        if len(suggestions) < 2:
            try:
                def clean_google_suggestion(sug):
                    import re
                    sug_lower = sug.lower().strip()
                    year_match = re.search(r'\b(19|20)\d{2}\b', sug_lower)
                    year = year_match.group(0) if year_match else None
                    if year:
                        sug_lower = sug_lower.replace(year, "")
                    suffixes = [
                        "movie", "ott", "release date", "review", "tamil movie", "telugu movie", 
                        "hindi", "tamil", "telugu", "download", "collection", "box office", 
                        "hit or flop", "budget", "cast", "story", "songs", "teaser", "trailer", 
                        "wiki", "imdb", "rating", "watch online", "streaming", "online", "full",
                        "worldwide", "success", "rating", "kannada", "malayalam"
                    ]
                    suffixes.sort(key=len, reverse=True)
                    for suffix in suffixes:
                        sug_lower = re.sub(r'\b' + re.escape(suffix) + r'\b', '', sug_lower)
                    sug_clean = re.sub(r'\s+', ' ', sug_lower).strip()
                    if not sug_clean:
                        return None
                    title = sug_clean.title()
                    title = title.replace("()", "").replace("[]", "")
                    title = re.sub(r'\s+', ' ', title).strip()
                    if year:
                        return f"{title} ({year})"
                    return title

                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                google_url = f"https://suggestqueries.google.com/complete/search?client=chrome&q={quote(clean_name)}"
                async with session.get(google_url, headers=headers, timeout=6) as response:
                    if response.status == 200:
                        data = await response.json(content_type=None)
                        raw_sugs = data[1]
                        seen = {s.lower() for s in suggestions}
                        for rs in raw_sugs:
                            cs = clean_google_suggestion(rs)
                            if cs and cs.lower() not in seen:
                                seen.add(cs.lower())
                                suggestions.append(cs)
                            if len(suggestions) >= 4:
                                break
            except Exception as e:
                logger.error(f"Google Autocomplete suggestions error: {e}")

        # Tier 3: Datamuse spell-correction + OMDb (handles typos like "kanatara" -> "kantara")
        if len(suggestions) < 2:
            try:
                words = clean_name.lower().split()
                corrected_words = []
                any_corrected = False
                for word in words:
                    if len(word) > 3:
                        dm_url = f"https://api.datamuse.com/words?sp={quote(word)}&max=1"
                        async with session.get(dm_url, timeout=5) as dm_resp:
                            if dm_resp.status == 200:
                                dm_data = await dm_resp.json()
                                if dm_data and dm_data[0].get("word", "").lower() != word.lower():
                                    corrected_words.append(dm_data[0]["word"])
                                    any_corrected = True
                                else:
                                    corrected_words.append(word)
                            else:
                                corrected_words.append(word)
                    else:
                        corrected_words.append(word)
                
                if any_corrected:
                    corrected_query = " ".join(corrected_words)
                    logger.info(f"Spell-corrected: '{clean_name}' -> '{corrected_query}'")
                    corrected = await omdb_search(corrected_query, session)
                    for sug in corrected:
                        if sug not in suggestions:
                            suggestions.append(sug)
                        if len(suggestions) >= 4:
                            break
            except Exception as e:
                logger.error(f"Datamuse+OMDb error: {e}")
        
        # Tier 4: Cinemagoer / IMDb last resort
        if len(suggestions) < 2:
            try:
                movies = await asyncio.wait_for(
                    asyncio.to_thread(imdb.search_movie, clean_name, results=5),
                    timeout=8.0
                )
                if movies:
                    for m in movies:
                        title = m.get("title")
                        year = m.get("year")
                        year_str = f" ({year})" if year else ""
                        if title:
                            sug = f"{title}{year_str}"
                            if sug not in suggestions:
                                suggestions.append(sug)
                            if len(suggestions) >= 4:
                                break
            except Exception as e:
                logger.error(f"Cinemagoer suggestions error: {e}")
    
    return suggestions[:4]



