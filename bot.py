import requests
import telebot
from telebot.types import InlineKeyboardButton as Btn, InlineKeyboardMarkup as Mak

token = "7142391067:AAFr5uEiqMD5pqA9RPplbxZjCVvQoUSmh_M"
bot = telebot.TeleBot(token)

@bot.message_handler(commands=["start"])
def start(message):
    welcome_message = ("• أهلاً بك عزيزي 👋🏻\n\nفي بوت التحميل من إنستقرام.\n\n"
                       "- يمكنك تحميل فيديوهات إنستقرام بجودة عالية.\n"
                       "- قم بإرسال رابط الفيديو للتحميل 🤍")

    markup = Mak().add(Btn('انقر هنا للانتقال إلى الصفحة', url='https://example.com'))

    bot.send_message(message.chat.id, welcome_message, reply_markup=markup)

@bot.message_handler(content_types=['text'])
def Down(message):
    try:
        link = message.text
        wait_message = bot.send_message(message.chat.id, 'يرجى الانتظار، يتم تحميل الفيديو...')

        json_data = {
            'url': link
        }
        response = requests.post('https://insta.savetube.me/downloadPostVideo', json=json_data).json()
        video = response['post_video_url']

        caption_text = '| 🎉 |\n✅ مبروك تم التحميل.'
        markup = Mak().add(Btn('انقر هنا للانتقال إلى الصفحة', url='https://example.com'))
        sent_video_message = bot.send_video(message.chat.id, video, caption=caption_text, reply_markup=markup)

        bot.delete_message(message.chat.id, wait_message.message_id)
    except:
        bot.reply_to(message, 'رابط غير صحيح')

bot.infinity_polling()
