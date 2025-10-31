import requests
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton as Btn
import threading
import os
import json
import traceback

# ====== إعدادات البوت ======
TOKEN = "7142391067:AAFr5uEiqMD5pqA9RPplbxZjCVvQoUSmh_M"  # توكنك
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

ADMINS = [205161246]
SECRET_TEXT = "brho123"
FORCED_CHANNEL = "@brho400"
FORCED_SUBS = True  # يتم تغييره من لوحة التحكم

USERS_FILE = "users.txt"
STATS_FILE = "stats.json"

# ====== تحميل البيانات ======
def load_data():
    users = set()
    stats = {"messages_received": 0, "videos_downloaded": 0}
    try:
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
    except Exception as e:
        print(f"Load error: {e}")
    return users, stats

def save_data(users, stats):
    try:
        with open(USERS_FILE, "w") as f:
            for uid in users:
                f.write(f"{uid}\n")
        with open(STATS_FILE, "w") as f:
            json.dump(stats, f)
    except Exception as e:
        print(f"Save error: {e}")

users, stats = load_data()

# ====== دوال مساعدة ======
def is_admin(user_id): return user_id in ADMINS

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
    if not FORCED_SUBS or is_admin(user_id): return True
    try:
        member = bot.get_chat_member(FORCED_CHANNEL, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Sub check error: {e}")
        try:
            bot.send_message(ADMINS[0], f"خطأ اشتراك: {user_id} - {e}")
        except:
            pass
        return False

def check_sub_markup():
    markup = InlineKeyboardMarkup()
    markup.add(Btn("اشترك في القناة", url=f"https://t.me/{FORCED_CHANNEL[1:]}"))
    markup.add(Btn("تحقق من الاشتراك", callback_data="check_sub"))
    return markup

# ====== لوحة التحكم ======
def admin_panel(chat_id):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        Btn("إذاعة", callback_data="broadcast"),
        Btn("الإحصائيات", callback_data="stats"),
        Btn("تفعيل الاشتراك", callback_data="enable_sub"),
        Btn("إيقاف الاشتراك", callback_data="disable_sub")
    )
    bot.send_message(chat_id, "*لوحة تحكم الأدمن*", reply_markup=markup, parse_mode="Markdown")

# ====== معالجة الأزرار (بدون global) ======
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id

    if call.data == "check_sub":
        if check_subscription(user_id):
            bot.answer_callback_query(call.id, "أنت مشترك الآن!")
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
            send_welcome(user_id)
        else:
            bot.answer_callback_query(call.id, "لم تشترك بعد!")
        return

    if not is_admin(user_id):
        bot.answer_callback_query(call.id, "ليس لديك صلاحية!")
        return

    try:
        if call.data == "broadcast":
            msg = bot.send_message(call.message.chat.id, "أرسل الرسالة للإذاعة:")
            bot.register_next_step_handler(msg, start_broadcast)

        elif call.data == "stats":
            text = (
                "*إحصائيات البوت*\n\n"
                f"المستخدمين: `{len(users)}`\n"
                f"الرسائل: `{stats['messages_received']}`\n"
                f"التحميلات: `{stats['videos_downloaded']}`"
            )
            bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

        elif call.data == "enable_sub":
            FORCED_SUBS = True  # لا global
            save_data(users, stats)
            bot.edit_message_text("تم تفعيل الاشتراك الإجباري", call.message.chat.id, call.message.message_id)

        elif call.data == "disable_sub":
            FORCED_SUBS = False  # لا global
            save_data(users, stats)
            bot.edit_message_text("تم إيقاف الاشتراك الإجباري", call.message.chat.id, call.message.message_id)

    except Exception as e:
        try:
            bot.send_message(ADMINS[0], f"خطأ في الأزرار: {e}")
        except:
            pass

# ====== الإذاعة ======
def start_broadcast(message):
    if not is_admin(message.from_user.id): return
    sent = failed = 0
    status_msg = bot.reply_to(message, "جاري الإذاعة...")

    def run():
        nonlocal sent, failed
        for uid in list(users):
            try:
                bot.copy_message(uid, message.chat.id, message.message_id)
                sent += 1
            except:
                failed += 1
            threading.Event().wait(0.05)
        bot.edit_message_text(
            f"تم: `{sent}` | فشل: `{failed}`",
            message.chat.id, status_msg.message_id,
            parse_mode="Markdown"
        )
        save_data(users, stats)

    threading.Thread(target=run, daemon=True).start()

# ====== الترحيب ======
def send_welcome(user_id):
    markup = InlineKeyboardMarkup()
    markup.add(Btn("قناة البوت", url=f"https://t.me/{FORCED_CHANNEL[1:]}"))
    bot.send_message(
        user_id,
        "*مرحبًا!*\n"
        "أرسل رابط إنستغرام وسأحمل لك الفيديو فورًا.\n\n"
        "مثال:\n"
        "`https://www.instagram.com/reel/C123abc/`",
        reply_markup=markup,
        parse_mode="Markdown"
    )

# ====== /start ======
@bot.message_handler(commands=['start'])
def start_command(m):
    user_id = m.from_user.id
    users.add(user_id)
    stats['messages_received'] += 1
    save_data(users, stats)

    if is_admin(user_id) and len(m.text.split()) > 1 and m.text.split()[1] == SECRET_TEXT:
        admin_panel(user_id)
        return

    if not check_subscription(user_id):
        bot.send_message(
            user_id,
            "*يجب الاشتراك في القناة أولاً!*",
            reply_markup=check_sub_markup(),
            parse_mode="Markdown"
        )
    else:
        send_welcome(user_id)

# ====== معالجة الرسائل ======
@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle_text(m):
    user_id = m.from_user.id
    text = m.text.strip()
    stats['messages_received'] += 1
    users.add(user_id)
    save_data(users, stats)

    if text in (SECRET_TEXT, f"/{SECRET_TEXT}"):
        if is_admin(user_id): admin_panel(user_id)
        else: bot.reply_to(m, "ليس لديك صلاحية.")
        return

    if not check_subscription(user_id):
        bot.reply_to(m, "يجب الاشتراك أولاً!", reply_markup=check_sub_markup())
        return

    if is_instagram_link(text):
        wait_msg = bot.reply_to(m, "جاري التحميل...")
        video_url = download_instagram_video(text)
        if video_url:
            try:
                markup = InlineKeyboardMarkup()
                markup.add(Btn("قناة البوت", url=f"https://t.me/{FORCED_CHANNEL[1:]}"))
                bot.send_video(
                    user_id, video_url,
                    caption="تم التحميل بنجاح!",
                    reply_markup=markup
                )
                stats['videos_downloaded'] += 1
                save_data(users, stats)
            except Exception as e:
                bot.reply_to(m, "فشل الإرسال (حجم كبير).")
                print(e)
        else:
            bot.reply_to(m, "تعذر التحميل. تأكد من الرابط.")
        try:
            bot.delete_message(user_id, wait_msg.message_id)
        except:
            pass
    else:
        bot.reply_to(m, "أرسل رابط إنستغرام صالح فقط.")

# ====== Webhook ======
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        if update:
            bot.process_new_updates([update])
        return '', 200
    return 'Forbidden', 403

@app.route('/')
def index():
    return "<h1>بوت تحميل إنستغرام يعمل!</h1><p>@brho400</p>", 200

# ====== تشغيل ======
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
