import json
import os
import re
import sys
import time
import requests
import telebot
from telebot import types

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
ROOT_ADMIN_ID = int(os.environ.get("ADMIN_ID", "6214336913"))
ENV_ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "netonligaming125").strip().lstrip("@")
WELCOME_VIDEO_URL = os.environ.get("WELCOME_VIDEO_URL", "").strip()

DATA_DIR = os.environ.get("DATA_DIR", "./beda_store_data")
DATA_FILE = os.path.join(DATA_DIR, "store_data.json")
QR_IMAGE_PATH = os.path.join(DATA_DIR, "pay_qr.jpg")

if not BOT_TOKEN:
    print("ERROR: Missing BOT_TOKEN.")
    sys.exit(1)

os.makedirs(DATA_DIR, exist_ok=True)
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

user_states = {}
admin_states = {}

DEFAULT_DATA = {
    "admins": [ROOT_ADMIN_ID],
    "admin_username": ENV_ADMIN_USERNAME or "netonligaming125",
    "button_labels": {
        "buy_now": "🛒 Buy Now / ទិញឥឡូវនេះ",
        "ff_acc": "🎮 លក់អាខោន Mobile Free Fire",
        "diamonds": "💎 Top up / ពេជ្រ ហ្គេម",
        "set_qr": "🖼 កំណត់ QR បង់ប្រាក់",
    },
    "premium_emojis": {
        "buy_now": "",
        "ff_acc": "",
        "diamonds": "",
        "menu": "",
    },
    "diamond_topups": [
        {"id": "dm_ff_100", "game": "Free Fire", "name": "FF 100 Diamonds", "price": 1.15},
        {"id": "dm_ff_310", "game": "Free Fire", "name": "FF 310 Diamonds", "price": 3.20},
        {"id": "dm_ml_86", "game": "MLBB", "name": "MLBB 86 Diamonds", "price": 1.35},
        {"id": "dm_ml_172", "game": "MLBB", "name": "MLBB 172 Diamonds", "price": 2.65},
    ],
    "ff_accounts": [
        {
            "id": "ff_acc_01",
            "name": "FF Mobile Acc #01 (Evo Gun / Vault)",
            "price": 14.00,
            "photo_file_id": "",
            "info_text": "អាខោនស្អាត មាន Evo Gun និង Vault ល្អ",
            "password": "ChangeMe123!",
        },
        {
            "id": "ff_acc_02",
            "name": "FF Mobile Acc #02 (Booyah / Bundle)",
            "price": 22.00,
            "photo_file_id": "",
            "info_text": "មាន Bundle កម្រ និង Booyah Pass ច្រើន",
            "password": "ChangeMe456!",
        },
    ],
    "orders": {},
    "next_order_num": 3001,
    "next_item_num": 101,
}


def load_data():
    if not os.path.exists(DATA_FILE):
        save_data(DEFAULT_DATA)
        return json.loads(json.dumps(DEFAULT_DATA))
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = json.loads(json.dumps(DEFAULT_DATA))

    for k, v in DEFAULT_DATA.items():
        if k not in data:
            data[k] = json.loads(json.dumps(v))

    for bk, bv in DEFAULT_DATA["button_labels"].items():
        data["button_labels"].setdefault(bk, bv)

    for ek, ev in DEFAULT_DATA["premium_emojis"].items():
        data["premium_emojis"].setdefault(ek, ev)

    admin_set = set(int(x) for x in data.get("admins", []) if str(x).isdigit())
    admin_set.add(int(ROOT_ADMIN_ID))
    data["admins"] = sorted(admin_set)
    return data


def save_data(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp_file = DATA_FILE + ".tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, DATA_FILE)


def is_admin(user_id):
    data = load_data()
    return int(user_id) in set(int(x) for x in data.get("admins", []))


def get_admin_username(data=None):
    if data is None:
        data = load_data()
    uname = (data.get("admin_username") or ENV_ADMIN_USERNAME or "netonligaming125").strip()
    return uname.lstrip("@") or "netonligaming125"


def fmt_premium_emoji_html(key, data=None):
    if data is None:
        data = load_data()
    eid = (data.get("premium_emojis", {}).get(key) or "").strip()
    if eid:
        return f'<tg-emoji emoji-id="{eid}">✨</tg-emoji>'
    return ""


def send_styled_message(chat_id, text, rows, parse_mode="HTML", emoji_key=None, data=None):
    prefix = fmt_premium_emoji_html(emoji_key, data) if emoji_key else ""
    final_text = f"{prefix} {text}".strip() if prefix else text

    inline_keyboard = []
    for row in rows:
        api_row = []
        for btn in row:
            item = {"text": btn["text"]}
            if btn.get("callback_data"):
                item["callback_data"] = btn["callback_data"]
            if btn.get("url"):
                item["url"] = btn["url"]
            if btn.get("style"):
                item["style"] = btn["style"]
            if btn.get("icon_custom_emoji_id"):
                item["icon_custom_emoji_id"] = str(btn["icon_custom_emoji_id"]).strip()
            api_row.append(item)
        inline_keyboard.append(api_row)

    payload = {
        "chat_id": chat_id,
        "text": final_text,
        "parse_mode": parse_mode,
        "reply_markup": {"inline_keyboard": inline_keyboard},
    }
    try:
        r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload, timeout=20)
        res = r.json()
        if res.get("ok"):
            return res
    except Exception:
        pass

    kb = types.InlineKeyboardMarkup()
    for row in rows:
        btns = []
        for btn in row:
            if btn.get("url"):
                btns.append(types.InlineKeyboardButton(btn["text"], url=btn["url"]))
            else:
                btns.append(types.InlineKeyboardButton(btn["text"], callback_data=btn.get("callback_data", "noop")))
        kb.add(*btns)
    return bot.send_message(chat_id, final_text, parse_mode=parse_mode, reply_markup=kb)


