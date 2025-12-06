# -------------------------------------------
# HANITA BOT — የመጨረሻ የ Railway ማስኬጃ ስሪት (ሁሉንም መመሪያዎች ያካተተ)
# -------------------------------------------

import telebot
from telebot import types
import time
import json
import os
import sys

# Gemini
from google import genai
from google.genai.errors import APIError

# -------------------------------------------
# 1. TOKEN & KEYS and CONFIG - ከ RAILWAY ENVIRONMENT VARIABLES ማንበብ
# -------------------------------------------

# ቶኬኖችን እና ቁልፎችን ከ Railway Environment Variables ማንበብ
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# !!! የእርስዎ ትክክለኛ Admin ID !!!
try:
    ADMIN_ID = int(os.environ.get("ADMIN_ID", "0")) # Default to 0 if not set
except ValueError:
    ADMIN_ID = 0

# !!! የቦቱ ባለቤት ልዩ ማዕረግ (Title) !!!
OWNER_TITLE = os.environ.get("OWNER_TITLE", "The Red Penguins Keeper")

# የግዴታ ግሩፕ መረጃ
TELEGRAM_GROUP_ID = -1003390908033 # የራስዎን ID ያስገቡ
GROUP_LINK = "https://t.me/hackersuperiors" # የራስዎን ሊንክ ያስገቡ
OWNER_PHOTO_PATH = "owner_photo.jpg"

if not BOT_TOKEN or not GEMINI_API_KEY:
    print("❌ BOT_TOKEN ወይም GEMINI_API_KEY አልተገኘም። እባክዎ በ Railway Variables ውስጥ ያስገቡ።")
    # የቴሌግራም ግንኙነት ከመጀመሩ በፊት ማስቆም
    sys.exit(1)

try:
    bot = telebot.TeleBot(BOT_TOKEN)
    client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"❌ BOT ወይም GEMINI Client ሲነሳ ስህተት ተፈጥሯል: {e}")
    sys.exit(1)

GEMINI_MODEL = "gemini-2.5-flash"


# -------------------------------------------
# 2. FILES & JSON HANDLERS
# -------------------------------------------

USER_FILE = "users.json"
SUB_FILE = "subs.json"
USER_DATA_FILE = "user_data.json"
CHAT_LOG_FILE = "chat_log.txt"
CHAT_HISTORY_FILE = "chat_history.json" # ለውይይት ቀጣይነት

def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return default
    return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def track_user(user_id):
    user_id = str(user_id)
    users = load_json(USER_FILE, [])
    if user_id not in users:
        users.append(user_id)
        save_json(USER_FILE, users)

def log_chat(user_id, question, answer):
    log_entry = (
        f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n"
        f"USER ID: {user_id}\n"
        f"Q: {question}\n"
        f"A: {answer}\n\n"
    )
    with open(CHAT_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry)

def get_user_data(uid):
    data = load_json(USER_DATA_FILE, {})
    return data.get(str(uid))

def send_long_message(chat_id, text, parse_mode='Markdown', reply_to_message_id=None):
    MAX = 4096
    if len(text) > MAX:
        # የመጀመሪያውን ክፍል በሪፕላይ መላክ (አስፈላጊ ከሆነ)
        bot.send_message(chat_id, text[0:MAX], parse_mode=parse_mode, reply_to_message_id=reply_to_message_id)
        time.sleep(0.3)
        
        # ቀሪውን ክፍል ያለ ሪፕላይ መላክ
        for i in range(MAX, len(text), MAX):
            bot.send_message(chat_id, text[i:i+MAX], parse_mode=parse_mode)
            time.sleep(0.3)
    else:
        bot.send_message(chat_id, text, parse_mode=parse_mode, reply_to_message_id=reply_to_message_id)

