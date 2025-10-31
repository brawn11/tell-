import json
import requests
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton as Btn

# ====== التوكن مباشر ======
TOKEN = "7142391067:AAFr5uEiqMD5pqA9RPplbxZjCVvQoUSmh_M"
# ADMINS: ضع هنا id المالك
ADMINS = [205161246]

# الإعدادات
FORCED_CHANNEL = "brho22"  # أو id القناة مثل "-1001234567890"
FORCED_SUBS = True  # الاشتراك الإجباري مفعل
COMM_ENABLED = True  # استقبال الرسائل مفعل
SECRET_TEXT = "brho123"  # كلمة السر للوصول للوحة التحكم

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# جلسات مؤقتة للردود
sessions = {}

# ====== الدوال المساعدة ======
def is_admin(user_id):
    return int(user_id) in ADMINS

def is_instagram_link(text):
    if not text: return False
    t = text.lower()
    return 'instagram.com' in t or 'insta.' in t

def download_instagram_video(url):
    try:
        r = requests.post('https://insta.savetube.me/downloadPostVideo', json={'url': url}, timeout=25)
        j = r.json()
        return j.get('post_video_url')
    except:
        return None

def check_forced_subscription(user_id):
    if not FORCED_SUBS or not FORCED_CHANNEL:
        return True
    try:
        member = bot.get_chat_member(FORCED_CHANNEL, user_id)
        if member.status in ['creator', 'administrator', 'member']:
            return True
        return False
    except:
        return False

def send_admin_menu(chat_id):
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        Btn("📢 إذاعة", callback_data='broadcast'),
        Btn("📊 إحصائيات (جلسات)", callback_data='stats'),
        Btn("🔔 تفعيل الاشتراك الإجباري", callback_data='enable_forced_sub'),
        Btn("🔕 إيقاف الاشتراك الإجباري", callback_data='disable_forced_sub'),
        Btn("➕ تعيين قناة اشتراك", callback_data='set_channel'),
        Btn("📬 تفعيل التواصل", callback_data='enable_comm'),
        Btn("📴 إيقاف التواصل", callback_data='disable_comm')
    )
    bot.send_message(chat_id, "لوحة التحكم (سرية):", reply_markup=markup)

# ====== التعامل مع الرسائل ======
@bot.message_handler(commands=['start'])
def handle_start(m):
    bot.send_message(m.chat.id, "أهلاً! أرسل رابط إنستغرام للتحميل، أو أي رسالة للتواصل.")

@bot.callback_query_handler(func=lambda c: True)
def handle_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "ليس لديك صلاحية.")
        return

    data = call.data
    global FORCED_SUBS, COMM_ENABLED, FORCED_CHANNEL

    if data == 'broadcast':
        msg = bot.send_message(call.message.chat.id, "أرسل نص الإذاعة الآن:")
        bot.register_next_step_handler(msg, lambda m: bot.send_message(call.message.chat.id, "لا يوجد قاعدة مستخدمين محفوظة (لا تخزين)."))
    elif data == 'stats':
        sessions_list = "\n".join([str(k) for k in sessions.keys()]) or "لا توجد جلسات حالياً"
        bot.send_message(call.message.chat.id, f"الجلسات المفتوحة (user_ids):\n{sessions_list}")
    elif data == 'enable_forced_sub':
        FORCED_SUBS = True
        bot.send_message(call.message.chat.id, "تم تفعيل الاشتراك الإجباري.")
    elif data == 'disable_forced_sub':
        FORCED_SUBS = False
        bot.send_message(call.message.chat.id, "تم إيقاف الاشتراك الإجباري.")
    elif data == 'set_channel':
        msg = bot.send_message(call.message.chat.id, "أرسل معرف القناة (username بدون @ أو id القناة):")
        bot.register_next_step_handler(msg, lambda m: set_channel(m))
    elif data == 'enable_comm':
        COMM_ENABLED = True
        bot.send_message(call.message.chat.id, "تم تفعيل استقبال الرسائل.")
    elif data == 'disable_comm':
        COMM_ENABLED = False
        bot.send_message(call.message.chat.id, "تم إيقاف استقبال الرسائل.")

def set_channel(m):
    global FORCED_CHANNEL
    ch = m.text.strip()
    FORCED_CHANNEL = ch
    bot.send_message(m.chat.id, f"تم تعيين قناة الاشتراك (مؤقتاً): {ch}")

@bot.message_handler(func=lambda m: True, content_types=['text'])
def main_handler(m):
    user_id = m.from_user.id
    text = m.text or ""

    # فتح لوحة التحكم
    if text.strip() in (SECRET_TEXT, f"/{SECRET_TEXT}"):
        if is_admin(user_id):
            send_admin_menu(user_id)
        else:
            bot.send_message(user_id, "ليس لديك صلاحية الوصول للوحة التحكم.")
        return

    if not COMM_ENABLED and not is_admin(user_id):
        bot.send_message(user_id, "التواصل مع المالك معطل حالياً.")
        return

    if (not is_admin(user_id)) and FORCED_SUBS:
        ok = check_forced_subscription(user_id)
        if not ok:
            ch = FORCED_CHANNEL or ""
            url = f"https://t.me/{ch.lstrip('@')}" if ch else "https://t.me/"
            markup = InlineKeyboardMarkup()
            markup.add(Btn("🔔 اضغط للاشتراك", url=url))
            bot.send_message(user_id, "⚠️ يجب عليك الاشتراك في القناة أولاً.", reply_markup=markup)
            return

    if is_instagram_link(text):
        wait = bot.send_message(user_id, "يرجى الانتظار، جارٍ تحميل الفيديو...")
        video_url = download_instagram_video(text)
        if video_url:
            try:
                bot.send_video(user_id, video_url, caption="✅ تم التحميل")
            except Exception:
                bot.send_message(user_id, "تم العثور على الفيديو لكن فشل الإرسال — ربما الحجم كبير.")
        else:
            bot.send_message(user_id, "عذراً، لم أتمكن من تحميل الفيديو. تأكد من الرابط.")
        try:
            bot.delete_message(user_id, wait.message_id)
        except:
            pass
        return

    if not FORCED_SUBS and not is_instagram_link(text):
        bot.send_message(user_id, "أرسل رابط صحيح")
        return

    # إرسال الرسالة للمالك (جلسة مؤقتة)
    for owner in ADMINS:
        try:
            sent = bot.send_message(owner, f"📨 رسالة من @{m.from_user.username or '-'}\nID: {user_id}\n\n{m.text}")
            sessions[user_id] = sent.message_id
        except:
            pass
    bot.send_message(user_id, "تم إرسال رسالتك إلى المالك، انتظر الرد.")

# ====== الرد من المالك ======
@bot.message_handler(func=lambda m: m.reply_to_message is not None and is_admin(m.from_user.id), content_types=['text'])
def owner_reply(m):
    reply_to = m.reply_to_message
    target_user = None
    for u, msg_id in sessions.items():
        if msg_id == reply_to.message_id:
            target_user = u
            break
    if target_user:
        try:
            bot.send_message(target_user, f"رد من المالك:\n{m.text}")
            bot.send_message(m.from_user.id, "تم إرسال الرد إلى المستخدم.")
        except:
            bot.send_message(m.from_user.id, "فشل إرسال الرد.")
    else:
        bot.send_message(m.from_user.id, "لم أتمكن من العثور على المستخدم المرتبط بهذه الرسالة.")

# ====== Webhook ======
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    try:
        json_str = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json.loads(json_str))
        bot.process_new_updates([update])
    except:
        pass
    return "ok", 200

@app.route('/')
def index():
    return "Bot is running!"

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