def main_inline_rows(user_id, data=None):
    if data is None:
        data = load_data()
    lbl = data["button_labels"]
    pe = data["premium_emojis"]

    rows = [
        [
            {
                "text": lbl["buy_now"],
                "callback_data": "menu_buy_now",
                "style": "success",
                "icon_custom_emoji_id": pe.get("buy_now", ""),
            }
        ],
        [
            {
                "text": lbl["ff_acc"],
                "callback_data": "menu_ff_acc",
                "style": "primary",
                "icon_custom_emoji_id": pe.get("ff_acc", ""),
            }
        ],
        [
            {
                "text": lbl["diamonds"],
                "callback_data": "menu_topup_diamonds",
                "style": "success",
                "icon_custom_emoji_id": pe.get("diamonds", ""),
            }
        ],
        [{"text": "📞 ទាក់ទង Admin", "callback_data": "menu_contact_admin", "style": "primary"}],
    ]
    if is_admin(user_id):
        rows.append([{"text": lbl["set_qr"], "callback_data": "admin_set_qr_btn", "style": "primary"}])
    return rows


def send_main_menu(chat_id, user_id, first_name="អ្នកប្រើប្រាស់"):
    data = load_data()
    try:
        rm = bot.send_message(chat_id, "⏳", reply_markup=types.ReplyKeyboardRemove())
        bot.delete_message(chat_id, rm.message_id)
    except Exception:
        pass

    if WELCOME_VIDEO_URL:
        try:
            bot.send_video(chat_id, WELCOME_VIDEO_URL)
        except Exception:
            pass

    send_styled_message(
        chat_id,
        f"សួស្តី <b>{first_name}</b>!\n"
        f"<b>BEDA STORE</b> — ស្វាគមន៍!\n"
        f"សូមជ្រើសរើសមុខងារពី Menu ខាងក្រោម៖",
        main_inline_rows(user_id, data),
        emoji_key="menu",
        data=data,
    )


@bot.message_handler(commands=["start", "menu"])
def cmd_start_menu(message):
    user_states.pop(message.from_user.id, None)
    admin_states.pop(message.from_user.id, None)
    send_main_menu(message.chat.id, message.from_user.id, message.from_user.first_name or "អ្នកប្រើប្រាស់")


@bot.callback_query_handler(func=lambda c: c.data == "open_menu")
def cb_open_menu(call):
    bot.answer_callback_query(call.id)
    user_states.pop(call.from_user.id, None)
    send_main_menu(call.message.chat.id, call.from_user.id, call.from_user.first_name or "អ្នកប្រើប្រាស់")


@bot.callback_query_handler(func=lambda c: c.data == "menu_buy_now")
def handle_buy_now(call):
    bot.answer_callback_query(call.id)
    data = load_data()
    lbl = data["button_labels"]
    send_styled_message(
        call.message.chat.id,
        f"<b>{lbl['buy_now']}</b>\nជ្រើសរើសប្រភេទដែលអ្នកចង់ទិញ៖",
        [
            [{"text": lbl["ff_acc"], "callback_data": "menu_ff_acc", "style": "success"}],
            [{"text": lbl["diamonds"], "callback_data": "menu_topup_diamonds", "style": "primary"}],
            [{"text": "⬅️ ត្រឡប់ទៅ Menu", "callback_data": "open_menu", "style": "primary"}],
        ],
        data=data,
    )


@bot.callback_query_handler(func=lambda c: c.data == "menu_ff_acc")
def handle_ff_accounts(call):
    bot.answer_callback_query(call.id)
    data = load_data()
    accs = data["ff_accounts"]
    if not accs:
        send_styled_message(
            call.message.chat.id,
            "<b>🎮 លក់អាខោន Mobile Free Fire</b>\nបច្ចុប្បន្នអស់ស្ដុកអាខោនបណ្ដោះអាសន្ន។",
            [[{"text": "⬅️ ត្រឡប់ទៅ Menu", "callback_data": "open_menu", "style": "primary"}]],
            data=data,
        )
        return

    rows = []
    for idx, acc in enumerate(accs):
        rows.append([
            {
                "text": f"🎮 {acc['name']} — ${float(acc['price']):.2f}",
                "callback_data": f"view_acc|{acc['id']}",
                "style": "success" if idx % 2 == 0 else "primary",
            }
        ])
    rows.append([{"text": "⬅️ ត្រឡប់ទៅ Menu", "callback_data": "open_menu", "style": "primary"}])
    send_styled_message(call.message.chat.id, "<b>🎮 លក់អាខោន Mobile Free Fire</b>\nជ្រើសរើសអាខោនដែលអ្នកចង់ទិញ៖", rows, data=data)


@bot.callback_query_handler(func=lambda c: c.data.startswith("view_acc|"))
def cb_view_acc(call):
    acc_id = call.data.split("|", 1)[1]
    data = load_data()
    acc = next((x for x in data["ff_accounts"] if x["id"] == acc_id), None)
    if not acc:
        bot.answer_callback_query(call.id, "រកអាខោនមិនឃើញ ឬត្រូវបានលក់/លុបហើយ។", show_alert=True)
        return

    bot.answer_callback_query(call.id)
    caption = (
        f"🎮 <b>{acc['name']}</b>\n"
        f"• តម្លៃ៖ <b>${float(acc['price']):.2f}</b>\n"
        f"• អត្តបទ / ព័ត៌មាន៖ {acc.get('info_text') or '-'}\n\n"
        f"ចុច <b>ទិញអាខោននេះ</b> ដើម្បីបញ្ចូល Contact និងស្កេន QR បង់ប្រាក់។"
    )
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(f"🛒 ទិញអាខោននេះ (${float(acc['price']):.2f})", callback_data=f"buy_item|ff_acc|{acc['id']}"))
    kb.add(types.InlineKeyboardButton("⬅️ ត្រឡប់ទៅបញ្ជីអាខោន", callback_data="menu_ff_acc"))

    if acc.get("photo_file_id"):
        try:
            bot.send_photo(call.message.chat.id, acc["photo_file_id"], caption=caption, reply_markup=kb)
            return
        except Exception:
            pass
    bot.send_message(call.message.chat.id, caption, reply_markup=kb)


