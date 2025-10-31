import os
import requests
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardButton as Btn, InlineKeyboardMarkup as Mak

# التوكن الخاص بالبوت
TOKEN = "7142391067:AAFr5uEiqMD5pqA9RPplbxZjCVvQoUSmh_M"
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# -----------------------
# أوامر البوت
# -----------------------
@bot.message_handler(commands=["start"])
def start(message):
    welcome_message = ("• أهلاً بك 👋🏻\n"
                       "- أرسل رابط فيديو للتحميل 🤍")
    markup = Mak().add(Btn('انقر هنا للصفحة', url='https://example.com'))
    bot.send_message(message.chat.id, welcome_message, reply_markup=markup)

@bot.message_handler(content_types=['text'])
def Down(message):
    try:
        link = message.text
        wait_message = bot.send_message(message.chat.id, 'يرجى الانتظار...')
        json_data = {'url': link}
        response = requests.post('https://insta.savetube.me/downloadPostVideo', json=json_data).json()
        video = response['post_video_url']
        caption_text = '| 🎉 |\n✅ تم التحميل'
        markup = Mak().add(Btn('انقر هنا للصفحة', url='https://example.com'))
        bot.send_video(message.chat.id, video, caption=caption_text, reply_markup=markup)
        bot.delete_message(message.chat.id, wait_message.message_id)
    except:
        bot.reply_to(message, 'رابط غير صحيح')

# -----------------------
# Webhook route
# -----------------------
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    json_data = request.get_json(force=True)
    bot.process_new_updates([telebot.types.Update.de_json(json_data)])
    return "ok", 200

# -----------------------
# رابط اختبار الخدمة
# -----------------------
@app.route('/')
def index():
    return "Bot is running!"

# -----------------------
# تشغيل Flask
# -----------------------
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)


