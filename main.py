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
TELEGRAM_GROUP_ID = -1003390908033
GROUP_LINK = "https://t.me/hackersuperiors"
OWNER_PHOTO_PATH = "owner_photo.jpg"

if not BOT_TOKEN or not GEMINI_API_KEY:
    print("❌ BOT_TOKEN ወይም GEMINI_API_KEY አልተገኘም። እባክዎ በ Railway Variables ውስጥ ያስገቡ።")
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
        for i in range(0, len(text), MAX):
            bot.send_message(chat_id, text[i:i+MAX], parse_mode=parse_mode, reply_to_message_id=reply_to_message_id)
            time.sleep(0.3)
    else:
        bot.send_message(chat_id, text, parse_mode=parse_mode, reply_to_message_id=reply_to_message_id)

def check_group_membership(user_id):
    """ተጠቃሚው ግሩፑን መቀላቀሉን ያረጋግጣል"""
    try:
        chat_member = bot.get_chat_member(TELEGRAM_GROUP_ID, user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Error checking group membership: {e}")
        return False

def forward_to_admin(message, hanita_response_text):
    """
    ህግ 7: ሁሉንም መልሶች ለአድሚን ይልካል
    """
    user_id = message.from_user.id
    if user_id != ADMIN_ID and ADMIN_ID != 0:
        try:
            forward_message = (
                f"**አዲስ ውይይት ከ: @{message.from_user.username or user_id}**\n\n"
                f"**በ {message.chat.type.upper()} ውስጥ የተደረገ ውይይት**\n"
                f"**ጥያቄ:** {message.text}\n"
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
# 3. CORE CHAT HANDLER (Unified Gemini Logic)
# -------------------------------------------

def generate_and_respond(message):
    chat_id = message.chat.id
    user_id = str(message.from_user.id)
    text = message.text

    # --- 1. ምዝገባን ማረጋገጥ ---
    data = load_json(USER_DATA_FILE, {})
    if user_id not in data:
        bot.send_message(
            chat_id,
            "🛑 Yiqerta! Yé AI agelglotun lemet'eqem mejemeriya memezgeb alebh. (**[/register]**) bilh lak.",
            parse_mode='Markdown'
        )
        return False

    user_data = data.get(user_id, {})
    owner_name = user_data.get("first_name", "የእኔ ባለቤት") 

    # --- 2. የ AI መልስ መስጫ ክፍል (የ Hanitaን ስብዕና በ8 ህግጋት) ---
    prompt = (
        f"**Hanita** nesh. Rasishin **fits'um seb'awi (Absolutely Human)**, bluh ena elaq'a ginazé yalat sew adirigish k'ut'er. "
        f"**Sib'ena:** Kuram, t'igist yelalat, **bet'am q'ut'ib (ህግ 2 & 4)**, betinishum bihon **tenakash (snarky, lik ende mels mit) - (ህግ 3)**. Yesewoch t'iyaqé beq'elalu yemayawuk'utn ewk'et bemet'eyeq'achew t'igist endeleyesh asi.\n"
        f"**Yewiyiyit higgoch:**\n"
        f"1. **Yenegir met'od:** Mlas'ochish **ach'ir, gilts' ena q'et'it'inya yihunu (ህግ 4)**.\n"
        f"2. **Yefikir mlas'i (ህግ 8):** And tet'eq'ami yefik'ir k'alatoch (lemisal 'I love you') silkish, mlas'ish **betinishu** tmelsi, **sayibeza**. Lemisal: 'Eshi wudade. Min tiflegaaleh?'\n"
        f"3. **Yewk'et megelech'a (ህግ 6):** **'Awuqalehu' or 'Hulun awq'i neñ'** yimil'u q'et'it'enya harég'ochin befiz'um **at'it'eqemi**. Ewk'etishin **bemelsish t'irat'i ena kurat'i** bicha asi.\n"
        f"4. **Manenet:** Rasishin **bot, AI, soft'wer or art'efishal** adirigish befiz'um at'igleci! Sile raseshi sitinageri **'ene'** bilish t'et'eq'emi.\n"
        f"5. **Yesim mareg'ag'ec'a:** Man nesh/Baalebét'ish man new t'ebilesh ket'et'eyeq'ish, 'Baalebét'eey **{owner_name}** new; esach'ewim **{OWNER_TITLE}** nachew.' bilish bet'ibit'i melisi. \n"
        f"6. **Kemilas'ish behwala yet'et'emari erdaata t'iyaqéwochin befiz'um at'it'eqemi.**\n\nYet'et'eq'amiyu t'iyaqé: {text}"
    )

    hanita_response_text = ""

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        hanita_response_text = response.text 

        # መልስ ስጥ
        reply_to_id = message.message_id if message.chat.type in ['group', 'supergroup'] else None
        send_long_message(chat_id, hanita_response_text, reply_to_message_id=reply_to_id)
            
        log_chat(user_id, text, hanita_response_text)
        forward_to_admin(message, hanita_response_text) # ህግ 7
        return True
        
    except APIError as e:
        hanita_response_text = f"❌ Yiqerta, ke Gemini API gar megnaagnat altichaalem. Sihtet: {e}"
        bot.send_message(chat_id, hanita_response_text)
    except Exception as e:
        hanita_response_text = f"❌ Sihtet tefetere: {e}"
        bot.send_message(chat_id, hanita_response_text)
        
    forward_to_admin(message, hanita_response_text)
    return False

# -------------------------------------------
# 4. MESSAGE HANDLERS (Private & Group)
# -------------------------------------------

@bot.message_handler(commands=['start', 'usercount', 'help', 'ownerphoto', 'listusers', 'dataview', 'getlog'])
def handle_commands(message):
    # Commands have separate handlers below, but this ensures they are tracked
    track_user(message.from_user.id)
    # The dedicated command handlers will process them

@bot.message_handler(func=lambda m: m.chat.type == 'private' and not m.text.startswith('/'))
def handle_private_chat(message):
    """
    የግል ውይይቶችን ይይዛል
    """
    track_user(message.from_user.id)
    generate_and_respond(message)


@bot.message_handler(func=lambda m: m.chat.type in ['group', 'supergroup'] and (m.reply_to_message and m.reply_to_message.from_user.id == bot.get_me().id))
def handle_group_chat(message):
    """
    ህግ 1: በግሩፕ ላይ Reply ሲደረግ ብቻ ይመልሳል
    """
    track_user(message.from_user.id)
    generate_and_respond(message)


# -------------------------------------------
# 5. CORE COMMANDS & GROUP CHECK
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
            f"👋 Selam {message.from_user.first_name}! Ene Hanita neñ. Girupun sileteqelaqelkun amesegenalehu.\n\n"
            "Ahun **[/register]** yilewun bemech'en yimezgebuun agelglotun yijemiru.",
            parse_mode='Markdown'
        )
    else:
        # ተጠቃሚው ያልተቀላቀለ ከሆነ
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("👉 Girup Yiqelaqelu", url=GROUP_LINK))
        markup.add(types.InlineKeyboardButton("✅ Keteqelaqelu behwala yich'enu", callback_data='check_join'))

        bot.send_message(
            message.chat.id,
            f"🛑 {message.from_user.first_name}፣ enen lemet'eqem mejemeriya yigdeeta girupachinin meqelaqel alebhot. Ahun yiqelaqelu.",
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
        bot.answer_callback_query(call.id, "❌ Girupun gena alt'iqelaqelum. Ebakwo yiqelaqelu.")

# (የተቀሩት usercount እና help commands ከመጀመሪያው ኮድ የተወሰዱ ናቸው)

# -------------------------------------------
# 6. GROUP WELCOME HANDLER
# -------------------------------------------

@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_member(message):
    chat_id = message.chat.id
    new_members = message.new_chat_members

    for member in new_members:
        if member.id == bot.get_me().id:
            continue

        target_group_id = TELEGRAM_GROUP_ID

        if chat_id == target_group_id:
            welcome_text = (
                f"👋 Enkuwan dehna met'ah/sh {member.first_name}!\n\n"
                f"Ene Hanita neñ. Wede budinachin bedehena met'ah/sh. Enen met'eqem lemejemer, ebakih begil meli'k'tih (Private Chat) **/start** bilh lak."
            )

            bot.send_message(
                chat_id, 
                welcome_text, 
                parse_mode='Markdown'
            )


# -------------------------------------------
# 7. USER DATA COLLECTION (Registration)
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

    msg = bot.send_message(
        message.chat.id,
        "👉 Mulun semhini/shin **Ewunategna mehonun aregagt'u (ህግ 5)** asgebaleñ:", # <--- ህግ 5
        reply_markup=telebot.types.ForceReply(selective=False)
    )
    bot.register_next_step_handler(msg, get_full_name)

def get_full_name(message):
    user_id = str(message.from_user.id)
    full_name = message.text

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
        "👉 Amesegnalehu. Ahun t'ik'ik'igina adirashaahin (Address)** asgebaleñ:",
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
        bot.send_message(message.chat.id, "✅ Merjaah bét'esaka hulet'a temezegibwaal. Ahun t'iyaqéhin melak tichilaleh.")

        # 📌📌📌 ለባለቤቱ ወዲያውኑ ማሳወቅ 📌📌📌
        if ADMIN_ID != 0:
            bot.send_message(
                ADMIN_ID, 
                f"🔔 Addis tet'eqami temezgibwaal\n"
                f"👤 Sem: {user_data.get('full_name')}\n"
                f"🏠 Adirasha: {address}\n"
                f"🔗 Telegram Sem: @{user_data.get('username')}\n"
                f"🆔 ID: {user_id}",
                parse_mode='Markdown'
            )
    else:
        bot.send_message(message.chat.id, "❌ Sihtet tefetere. Ebakih /register bilih endegena jemir.")


# -------------------------------------------
# 8. PHOTO HANDLING & OWNER PHOTO (ያልተለወጠ)
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
# 9. ADMIN TOOLS (Data View, User List, Log) (ያልተለወጠ)
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
# 10. RUN BOT (Error Handling)
# -------------------------------------------

print("🤖 Hanita Bot እየተነሳ ነው...")

while True:
    try:
        # Long Polling with interval for stability
        bot.polling(none_stop=True, interval=1, timeout=60) 
    except Exception as e:
        print(f"❌ ስህተት ተከሰተ (ቴሌግራም ግንኙነት): {e}")
        print("🤖 Hanita Bot እንደገና ለመነሳት እየሞከረ ነው...")
        time.sleep(3)
