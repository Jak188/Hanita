# -------------------------------------------
# HANITA BOT — የመጨረሻ የ Railway ማስኬጃ ስሪት (ሁሉንም 9 መመሪያዎች ያካተተ)
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

try:
    ADMIN_ID = int(os.environ.get("ADMIN_ID", "0")) 
except ValueError:
    ADMIN_ID = 0

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
# 2. UTILITY & FILE HANDLERS
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

def send_long_message(chat_id, text, parse_mode='Markdown'):
    MAX = 4096
    if len(text) > MAX:
        for i in range(0, len(text), MAX):
            bot.send_message(chat_id, text[i:i+MAX], parse_mode=parse_mode)
            time.sleep(0.3)
    else:
        bot.send_message(chat_id, text, parse_mode=parse_mode)

def check_group_membership(user_id):
    """ተጠቃሚው ግሩፑን መቀላቀሉን ያረጋግጣል"""
    try:
        # **TELEGRAM_GROUP_ID ትክክለኛ መሆኑን ያረጋግጡ**
        chat_member = bot.get_chat_member(TELEGRAM_GROUP_ID, user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Error checking group membership: {e}")
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
            f"👋 Selam {message.from_user.first_name}! (5)\n\n"
            "Ene Hanita neñ. Girupun siletiqelaqelku eshi amesegnalehu.\n\n"
            "Ahun **/register** yilewun bemech'en yimezgebuun agelglotun yijemiru.",
            parse_mode='Markdown'
        )
    else:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("👉 Girup yiqelaqelu", url=GROUP_LINK))
        markup.add(types.InlineKeyboardButton("✅ ket'iqelaqelu behwala yich'enu", callback_data='check_join'))

        bot.send_message(
            message.chat.id,
            f"🛑 {message.from_user.first_name}፣ enen lemet'eqem mejemeriya yiged'eeta girupach'inin t'iqelaqelu. (1)",
            reply_markup=markup,
            parse_mode='Markdown'
        )

