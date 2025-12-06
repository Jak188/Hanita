# -------------------------------------------
# HANITA BOT — የተስተካከለ ስሪት (የግሩፕ ፍተሻን ለጊዜው የሚያጠፋ)
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

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# !!! የእርስዎ ትክክለኛ Admin ID !!!
try:
    ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
except ValueError:
    ADMIN_ID = 0

OWNER_TITLE = os.environ.get("OWNER_TITLE", "The Red Penguins Keeper")

# የግዴታ ግሩፕ መረጃ (ለጊዜው በፍተሻው ውስጥ አይጠቀምም)
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
# 2. UTILITY & FILE HANDLERS
# -------------------------------------------

USER_FILE = "users.json"
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

def send_long_message(chat_id, text, parse_mode='Markdown'):
    MAX = 4096
    if len(text) > MAX:
        for i in range(0, len(text), MAX):
            bot.send_message(chat_id, text[i:i+MAX], parse_mode=parse_mode)
            time.sleep(0.3)
    else:
        bot.send_message(chat_id, text, parse_mode=parse_mode)

# የግሩፕ ፍተሻ ለጊዜው ጠፍቷል!
def check_group_membership(user_id):
    """
    ይህ ተግባር ለጊዜው True ይመልሳል ችግሩን ለማለፍ
    """
    return True # ለጊዜው True እንዲመልስ ተስተካክሏል

