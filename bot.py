import os
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv
import datetime
import json

# تحميل المتغيرات من ملف .env
load_dotenv()

# قراءة القيم من البيئة
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
FAUCET_EMAIL = os.getenv("FAUCET_EMAIL")

if not BOT_TOKEN or not ADMIN_ID or not FAUCET_EMAIL:
    raise ValueError("تأكد من ضبط BOT_TOKEN, ADMIN_ID, FAUCET_EMAIL في ملف .env")

bot = telebot.TeleBot(BOT_TOKEN)

# تخزين البيانات في ملف JSON
DATA_FILE = "users_data.json"

def load_users_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users_data():
    with open(DATA_FILE, "w") as f:
        json.dump(users_data, f)

# تحميل البيانات
users_data = load_users_data()

# القائمة الرئيسية
def main_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("👤 معلومات حسابي", callback_data="account"),
        InlineKeyboardButton("🎁 المكافأة اليومية", callback_data="daily_bonus"),
        InlineKeyboardButton("🤝 دعوة الأصدقاء", callback_data="referral"),
        InlineKeyboardButton("💸 سحب الأرباح", callback_data="withdraw"),
        InlineKeyboardButton("📢 مشاهدة الإعلانات", callback_data="ads")
    )
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.from_user.id)
    if user_id not in users_data:
        users_data[user_id] = {
            "balance": 0.0,
            "referrals": [],
            "last_bonus": None
        }
        save_users_data()
    bot.send_message(message.chat.id, "🎉 مرحبًا بك في بوت ربح البيتكوين!\nاختر من القائمة:", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    user_id = str(call.from_user.id)

    if user_id not in users_data:
        users_data[user_id] = {
            "balance": 0.0,
            "referrals": [],
            "last_bonus": None
        }
        save_users_data()

    if call.data == "account":
        balance = users_data[user_id]["balance"]
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, f"💰 رصيدك الحالي: {balance:.8f} BTC")

    elif call.data == "daily_bonus":
        now = datetime.datetime.now()
        last_bonus_str = users_data[user_id].get("last_bonus")
        last_bonus = datetime.datetime.fromisoformat(last_bonus_str) if last_bonus_str else None

        if last_bonus and (now - last_bonus).total_seconds() < 86400:
            remaining = 86400 - (now - last_bonus).total_seconds()
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            bot.answer_callback_query(call.id, text=f"⏳ جرب بعد {hours} ساعة و {minutes} دقيقة.")
        else:
            users_data[user_id]["balance"] += 0.00000050
            users_data[user_id]["last_bonus"] = now.isoformat()
            save_users_data()
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, "🎁 تم إضافة 0.00000050 BTC إلى رصيدك.")

    elif call.data == "referral":
        ref_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, f"🤝 رابط الإحالة الخاص بك:\n{ref_link}")

    elif call.data == "withdraw":
        balance = users_data[user_id]["balance"]
        if balance >= 0.0001:
            users_data[user_id]["balance"] = 0.0
            save_users_data()
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, f"✅ تم إرسال طلب سحب {balance:.8f} BTC إلى {FAUCET_EMAIL}.")
            bot.send_message(ADMIN_ID, f"🔔 طلب سحب جديد:\nمستخدم: {user_id}\nالمبلغ: {balance:.8f} BTC")
        else:
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, "❌ الحد الأدنى للسحب هو 0.0001 BTC")

    elif call.data == "ads":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "📢 سيتم عرض الإعلانات هنا لاحقًا.")

# تشغيل البوت
bot.infinity_polling()
