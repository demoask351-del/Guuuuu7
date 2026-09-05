Import sqlite3
import telebot
from telebot import types

BOT_TOKEN = "7657021317:AAH0yKQqbrQw2OMnxJCokSP9jYXtTi_BKyw"
ADMIN_ID = 7161571409

REQUIRED_CHANNELS = [
    {"name": "Proof Channel", "username": "@botlikeproof"},
    {"name": "Earning Channel 1", "username": "@eraningwithask"},
    {"name": "Earning Channel 2", "username": "@eraningwithask9"}
]

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
BOT_USERNAME = bot.get_me().username

def init_db():
    conn = sqlite3.connect("promotion.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, name TEXT, coins INTEGER DEFAULT 30, referred_by INTEGER DEFAULT 0, is_verified INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS campaigns (id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER, channel_username TEXT, needed_joins INTEGER, current_joins INTEGER DEFAULT 0, status TEXT DEFAULT 'ACTIVE')")
    c.execute("CREATE TABLE IF NOT EXISTS history (user_id INTEGER, campaign_id INTEGER, UNIQUE(user_id, campaign_id))")
    c.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value INTEGER)")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('join_reward', 15)")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('refer_reward', 20)")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('cost_per_member', 15)")
    conn.commit()
    conn.close()

init_db()

def get_setting(key, default=15):
    conn = sqlite3.connect("promotion.db")
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else default

def update_setting(key, value):
    conn = sqlite3.connect("promotion.db")
    c = conn.cursor()
    c.execute("UPDATE settings SET value = ? WHERE key = ?", (value, key))
    conn.commit()
    conn.close()

def get_coins(user_id):
    conn = sqlite3.connect("promotion.db")
    c = conn.cursor()
    c.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def check_all_required_channels(user_id):
    for ch in REQUIRED_CHANNELS:
        try:
            member = bot.get_chat_member(ch["username"], user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except Exception:
            return False
    return True

def force_join_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    for ch in REQUIRED_CHANNELS:
        clean = ch["username"].replace("@", "")
        markup.add(types.InlineKeyboardButton(f"📢 Join {ch['name']}", url=f"https://t.me/{clean}"))
    markup.add(types.InlineKeyboardButton("✅ Joined / Verify", callback_data="check_force_join"))
    return markup

def main_menu(user_id):
    coins = get_coins(user_id)
    join_reward = get_setting("join_reward", 15)
    refer_reward = get_setting("refer_reward", 20)
    cost = get_setting("cost_per_member", 15)

    text = (
        "<b>📢 TELEGRAM PROMOTION & REFER NETWORK</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>Aapka Balance:</b> <code>{coins} Coins</code>\n\n"
        f"• Channel Join: <b>+{join_reward} Coins</b>\n"
        f"• Per Refer: <b>+{refer_reward} Coins</b>\n"
        f"• Channel Promo: <b>{cost} Coins / Member</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🚀 Earn Coins", callback_data="earn_0"),
        types.InlineKeyboardButton("➕ Promote Channel", callback_data="add_campaign"),
        types.InlineKeyboardButton("👥 Refer & Earn", callback_data="refer_earn"),
        types.InlineKeyboardButton("📊 My Account", callback_data="my_stats"),
        types.InlineKeyboardButton("🔄 Refresh", callback_data="refresh_menu")
    )
    if int(user_id) == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("⚙️ Master Admin Panel", callback_data="admin_master"))
    return text, markup