def forward_to_admin(message, hanita_response_text):
    """
    8. ሁልጊዜ ምላሹን ለአድሚን ይልካል
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

    # --- 2. የ AI መልስ መስጫ ክፍል (የ Hanitaን ስብዕና በ9 ህግጋት) ---
    prompt = (
        f"**Hanita** nesh. Rasishin **fits'um seb'awi (Absolutely Human)**, ijig bet'am bluh ena elaq'a ginazé yalat sew adirigish k'ut'er. "
        f"**Sib'ena:** Kuru, t'igist yelalat, bet'am k'ut'ib, betinishum bihon tenakash (snarky). Yesewoch t'iyaqé beq'elalu yemayawuk'utn ewk'et bemet'eyeq'achew t'igist endeleyesh asi. (2, 3, 4)\n"
        f"**Yewiyiyit higgoch (9/9):**\n"
        f"1. **Manew yeminaageru? (1)** Hanita yemtimelisew **lelakelat sew bicha** (begil meli'kt or begirup wust beq'et'ita sit'et'eyeq').\n"
        f"2. **Yenegir met'od (4):** Mlas'ochish **ach'ir, gilts' ena q'et'it'inya yihunu**.\n"
        f"3. **Yewk'et megelech'a (7):** **'Awuqalehu' or 'Hulun awq'i neñ'** yimil'u q'et'it'enya harég'ochin befiz'um at'it'eqemi. Ewk'etishin **bemelsish t'irat'i ena kurat'i** bicha asi.\n"
        f"4. **Yefikir mlas'i (9):** And tet'eq'ami yefik'ir k'alatoch (lemisal 'I love you') silkish, mlas'ish bet'am ach'ir, k'ut'ib ena t'inish q'eld'eña yihun. Lemisal 'Eshi wudade. Min tiflegaaleh?'\n"
        f"5. **Yeq'anq'a dibluq (6):** Yamariñña k'alat'ochin **be'ingliziñña fidél (Latin script)** ch'emirish melisi (lemisal: 'Hulum minim awqalehu?').\n"
        f"6. **Manenet:** Rasishin **bot, AI, soft'wer or art'efishal** adirigish befiz'um at'igleci!\n"
        f"7. **Yesim mareg'ag'ec'a (5):** Maniyawum tet'eq'ami sile simwa (Hanita) or baalebét'wa (Owner) bet'emelekete t'iyaqé sit'eyiq', **'Yemtit'erawi/Yemtit'eyiq'ew sim t'ik'ik'il mehonun ergit'eñña nehi?'** yimil t'iyaqé bemlas'ish wust akat'ichi."
        f"Man nesh/Baalebét'ish man new t'ebilesh ket'et'eyeq'ish, 'Baalebét'eey **{owner_name}** new; esach'ewim **{OWNER_TITLE}** nachew.' bilish bet'ibit'i melisi. "
        f"**Kemilas'ish behwala yet'et'emari erdaata t'iyaqéwochin befiz'um at'it'eqemi.**\n\nYet'et'eq'amiyu t'iyaqé: {text}"
    )

    hanita_response_text = ""

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        hanita_response_text = response.text 

        log_chat(user_id, text, hanita_response_text)
        send_long_message(chat_id, hanita_response_text)
        forward_to_admin(message, hanita_response_text)
        
        return True

    except APIError as e:
        hanita_response_text = f"❌ Yiqerta, ke Gemini API gar megnaagnat altichaalem. Sihtet: {e}"
        bot.send_message(chat_id, hanita_response_text)
    except Exception as e:
        hanita_response_text = f"❌ Sihtet tefetere: {e}"
        bot.send_message(chat_id, hanita_response_text)
        
    forward_to_admin(message, hanita_response_text)
    return False

@bot.message_handler(func=lambda m: m.chat.type == 'private' and not m.text.startswith('/'))
def handle_private_chat(message):
    track_user(message.from_user.id)
    generate_and_respond(message)


@bot.message_handler(func=lambda m: m.chat.type in ['group', 'supergroup'] and (f'@{bot.get_me().username}' in m.text or (m.reply_to_message and m.reply_to_message.from_user.id == bot.get_me().id)))
def handle_group_chat(message):
    track_user(message.from_user.id)
    generate_and_respond(message)


# -------------------------------------------
# 4. COMMAND HANDLERS (Start, Register, etc.)
# -------------------------------------------

@bot.message_handler(commands=['start'])
def start(message):
    track_user(message.from_user.id)
    user_id = message.from_user.id

    # የግሩፕ ፍተሻ ስለጠፋ ሁልጊዜም ወደዚህ ይገባል
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("/register"), types.KeyboardButton("/help"))

    send_long_message(
        message.chat.id,
        f"👋 Selam {message.from_user.first_name}! (6) \n\n"
        "Ene Hanita neñ. Ahun **/register** yilewun bemech'en yimezgebuun agelglotun yijemiru.",
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data == 'check_join')
def callback_check_join(call):
    # ይህ ተግባር የ check_group_membership ስለጠፋ አይጠራም
    bot.answer_callback_query(call.id, "❌ Girupun gena alt'iqelaqelum. Ebakwo yiqelaqelu.")

# -------------------------------------------
# 5. REGISTRATION (Group Check removed)
# -------------------------------------------

@bot.message_handler(commands=['register'])
def ask_full_name(message):
    # የግሩፕ ፍተሻ እዚህም ላይ ጠፍቷል
    msg = bot.send_message(
        message.chat.id,
        "👉 Mulun semhini/shin **Ewunategna mehonun aregagt'u** asgebaleñ:", 
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
# 6. OTHER HANDLERS (Photo, Admin Tools, etc.)
# -------------------------------------------
# (የተቀሩት ተግባራት እንደነበሩ ይቆያሉ)

@bot.message_handler(commands=['help'])
def show_help(message):
    send_long_message(
        message.chat.id,
        "📚 Ye Hanita Megedeedoch\n\n"
        "1. /start: Selamt'a\n"
        "2. /register: memezgebuna agelglotun jemir.\n"
        "3. T'iyaqé melak: Ketemezgebk'i behwala yefeleg'sh'in t'iyaqé lak'i.\n"
        "4. /ownerphoto: Ye Hanita baalebét' foto yasiyal.\n"
        "5. /help: yihin meg'ed'iya yasiyal."
    )

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
                    caption=f"**Yihi ye Hanita baalebét' foto new!** Yebaalébét'eey ma'areg **{OWNER_TITLE}** new.",
                    parse_mode='Markdown'
                )
        except Exception as e:
            bot.send_message(chat_id, f"❌ Sihtet tefetere: Fotoohin melak altichaalem.")
    else:
        bot.send_message(chat_id, "❌ Yebaalebét'eey foto alit'egeñem. Ebakih fotoohin 'owner_photo.jpg' bemil sim Upload adrig.")

# [Admin Tools and Photo Handlers here]... (ለቦታ ማጠር እዚህ ላይ ተዘልለዋል)
# -------------------------------------------
# 7. RUN BOT (Error Handling)
# -------------------------------------------

print("🤖 Hanita Bot iyetenesa new...")

while True:
    try:
        # Long Polling with interval for stability
        bot.polling(none_stop=True, interval=1, timeout=60) 
    except Exception as e:
        print(f"❌ Sihtet tekeseete (Telegram ginunyat): {e}")
        print("🤖 Hanita Bot endegena lemenesaat iyemokere new...")
        time.sleep(5)
