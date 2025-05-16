import json
import os
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv
import datetime

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
FAUCET_EMAIL = os.getenv("FAUCET_EMAIL")

bot = telebot.TeleBot(BOT_TOKEN)

DATA_FILE = "users_data.json"
ADMIN_FILE = "admin_panel.json"

def load_json_file(filename):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_json_file(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f)

users_data = load_json_file(DATA_FILE)
admin_data = load_json_file(ADMIN_FILE)

# قائمة الأزرار من ملف التحكم
def main_menu():
    b = admin_data.get("buttons", {})
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(b.get("account", "معلوماتي"), callback_data="account"),
        InlineKeyboardButton(b.get("daily_bonus", "المكافأة اليومية"), callback_data="daily_bonus"),
        InlineKeyboardButton(b.get("referral", "دعوة الأصدقاء"), callback_data="referral"),
        InlineKeyboardButton(b.get("withdraw", "سحب"), callback_data="withdraw"),
        InlineKeyboardButton(b.get("ads_section", "الإعلانات"), callback_data="ads")
    )
    return markup

@bot.message_handler(commands=["start"])
def start(message):
    user_id = str(message.from_user.id)
    if user_id not in users_data:
        users_data[user_id] = {
            "balance": 0.0,
            "referrals": [],
            "last_bonus": None
        }
        save_json_file(DATA_FILE, users_data)

    welcome = admin_data.get("welcome_message", "مرحبًا بك!")
    bot.send_message(message.chat.id, welcome, reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    user_id = str(call.from_user.id)
    if user_id not in users_data:
        users_data[user_id] = {
            "balance": 0.0,
            "referrals": [],
            "last_bonus": None
        }
        save_json_file(DATA_FILE, users_data)

    data = call.data
    if data == "account":
        balance = users_data[user_id]["balance"]
        bot.send_message(call.message.chat.id, f"💰 رصيدك الحالي: {balance:.8f} BTC")

    elif data == "daily_bonus":
        now = datetime.datetime.now()
        last_bonus_str = users_data[user_id].get("last_bonus")
        last_bonus = datetime.datetime.fromisoformat(last_bonus_str) if last_bonus_str else None

        if last_bonus and (now - last_bonus).total_seconds() < 86400:
            remaining = 86400 - (now - last_bonus).total_seconds()
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            bot.send_message(call.message.chat.id, f"⏳ جرب بعد {hours} ساعة و {minutes} دقيقة.")
        else:
            users_data[user_id]["balance"] += 0.00000050
            users_data[user_id]["last_bonus"] = now.isoformat()
            save_json_file(DATA_FILE, users_data)
            bot.send_message(call.message.chat.id, "🎁 تم إضافة 0.00000050 BTC إلى رصيدك.")

    elif data == "referral":
        ref_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        share_markup = InlineKeyboardMarkup()
        share_markup.add(
            InlineKeyboardButton("🔗 مشاركة على واتساب", url=f"https://wa.me/?text=اربح_معي {ref_link}"),
            InlineKeyboardButton("🔗 مشاركة على تيليجرام", url=f"https://t.me/share/url?url={ref_link}&text=اربح_البيتكوين")
        )
        bot.send_message(call.message.chat.id, f"🤝 رابط الإحالة الخاص بك:\n{ref_link}", reply_markup=share_markup)

    elif data == "withdraw":
        balance = users_data[user_id]["balance"]
        if balance >= 0.0001:
            users_data[user_id]["balance"] = 0.0
            save_json_file(DATA_FILE, users_data)
            bot.send_message(call.message.chat.id, f"✅ تم إرسال طلب سحب {balance:.8f} BTC إلى {FAUCET_EMAIL}")
            bot.send_message(ADMIN_ID, f"📤 طلب سحب جديد من {user_id} بمبلغ {balance:.8f} BTC")
        else:
            bot.send_message(call.message.chat.id, "❌ الحد الأدنى للسحب هو 0.0001 BTC.")

    elif data == "ads":
        ads_list = admin_data.get("ads", [])
        if not ads_list:
            bot.send_message(call.message.chat.id, "📢 لا توجد إعلانات حاليًا.")
        else:
            for ad in ads_list:
                bot.send_message(call.message.chat.id, f"📢 {ad}")

@bot.message_handler(commands=["admin"])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        return
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("➕ أضف إعلان", callback_data="admin_add_ad"))
    bot.send_message(message.chat.id, "🎛️ لوحة التحكم:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_add_ad")
def add_ad_handler(call):
    if call.from_user.id != ADMIN_ID:
        return
    msg = bot.send_message(call.message.chat.id, "✍️ أرسل نص الإعلان الجديد:")
    bot.register_next_step_handler(msg, save_new_ad)

def save_new_ad(message):
    ad_text = message.text
    ads = admin_data.get("ads", [])
    ads.append(ad_text)
    admin_data["ads"] = ads
    save_json_file(ADMIN_FILE, admin_data)
    bot.send_message(message.chat.id, "✅ تم حفظ الإعلان.")

# تشغيل البوت
bot.infinity_polling()
