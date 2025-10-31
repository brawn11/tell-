import requests
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton as Btn
import threading
import os
import json

# ====== إعدادات البوت ======
TOKEN = "7142391067:AAFr5uEiqMD5pqA9RPplbxZjCVvQoUSmh_M"
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# الأدمن
ADMINS = [205161246]
SECRET_TEXT = "brho123"

# الاشتراك الإجباري
FORCED_CHANNEL = "@brho330"
FORCED_SUBS = True

# ملف حفظ المستخدمين والإحصائيات
USERS_FILE = "users.txt"
STATS_FILE = "stats.json"

# تحميل البيانات
def load_data():
    users = set()
    stats = {"messages_received": 0, "videos_downloaded": 0}
    
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            for line in f:
                uid = line.strip()
                if uid.isdigit():
                    users.add(int(uid))
    
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r") as f:
            data = json.load(f)
            stats.update(data)
    
    return users, stats

def save_data(users, stats):
    with open(USERS_FILE, "w") as f:
        for uid in users:
            f.write(f"{uid}\n")
    
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f)

users, stats = load_data()

# ====== دوال مساعدة ======
def is_admin(user_id):
    return user_id in ADMINS

def is_instagram_link(text):
    if not text: return False
    t = text.lower()
    return 'instagram.com' in t or 'instagr.am' in t or 'insta.' in t

def download_instagram_video(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.post(
            'https://insta.savetube.me/downloadPostVideo',
            json={'url': url},
            headers=headers,
            timeout=30
        )
        j = r.json()
        return j.get('post_video_url') or j.get('video_url')
    except Exception as e:
        print(f"Download error: {e}")
        return None

def check_subscription(user_id):
    if not FORCED_SUBS or is_admin(user_id):
        return True
    try:
        member = bot.get_chat_member(FORCED_CHANNEL, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

def check_sub_markup():
    markup = InlineKeyboardMarkup()
    markup.add(Btn("🔔 اشترك في القناة", url=f"https://t.me/{FORCED_CHANNEL[1:]}"))
    markup.add(Btn("✅ تحقق من الاشتراك", callback_data="check_sub"))
    return markup

# ====== لوحة التحكم ======
def admin_panel(chat_id):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        Btn("📢 إذاعة", callback_data="broadcast"),
        Btn("📊 الإحصائيات", callback_data="stats"),
        Btn("🔔 تفعيل الاشتراك", callback_data="enable_sub"),
        Btn("🔕 إيقاف الاشتراك", callback_data="disable_sub")
    )
    bot.send_message(chat_id, "*⚙️ لوحة تحكم الأدمن*", reply_markup=markup, parse_mode="Markdown")

# ====== معالجة الأزرار ======
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id

    if not is_admin(user_id):
        bot.answer_callback_query(call.id, "🚫 ليس لديك صلاحية!")
        return

    try:
        if call.data == "check_sub":
            if check_subscription(call.from_user.id):
                bot.answer_callback_query(call.id, "✅ أنت مشترك!")
                bot.delete_message(call.message.chat.id, call.message.message_id)
            else:
                bot.answer_callback_query(call.id, "⚠️ لم تشترك بعد!")

        elif call.data == "broadcast":
            msg = bot.send_message(call.message.chat.id, "📩 أرسل الرسالة التي تريد إذاعتها (نص، صورة، فيديو...):")
            bot.register_next_step_handler(msg, start_broadcast)

        elif call.data == "stats":
            text = (
                "*📊 إحصائيات البوت*\n\n"
                f"👥 عدد المستخدمين: `{len(users)}`\n"
                f"📩 الرسائل المستلمة: `{stats['messages_received']}`\n"
                f"📥 الفيديوهات المحملة: `{stats['videos_downloaded']}`"
            )
            bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

        elif call.data == "enable_sub":
            global FORCED_SUBS
            FORCED_SUBS = True
            save_data(users, stats)
            bot.answer_callback_query(call.id, "تم تفعيل الاشتراك")
            bot.edit_message_text("🔔 تم تفعيل الاشتراك الإجباري", call.message.chat.id, call.message.message_id)

        elif call.data == "disable_sub":
            FORCED_SUBS = False
            save_data(users, stats)
            bot.answer_callback_query(call.id, "تم إيقاف الاشتراك")
            bot.edit_message_text("🔕 تم إيقاف الاشتراك الإجباري", call.message.chat.id, call.message.message_id)

    except Exception as e:
        bot.send_message(ADMINS[0], f"خطأ في Callback: {e}")

# ====== الإذاعة في خلفية منفصلة ======
def send_broadcast_message(user_id, message):
    try:
        bot.forward_message(user_id, message.chat.id, message.message_id)
        return True
    except:
        try:
            bot.copy_message(user_id, message.chat.id, message.message_id)
            return True
        except:
            return False

def start_broadcast(message):
    if not is_admin(message.from_user.id):
        return

    sent = 0
    failed = 0
    bot.reply_to(message, "🚀 جاري الإذاعة...")

    def broadcast_thread():
        nonlocal sent, failed
        for user_id in list(users):
            if send_broadcast_message(user_id, message):
                sent += 1
            else:
                failed += 1
            # تجنب الحظر
            threading.Event().wait(0.05)

        save_data(users, stats)
        bot.send_message(message.chat.id, f"✅ تمت الإذاعة:\nإرسال: `{sent}`\nفشل: `{failed}`", parse_mode="Markdown")

    threading.Thread(target=broadcast_thread, daemon=True).start()

# ====== معالجة الرسائل ======
@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle_text(m):
    user_id = m.from_user.id
    text = m.text.strip()
    stats['messages_received'] += 1
    users.add(user_id)
    save_data(users, stats)

    # لوحة التحكم
    if text in (SECRET_TEXT, f"/{SECRET_TEXT}"):
        if is_admin(user_id):
            admin_panel(user_id)
        else:
            bot.reply_to(m, "🚫 ليس لديك صلاحية.")
        return

    # فحص الاشتراك
    if not check_subscription(user_id):
        bot.reply_to(m, "⚠️ يجب عليك الاشتراك في القناة أولاً!", reply_markup=check_sub_markup())
        return

    # تحميل فيديو إنستا
    if is_instagram_link(text):
        wait_msg = bot.reply_to(m, "⏳ جاري تحميل الفيديو...")
        video_url = download_instagram_video(text)

        if video_url:
            try:
                markup = InlineKeyboardMarkup()
                markup.add(Btn("📢 قناة البوت", url=f"https://t.me/{FORCED_CHANNEL[1:]}"))
                bot.send_video(
                    user_id,
                    video_url,
                    caption="✅ تم تحميل الفيديو بنجاح!",
                    reply_markup=markup
                )
                stats['videos_downloaded'] += 1
                save_data(users, stats)
            except Exception as e:
                bot.reply_to(m, "❌ فشل إرسال الفيديو (ربما حجمه كبير جداً).")
                print(e)
        else:
            bot.reply_to(m, "❌ عذراً، لم أتمكن من تحميل الفيديو. تأكد من الرابط.")
        
        bot.delete_message(chat_id=user_id, message_id=wait_msg.message_id)
    else:
        bot.reply_to(m, "🔗 أرسل رابط إنستغرام صالح فقط.")

# ====== Webhook ======
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        return 'Forbidden', 403

@app.route('/')
def index():
    return "<h1>🤖 بوت تحميل إنستغرام يعمل!</h1><p>القناة: <a href='https://t.me/brho330'>@brho330</a></p>", 200

# ====== تشغيل البوت ======
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