@bot.callback_query_handler(func=lambda c: c.data == "menu_topup_diamonds")
def handle_topup_diamonds(call):
    bot.answer_callback_query(call.id)
    data = load_data()
    send_styled_message(
        call.message.chat.id,
        "<b>💎 Top up / ពេជ្រ ហ្គេម</b>\nសូមជ្រើសរើសហ្គេមដែលអ្នកចង់បញ្ចូលពេជ្រ៖",
        [
            [{"text": "🔥 Free Fire", "callback_data": "dm_game|Free Fire", "style": "success"}],
            [{"text": "⚔️ Mobile Legends (MLBB)", "callback_data": "dm_game|MLBB", "style": "primary"}],
            [{"text": "⬅️ ត្រឡប់ទៅ Menu", "callback_data": "open_menu", "style": "primary"}],
        ],
        data=data,
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("dm_game|"))
def cb_diamond_game_packages(call):
    game_name = call.data.split("|", 1)[1]
    bot.answer_callback_query(call.id)
    data = load_data()
    items = [x for x in data["diamond_topups"] if x.get("game", "").lower() == game_name.lower()]
    if not items:
        send_styled_message(
            call.message.chat.id,
            f"<b>💎 Top up — {game_name}</b>\nបច្ចុប្បន្នមិនទាន់មានកញ្ចប់តម្លៃទេ។",
            [[{"text": "⬅️ ត្រឡប់ជ្រើសរើសហ្គេម", "callback_data": "menu_topup_diamonds", "style": "primary"}]],
            data=data,
        )
        return

    rows = []
    for idx, item in enumerate(items):
        rows.append([
            {
                "text": f"💎 {item['name']} — ${float(item['price']):.2f}",
                "callback_data": f"buy_item|diamond|{item['id']}",
                "style": "success" if idx % 2 == 0 else "primary",
            }
        ])
    rows.append([{"text": "⬅️ ត្រឡប់ជ្រើសរើសហ្គេម", "callback_data": "menu_topup_diamonds", "style": "primary"}])
    send_styled_message(call.message.chat.id, f"<b>💎 Top up — {game_name}</b>\nជ្រើសរើសកញ្ចប់ Diamonds ដែលអ្នកចង់បាន៖", rows, data=data)


@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_item|"))
def cb_buy_item(call):
    _, category, item_id = call.data.split("|", 2)
    data = load_data()

    if category == "ff_acc":
        chosen = next((x for x in data["ff_accounts"] if x["id"] == item_id), None)
        if not chosen:
            bot.answer_callback_query(call.id, "រកអាខោនមិនឃើញទេ។", show_alert=True)
            return
        user_states[call.from_user.id] = {
            "step": "awaiting_details",
            "category": "លក់អាខោន Mobile Free Fire",
            "item_id": chosen["id"],
            "item_name": chosen["name"],
            "price": float(chosen["price"]),
            "password": chosen.get("password", ""),
        }
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            f"អ្នកបានជ្រើសរើស៖ <b>{chosen['name']}</b> (${float(chosen['price']):.2f})\n"
            f"សូមផ្ញើ <b>Username / លេខទំនាក់ទំនង</b> របស់អ្នក៖",
        )
        return

    chosen = next((x for x in data["diamond_topups"] if x["id"] == item_id), None)
    if not chosen:
        bot.answer_callback_query(call.id, "រកកញ្ចប់មិនឃើញទេ។", show_alert=True)
        return

    g = chosen.get("game", "")
    prompt_text = (
        "ផ្ញើ <b>User ID និង Server ID</b> (ឧ. <code>123456789 (2024)</code>)៖"
        if g == "MLBB"
        else "ផ្ញើ <b>Free Fire Player UID</b> របស់អ្នក៖"
    )
    user_states[call.from_user.id] = {
        "step": "awaiting_details",
        "category": f"Top up / ពេជ្រ ហ្គេម ({g or 'Game'})",
        "item_id": chosen["id"],
        "item_name": chosen["name"],
        "price": float(chosen["price"]),
        "password": "",
    }
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        f"អ្នកបានជ្រើសរើស៖ <b>{chosen['name']}</b> (${float(chosen['price']):.2f})\nសូម{prompt_text}",
    )


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("step") == "awaiting_details")
def handle_order_details(message):
    uid = message.from_user.id
    details = (message.text or "").strip()
    if not details:
        bot.send_message(message.chat.id, "❌ សូមវាយព័ត៌មានឱ្យបានត្រឹមត្រូវ។")
        return

    st = user_states[uid]
    st["step"] = "awaiting_receipt"
    st["details"] = details

    caption = (
        f"💳 <b>QR បង់ប្រាក់ — BEDA STORE</b>\n"
        f"• សេវាកម្ម៖ <b>{st['category']}</b>\n"
        f"• មុខទំនិញ៖ <b>{st['item_name']}</b>\n"
        f"• តម្លៃត្រូវបង់៖ <b>${st['price']:.2f}</b>\n"
        f"• ព័ត៌មាន៖ <code>{details}</code>\n\n"
        f"១. ស្កេន QR បង់ប្រាក់ឱ្យគ្រប់ចំនួន\n"
        f"២. បាញ់រួច សូម<b>ថតបត / ផ្ញើរូបភាពវិក្កយប័ត្រ</b> មកក្នុង Chat នេះ!"
    )
    if os.path.exists(QR_IMAGE_PATH):
        with open(QR_IMAGE_PATH, "rb") as f_qr:
            bot.send_photo(message.chat.id, f_qr, caption=caption)
    else:
        bot.send_message(
            message.chat.id,
            caption + "\n\n<i>(សូមផ្ញើរូបវិក្កយប័ត្រមកផ្ទាល់ ដើម្បីឱ្យ Admin ពិនិត្យ)</i>",
        )