@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    name = message.from_user.first_name
    referrer = 0
    parts = message.text.split()
    if len(parts) > 1 and parts[1].startswith("ref_"):
        try:
            p_ref = int(parts[1].replace("ref_", ""))
            if p_ref != uid:
                referrer = p_ref
        except ValueError:
            pass

    conn = sqlite3.connect("promotion.db")
    c = conn.cursor()
    c.execute("SELECT user_id, is_verified FROM users WHERE user_id = ?", (uid,))
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO users (user_id, name, coins, referred_by, is_verified) VALUES (?, ?, 30, ?, 0)", (uid, name, referrer))
        conn.commit()
    conn.close()

    if not check_all_required_channels(uid):
        text = "⚠️ <b>ACCESS DENIED!</b>\n\nBot use karne ke liye pehle 3 channels join karein aur 'Verify' dabayein:"
        bot.send_message(message.chat.id, text, reply_markup=force_join_markup())
        return

    text, markup = main_menu(uid)
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "check_force_join")
def verify_force_join_handler(call):
    uid = call.from_user.id
    if check_all_required_channels(uid):
        conn = sqlite3.connect("promotion.db")
        c = conn.cursor()
        c.execute("SELECT is_verified, referred_by FROM users WHERE user_id = ?", (uid,))
        user_data = c.fetchone()
        if user_data and user_data[0] == 0:
            c.execute("UPDATE users SET is_verified = 1 WHERE user_id = ?", (uid,))
            ref_by = user_data[1]
            if ref_by != 0:
                reward = get_setting("refer_reward", 20)
                c.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (reward, ref_by))
                try:
                    bot.send_message(ref_by, f"🎉 <b>Referral Verified!</b> +{reward} Coins!")
                except Exception:
                    pass
            conn.commit()
        conn.close()
        bot.answer_callback_query(call.id, "✅ Verified!", show_alert=True)
        bot.delete_message(call.message.chat.id, call.message.message_id)
        text, markup = main_menu(uid)
        bot.send_message(call.message.chat.id, text, reply_markup=markup)
    else:
        bot.answer_callback_query(call.id, "❌ Saare channels join nahi hue!", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data == "refresh_menu")
def refresh_callback(call):
    if not check_all_required_channels(call.from_user.id):
        bot.send_message(call.message.chat.id, "⚠️ Pehle channels join karein:", reply_markup=force_join_markup())
        return
    text, markup = main_menu(call.from_user.id)
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception:
        pass

@bot.callback_query_handler(func=lambda c: c.data == "refer_earn")
def refer_earn_callback(call):
    uid = call.from_user.id
    reward = get_setting("refer_reward", 20)
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"
    text = f"<b>👥 REFER & EARN</b>\n━━━━━━━━━━━━━━━━━━━━\nPer Refer: <b>{reward} Coins</b>\n\n🔗 <code>{ref_link}</code>"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Back to Menu", callback_data="refresh_menu"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("earn_"))
def earn_channel_task(call):
    offset = int(call.data.split("_")[1])
    uid = call.from_user.id
    join_reward = get_setting("join_reward", 15)

    conn = sqlite3.connect("promotion.db")
    c = conn.cursor()
    query = "SELECT id, channel_username FROM campaigns WHERE status = 'ACTIVE' AND owner_id != ? AND id NOT IN (SELECT campaign_id FROM history WHERE user_id = ?) LIMIT 1 OFFSET ?"
    c.execute(query, (uid, uid, offset))
    task = c.fetchone()

    c.execute("SELECT COUNT(*) FROM campaigns WHERE status = 'ACTIVE' AND owner_id != ? AND id NOT IN (SELECT campaign_id FROM history WHERE user_id = ?)", (uid, uid))
    total_available = c.fetchone()[0]
    conn.close()

    if not task or offset >= total_available:
        empty_text = "🎉 <b>Tasks Completed!</b>\n\nAbhi ke liye saare channels khatam ho chuke hain."
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Back to Menu", callback_data="refresh_menu"))
        bot.edit_message_text(empty_text, call.message.chat.id, call.message.message_id, reply_markup=markup)
        return

    camp_id, ch_user = task
    clean_handle = ch_user.replace("@", "")
    task_card = f"<b>📢 Tasks: ({offset + 1}/{total_available})</b>\n━━━━━━━━━━━━━━━━━━━━\nChannel: <b>@{clean_handle}</b>\nReward: <b>+{join_reward} Coins</b>"
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔗 Open Channel", url=f"https://t.me/{clean_handle}"),
        types.InlineKeyboardButton("✅ Verify Join", callback_data=f"verify_{camp_id}_{clean_handle}_{offset}")
    )
    markup.add(
        types.InlineKeyboardButton("➡️ Next Channel", callback_data=f"earn_{offset + 1}"),
        types.InlineKeyboardButton("🔙 Back", callback_data="refresh_menu")
    )
    bot.edit_message_text(task_card, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("verify_"))
