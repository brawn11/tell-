import requests
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton as Btn

# ====== إعدادات البوت ======
TOKEN = "7142391067:AAFr5uEiqMD5pqA9RPplbxZjCVvQoUSmh_M"
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# الأدمن للوصول للوحة التحكم
ADMINS = [205161246]  # ضع ID المالك
SECRET_TEXT = "brho123"

# الاشتراك الإجباري
FORCED_CHANNEL = "brho330"
FORCED_SUBS = True

# إحصائيات في الذاكرة
stats = {
    "messages_received": 0,
    "videos_downloaded": 0
}

# قائمة المستخدمين مؤقتًا (للاستخدام في الإذاعة)
users = set()

# ====== دوال مساعدة ======
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
    if not FORCED_SUBS:
        return True
    try:
        member = bot.get_chat_member(FORCED_CHANNEL, user_id)
        if member.status in ['creator', 'administrator', 'member']:
            return True
        return False
    except:
        return False

# ====== لوحة التحكم ======
def send_admin_menu(chat_id):
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        Btn("📢 إذاعة", callback_data='broadcast'),
        Btn("📊 إحصائيات", callback_data='stats'),
        Btn("🔔 تفعيل الاشتراك", callback_data='enable_forced_sub'),
        Btn("🔕 إيقاف الاشتراك", callback_data='disable_forced_sub')
    )
    bot.send_message(chat_id, "لوحة التحكم:", reply_markup=markup)

# ====== Callback للوحة التحكم ======
@bot.callback_query_handler(func=lambda c: True)
def handle_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "ليس لديك صلاحية.")
        return

    global FORCED_SUBS

    if call.data == 'broadcast':
        msg = bot.send_message(call.message.chat.id, "أرسل نص الإذاعة الآن:")
        bot.register_next_step_handler(msg, do_broadcast)
    elif call.data == 'stats':
        msg = f"عدد الرسائل المستلمة: {stats['messages_received']}\nعدد الفيديوهات المحملة: {stats['videos_downloaded']}\nعدد المستخدمين: {len(users)}"
        bot.send_message(call.message.chat.id, msg)
    elif call.data == 'enable_forced_sub':
        FORCED_SUBS = True
        bot.send_message(call.message.chat.id, "تم تفعيل الاشتراك الإجباري.")
    elif call.data == 'disable_forced_sub':
        FORCED_SUBS = False
        bot.send_message(call.message.chat.id, "تم إيقاف الاشتراك الإجباري.")

def do_broadcast(m):
    text = m.text or ""
    sent_count = 0
    for user_id in users:
        try:
            bot.send_message(user_id, text)
            sent_count += 1
        except:
            pass
    bot.send_message(m.chat.id, f"تم الإرسال إلى {sent_count} مستخدم.")

# ====== استقبال الرسائل ======
@bot.message_handler(func=lambda m: True, content_types=['text'])
def main_handler(m):
    user_id = m.from_user.id
    text = m.text.strip()
    stats['messages_received'] += 1
    users.add(user_id)

    # فتح لوحة التحكم
    if text in (SECRET_TEXT, f"/{SECRET_TEXT}"):
        if is_admin(user_id):
            send_admin_menu(user_id)
        else:
            bot.send_message(user_id, "ليس لديك صلاحية.")
        return

    # تحقق الاشتراك الاجباري
    if not is_admin(user_id) and FORCED_SUBS:
        ok = check_forced_subscription(user_id)
        if not ok:
            markup = InlineKeyboardMarkup()
            markup.add(Btn("🔔 اضغط للاشتراك", url=f"https://t.me/{FORCED_CHANNEL}"))
            bot.send_message(user_id, "⚠️ يجب عليك الاشتراك في القناة أولاً.", reply_markup=markup)
            return

    # تحقق الرابط
    if is_instagram_link(text):
        wait = bot.send_message(user_id, "جارٍ تحميل الفيديو، يرجى الانتظار...")
        video_url = download_instagram_video(text)
        if video_url:
            try:
                markup = InlineKeyboardMarkup()
                markup.add(Btn("🔗 قناة البوت", url=f"https://t.me/{FORCED_CHANNEL}"))
                bot.send_video(user_id, video_url, caption="✅ تم التحميل", reply_markup=markup)
                stats['videos_downloaded'] += 1
            except:
                bot.send_message(user_id, "تم العثور على الفيديو لكن فشل الإرسال — ربما الحجم كبير.")
        else:
            bot.send_message(user_id, "عذراً، لم أتمكن من تحميل الفيديو. تأكد من الرابط.")
        try:
            bot.delete_message(user_id, wait.message_id)
        except:
            pass
    else:
        bot.send_message(user_id, "رابط غير صحيح")

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