@bot.message_handler(
    content_types=["photo"],
    func=lambda m: user_states.get(m.from_user.id, {}).get("step") == "awaiting_receipt",
)
def handle_order_receipt(message):
    uid = message.from_user.id
    st = user_states.pop(uid, None)
    if not st:
        return

    receipt_file_id = message.photo[-1].file_id
    data = load_data()
    order_id = f"ORD{data['next_order_num']}"
    data["next_order_num"] += 1

    data["orders"][order_id] = {
        "order_id": order_id,
        "user_id": uid,
        "username": message.from_user.username or "",
        "category": st["category"],
        "item_id": st.get("item_id", ""),
        "item_name": st["item_name"],
        "price": float(st["price"]),
        "details": st["details"],
        "password": st.get("password", ""),
        "receipt_file_id": receipt_file_id,
        "status": "pending",
        "created_at": int(time.time()),
    }
    save_data(data)

    bot.send_message(
        message.chat.id,
        f"✅ បានទទួលវិក្កយប័ត្រសម្រាប់ Order <b>{order_id}</b>!\nកំពុងរង់ចាំ Admin ពិនិត្យ និងអនុម័ត...",
    )

    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("✅ អនុម័ត", callback_data=f"ord_app|{order_id}"),
        types.InlineKeyboardButton("❌ បដិសេធ", callback_data=f"ord_rej|{order_id}"),
    )
    admin_caption = (
        f"🆕 <b>Order ថ្មី: {order_id}</b>\n"
        f"• អ្នកទិញ៖ <code>{uid}</code> (@{message.from_user.username or 'none'})\n"
        f"• សេវាកម្ម៖ <b>{st['category']}</b>\n"
        f"• មុខទំនិញ៖ <b>{st['item_name']}</b> (${st['price']:.2f})\n"
        f"• ព័ត៌មាន៖ <code>{st['details']}</code>"
    )
    for aid in data.get("admins", [ROOT_ADMIN_ID]):
        try:
            bot.send_photo(int(aid), receipt_file_id, caption=admin_caption, reply_markup=kb)
        except Exception:
            pass


