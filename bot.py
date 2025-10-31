import requests
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton as Btn
import threading
import os
import json
import traceback
from datetime import datetime
import time

# ====== إعدادات البوت ======
TOKEN = "7142391067:AAFr5uEiqMD5pqA9RPplbxZjCVvQoUSmh_M"
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

ADMINS = [205161246]
SECRET_TEXT = "brho123"
FORCED_CHANNEL = "@brho400"
FORCED_SUBS = True

# ملفات الحفظ
USERS_FILE = "users.txt"
STATS_FILE = "stats.json"
BLOCKED_FILE = "blocked.txt"
LOGS_FILE = "logs.txt"

# ====== تحميل البيانات ======
def load_data():
    users = set()
    blocked = set()
    stats = {"messages_received": 0, "videos_downloaded": 0, "last_daily": 0}
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r") as f:
                for line in f:
                    uid = line.strip()
                    if uid.isdigit():
                        users.add(int(uid))
        if os.path.exists(BLOCKED_FILE):
            with open(BLOCKED_FILE, "r") as f:
                for line in f:
                    uid = line.strip()
                    if uid.isdigit():
                        blocked.add(int(uid))
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, "r") as f:
                data = json.load(f)
                stats.update(data)
    except Exception as e:
        log_error(f"Load error: {e}")
    return users, blocked, stats

def save_data(users, blocked, stats):
    try:
        with open(USERS_FILE, "w") as f:
            for uid in users:
                f.write(f"{uid}\n")
        with open(BLOCKED_FILE, "w") as f:
            for uid in blocked:
                f.write(f"{uid}\n")
        with open(STATS_FILE, "w") as f:
            json.dump(stats, f)
    except Exception as e:
        log_error(f"Save error: {e}")

def log_error(msg):
    try:
        with open(LOGS_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] {msg}\n")
    except:
        pass

users, blocked, stats = load_data()

# ====== دوال مساعدة ======
def is_admin(user_id): return user_id in ADMINS
def is_blocked(user_id): return user_id in blocked

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
        log_error(f"Download error: {e}")
        return None

# فحص الاشتراك + الحظر
def check_subscription(user_id):
    if not FORCED_SUBS or is_admin(user_id):
        return True
    try:
        member = bot.get_chat_member(FORCED_CHANNEL, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            if user_id in blocked:
                blocked.remove(user_id)
                save_data(users, blocked, stats)
            return True
        else:
            if user_id not in blocked:
                blocked.add(user_id)
                save_data(users, blocked, stats)
                try:
                    bot.send_message(user_id, "تم حظرك لأنك غادرت القناة.")
                except:
                    pass
            return False
    except Exception as e:
        log_error(f"Sub check failed for {user_id}: {e}")
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
        Btn("إيقاف الاشتراك", callback_data="disable_sub"),
        Btn("حذف مستخدم", callback_data="delete_user"),
        Btn("قائمة المحظورين", callback_data="list_blocked")
    )
    bot.send_message(chat_id, "*لوحة تحكم الأدمن*", reply_markup=markup, parse_mode="Markdown")

# ====== معالجة الأزرار ======
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
                f"المحظورين: `{len(blocked)}`\n"
                f"الرسائل: `{stats['messages_received']}`\n"
                f"التحميلات: `{stats['videos_downloaded']}`"
            )
            bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

        elif call.data == "enable_sub":
            FORCED_SUBS
            FORCED_SUBS = True
            save_data(users, blocked, stats)
            bot.edit_message_text("تم تفعيل الاشتراك الإجباري", call.message.chat.id, call.message.message_id)

        elif call.data == "disable_sub":
            FORCED_SUBS
            FORCED_SUBS = False
            save_data(users, blocked, stats)
            bot.edit_message_text("تم إيقاف الاشتراك الإجباري", call.message.chat.id, call.message.message_id)

        elif call.data == "delete_user":
            msg = bot.send_message(call.message.chat.id, "أرسل ID المستخدم للحذف:")
            bot.register_next_step_handler(msg, delete_user_handler)

        elif call.data == "list_blocked":
            if not blocked:
                bot.send_message(call.message.chat.id, "لا يوجد محظورين.")
            else:
                block_list = "\n".join([str(uid) for uid in sorted(blocked)[:50]])
                bot.send_message(call.message.chat.id, f"*المحظورين (أول 50):*\n\n`{block_list}`", parse_mode="Markdown")

    except Exception as e:
        log_error(f"Callback error: {e}")

# ====== حذف مستخدم ======
def delete_user_handler(message):
    if not is_admin(message.from_user.id): return
    try:
        uid = int(message.text.strip())
        if uid in users:
            users.remove(uid)
        if uid in blocked:
            blocked.remove(uid)
        save_data(users, blocked, stats)
        bot.reply_to(message, f"تم حذف المستخدم {uid} من القوائم.")
    except:
        bot.reply_to(message, "أرسل ID صحيح.")

# ====== الإذاعة ======
def start_broadcast(message):
    if not is_admin(message.from_user.id): return
    sent = failed = 0
    status_msg = bot.reply_to(message, "جاري الإذاعة...")

    def run():
        nonlocal sent, failed
        for uid in list(users):
            if uid in blocked: continue
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
        save_data(users, blocked, stats)

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

# ====== إحصائيات يومية ======
def send_daily_stats():
    while True:
        now = time.time()
        if now - stats.get('last_daily', 0) > 86400:  # كل 24 ساعة
            text = (
                "*إحصائيات اليوم*\n\n"
                f"المستخدمين: `{len(users)}`\n"
                f"المحظورين: `{len(blocked)}`\n"
                f"التحميلات: `{stats['videos_downloaded']}`"
            )
            for admin in ADMINS:
                try:
                    bot.send_message(admin, text, parse_mode="Markdown")
                except:
                    pass
            stats['last_daily'] = now
            save_data(users, blocked, stats)
        time.sleep(3600)  # كل ساعة

threading.Thread(target=send_daily_stats, daemon=True).start()

# ====== /start ======
@bot.message_handler(commands=['start'])
def start_command(m):
    user_id = m.from_user.id
    users.add(user_id)
    stats['messages_received'] += 1
    save_data(users, blocked, stats)

    if is_admin(user_id) and len(m.text.split()) > 1 and m.text.split()[1] == SECRET_TEXT:
        admin_panel(user_id)
        return

    if is_blocked(user_id):
        bot.send_message(user_id, "أنت محظور. لا يمكنك استخدام البوت.")
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
    save_data(users, blocked, stats)

    if text in (SECRET_TEXT, f"/{SECRET_TEXT}"):
        if is_admin(user_id):
            admin_panel(user_id)
        else:
            bot.reply_to(m, "ليس لديك صلاحية.")
        return

    if is_blocked(user_id):
        bot.reply_to(m, "أنت محظور.")
        return

    if not check_subscription(user_id):
        bot.reply_to(m, "انتهت صلاحية اشتراكك! يجب الاشتراك مجددًا.", reply_markup=check_sub_markup())
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
                save_data(users, blocked, stats)
                # إشعار للأدمن
                for admin in ADMINS:
                    try:
                        bot.send_message(admin, f"تم تحميل فيديو من {user_id}")
                    except:
                        pass
            except Exception as e:
                bot.reply_to(m, "فشل الإرسال (حجم كبير).")
                log_error(f"Send video error: {e}")
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
        update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
        if update:
            bot.process_new_updates([update])
        return '', 200
    return 'Forbidden', 403

@app.route('/')
def index():
    return "<h1>بوت تحميل إنستغرام يعمل!</h1><p>@brho400</p>", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)