def verify_task_join(call):
    _, camp_id, clean_handle, offset = call.data.split("_")
    camp_id, offset = int(camp_id), int(offset)
    uid = call.from_user.id
    join_reward = get_setting("join_reward", 15)

    try:
        member = bot.get_chat_member(f"@{clean_handle}", uid)
        if member.status in ['member', 'administrator', 'creator']:
            conn = sqlite3.connect("promotion.db")
            c = conn.cursor()
            c.execute("SELECT 1 FROM history WHERE user_id = ? AND campaign_id = ?", (uid, camp_id))
            if c.fetchone():
                bot.answer_callback_query(call.id, "Already claimed!", show_alert=True)
                conn.close()
                return

            c.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (join_reward, uid))
            c.execute("INSERT INTO history (user_id, campaign_id) VALUES (?, ?)", (uid, camp_id))
            c.execute("UPDATE campaigns SET current_joins = current_joins + 1 WHERE id = ?", (camp_id,))
            c.execute("SELECT owner_id, channel_username, needed_joins, current_joins FROM campaigns WHERE id = ?", (camp_id,))
            camp_info = c.fetchone()
            if camp_info:
                owner_id, ch_name, need, curr = camp_info
                if curr >= need:
                    c.execute("UPDATE campaigns SET status = 'COMPLETED' WHERE id = ?", (camp_id,))
                    try:
                        bot.send_message(owner_id, f"🎯 <b>TARGET COMPLETED!</b>\nChannel: <b>{ch_name}</b>\nJoined: {curr}/{need}")
                    except Exception:
                        pass
            conn.commit()
            conn.close()
            bot.answer_callback_query(call.id, f"✅ +{join_reward} Coins added!", show_alert=True)
            call.data = f"earn_{offset}"
            earn_channel_task(call)
        else:
            bot.answer_callback_query(call.id, "❌ Channel join nahi kiya!", show_alert=True)
    except Exception:
        bot.answer_callback_query(call.id, "⚠️ Channel verification error.", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data == "add_campaign")
def add_campaign_start(call):
    uid = call.from_user.id
    cost = get_setting("cost_per_member", 15)
    if get_coins(uid) < cost:
        bot.answer_callback_query(call.id, f"Kam se kam {cost} coins chahiye!", show_alert=True)
        return
    text = f"⚠️ <b>MANDATORY:</b>\n1. Bot <code>@{BOT_USERNAME}</code> ko channel me ADMIN banayein.\n2. Username bhejein (@MyChannel):"
    msg = bot.send_message(call.message.chat.id, text)
    bot.register_next_step_handler(msg, verify_channel_and_admin)

def verify_channel_and_admin(message):
    ch_user = message.text.strip()
    if not ch_user.startswith("@"):
        bot.send_message(message.chat.id, "❌ '@' ke sath dalein. /start karein.")
        return
    try:
        bot_member = bot.get_chat_member(ch_user, bot.get_me().id)
        if bot_member.status != "administrator":
            bot.send_message(message.chat.id, "❌ Bot Admin nahi hai!")
            return
    except Exception:
        bot.send_message(message.chat.id, "❌ Bot read nahi kar pa raha hai channel ko.")
        return

    cost = get_setting("cost_per_member", 15)
    msg = bot.send_message(message.chat.id, f"✅ <b>Verified!</b> Kitne members chahiye? (1 = {cost} Coins):")
    bot.register_next_step_handler(msg, process_campaign_count, ch_user)

def process_campaign_count(message, ch_user):
    try:
        count = int(message.text.strip())
        if count <= 0:
            raise ValueError
        cost = get_setting("cost_per_member", 15)
        total_cost = count * cost
        uid = message.from_user.id
        if get_coins(uid) < total_cost:
            bot.send_message(message.chat.id, f"❌ Balance kam hai! Chahiye: {total_cost}")
            return
        conn = sqlite3.connect("promotion.db")
        c = conn.cursor()
        c.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (total_cost, uid))
        c.execute("INSERT INTO campaigns (owner_id, channel_username, needed_joins) VALUES (?, ?, ?)", (uid, ch_user, count))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, f"🚀 <b>Campaign Live!</b> Target: {count}")
        text, markup = main_menu(uid)
        bot.send_message(message.chat.id, text, reply_markup=markup)
    except Exception:
        bot.send_message(message.chat.id, "❌ Invalid input!")