@bot.callback_query_handler(func=lambda c: c.data.startswith(("ord_app|", "ord_rej|")))
def cb_admin_order_decision(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "សម្រាប់ Admin ប៉ុណ្ណោះ។", show_alert=True)
        return

    action, order_id = call.data.split("|", 1)
    data = load_data()
    order = data["orders"].get(order_id)
    if not order or order.get("status") != "pending":
        bot.answer_callback_query(call.id, "Order មិនមានឬបានដោះស្រាយរួចហើយ។", show_alert=True)
        return

    buyer_id = int(order["user_id"])
    if action == "ord_app":
        order["status"] = "approved"
        if order.get("item_id"):
            data["ff_accounts"] = [x for x in data["ff_accounts"] if x["id"] != order["item_id"]]
        save_data(data)
        bot.answer_callback_query(call.id, "បានអនុម័ត!")
        try:
            bot.edit_message_caption(f"{call.message.caption or ''}\n\n✅ <b>បានអនុម័ត (APPROVED)</b>", call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        pw_line = f"\n• Password: <code>{order['password']}</code>" if order.get("password") else ""
        try:
            bot.send_message(
                buyer_id,
                f"✅ <b>Order {order_id} ត្រូវបានអនុម័ត!</b>\n"
                f"• មុខទំនិញ៖ <b>{order['item_name']}</b>{pw_line}",
            )
        except Exception:
            pass
    else:
        order["status"] = "rejected"
        save_data(data)
        bot.answer_callback_query(call.id, "បានបដិសេធ!")
        try:
            bot.edit_message_caption(f"{call.message.caption or ''}\n\n❌ <b>បានបដិសេធ (REJECTED)</b>", call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        try:
            bot.send_message(buyer_id, f"❌ <b>Order {order_id} ត្រូវបានបដិសេធ</b>\nសូមទាក់ទង Admin @{get_admin_username(data)}។")
        except Exception:
            pass


@bot.message_handler(commands=["contact"])
def cmd_contact_admin(message):
    send_contact_admin_ui(message.chat.id)


@bot.callback_query_handler(func=lambda c: c.data == "menu_contact_admin")
def cb_menu_contact_admin(call):
    bot.answer_callback_query(call.id)
    send_contact_admin_ui(call.message.chat.id)


def send_contact_admin_ui(chat_id):
    data = load_data()
    uname = get_admin_username(data)
    text = (
        f"<b>📞 ទាក់ទង Admin — BEDA STORE</b>\n"
        f"• Username Admin៖ <b>@{uname}</b>\n\n"
        f"អ្នកអាចចុចប៊ូតុងខាងក្រោមដើម្បីបើក Chat ជាមួយ Admin ឬផ្ញើសារផ្ទាល់តាម Bot៖"
    )
    rows = [
        [{"text": f"💬 ឆាតផ្ទាល់ទៅ @{uname}", "url": f"https://t.me/{uname}"}],
        [{"text": "✉️ ផ្ញើសារទៅ Admin តាម Bot", "callback_data": "contact_send_msg", "style": "success"}],
        [{"text": "⬅️ ត្រឡប់ទៅ Menu", "callback_data": "open_menu", "style": "primary"}],
    ]
    send_styled_message(chat_id, text, rows, data=data)


@bot.callback_query_handler(func=lambda c: c.data == "contact_send_msg")
def cb_contact_send_msg(call):
    bot.answer_callback_query(call.id)
    user_states[call.from_user.id] = {"step": "awaiting_contact_admin_msg"}
    bot.send_message(call.message.chat.id, "សូមវាយ <b>សារ</b> ដែលអ្នកចង់ផ្ញើទៅកាន់ Admin៖")


@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get("step") == "awaiting_contact_admin_msg")
def handle_contact_admin_msg(message):
    uid = message.from_user.id
    msg_txt = (message.text or "").strip()
    if not msg_txt:
        bot.send_message(message.chat.id, "❌ សូមវាយសារជាអក្សរមុនផ្ញើ។")
        return

    user_states.pop(uid, None)
    data = load_data()
    uname = get_admin_username(data)
    bot.send_message(message.chat.id, f"✅ បានផ្ញើសាររបស់អ្នកទៅកាន់ Admin (<b>@{uname}</b>) រួចរាល់!")

    forward_txt = (
        f"✉️ <b>សារទាក់ទង Admin ថ្មី</b>\n"
        f"• អ្នកផ្ញើ៖ <code>{uid}</code> (@{message.from_user.username or 'none'})\n"
        f"• សារ៖ {msg_txt}"
    )
    for aid in data.get("admins", [ROOT_ADMIN_ID]):
        try:
            bot.send_message(int(aid), forward_txt)
        except Exception:
            pass


def send_admin_panel(chat_id):
    data = load_data()
    text = (
        f"<b>⚙️ /admin — ផ្ទាំងគ្រប់គ្រង BEDA STORE</b>\n"
        f"• Username Admin៖ <b>@{get_admin_username(data)}</b>\n"
        f"• ស្ដុកអាខោន FF៖ <b>{len(data['ff_accounts'])}</b>\n"
        f"• កញ្ចប់ពេជ្រហ្គេម៖ <b>{len(data['diamond_topups'])}</b>\n"
        f"• ចំនួន Admin៖ <b>{len(data['admins'])}</b>"
    )
    rows = [
        [{"text": "✏️ កែឈ្មោះប៊ូតុង", "callback_data": "adm_edit_btns", "style": "primary"}],
        [
            {"text": "💲 កំណត់តម្លៃ Top up / ពេជ្រ", "callback_data": "adm_set_price_menu", "style": "success"},
            {"text": "🗑 លុបកញ្ចប់តម្លៃពេជ្រ", "callback_data": "adm_del_dm_menu", "style": "danger"},
        ],
        [
            {"text": "➕ បន្ថែមអាខោនក្នុងស្ដុក", "callback_data": "adm_add_acc_start", "style": "success"},
            {"text": "🗑 លុបអាខោនក្នុងស្ដុក", "callback_data": "adm_del_acc_menu", "style": "danger"},
        ],
        [
            {"text": "👤 Add Admin", "callback_data": "adm_add_admin_start", "style": "primary"},
            {"text": "✏️ កែ Username Admin", "callback_data": "adm_edit_username_start", "style": "success"},
        ],
        [
            {"text": "✨ Add Emoji Premium តាម ID", "callback_data": "adm_emoji_menu", "style": "primary"},
            {"text": "🖼 កំណត់ QR បង់ប្រាក់", "callback_data": "admin_set_qr_btn", "style": "success"},
        ],
        [{"text": "☰ Menu មេ", "callback_data": "open_menu", "style": "primary"}],
    ]
    send_styled_message(chat_id, text, rows, data=data)


@bot.message_handler(commands=["admin"])
def cmd_admin_panel(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ ពាក្យបញ្ជា /admin សម្រាប់ Admin ប៉ុណ្ណោះ។")
        return
    admin_states.pop(message.from_user.id, None)
    send_admin_panel(message.chat.id)


@bot.callback_query_handler(func=lambda c: c.data == "adm_back")
def cb_adm_back(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "សម្រាប់ Admin ប៉ុណ្ណោះ។", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    admin_states.pop(call.from_user.id, None)
    send_admin_panel(call.message.chat.id)


@bot.callback_query_handler(func=lambda c: c.data == "adm_edit_username_start")
def cb_adm_edit_username_start(call):
    if not is_admin(call.from_user.id):
        return
    bot.answer_callback_query(call.id)
    cur_u = get_admin_username()
    admin_states[call.from_user.id] = {"step": "set_admin_username"}
    bot.send_message(
        call.message.chat.id,
        f"Username Admin បច្ចុប្បន្ន៖ <b>@{cur_u}</b>\n"
        f"សូមវាយ <b>Username ថ្មី</b> (ឧ. <code>@NewAdmin</code> ឬ <code>NewAdmin</code>)៖",
    )


@bot.callback_query_handler(func=lambda c: c.data == "adm_edit_btns")
def cb_adm_edit_btns(call):
    if not is_admin(call.from_user.id):
        return
    bot.answer_callback_query(call.id)
    data = load_data()
    lbl = data["button_labels"]
    rows = [
        [{"text": f"Buy Now: {lbl['buy_now']}", "callback_data": "adm_ren_btn|buy_now", "style": "success"}],
        [{"text": f"FF Acc: {lbl['ff_acc']}", "callback_data": "adm_ren_btn|ff_acc", "style": "primary"}],
        [{"text": f"ពេជ្រហ្គេម: {lbl['diamonds']}", "callback_data": "adm_ren_btn|diamonds", "style": "success"}],
        [{"text": f"កំណត់ QR: {lbl['set_qr']}", "callback_data": "adm_ren_btn|set_qr", "style": "primary"}],
        [{"text": "⬅️ ត្រឡប់ /admin", "callback_data": "adm_back", "style": "primary"}],
    ]
    send_styled_message(call.message.chat.id, "<b>✏️ ជ្រើសរើសប៊ូតុងដែលចង់កែឈ្មោះ៖</b>", rows)


@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_ren_btn|"))
def cb_adm_ren_btn_ask(call):
    if not is_admin(call.from_user.id):
        return
    bkey = call.data.split("|", 1)[1]
    bot.answer_callback_query(call.id)
    admin_states[call.from_user.id] = {"step": "rename_btn", "bkey": bkey}
    bot.send_message(call.message.chat.id, f"វាយ <b>ឈ្មោះប៊ូតុងថ្មី</b> សម្រាប់ <code>{bkey}</code>៖")


@bot.callback_query_handler(func=lambda c: c.data == "adm_set_price_menu")
def cb_adm_set_price_menu(call):
    if not is_admin(call.from_user.id):
        return
    bot.answer_callback_query(call.id)
    data = load_data()
    rows = []
    for item in data["diamond_topups"]:
        rows.append([
            {
                "text": f"💎 {item['game']} — {item['name']} (${float(item['price']):.2f})",
                "callback_data": f"adm_price_pick|dm|{item['id']}",
                "style": "primary",
            }
        ])
    for acc in data["ff_accounts"]:
        rows.append([
            {
                "text": f"🎮 {acc['name']} (${float(acc['price']):.2f})",
                "callback_data": f"adm_price_pick|acc|{acc['id']}",
                "style": "success",
            }
        ])
    rows.append([{"text": "➕ បន្ថែមកញ្ចប់ពេជ្រថ្មី", "callback_data": "adm_add_dm_start", "style": "success"}])
    rows.append([{"text": "⬅️ ត្រឡប់ /admin", "callback_data": "adm_back", "style": "primary"}])
    send_styled_message(call.message.chat.id, "<b>💲 ជ្រើសរើសមុខទំនិញ/កញ្ចប់ដើម្បីកំណត់តម្លៃថ្មី៖</b>", rows)


@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_price_pick|"))
def cb_adm_price_pick(call):
    if not is_admin(call.from_user.id):
        return
    _, kind, iid = call.data.split("|", 2)
    bot.answer_callback_query(call.id)
    admin_states[call.from_user.id] = {"step": "set_price_val", "kind": kind, "iid": iid}
    bot.send_message(call.message.chat.id, "វាយ <b>តម្លៃថ្មី (USD)</b> ឧ. <code>2.50</code> ឬ <code>12</code>៖")


@bot.callback_query_handler(func=lambda c: c.data == "adm_add_dm_start")
def cb_adm_add_dm_start(call):
    if not is_admin(call.from_user.id):
        return
    bot.answer_callback_query(call.id)
    admin_states[call.from_user.id] = {"step": "add_dm_game"}
    bot.send_message(call.message.chat.id, "វាយឈ្មោះហ្គេម (ឧ. <code>Free Fire</code> ឬ <code>MLBB</code>)៖")


@bot.callback_query_handler(func=lambda c: c.data == "adm_del_dm_menu")
def cb_adm_del_dm_menu(call):
    if not is_admin(call.from_user.id):
        return
    bot.answer_callback_query(call.id)
    data = load_data()
    rows = []
    for item in data["diamond_topups"]:
        rows.append([
            {
                "text": f"🗑 {item['game']} — {item['name']} (${float(item['price']):.2f})",
                "callback_data": f"adm_del_dm_do|{item['id']}",
                "style": "danger",
            }
        ])
    rows.append([{"text": "⬅️ ត្រឡប់ /admin", "callback_data": "adm_back", "style": "primary"}])
    send_styled_message(call.message.chat.id, "<b>🗑 ជ្រើសរើសកញ្ចប់តម្លៃពេជ្រដើម្បីលុប៖</b>", rows)


@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_del_dm_do|"))
def cb_adm_del_dm_do(call):
    if not is_admin(call.from_user.id):
        return
    iid = call.data.split("|", 1)[1]
    data = load_data()
    data["diamond_topups"] = [x for x in data["diamond_topups"] if x["id"] != iid]
    save_data(data)
    bot.answer_callback_query(call.id, "បានលុបកញ្ចប់ពេជ្ររួចរាល់!")
    cb_adm_del_dm_menu(call)


@bot.callback_query_handler(func=lambda c: c.data == "adm_add_acc_start")
def cb_adm_add_acc_start(call):
    if not is_admin(call.from_user.id):
        return
    bot.answer_callback_query(call.id)
    admin_states[call.from_user.id] = {"step": "acc_name"}
    bot.send_message(call.message.chat.id, "១/៥: វាយ <b>ឈ្មោះអាខោន</b> (ឧ. <code>FF Acc VIP #10</code>)៖")


@bot.message_handler(
    content_types=["photo"],
    func=lambda m: is_admin(m.from_user.id) and admin_states.get(m.from_user.id, {}).get("step") == "acc_photo",
)
def handle_adm_acc_photo(message):
    st = admin_states[message.from_user.id]
    st["photo_file_id"] = message.photo[-1].file_id
    st["step"] = "acc_info"
    bot.send_message(message.chat.id, "៤/៥: វាយ <b>អត្តបទ / ព័ត៌មានអាខោន</b> (ឬវាយ <code>-</code> បើមិនមាន)៖")


@bot.callback_query_handler(func=lambda c: c.data == "adm_del_acc_menu")
def cb_adm_del_acc_menu(call):
    if not is_admin(call.from_user.id):
        return
    bot.answer_callback_query(call.id)
    data = load_data()
    rows = []
    for acc in data["ff_accounts"]:
        rows.append([
            {
                "text": f"🗑 {acc['name']} (${float(acc['price']):.2f})",
                "callback_data": f"adm_del_acc_do|{acc['id']}",
                "style": "danger",
            }
        ])
    rows.append([{"text": "⬅️ ត្រឡប់ /admin", "callback_data": "adm_back", "style": "primary"}])
    send_styled_message(call.message.chat.id, "<b>🗑 ជ្រើសរើសអាខោនក្នុងស្ដុកដើម្បីលុប៖</b>", rows)


@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_del_acc_do|"))
def cb_adm_del_acc_do(call):
    if not is_admin(call.from_user.id):
        return
    aid = call.data.split("|", 1)[1]
    data = load_data()
    data["ff_accounts"] = [x for x in data["ff_accounts"] if x["id"] != aid]
    save_data(data)
    bot.answer_callback_query(call.id, "បានលុបអាខោនចេញពីស្ដុក!")
    cb_adm_del_acc_menu(call)


@bot.callback_query_handler(func=lambda c: c.data == "adm_add_admin_start")
def cb_adm_add_admin_start(call):
    if not is_admin(call.from_user.id):
        return
    bot.answer_callback_query(call.id)
    admin_states[call.from_user.id] = {"step": "add_admin_id"}
    bot.send_message(call.message.chat.id, "វាយ <b>Telegram User ID</b> របស់ Admin ថ្មី (ឧ. <code>123456789</code>)៖")


@bot.callback_query_handler(func=lambda c: c.data == "adm_emoji_menu")
def cb_adm_emoji_menu(call):
    if not is_admin(call.from_user.id):
        return
    bot.answer_callback_query(call.id)
    data = load_data()
    pe = data["premium_emojis"]
    rows = [
        [{"text": f"Menu Emoji ID: {pe.get('menu') or 'none'}", "callback_data": "adm_set_eid|menu", "style": "primary"}],
        [{"text": f"Buy Now Emoji ID: {pe.get('buy_now') or 'none'}", "callback_data": "adm_set_eid|buy_now", "style": "success"}],
        [{"text": f"FF Acc Emoji ID: {pe.get('ff_acc') or 'none'}", "callback_data": "adm_set_eid|ff_acc", "style": "primary"}],
        [{"text": f"ពេជ្រ Emoji ID: {pe.get('diamonds') or 'none'}", "callback_data": "adm_set_eid|diamonds", "style": "success"}],
        [{"text": "⬅️ ត្រឡប់ /admin", "callback_data": "adm_back", "style": "primary"}],
    ]
    send_styled_message(call.message.chat.id, "<b>✨ កំណត់ Custom Emoji ID (Premium) តាម ID៖</b>", rows)


@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_set_eid|"))
def cb_adm_set_eid_ask(call):
    if not is_admin(call.from_user.id):
        return
    ekey = call.data.split("|", 1)[1]
    bot.answer_callback_query(call.id)
    admin_states[call.from_user.id] = {"step": "set_emoji_id", "ekey": ekey}
    bot.send_message(
        call.message.chat.id,
        f"វាយ <b>Custom Emoji ID</b> សម្រាប់ <code>{ekey}</code> (ឧ. <code>5368324170671202286</code> ឬវាយ <code>clear</code> ដើម្បីលុប)៖",
    )


@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.from_user.id in admin_states)
def handle_admin_text_steps(message):
    uid = message.from_user.id
    st = admin_states.get(uid)
    if not st:
        return
    txt = (message.text or "").strip()
    step = st.get("step")
    data = load_data()

    if step == "set_admin_username":
        clean_u = txt.lstrip("@").strip()
        if not clean_u:
            bot.send_message(message.chat.id, "❌ សូមវាយ Username ឱ្យបានត្រឹមត្រូវ។")
            return
        data["admin_username"] = clean_u
        save_data(data)
        admin_states.pop(uid, None)
        bot.send_message(message.chat.id, f"✅ បានកែ Username Admin ទៅជា៖ <b>@{clean_u}</b>")
        send_admin_panel(message.chat.id)

    elif step == "rename_btn":
        if not txt:
            bot.send_message(message.chat.id, "❌ ឈ្មោះមិនអាចទទេបានទេ។")
            return
        data["button_labels"][st["bkey"]] = txt
        save_data(data)
        admin_states.pop(uid, None)
        bot.send_message(message.chat.id, f"✅ បានកែឈ្មោះប៊ូតុងទៅជា៖ <b>{txt}</b>")
        send_admin_panel(message.chat.id)

    elif step == "set_price_val":
        try:
            val = float(txt)
            if val < 0:
                raise ValueError()
        except ValueError:
            bot.send_message(message.chat.id, "❌ សូមវាយតម្លៃជាលេខ (ឧ. <code>1.50</code>)។")
            return
        if st["kind"] == "dm":
            for item in data["diamond_topups"]:
                if item["id"] == st["iid"]:
                    item["price"] = val
        elif st["kind"] == "acc":
            for acc in data["ff_accounts"]:
                if acc["id"] == st["iid"]:
                    acc["price"] = val
        save_data(data)
        admin_states.pop(uid, None)
        bot.send_message(message.chat.id, f"✅ បានកំណត់តម្លៃថ្មី <b>${val:.2f}</b> រួចរាល់!")
        send_admin_panel(message.chat.id)

    elif step == "add_dm_game":
        if not txt:
            bot.send_message(message.chat.id, "❌ សូមវាយឈ្មោះហ្គេម។")
            return
        st["game"] = txt
        st["step"] = "add_dm_name"
        bot.send_message(message.chat.id, "វាយឈ្មោះកញ្ចប់ពេជ្រ (ឧ. <code>FF 520 Diamonds</code>)៖")

    elif step == "add_dm_name":
        if not txt:
            bot.send_message(message.chat.id, "❌ សូមវាយឈ្មោះកញ្ចប់។")
            return
        st["name"] = txt
        st["step"] = "add_dm_price"
        bot.send_message(message.chat.id, "វាយតម្លៃកញ្ចប់ជា USD (ឧ. <code>5.20</code>)៖")

    elif step == "add_dm_price":
        try:
            price = float(txt)
            if price < 0:
                raise ValueError()
        except ValueError:
            bot.send_message(message.chat.id, "❌ សូមវាយតម្លៃជាលេខ។")
            return
        new_id = f"dm_{data['next_item_num']}"
        data["next_item_num"] += 1
        data["diamond_topups"].append({"id": new_id, "game": st["game"], "name": st["name"], "price": price})
        save_data(data)
        admin_states.pop(uid, None)
        bot.send_message(message.chat.id, f"✅ បានបន្ថែមកញ្ចប់ <b>{st['game']} — {st['name']}</b> (${price:.2f})!")
        send_admin_panel(message.chat.id)

    elif step == "acc_name":
        if not txt:
            bot.send_message(message.chat.id, "❌ សូមវាយឈ្មោះអាខោន។")
            return
        st["name"] = txt
        st["step"] = "acc_price"
        bot.send_message(message.chat.id, "២/៥: វាយ <b>តម្លៃអាខោន (USD)</b> ឧ. <code>15.00</code>៖")

    elif step == "acc_price":
        try:
            price = float(txt)
            if price < 0:
                raise ValueError()
        except ValueError:
            bot.send_message(message.chat.id, "❌ សូមវាយតម្លៃជាលេខ។")
            return
        st["price"] = price
        st["step"] = "acc_photo"
        bot.send_message(message.chat.id, "៣/៥: ផ្ញើ <b>រូបភាពអាខោន</b> មកកាន់ Bot នេះ៖")

    elif step == "acc_info":
        st["info_text"] = "" if txt == "-" else txt
        st["step"] = "acc_pw"
        bot.send_message(message.chat.id, "៥/៥: វាយ <b>Password អាខោន</b> (ដើម្បីរក្សាទុកក្នុងស្ដុក)៖")

    elif step == "acc_pw":
        new_id = f"acc_{data['next_item_num']}"
        data["next_item_num"] += 1
        data["ff_accounts"].append({
            "id": new_id,
            "name": st["name"],
            "price": st["price"],
            "photo_file_id": st.get("photo_file_id", ""),
            "info_text": st.get("info_text", ""),
            "password": txt,
        })
        save_data(data)
        admin_states.pop(uid, None)
        bot.send_message(
            message.chat.id,
            f"✅ បានបន្ថែមអាខោនចូលស្ដុករួចរាល់!\n"
            f"• ឈ្មោះ៖ <b>{st['name']}</b> (${st['price']:.2f})\n"
            f"• អត្តបទ៖ {st.get('info_text') or '-'}\n"
            f"• PW៖ <code>{txt}</code>",
        )
        send_admin_panel(message.chat.id)

    elif step == "add_admin_id":
        if not txt.isdigit():
            bot.send_message(message.chat.id, "❌ សូមវាយ User ID ជាលេខតែប៉ុណ្ណោះ។")
            return
        new_aid = int(txt)
        admins = set(int(x) for x in data.get("admins", []))
        admins.add(new_aid)
        data["admins"] = sorted(admins)
        save_data(data)
        admin_states.pop(uid, None)
        bot.send_message(message.chat.id, f"✅ បាន Add Admin ID <code>{new_aid}</code> រួចរាល់!")
        send_admin_panel(message.chat.id)

    elif step == "set_emoji_id":
        val = "" if txt.lower() in ("clear", "none", "-") else txt
        data["premium_emojis"][st["ekey"]] = val
        save_data(data)
        admin_states.pop(uid, None)
        bot.send_message(message.chat.id, f"✅ បានកំណត់ Emoji ID សម្រាប់ <code>{st['ekey']}</code>៖ <code>{val or 'none'}</code>")
        send_admin_panel(message.chat.id)


@bot.callback_query_handler(func=lambda c: c.data == "admin_set_qr_btn")
def cb_admin_set_qr_btn(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "សម្រាប់ Admin ប៉ុណ្ណោះ។", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    admin_states[call.from_user.id] = {"step": "set_qr_photo"}
    bot.send_message(call.message.chat.id, "សូមផ្ញើ <b>រូបភាព QR Code បង់ប្រាក់</b> មកកាន់ Bot នេះ៖")


@bot.message_handler(
    content_types=["photo"],
    func=lambda m: is_admin(m.from_user.id) and admin_states.get(m.from_user.id, {}).get("step") == "set_qr_photo",
)
def handle_set_qr_save(message):
    admin_states.pop(message.from_user.id, None)
    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    downloaded = bot.download_file(file_info.file_path)
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(QR_IMAGE_PATH, "wb") as f_out:
        f_out.write(downloaded)
    bot.send_message(message.chat.id, "✅ បានរក្សាទុករូបភាព QR បង់ប្រាក់រួចរាល់!")
    send_admin_panel(message.chat.id)


def setup_chat_menu_button():
    commands = [
        {"command": "start", "description": "☰ ចាប់ផ្តើម / Menu មេ"},
        {"command": "menu", "description": "📋 បង្ហាញបញ្ជីម៉ឺនុយ"},
        {"command": "contact", "description": "📞 ទាក់ទង Admin"},
        {"command": "admin", "description": "⚙️ ផ្ទាំងគ្រប់គ្រង Admin"},
    ]
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/setMyCommands",
            json={"commands": commands},
            timeout=15,
        )
        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/setChatMenuButton",
            json={"menu_button": {"type": "commands"}},
            timeout=15,
        )
        print("setChatMenuButton:", r.text)
    except Exception as e:
        print("Menu button setup warning:", e)


def extract_retry_after(err_str):
    m = re.search(r"retry after (\d+)", err_str, re.IGNORECASE)
    return int(m.group(1)) if m else 15


if __name__ == "__main__":
    setup_chat_menu_button()
    print("BEDA STORE Bot is running...")
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=20, skip_pending=True)
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "Too Many Requests" in err_str:
                wait_sec = extract_retry_after(err_str) + 3
                print(f"Rate limited (429). Waiting {wait_sec}s...")
                time.sleep(wait_sec)
            else:
                print("Polling error:", err_str)
                time.sleep(5)
