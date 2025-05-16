import os
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv
import datetime
import json

# تحميل المتغيرات من ملف .env
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
FAUCET_EMAIL = os.getenv("FAUCET_EMAIL")

if not BOT_TOKEN or not ADMIN_ID or not FAUCET_EMAIL:
    raise ValueError("تأكد من ضبط BOT_TOKEN, ADMIN_ID, FAUCET_EMAIL في ملف .env")

bot = telebot.TeleBot(BOT_TOKEN)

# بيانات المستخدمين
DATA_FILE = "users_data.json"
CONFIG_FILE = "config.json"

def load_users_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users_data():
    with open(DATA_FILE, "w") as f:
        json.dump(users_data, f)

def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "daily_bonus_amount": 0.00000050,
            "minimum_withdraw_amount": 0.0001,
            "referral_bonus": 0.00000020
        }

def save_config():
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

users_data = load_users_data()
config = load_config()

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

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        return
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔧 تغيير المكافأة اليومية", callback_data="edit_bonus"))
    markup.add(InlineKeyboardButton("🔧 تغيير الحد الأدنى للسحب", callback_data="edit_min_withdraw"))
    bot.send_message(message.chat.id, "👨‍💻 لوحة تحكم الأدمن:", reply_markup=markup)

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
            users_data[user_id]["balance"] += config["daily_bonus_amount"]
            users_data[user_id]["last_bonus"] = now.isoformat()
            save_users_data()
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, f"🎁 تم إضافة {config['daily_bonus_amount']:.8f} BTC إلى رصيدك.")

    elif call.data == "referral":
        ref_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        share_text = f"اربح بيتكوين بسهولة عبر هذا البوت! سجل من هنا:\n{ref_link}"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔗 مشاركة على تيليجرام", url=f"https://t.me/share/url?url={ref_link}&text={share_text}"))
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, f"🤝 رابط الإحالة الخاص بك:\n{ref_link}", reply_markup=markup)

    elif call.data == "withdraw":
        balance = users_data[user_id]["balance"]
        if balance >= config["minimum_withdraw_amount"]:
            users_data[user_id]["balance"] = 0.0
            save_users_data()
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, f"✅ تم إرسال طلب سحب {balance:.8f} BTC إلى {FAUCET_EMAIL}.")
            bot.send_message(ADMIN_ID, f"🔔 طلب سحب جديد:\nمستخدم: {user_id}\nالمبلغ: {balance:.8f} BTC")
        else:
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, f"❌ الحد الأدنى للسحب هو {config['minimum_withdraw_amount']:.8f} BTC")

    elif call.data == "ads":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "📢 سيتم عرض الإعلانات هنا لاحقًا.")

    elif call.data == "edit_bonus" and call.from_user.id == ADMIN_ID:
        msg = bot.send_message(call.message.chat.id, "🔧 أرسل قيمة المكافأة اليومية الجديدة (مثال: 0.00000100):")
        bot.register_next_step_handler(msg, update_bonus)

    elif call.data == "edit_min_withdraw" and call.from_user.id == ADMIN_ID:
        msg = bot.send_message(call.message.chat.id, "🔧 أرسل الحد الأدنى للسحب الجديد (مثال: 0.0001):")
        bot.register_next_step_handler(msg, update_min_withdraw)

def update_bonus(message):
    try:
        value = float(message.text)
        config["daily_bonus_amount"] = value
        save_config()
        bot.send_message(message.chat.id, f"✅ تم تحديث مكافأة اليومية إلى {value:.8f} BTC")
    except:
        bot.send_message(message.chat.id, "❌ صيغة غير صحيحة.")

def update_min_withdraw(message):
    try:
        value = float(message.text)
        config["minimum_withdraw_amount"] = value
        save_config()
        bot.send_message(message.chat.id, f"✅ تم تحديث الحد الأدنى للسحب إلى {value:.8f} BTC")
    except:
        bot.send_message(message.chat.id, "❌ صيغة غير صحيحة.")

# بدء البوت
bot.infinity_polling()