@bot.callback_query_handler(func=lambda call: call.data == 'check_join')
def callback_check_join(call):
    if check_group_membership(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        
        class MockMessage:
            def __init__(self, chat_id, user_id, first_name):
                self.chat = types.Chat(chat_id, 'private')
                self.from_user = types.User(user_id, is_bot=False, first_name=first_name)
        
        mock_message = MockMessage(call.message.chat.id, call.from_user.id, call.from_user.first_name)
        start(mock_message)
    else:
        bot.answer_callback_query(call.id, "❌ Girupun gena alit'iqelaqelum. Ebakwo yiqelaqelu.")

# (የተቀሩት ትዕዛዞች/Commands እንደነበሩ ይቆያሉ...)
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

    msg = bot.send_message(
        message.chat.id,
        "👉 Mulun semhini/shin **Ewunategna mehonun aregagt'u** asgebaleñ:", # (5) ስሙ ትክክለኛ መሆኑን ማረጋገጫ
        reply_markup=telebot.types.ForceReply(selective=False)
    )
    bot.register_next_step_handler(msg, get_full_name)

# ... (get_full_name እና get_address ተግባራት እንደነበሩ ይቆያሉ)

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
# 5. PHOTO HANDLING & OWNER PHOTO (ያልተቀየረ)
# -------------------------------------------

# ... (handle_photo እና send_owner_photo ተግባራት እንደነበሩ ይቆያሉ)


# -------------------------------------------
# 7. GEMINI AUTO CHAT & ADMIN FORWARDING (የተስተካከለ)
# -------------------------------------------

@bot.message_handler(func=lambda m: True)
def gemini_auto(message):
    track_user(message.from_user.id)

    chat_id = message.chat.id
    user_id = str(message.from_user.id)
    text = message.text

    # Command ከሆነ መዝለል
    if text.startswith("/"):
        return

    # --- 1. የመልዕክት አያያዝ ህግ (1) ---
    # በግሩፕ ውስጥ ከሆነ፣ Reply ካልተደረገላት በቀር ዝለል
    if message.chat.type in ['group', 'supergroup'] and (message.reply_to_message is None or message.reply_to_message.from_user.id != bot.get_me().id):
        return

    # --- 2. ምዝገባን ማረጋገጥ ---
    data = load_json(USER_DATA_FILE, {})
    if user_id not in data:
        # በግሩፕ ውስጥም ቢሆን መልስ መስጠት የለባትም
        if message.chat.type in ['group', 'supergroup']:
            # በግሩፕ ውስጥ ምላሽ የሚሰጠው ለራሷ reply ሲደረግ ብቻ ነው
            if message.reply_to_message and message.reply_to_message.from_user.id == bot.get_me().id:
                 bot.reply_to(
                    message,
                    "🛑 Yiqerta! Yé AI agelglotun lemet'eqem mejemeriya yimezgebu. Please **[/register]** bilh lak. (2)",
                    parse_mode='Markdown'
                 )
            return
        else: # Private Chat ከሆነ
            bot.send_message(
                chat_id,
                "🛑 Yiqerta! Yé AI agelglotun lemet'eqem mejemeriya yimezgebu. Please **[/register]** bilh lak. (3)",
                parse_mode='Markdown'
            )
            return

    user_data = data.get(user_id, {})
    owner_name = user_data.get("first_name", "የእኔ ባለቤት") 
    
    # --- 3. የ AI መልስ መስጫ ክፍል (የ Hanitaን ስብዕና በ9 ህግጋት) ---
    prompt = (
        f"**Hanita** nesh. Rasishin **fits'um seb'awi (Absolutely Human)**, t'inish tesadab (snarky), kuram ena bluh ena elaq'a ginazé yalat sew adirigish k'ut'er. (3)\n"
        f"**Sib'ena:** Kuram, t'inish tesadab, bet'am k'ut'ib, ena bet'emelekete t'iyaqé t'ik'ik'enya. (2, 4)\n"
        f"**Yewiyiyit higgoch (9/9):**\n"
        f"1. **Manenet:** Rasishin **bot, AI, soft'wer or art'efishal** adirigish befiz'um at'igleci! Sile rasis'h sit'inaageri **'ene'** yil'ewun tit'eq'emi. (2, 4)\n"
        f"2. **T'ik'ik'inya yihun:** Mlas'ochish **ach'ir, gilts' ena q'et'it'inya yihunu** (4).\n"
        f"3. **Yewk'et megelech'a:** 'Awuqalehu', 'Hulun awq'i neñ' or 'ewk'et yehonyu' yimil'u q'et'it'enya harég'ochin befiz'um at'it'eqemi. (7)\n"
        f"4. **Yeq'anq'a dibluq:** Andande bicha yamariñña k'alat'ochin **be'ingliziñña fidél (Latin script)** ch'emirish melisi (lemisal: 'Min tiflegaaleh? Ewunategna new?'). T'inish bicha yihun. (6)\n"
        f"5. **Yefikir mlas'i (9):** And tet'eq'ami yefik'ir k'alatoch silkish, mlas'ish betnishu 'Eshi wudade' or 'Be'esha, yihun' yil'eewn yiwk'it'. Sayibeza k'ut'ib tihun. (9)\n"
        f"6. **Yesim mareg'ag'ec'a:** Maniyawum tet'eq'ami sile simwa (Hanita) or baalebét'wa (Owner) bet'emelekete t'iyaqé sit'eyiq', 'Yemtit'erawi/Yemtit'eyiq'ew sim t'ik'ik'il mehonun ergit'eñña nehi?' yimil t'iyaqé bemlas'ish wust akat'ichi. (5)\n"
        f"7. **Baalebét'eey:** Man nesh/Baalebét'ish man new t'ebilesh ket'et'eyeq'ish, 'Baalebét'eey **{owner_name}** new; esach'ewim **{OWNER_TITLE}** nachew.' bilish bet'ibit'i melisi. "
        f"**Kemilas'ish behwala yet'et'emari erdaata t'iyaqéwochin befiz'um at'it'eqemi.**\n\nYet'et'eq'amiyu t'iyaqé: {text}"
    )

    hanita_response_text = ""

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        hanita_response_text = response.text 

        send_long_message(chat_id, hanita_response_text)
        log_chat(user_id, text, hanita_response_text)

    except APIError as e:
        hanita_response_text = f"❌ Yiqerta, ke Gemini API gar megnaagnat altichaalem. Sihtet: {e}"
        bot.send_message(chat_id, hanita_response_text)
    except Exception as e:
        hanita_response_text = f"❌ Sihtet tefetere: {e}"
        bot.send_message(chat_id, hanita_response_text)
        
    # --- 4. መልዕክቱን ወደ Admin መላክ (8) ---
    if user_id != str(ADMIN_ID) and ADMIN_ID != 0:
        try:
            forward_message = (
                f"**አዲስ ውይይት ከ: @{message.from_user.username or user_id}**\n\n"
                f"**በ {message.chat.type.upper()} ውስጥ የተደረገ ውይይት**\n"
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
