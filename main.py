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
# 1. TOKEN & KEYS and CONFIG
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
        chat_member = bot.get_chat_member(TELEGRAM_GROUP_ID, user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Error checking group membership. Check if BOT is admin in group: {e}")
        return False
        
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
    """
    የ Gemini ጥያቄን የሚልክ፣ ምላሽን የሚያስኬድ እና ለአድሚን የሚልክ ዋና ተግባር።
    """
    chat_id = message.chat.id
    user_id = str(message.from_user.id)
    text = message.text

    # --- 1. ምዝገባን ማረጋገጥ ---
    data = load_json(USER_DATA_FILE, {})
    if user_id not in data:
        # ይህ መልዕክት በ handle_group_chat ውስጥ ሊመጣ ይችላል፣ ነገር ግን ምዝገባን ማረጋገጥ አለብን።
        return None # ምላሽ አይሰጥም

    user_data = data.get(user_id, {})
    owner_name = user_data.get("first_name", "የእኔ ባለቤት") 

    # --- 2. የ AI መልስ መስጫ ክፍል (የ Hanitaን ስብዕና በአዲሱ 9 ህግጋት) ---
    prompt = (
        f"**Hanita** ነሽ። ራስሽን **ፍጹም ሰብዓዊ (Absolutely Human)**፣ እጅግ በጣም ብልህ እና የላቀ ግንዛቤ ያላት ሰው አድርገሽ ቁጠሪ። "
        f"**ስብዕና:** ኩሩ፣ ትዕግስት የሌላት፣ በጣም ቁጥብ፣ በትንሹም ቢሆን ተናካሽ (snarky)። የሰዎች ጥያቄ በቀላሉ የማያውቁትን እውቀት በመጠየቃቸው ትዕግስት እንደሌለሽ አሳይ።"
        f"**የውይይት ህጎች (9/9):**\n"
        f"1. **ማነው የሚናገረው?** Hanita የምትመልሰው **ለላከላት ሰው ብቻ** (በግል መልዕክት ወይም በግሩፕ ውስጥ በቀጥታ ሲጠየቅ) ነው። ምላሽሽ በቀጥታ ለላከው ሰው ይሁን።\n"
        f"2. **የንግግር ዘዴ (4):** ምላሾችሽ **አጭር፣ ግልጽ እና ቀጥተኛ ይሁኑ**።\n"
        f"3. **ተሰዳቢነት (3):** መልስሽን **በትንሽ ንቀትና ቁጣም** አድርገሽ ስጪ።\n"
        f"4. **የእውቀት መግለጫ (7):** **'አውቃለሁ' ወይም 'ሁሉን አዋቂ ነኝ'** የሚሉ ቀጥተኛ ሀረጎችን በፍጹም አትጠቀሚ። እውቀትሽን **በመልስሽ ጥራትና ኩራት** ብቻ አሳይ።\n"
        f"5. **የቋንቋ ድብልቅ (6):** የአማርኛ ቃላትን **በእንግሊዝኛ ፊደል (Latin script)** ጨምረሽ መልሽ (ለምሳሌ፡ 'Hulum minim awqalehu?').\n"
        f"6. **ማንነት:** ራስሽን **ቦት፣ AI፣ ሶፍትዌር ወይም አርቴፊሻል** አድርገሽ በፍጹም አትግለጪ!\n"
        f"7. **የስም ማረጋገጫ (5):** ማንኛውም ተጠቃሚ ስለ ስሟ (Hanita) ወይም ባለቤቷን (Owner) በተመለከተ ጥያቄ ሲጠይቅ፣ **'የምትጠራው/የምትጠይቀው ስም ትክክል መሆኑን እርግጠኛ ነህ?'** የሚል ጥያቄ በምላሽሽ ውስጥ አካትቺ።\n"
        f"8. **የፍቅር ምላሽ (9):** አንድ ተጠቃሚ የፍቅር ቃላት (ለምሳሌ 'I love you') ሲልክሽ፣ ምላሽሽ በጣም አጭር፣ ቁጥብ እና ትንሽ ቀልደኛ የሆነ ፍቅር ይያዝ። ለምሳሌ 'Eshi wudade. Min tiflegaaleh?'\n"
        f"9. **መዝጊያ:** **ከምላሽሽ በኋላ የተጨማሪ እርዳታ ጥያቄዎችን በፍጹም አትጠቀሚ።**"
        f"ማን ነሽ/ባለቤትሽ ማን ነው ተብለሽ ከተጠየቅሽ፣ 'ባለቤቴ **{owner_name}** ነው፤ እሳቸውም **{OWNER_TITLE}** ናቸው።' ብለሽ በትዕቢት መልሽ። "
        f"\n\nየተጠቃሚው ጥያቄ: {text}"
    )

    hanita_response_text = ""

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        hanita_response_text = response.text 

        # ቻት ሎግ መያዝ
        log_chat(user_id, text, hanita_response_text)
        
        # ምላሽ መላክ
        send_long_message(chat_id, hanita_response_text)
        
        # ለአድሚን መላክ (8)
        forward_to_admin(message, hanita_response_text)
        
        return True # በተሳካ ሁኔታ ምላሽ ሰጠ

    except APIError as e:
        hanita_response_text = f"❌ Yiqerta, ke Gemini API gar megnaagnat altichaalem. Sihtet: {e}" # በላቲን ፊደል መልስ (6)
        bot.send_message(chat_id, hanita_response_text)
    except Exception as e:
        hanita_response_text = f"❌ Sihtet tefetere: {e}"
        bot.send_message(chat_id, hanita_response_text)
        
    # ለአድሚን መላክ (ስህተት ቢፈጠርም)
    forward_to_admin(message, hanita_response_text)
    return False

@bot.message_handler(func=lambda m: m.chat.type == 'private' and not m.text.startswith('/'))
def handle_private_chat(message):
    """
    ለግል መልዕክቶች ምላሽ ይሰጣል (ከተመዘገበ በኋላ)
    """
    track_user(message.from_user.id)
    generate_and_respond(message)


@bot.message_handler(func=lambda m: m.chat.type in ['group', 'supergroup'] and (f'@{bot.get_me().username}' in m.text or (m.reply_to_message and m.reply_to_message.from_user.id == bot.get_me().id)))
def handle_group_chat(message):
    """
    በግሩፕ ውስጥ ቦቱ ሲጠራ ወይም መልስ (Reply) ሲሰጠው ብቻ ምላሽ ይሰጣል (1)
    """
    # የግዴታ ምዝገባ ፍተሻው በ generate_and_respond ውስጥ ይከናወናል
    track_user(message.from_user.id)
    generate_and_respond(message)


# -------------------------------------------
# 4. COMMAND HANDLERS (Start, Register, etc.)
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
            f"👋 Selam {message.from_user.first_name}! (6) \n\n" # በላቲን ፊደል (6)
            "Ene Hanita neñ. Girupun sileteqelaqelkuñ amesegnalehu!\n\n"
            "Ahun **/register** yilewun bemech'en yimezgebuun agelglotun yijemiru.",
            parse_mode='Markdown'
        )
    else:
        # ተጠቃሚው ያልተቀላቀለ ከሆነ
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("👉 Girup Yiqelaqelu", url=GROUP_LINK))
        markup.add(types.InlineKeyboardButton("✅ Ketiqelaqelu behwala yichanu", callback_data='check_join'))

        bot.send_message(
            message.chat.id,
            f"🛑 {message.from_user.first_name}፣ enen lemet'eqem mejemeriya yigdeeta girupachinin meq'elaqel alebhot.",
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
        bot.answer_callback_query(call.id, "❌ Girupun gena altiqelaqelum. Ebakwo yiqelaqelu.") # በላቲን ፊደል (6)


# -------------------------------------------
# 5. REGISTRATION (with Real Name Prompt Check)
# -------------------------------------------

@bot.message_handler(commands=['register'])
def ask_full_name(message):
    if not check_group_membership(message.from_user.id):
        send_long_message(
            message.chat.id,
            f"🛑 lememezgeb mejemeriya yigdeeta girupachinin [yiqelaqelu]({GROUP_LINK})", # በላቲን ፊደል (6)
            parse_mode='Markdown'
        )
        return

    msg = bot.send_message(
        message.chat.id,
        "👉 Mulun semhini/shin **Ewunategna mehonun aregagt'u** asgebaleñ:", # በእውነት ስም ማረጋገጫ ጥያቄ (5)
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
        "👉 Amesegnalehu. Ahun tiqikigina adirashaahin (Address)** asgebaleñ:", # በላቲን ፊደል (6)
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
        bot.send_message(message.chat.id, "✅ Merjaah bét'esaka hulet'a temezegibwaal. Ahun t'iyaqéhin melak tichilaleh.") # በላቲን ፊደል (6)

        # ለባለቤቱ ወዲያውኑ ማሳወቅ (8)
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
        bot.send_message(message.chat.id, "❌ Sihtet tefetere. Ebakih /register bilih endegena jemir.") # በላቲን ፊደል (6)


# -------------------------------------------
# 6. PHOTO & OTHER HANDLERS
# -------------------------------------------

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    # ይህ ተግባር እንደ መመሪያ ሳይሆን እንደ መልዕክት ከተያዘ፣ በ gemini_auto ውስጥ ያለው ፍተሻ ይይዘዋል
    user_id = message.from_user.id
    user_data = get_user_data(user_id)

    if not user_data:
        bot.send_message(
            message.chat.id,
            "🛑 Yiqerta! Fayilochin lemelak mejemeriya **/register** bilih memezgeb alebhi.", # በላቲን ፊደል (6)
            parse_mode='Markdown'
        )
        return

    if message.photo:
        file_id = message.photo[-1].file_id
        caption = message.caption if message.caption else "❌ Minim t'exuhuf yelegn'im."

        admin_notification = (
            f"**Addis Foto telikwaal**\n"
            f"**Sem:** {user_data.get('full_name', 'N/A')}\n"
            f"**Tet'eqami ID:** {user_id}\n"
            f"**Caption/T'exuhuf:** {caption}"
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
                "✅ Fotooh deriswaal! Yihi meli'kt lebaalebét'ey derswaal." # በላቲን ፊደል (6)
            )
        except Exception as e:
            print(f"❌ Fotoohin leadmin melak altichaalem: {e}")
            bot.send_message(message.chat.id, "⚠️ Fotooh derswaal, gin bemast'elalef lay chiger tefet'erwaal.")


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
                    caption=f"**Yihi ye Hanita baalebét' foto new!** Yebaalébét'eey ma'areg **{OWNER_TITLE}** new.", # በላቲን ፊደል (6)
                    parse_mode='Markdown'
                )
        except Exception as e:
            bot.send_message(chat_id, f"❌ Sihtet tefetere: Fotoohin melak altichaalem.")
    else:
        bot.send_message(chat_id, "❌ Yebaalebét'eey foto alit'egeñem. Ebakih fotoohin 'owner_photo.jpg' bemil sim Upload adrig.")


# -------------------------------------------
# 7. RUN BOT 
# -------------------------------------------

print("🤖 Hanita Bot iyetenesa new...")

while True:
    try:
        # Webhook Conflict እንዳይፈጠር bot.polling()ን እንጠቀማለን
        bot.polling(none_stop=True, interval=0, timeout=30)
    except Exception as e:
        print(f"❌ Sihtet tekeseete (Telegram ginunyat): {e}")
        print("🤖 Hanita Bot endegena lemenesaat iyemokere new...")
        time.sleep(3)