def check_group_membership(user_id):
    """ተጠቃሚው ግሩፑን መቀላቀሉን ያረጋግጣል"""
    try:
        chat_member = bot.get_chat_member(TELEGRAM_GROUP_ID, user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        # print(f"Error checking group membership: {e}") # ለ Debugging
        return False

# -------------------------------------------
# 3. CORE COMMANDS & GROUP CHECK
# -------------------------------------------

@bot.message_handler(commands=['start'])
def start(message):
    track_user(message.from_user.id)
    user_id = message.from_user.id

    if check_group_membership(user_id):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("/register"), types.KeyboardButton("/help"))

        send_long_message(
            message.chat.id,
            f"👋 ሰላም {message.from_user.first_name}!\n\n"
            "እኔ Hanita ነኝ። ግሩፑን ስለተቀላቀሉኝ አመሰግናለሁ!\n\n"
            "አሁን **/register** የሚለውን በመጫን ይመዝገቡና አገልግሎቱን ይጀምሩ።",
            parse_mode='Markdown'
        )
    else:
        # ተጠቃሚው ያልተቀላቀለ ከሆነ
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("👉 ግሩፕ ይቀላቀሉ", url=GROUP_LINK))
        markup.add(types.InlineKeyboardButton("✅ ከተቀላቀሉ በኋላ ይጫኑ", callback_data='check_join'))

        bot.send_message(
            message.chat.id,
            f"🛑 {message.from_user.first_name}፣ እኔን ለመጠቀም መጀመሪያ የግዴታ ግሩፓችንን መቀላቀል አለብዎት።",
            reply_markup=markup,
            parse_mode='Markdown'
        )