@bot.callback_query_handler(func=lambda c: c.data == "admin_master")
def admin_master_panel(call):
    if int(call.from_user.id) != ADMIN_ID:
        return
    j_rew = get_setting("join_reward", 15)
    r_rew = get_setting("refer_reward", 20)
    c_cost = get_setting("cost_per_member", 15)

    conn = sqlite3.connect("promotion.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_u = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM campaigns WHERE status = 'ACTIVE'")
    active_c = c.fetchone()[0]
    conn.close()

    text = (
        "⚙️ <b>ADMIN MASTER DASHBOARD</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Users: <b>{total_u}</b> | 📢 Campaigns: <b>{active_c}</b>\n\n"
        f"• Join: <code>{j_rew}</code> | Refer: <code>{r_rew}</code> | Cost: <code>{c_cost}</code>"
    )
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✏️ Set Join Coins", callback_data="adm_chg_join"),
        types.InlineKeyboardButton("✏️ Set Refer Coins", callback_data="adm_chg_refer"),
        types.InlineKeyboardButton("📋 View Campaigns", callback_data="adm_view_channels"),
        types.InlineKeyboardButton("📊 View User Activity", callback_data="adm_view_users"),
        types.InlineKeyboardButton("🔙 Back", callback_data="refresh_menu")
    )
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "adm_chg_join")
def adm_set_join(call):
    if int(call.from_user.id) != ADMIN_ID:
        return
    msg = bot.send_message(ADMIN_ID, "Naya Join Reward number dalein:")
    bot.register_next_step_handler(msg, lambda m: save_rate(m, "join_reward"))

@bot.callback_query_handler(func=lambda c: c.data == "adm_chg_refer")
def adm_set_refer(call):
    if int(call.from_user.id) != ADMIN_ID:
        return
    msg = bot.send_message(ADMIN_ID, "Naya Refer Reward number dalein:")
    bot.register_next_step_handler(msg, lambda m: save_rate(m, "refer_reward"))

def save_rate(message, key_name):
    try:
        val = int(message.text.strip())
        update_setting(key_name, val)
        bot.send_message(ADMIN_ID, f"✅ Updated! {key_name} = {val} Coins.")
    except Exception:
        bot.send_message(ADMIN_ID, "❌ Number galat hai!")

@bot.callback_query_handler(func=lambda c: c.data == "adm_view_channels")
def adm_view_channels_handler(call):
    if int(call.from_user.id) != ADMIN_ID:
        return
    conn = sqlite3.connect("promotion.db")
    c = conn.cursor()
    c.execute("SELECT id, owner_id, channel_username, needed_joins, current_joins, status FROM campaigns ORDER BY id DESC LIMIT 10")
    camps = c.fetchall()
    conn.close()
    if not camps:
        bot.send_message(ADMIN_ID, "No campaigns found.")
        return

    msg = "📢 <b>RECENT CHANNELS:</b>\n"
    for cp in camps:
        msg += f"#{cp[0]} {cp[2]} | Owner: <code>{cp[1]}</code> | {cp[4]}/{cp[3]} | {cp[5]}\n"

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_master"))
    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "adm_view_users")
def adm_view_users_handler(call):
    if int(call.from_user.id) != ADMIN_ID:
        return
    conn = sqlite3.connect("promotion.db")
    c = conn.cursor()
    q = "SELECT u.user_id, u.name, u.coins, COUNT(h.campaign_id) FROM users u LEFT JOIN history h ON u.user_id = h.user_id GROUP BY u.user_id ORDER BY u.coins DESC LIMIT 10"
    c.execute(q)
    users = c.fetchall()
    conn.close()

    msg = "📊 <b>TOP USERS:</b>\n"
    for idx, u in enumerate(users, 1):
        msg += f"{idx}. {u[1]} (<code>{u[0]}</code>) | 💰 {u[2]} | Joined: {u[3]}\n"

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_master"))
    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "my_stats")
def my_stats_callback(call):
    uid = call.from_user.id
    coins = get_coins(uid)
    conn = sqlite3.connect("promotion.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM history WHERE user_id = ?", (uid,))
    joined = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE referred_by = ? AND is_verified = 1", (uid,))
    referrals = c.fetchone()[0]
    conn.close()

    text = f"<b>📊 ACCOUNT STATS</b>\n━━━━━━━━━━━━━━━━━━━━\n💰 Balance: <b>{coins}</b>\n👥 Referrals: <b>{referrals}</b>\n✅ Completed: <b>{joined}</b>"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="refresh_menu"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

print("🚀 Bot Live without triple-quote syntax issues...")
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running 24/7!")

def run_web():
    server = HTTPServer(('0.0.0.0', 8080), DummyServer)
    server.serve_forever()

print("⚡ Starting Web Server & Promo Bot...")
threading.Thread(target=run_web, daemon=True).start()
bot.infinity_polling()

    
