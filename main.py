import os
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv
import datetime
import json

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = telebot.TeleBot(BOT_TOKEN)

DATA_FILE = "users_data.json"
WELCOME_FILE = "bot_files/welcome_message.txt"
CONFIG_FILE = "bot_files/config.json"
BUTTONS_FILE = "bot_files/buttons.json"

def load_users_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_users_data():
    with open(DATA_FILE, "w") as f:
        json.dump(users_data, f)

def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except:
        return {"daily_bonus": 0.00000050}

def load_buttons():
    try:
        with open(BUTTONS_FILE, "r") as f:
            return json.load(f)
    except:
        return []

users_data = load_users_data()
config = load_config()

def main_menu(user_id=None):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("👤 حسابي", callback_data="account"),
        InlineKeyboardButton("🎁 المكافأة اليومية", callback_data="daily_bonus"),
        InlineKeyboardButton("🤝 دعوة الأصدقاء", callback_data="referral"),
        InlineKeyboardButton("💸 سحب الأرباح", callback_data="withdraw"),
        InlineKeyboardButton("📢 الإعلانات", callback_data="ads"),
        InlineKeyboardButton("📊 إحصائياتي", callback_data="my_stats")
    )
    for btn in load_buttons():
        markup.add(InlineKeyboardButton(btn["text"], url=btn["url"]))
    if user_id == ADMIN_ID:
        markup.add(InlineKeyboardButton("🛠 لوحة التحكم", callback_data="admin_panel"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.from_user.id)
    now = datetime.datetime.now()
    if user_id not in users_data:
        users_data[user_id] = {
            "balance": 0.0,
            "referrals": [],
            "last_bonus": None,
            "daily_bonus_count": 0,
            "referral_earnings": 0.0,
            "last_active": now.isoformat()
        }
        save_users_data()
    else:
        users_data[user_id]["last_active"] = now.isoformat()
        save_users_data()

    welcome_msg = open(WELCOME_FILE, "r", encoding="utf-8").read()
    bot.send_message(message.chat.id, welcome_msg, reply_markup=main_menu(message.from_user.id))

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    user_id = str(call.from_user.id)
    now = datetime.datetime.now()

    if user_id not in users_data:
        users_data[user_id] = {
            "balance": 0.0,
            "referrals": [],
            "last_bonus": None,
            "daily_bonus_count": 0,
            "referral_earnings": 0.0,
            "last_active": now.isoformat()
        }
        save_users_data()

    users_data[user_id]["last_active"] = now.isoformat()
    save_users_data()

    if call.data == "account":
        bal = users_data[user_id]["balance"]
        bot.edit_message_text(f"💰 رصيدك الحالي: {bal:.8f} BTC", call.message.chat.id, call.message.message_id)

    elif call.data == "daily_bonus":
        last = users_data[user_id]["last_bonus"]
        if last:
            last = datetime.datetime.fromisoformat(last)
            diff = (now - last).total_seconds()
            if diff < 86400:
                h, m = int((86400 - diff) // 3600), int((86400 - diff) % 3600 // 60)
                bot.answer_callback_query(call.id, f"⏳ حاول بعد {h} ساعة و {m} دقيقة.")
                return

        bonus = config.get("daily_bonus", 0.00000050)
        users_data[user_id]["balance"] += bonus
        users_data[user_id]["last_bonus"] = now.isoformat()
        users_data[user_id]["daily_bonus_count"] += 1
        save_users_data()
        bot.edit_message_text(f"🎉 تم إضافة {bonus} BTC إلى رصيدك.", call.message.chat.id, call.message.message_id)

    elif call.data == "referral":
        ref_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        text = f"🤝 رابط الإحالة الخاص بك:\n{ref_link}"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id)

    elif call.data == "withdraw":
        bal = users_data[user_id]["balance"]
        if bal >= 0.0001:
            users_data[user_id]["balance"] = 0.0
            save_users_data()
            bot.edit_message_text(f"✅ تم إرسال طلب سحب {bal:.8f} BTC. سيتم مراجعته.", call.message.chat.id, call.message.message_id)
            bot.send_message(ADMIN_ID, f"🟡 طلب سحب من المستخدم {user_id}: {bal:.8f} BTC")
        else:
            bot.edit_message_text("❌ الحد الأدنى للسحب هو 0.0001 BTC", call.message.chat.id, call.message.message_id)

    elif call.data == "ads":
        bot.edit_message_text("📢 سيتم عرض الإعلانات هنا لاحقًا.", call.message.chat.id, call.message.message_id)

    elif call.data == "my_stats":
        data = users_data[user_id]
        stats_msg = (
            f"📊 إحصائياتك:\n"
            f"💰 الرصيد: {data['balance']:.8f} BTC\n"
            f"👥 عدد الإحالات: {len(data['referrals'])}\n"
            f"💸 أرباح الإحالات: {data['referral_earnings']:.8f} BTC\n"
            f"🎁 مرات المكافأة اليومية: {data['daily_bonus_count']}\n"
            f"🕒 آخر نشاط: {data['last_active'].split('T')[0]} {data['last_active'].split('T')[1][:8]}"
        )
        bot.edit_message_text(stats_msg, call.message.chat.id, call.message.message_id)

    elif call.data == "admin_panel" and call.from_user.id == ADMIN_ID:
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✏️ تغيير الترحيب", callback_data="edit_welcome"),
            InlineKeyboardButton("💰 تعديل المكافأة", callback_data="edit_bonus"),
            InlineKeyboardButton("➕ إضافة زر خارجي", callback_data="add_button")
        )
        bot.edit_message_text("🛠 لوحة تحكم الأدمن", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data == "edit_welcome" and call.from_user.id == ADMIN_ID:
        bot.send_message(call.message.chat.id, "✍️ أرسل الرسالة الجديدة للترحيب:")
        bot.register_next_step_handler(call.message, set_welcome)

    elif call.data == "edit_bonus" and call.from_user.id == ADMIN_ID:
        bot.send_message(call.message.chat.id, "💰 أرسل قيمة المكافأة اليومية (مثال: 0.000001):")
        bot.register_next_step_handler(call.message, set_bonus)

    elif call.data == "add_button" and call.from_user.id == ADMIN_ID:
        bot.send_message(call.message.chat.id, "🆕 أرسل النص والرابط بهذا الشكل:\n`زر جديد - https://example.com`")
        bot.register_next_step_handler(call.message, add_button)

def set_welcome(message):
    with open(WELCOME_FILE, "w", encoding="utf-8") as f:
        f.write(message.text)
    bot.send_message(message.chat.id, "✅ تم تحديث رسالة الترحيب.")

def set_bonus(message):
    try:
        val = float(message.text)
        config["daily_bonus"] = val
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f)
        bot.send_message(message.chat.id, f"✅ تم ضبط المكافأة إلى {val}")
    except:
        bot.send_message(message.chat.id, "❌ تأكد من كتابة رقم صحيح.")

def add_button(message):
    try:
        text, url = message.text.split(" - ")
        btns = load_buttons()
        btns.append({"text": text, "url": url})
        with open(BUTTONS_FILE, "w") as f:
            json.dump(btns, f)
        bot.send_message(message.chat.id, "✅ تم إضافة الزر.")
    except:
        bot.send_message(message.chat.id, "❌ تأكد من الشكل: `النص - الرابط`")

bot.infinity_polling()