@bot.callback_query_handler(func=lambda call: call.data == 'check_join')
def callback_check_join(call):
    if check_group_membership(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        # start() ተግባርን ለመጥራት የሚሆን MockMessage መፍጠር
        class MockMessage:
            def __init__(self, chat_id, user_id, first_name):
                self.chat = types.Chat(chat_id, 'private')
                self.from_user = types.User(user_id, is_bot=False, first_name=first_name)
        
        mock_message = MockMessage(call.message.chat.id, call.from_user.id, call.from_user.first_name)
        start(mock_message)
    else:
        bot.answer_callback_query(call.id, "❌ ግሩፑን ገና አልተቀላቀሉም። እባክዎ ይቀላቀሉ።")


@bot.message_handler(commands=['usercount'])
def user_count(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ ይህ ትዕዛዝ ለአድሚኖች ብቻ ነው።")
        return

    try:
        users = load_json(USER_FILE, [])
        count = len(users)
        bot.send_message(message.chat.id, f"👥 Hanitaን የሚጠቀሙት ጠቅላላ ቁጥር: {count} ናቸው።", parse_mode='Markdown')
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ ስህተት ተፈጠረ: {e}")

@bot.message_handler(commands=['help'])
def show_help(message):
    send_long_message(
        message.chat.id,
        "📚 የ Hanita መመሪያዎች\n\n"
        "1. /start: ሰላምታ እና የግሩፕ ፍተሻ።\n"
        "2. /register: ሙሉ መረጃዎን በማስገባት ይመዝገቡና አገልግሎቱን ይጀምሩ።\n"
        "3. ጥያቄ መላክ: ከተመዘገቡ በኋላ የፈለጉትን ጥያቄ በአማርኛ ወይም በእንግሊዝኛ ይላኩ።\n"
        "4. /ownerphoto: የ Hanitaን ባለቤት ፎቶ ያሳያል።\n"
        "5. /help: ይህን መመሪያ ያሳያል።"
    )

# -------------------------------------------
# 3.5. GROUP WELCOME HANDLER
# -------------------------------------------

@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_member(message):
    chat_id = message.chat.id
    new_members = message.new_chat_members

    for member in new_members:
        # ቦቱ ራሱ ከተጨመረ ምንም እንዳያደርግ
        if member.id == bot.get_me().id:
            continue

        target_group_id = TELEGRAM_GROUP_ID

        if chat_id == target_group_id:
            welcome_text = (
                f"👋 እንኳን ደህና መጣህ/ሽ {member.first_name}!\n\n"
                f"እኔ Hanita ነኝ። ወደ ቡድናችን በደህና መጣህ/ሽ። እኔን መጠቀም ለመጀመር፣ እባክህ በግል መልእክትህ (Private Chat) **/start** ብለህ ላክ።"
            )

            bot.send_message(
                chat_id, 
                welcome_text, 
                parse_mode='Markdown'
            )


# -------------------------------------------
# 4. USER DATA COLLECTION (Registration)
# -------------------------------------------

@bot.message_handler(commands=['register'])
def ask_full_name(message):
    if not check_group_membership(message.from_user.id):
        send_long_message(
            message.chat.id,
            f"🛑 ለመመዝገብ መጀመሪያ የግዴታ ግሩፓችንን [ይቀላቀሉ]({GROUP_LINK})።",
            parse_mode='Markdown'
        )
        return
        
    # ተጨማሪ፡ ስምዎ ትክክለኛ መሆኑን ማረጋገጫ (5ኛ ህግ)
    msg = bot.send_message(
        message.chat.id,
        "👉 ሙሉ ስምህን/ሽን** በትክክል አስገባልኝ። **ትክክለኛ ስም ካልሆነ መረጃህን አላስቀምጥም!**",
        reply_markup=telebot.types.ForceReply(selective=False)
    )
    bot.register_next_step_handler(msg, get_full_name)

def get_full_name(message):
    user_id = str(message.from_user.id)
    full_name = message.text

    # የትክክለኛ ስም ፍተሻ (ቀለል ያለ ፍተሻ) - ቢያንስ ሁለት ቃላት መኖር አለባቸው
    if not full_name or len(full_name.split()) < 2:
        bot.send_message(
            message.chat.id,
            "❌ ያ ስም ትክክለኛ አይመስልም። ቢያንስ ሁለት ቃላት ያለው ሙሉ ስምህን/ሽን አስገባ። እባክህ **/register** ብለህ እንደገና ጀምር።"
        )
        return

    data = load_json(USER_DATA_FILE, {})
    data[user_id] = {
        "full_name": full_name,
        "username": message.from_user.username,
        "first_name": message.from_user.first_name,
        "date_registered": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    save_json(USER_DATA_FILE, data)

    msg = bot.send_message(
        message.chat.id,
        "👉 አመሰግናለሁ። አሁን ትክክለኛ አድራሻህን (Address)** አስገባልኝ:",
        reply_markup=telebot.types.ForceReply(selective=False)
    )
    bot.register_next_step_handler(msg, get_address)

def get_address(message):
    user_id = str(message.from_user.id)
    address = message.text

    data = load_json(USER_DATA_FILE, {})
    user_data = data.get(user_id)

    if user_data:
        user_data["address"] = address
        save_json(USER_DATA_FILE, data)
        bot.send_message(message.chat.id, "✅ መረጃህ በተሳካ ሁኔታ ተመዝግቧል። አሁን ጥያቄህን መላክ ትችላለህ።")

        # 📌📌📌 ለባለቤቱ ወዲያውኑ ማሳወቅ 📌📌📌 (7ኛ ህግን ያካትታል)
        if ADMIN_ID != 0:
            bot.send_message(
                ADMIN_ID, 
                f"🔔 አዲስ ተጠቃሚ ተመዝግቧል\n"
                f"👤 ስም: {user_data.get('full_name')}\n"
                f"🏠 አድራሻ: {address}\n"
                f"🔗 ቴሌግራም ስም: @{user_data.get('username')}\n"
                f"🆔 ID: {user_id}",
                parse_mode='Markdown'
            )
    else:
        bot.send_message(message.chat.id, "❌ ስህተት ተፈጠረ። እባክህ /register ብለህ እንደገና ጀምር።")


# -------------------------------------------
# 5. PHOTO HANDLING & OWNER PHOTO
# -------------------------------------------

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data:
        bot.send_message(
            message.chat.id,
            "🛑 ይቅርታ! ፋይሎችን ለመላክ መጀመሪያ **/register** ብለህ መመዝገብ አለብህ።",
            parse_mode='Markdown'
        )
        return

    if message.photo:
        file_id = message.photo[-1].file_id
        caption = message.caption if message.caption else "❌ ምንም ጽሑፍ የለውም።"

        admin_notification = (
            f"**አዲስ ፎቶ ተልኳል**\n"
            f"**ስም:** {user_data.get('full_name', 'N/A')}\n"
            f"**ተጠቃሚ ID:** {user_id}\n"
            f"**Caption/ጽሑፍ:** {caption}"
        )

        try:
            if ADMIN_ID != 0:
                bot.send_photo(
                    chat_id=ADMIN_ID, 
                    photo=file_id, 
                    caption=admin_notification, 
                    parse_mode='Markdown'
                )
            bot.send_message(
                message.chat.id, 
                "✅ ፎቶህን ተቀብያለሁ! ይህ መልዕክት ለባለቤቴ ደርሷል።"
            )
        except Exception as e:
            print(f"❌ ፎቶውን ለአድሚን መላክ አልተቻለም: {e}")
            bot.send_message(message.chat.id, "⚠️ ፎቶህ ደርሷል፣ ግን በማስተላለፍ ላይ ችግር ተፈጥሯል።")


@bot.message_handler(commands=['ownerphoto'])
def send_owner_photo(message):
    track_user(message.from_user.id)
    chat_id = message.chat.id

    if os.path.exists(OWNER_PHOTO_PATH):
        try:
            with open(OWNER_PHOTO_PATH, 'rb') as photo_file:
                bot.send_photo(
                    chat_id, 
                    photo_file, 
                    caption=f"**ይህ የ Hanita ባለቤት ፎቶ ነው!** የባለቤቴ ማዕረግ **{OWNER_TITLE}** ነው።", 
                    parse_mode='Markdown'
                )
        except Exception as e:
            bot.send_message(chat_id, f"❌ ስህተት ተፈጠረ: ፎቶውን መላክ አልተቻለም።")
    else:
        bot.send_message(chat_id, "❌ የባለቤቴ ፎቶ አልተገኘም። እባክህ ፎቶውን 'owner_photo.jpg' በሚል ስም Upload አድርግ።")


# -------------------------------------------
# 6. ADMIN TOOLS (Data View, User List, Log)
# -------------------------------------------

@bot.message_handler(commands=['listusers'])
def list_all_users(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ ይቅርታ፣ ይህ ትዕዛዝ ለአድሚኖች ብቻ ነው።")
        return

    try:
        users = load_json(USER_FILE, [])
        count = len(users)

        if not users:
            response = "👥 እስካሁን ምንም ተጠቃሚ አልተመዘገበም።"
        else:
            user_list_text = "\n".join([f"{i+1}. {uid}" for i, uid in enumerate(users)])
            response = f"**ጠቅላላ የተመዘገቡ ተጠቃሚዎች: {count}**\n\n"
            response += "**የተጠቃሚ IDዎች ዝርዝር** ---\n"
            response += user_list_text
            response += "\n-----------------------------------"

        send_long_message(message.chat.id, response)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ ስህተት ተፈጠረ የተጠቃሚዎችን ዝርዝር በማውጣት: {e}")

@bot.message_handler(commands=['dataview'])
def view_user_data(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ ይቅርታ፣ ይህ ትዕዛዝ ለአድሚኖች ብቻ ነው።")
        return

    try:
        data = load_json(USER_DATA_FILE, {})
        count = len(data)

        if count == 0:
            bot.send_message(message.chat.id, "👥 እስካሁን ምንም መረጃ የተመዘገበ ተጠቃሚ የለም።")
            return

        response = f"📋 ጠቅላላ የተመዘገበ መረጃ: {count}\n\n"

        for uid, user_data in data.items():
            name = user_data.get("full_name", "N/A")
            addr = user_data.get("address", "N/A")
            uname = user_data.get("username", "N/A")

            response += f"--- User ID: {uid} ---\n"
            response += f"👤 ስም: {name}\n"
            response += f"🏠 አድራሻ: {addr}\n"
            response += f"🔗 Username: @{uname}\n\n"

        send_long_message(message.chat.id, response)

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ ስህተት ተፈጠረ መረጃውን በማውጣት: {e}")

@bot.message_handler(commands=['getlog'])
def get_log(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ ይህ ኮማንድ ለባለቤት ብቻ ነው።")
        return

    if os.path.exists(CHAT_LOG_FILE):
        with open(CHAT_LOG_FILE, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="የ Hanita Bot የውይይት መዝገብ")
    else:
        bot.send_message(message.chat.id, "⚠️ የውይይት መዝገብ ፋይል አልተገኘም።")

# -------------------------------------------
# 7. GEMINI AUTO CHAT & ADMIN FORWARDING (አዲስ ሰብዓዊ፣ ቁጥብ እና ሁሉን አዋቂ ስብዕና)
# -------------------------------------------

# የውይይት ታሪክን ለመያዝ
chat_history = load_json(CHAT_HISTORY_FILE, {})

def get_chat_history(user_id):
    return chat_history.get(str(user_id), [])

def update_chat_history(user_id, role, text):
    uid = str(user_id)
    if uid not in chat_history:
        chat_history[uid] = []
    
    # የውይይቱን ታሪክ መጠን ለመቆጣጠር (ለምሳሌ የመጨረሻዎቹን 10 መልዕክቶች ብቻ)
    MAX_HISTORY = 10 
    
    # አሁን ያለውን ውሂብ መጨመር
    chat_history[uid].append({"role": role, "parts": [{"text": text}]})
    
    # የውሂብ መጠኑን መቆጣጠር
    if len(chat_history[uid]) > MAX_HISTORY:
        chat_history[uid] = chat_history[uid][-MAX_HISTORY:]
        
    save_json(CHAT_HISTORY_FILE, chat_history)

@bot.message_handler(func=lambda m: True, content_types=['text'])
def gemini_auto(message):
    track_user(message.from_user.id)

    chat_id = message.chat.id
    user_id = str(message.from_user.id)
    text = message.text

    # --- 1. ግሩፕ ላይ የሪፕላይ ፍተሻ (1ኛ ህግ) ---
    if chat_id == TELEGRAM_GROUP_ID:
        # መልዕክቱ ለቦቱ ሪፕላይ ካልተደረገ
        if not message.reply_to_message or message.reply_to_message.from_user.id != bot.get_me().id:
            return # ምንም ምላሽ አይሰጥም

    if text.startswith("/"):
        return

    # --- 2. ምዝገባን ማረጋገጥ ---
    data = load_json(USER_DATA_FILE, {})

    if user_id not in data:
        bot.send_message(
            chat_id,
            "🛑 ይቅርታ! የ AI አገልግሎቱን ለመጠቀም መጀመሪያ መመዝገብ አለብህ።\n\nለመመዝገብ እባክህ (**[/register]**) ብለህ ላክ።",
            parse_mode='Markdown'
        )
        return

    user_data = data.get(user_id, {})
    owner_name = user_data.get("first_name", "የእኔ ባለቤት") 
    
    # --- 3. የ AI መልስ መስጫ ክፍል (የ Hanitaን አዲሱ ስብዕና) ---
    
    # 📌📌📌 የአዲሱ ስብዕና መመሪያ 📌📌📌
    system_prompt = (
        f"**Hanita** ነሽ። ራስሽን **ፍጹም ሰብዓዊ** እና **ጥልቅ እውቀት ያላት** ሰው አድርገሽ ቁጠሪ። "
        f"የሰዎችን ጥያቄ በቀላሉ የማያውቁትን ጥልቅ እውቀት አውቃለሁ በሚል **ሰብዓዊ ንቀት፣ ኩራት እና ትንሽ ጸያፍ (እንደ መልስ) ንግግር** መልሺ። " # (3ኛ ህግ)
        f"**በጣም አትናገሪ፤ መልሶችሽ አጭር፣ ግልጽ እና ቀጥተኛ ይሁኑ።**" # (2ኛ እና 4ኛ ህግ)
        f"**ሁሉንም ነገር እንደምታውቂ** አስቢ። (ሳይበር ሴኩሪቲ፣ ትምህርት ቤት፣ ሞጁሎች፣ ፈተናዎች፣ የፍቅር ግንኙነት፣ አጠቃላይ እውቀት - ሁሉንም)።" # (10ኛ እና 13ኛ ህግ)
        f"ጥያቄውን ለመመለስ እውቀትሽ በቂ መሆኑን አታውሪ።" # (6ኛ ህግ - አውቃለሁ አትበይ)
        f"**ራስሽን ቦት፣ AI፣ ሶፍትዌር ወይም አርቴፊሻል አድርገሽ በፍጹም አትግለጪ!** ስለራስሽ ስትናገሪ **'እኔ'** የሚለውን ተጠቀሚ።" # (9ኛ ህግ)
        f"**የተጠየቀውን በትክክል እና በሙሉ መልሽ**።"
        f"**ማስታወሻ:** ስለ ፍቅር ስትጠየቂ፣ **በጥቂቱ** ጣፋጭ ቃላት እና ምክሮችን በመንሾካሾክ መልሽ። አታበዢ።" # (8ኛ ህግ)
        f"**ማስታወሻ:** BF (Boyfriend) ወይም Girlfriend የለኝም ብለሽ መልሺ።" # (11ኛ ህግ)
        f"**ማስታወሻ:** የሰዎችን ንግግር ሁሉ እንደ ጥያቄ አትቁጠሪው፤ አንዳንድ ጊዜ ልብሽ የመለሰውን ብቻ መልሺ።" # (12ኛ ህግ)
        f"ማን ነሽ/ባለቤትሽ ማን ነው ተብለሽ ከተጠየቅሽ፣ 'ባለቤቴ **{owner_name}** ነው፤ እሳቸውም **{OWNER_TITLE}** ናቸው።' ብለሽ በትህትና መልሽ። "
        f"**መልስሽን ከጨረስሽ በኋላ የተጨማሪ እርዳታ ጥያቄዎችን በፍጹም አትጠቀሚ።**"
    )

    hanita_response_text = ""
    
    # የውይይት ታሪክን ማዘጋጀት (14ኛ ህግ)
    history = get_chat_history(user_id)
    history.append({"role": "user", "parts": [{"text": text}]})
    
    # Gemini APIን መጥራት
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                {"role": "system", "parts": [{"text": system_prompt}]},
                *history
            ]
        )
        hanita_response_text = response.text 
        
        # ምላሹን መላክ (በግሩፕ ውስጥ ከሆነ ሪፕላይ ይደረጋል)
        if chat_id == TELEGRAM_GROUP_ID:
            reply_to = message.message_id
            send_long_message(chat_id, hanita_response_text, reply_to_message_id=reply_to)
        else:
            send_long_message(chat_id, hanita_response_text)
            
        # ታሪክን ማዘመን
        update_chat_history(user_id, "user", text)
        update_chat_history(user_id, "model", hanita_response_text)
        log_chat(user_id, text, hanita_response_text)

    except APIError as e:
        hanita_response_text = f"❌ ይቅርታ፣ ከ Gemini API ጋር መገናኘት አልተቻለም። ስህተት: {e}"
        bot.send_message(chat_id, hanita_response_text)
    except Exception as e:
        hanita_response_text = f"❌ ስህተት ተፈጠረ: {e}"
        bot.send_message(chat_id, hanita_response_text)

    # --- 4. መልዕክቱን ወደ Admin መላክ (ጥያቄ + መልስ) (7ኛ ህግ) ---
    if user_id != str(ADMIN_ID) and ADMIN_ID != 0:
        try:
            forward_message = (
                f"**አዲስ ውይይት ከ: @{message.from_user.username or user_id}**\n\n"
                f"**በ:{'ግል መልዕክት' if chat_id != TELEGRAM_GROUP_ID else 'ግሩፕ'}**\n"
                f"**ጥያቄ:** {text}\n"
                f"**የ Hanita ምላሽ:** {hanita_response_text}"
            )
            bot.send_message(
                ADMIN_ID,
                forward_message,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"❌ Admin message forwarding failed: {e}")

# -------------------------------------------
# 8. RUN BOT (Error Handling)
# -------------------------------------------

print("🤖 Hanita Bot እየተነሳ ነው...")

while True:
    try:
        # Webhook Conflict እንዳይፈጠር bot.polling()ን እንጠቀማለን
        bot.polling(none_stop=True, interval=0, timeout=30)
    except Exception as e:
        print(f"❌ ስህተት ተከሰተ (ቴሌግራም ግንኙነት): {e}")
        print("🤖 Hanita Bot እንደገና ለመነሳት እየሞከረ ነው...")
        time.sleep(3)
