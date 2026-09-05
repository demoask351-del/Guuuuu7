import sqlite3
import telebot
from telebot import types

BOT_TOKEN = "7657021317:AAH0yKQqbrQw2OMnxJCokSP9jYXtTi_BKyw"
ADMIN_ID = 7161571409
BOT_USERNAME = "Earning_With_Ask_Bot"

REQUIRED_CHANNELS = [
    {"name": "Proof Channel", "username": "@botlikeproof"},
    {"name": "Earning Channel 1", "username": "@eraningwithask"},
    {"name": "Earning Channel 2", "username": "@eraningwithask9"}
]

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

conn = sqlite3.connect("promotion.db", check_same_thread=False)
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, name TEXT, coins INTEGER DEFAULT 30, referred_by INTEGER DEFAULT 0, is_verified INTEGER DEFAULT 0)")
c.execute("CREATE TABLE IF NOT EXISTS campaigns (id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER, channel_username TEXT, needed_joins INTEGER, current_joins INTEGER DEFAULT 0, status TEXT DEFAULT 'ACTIVE')")
c.execute("CREATE TABLE IF NOT EXISTS history (user_id INTEGER, campaign_id INTEGER, UNIQUE(user_id, campaign_id))")
c.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value INTEGER)")
c.execute("INSERT OR IGNORE INTO settings VALUES ('join_reward', 15)")
c.execute("INSERT OR IGNORE INTO settings VALUES ('refer_reward', 20)")
c.execute("INSERT OR IGNORE INTO settings VALUES ('cost_per_member', 15)")
conn.commit()

def get_setting(k, d=15):
    c.execute("SELECT value FROM settings WHERE key=?", (k,))
    r = c.fetchone()
    return r[0] if r else d

def set_setting(k, v):
    c.execute("UPDATE settings SET value=? WHERE key=?", (v, k))
    conn.commit()

def get_coins(uid):
    c.execute("SELECT coins FROM users WHERE user_id=?", (uid,))
    r = c.fetchone()
    return r[0] if r else 0

def check_channels(uid):
    for ch in REQUIRED_CHANNELS:
        try:
            m = bot.get_chat_member(ch["username"], uid)
            if m.status not in ['member', 'administrator', 'creator']:
                return False
        except Exception:
            return False
    return True

def force_markup():
    kb = types.InlineKeyboardMarkup(row_width=1)
    for ch in REQUIRED_CHANNELS:
        kb.add(types.InlineKeyboardButton(f"📢 Join {ch['name']}", url=f"https://t.me/{ch['username'].replace('@','')}"))
    kb.add(types.InlineKeyboardButton("✨ Verify Channels", callback_data="check_force"))
    return kb

def menu(uid):
    coins = get_coins(uid)
    jr = get_setting('join_reward', 15)
    rr = get_setting('refer_reward', 20)
    cp = get_setting('cost_per_member', 15)
    txt = f"⚡ <b>PROMO BOOST NETWORK</b> ⚡\n\n💎 <b>Balance:</b> <code>{coins} Coins</code>\n🎁 <b>Per Join:</b> +{jr} Coins\n👥 <b>Per Refer:</b> +{rr} Coins\n🚀 <b>Promo Cost:</b> {cp} Coins/Sub"
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("🎯 Earn Coins", callback_data="earn_0"),
        types.InlineKeyboardButton("📢 Promote Channel", callback_data="add_camp"),
        types.InlineKeyboardButton("👥 Refer & Earn", callback_data="ref_sys"),
        types.InlineKeyboardButton("📊 Dashboard", callback_data="my_stats"),
        types.InlineKeyboardButton("🔄 Refresh", callback_data="refresh")
    )
    if int(uid) == ADMIN_ID:
        kb.add(types.InlineKeyboardButton("⚡ Admin Panel ⚡", callback_data="adm_panel"))
    return txt, kb

@bot.message_handler(commands=['start'])
def start_cmd(m):
    uid = m.from_user.id
    name = m.from_user.first_name
    ref = 0
    p = m.text.split()
    if len(p) > 1 and p[1].startswith("ref_"):
        try:
            val = int(p[1].replace("ref_", ""))
            if val != uid:
                ref = val
        except Exception:
            pass
    c.execute("SELECT user_id FROM users WHERE user_id=?", (uid,))
    if not c.fetchone():
        c.execute("INSERT INTO users (user_id, name, coins, referred_by, is_verified) VALUES (?, ?, 30, ?, 0)", (uid, name, ref))
        conn.commit()
    if not check_channels(uid):
        bot.send_message(m.chat.id, "🔒 <b>Pehle ye channels join karein:</b>", reply_markup=force_markup())
        return
    t, k = menu(uid)
    bot.send_message(m.chat.id, t, reply_markup=k)

@bot.callback_query_handler(func=lambda call: call.data == "check_force")
def verify_force(call):
    uid = call.from_user.id
    if check_channels(uid):
        c.execute("SELECT is_verified, referred_by FROM users WHERE user_id=?", (uid,))
        r = c.fetchone()
        if r and r[0] == 0:
            c.execute("UPDATE users SET is_verified=1 WHERE user_id=?", (uid,))
            ref_by = r[1]
            if ref_by != 0:
                reward = get_setting('refer_reward', 20)
                c.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (reward, ref_by))
                try:
                    bot.send_message(ref_by, f"🎉 Referral verified! +{reward} Coins added.")
                except Exception:
                    pass
            conn.commit()
        bot.answer_callback_query(call.id, "✅ Verified!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        t, k = menu(uid)
        bot.send_message(call.message.chat.id, t, reply_markup=k)
    else:
        bot.answer_callback_query(call.id, "❌ Saare channel join karo pehle!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "refresh")
def ref_call(call):
    t, k = menu(call.from_user.id)
    try:
        bot.edit_message_text(t, call.message.chat.id, call.message.message_id, reply_markup=k)
    except Exception:
        pass

@bot.callback_query_handler(func=lambda call: call.data == "ref_sys")
def ref_show(call):
    uid = call.from_user.id
    rr = get_setting('refer_reward', 20)
    link = f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"
    txt = f"👥 <b>REFER & EARN</b>\n\nReward: <b>+{rr} Coins</b>\n\n🔗 <code>{link}</code>"
    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Back", callback_data="refresh"))
    bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("earn_"))
def earn_sys(call):
    offset = int(call.data.split("_")[1])
    uid = call.from_user.id
    jr = get_setting('join_reward', 15)
    c.execute("SELECT id, channel_username FROM campaigns WHERE status='ACTIVE' AND owner_id!=? AND id NOT IN (SELECT campaign_id FROM history WHERE user_id=?) LIMIT 1 OFFSET ?", (uid, uid, offset))
    task = c.fetchone()
    c.execute("SELECT COUNT(*) FROM campaigns WHERE status='ACTIVE' AND owner_id!=? AND id NOT IN (SELECT campaign_id FROM history WHERE user_id=?)", (uid, uid))
    tot = c.fetchone()[0]
    if not task or offset >= tot:
        bot.edit_message_text("✨ <b>Saare tasks complete ho gaye!</b>", call.message.chat.id, call.message.message_id, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Back", callback_data="refresh")))
        return
    camp_id, ch_u = task
    clean = ch_u.replace("@", "")
    card = f"🎯 <b>Task ({offset+1}/{tot})</b>\n\nChannel: @{clean}\nReward: +{jr} Coins"
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("🔗 Open", url=f"https://t.me/{clean}"),
        types.InlineKeyboardButton("✅ Verify", callback_data=f"v_{camp_id}_{clean}_{offset}")
    )
    kb.add(types.InlineKeyboardButton("➡️ Next", callback_data=f"earn_{offset+1}"), types.InlineKeyboardButton("🔙 Back", callback_data="refresh"))
    bot.edit_message_text(card, call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("v_"))
def v_task(call):
    _, camp_id, clean, offset = call.data.split("_")
    camp_id, offset, uid = int(camp_id), int(offset), call.from_user.id
    jr = get_setting('join_reward', 15)
    try:
        m = bot.get_chat_member(f"@{clean}", uid)
        if m.status in ['member', 'administrator', 'creator']:
            c.execute("SELECT 1 FROM history WHERE user_id=? AND campaign_id=?", (uid, camp_id))
            if c.fetchone():
                bot.answer_callback_query(call.id, "Already Claimed!")
                return
            c.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (jr, uid))
            c.execute("INSERT INTO history VALUES (?, ?)", (uid, camp_id))
            c.execute("UPDATE campaigns SET current_joins=current_joins+1 WHERE id=?", (camp_id,))
            c.execute("SELECT owner_id, channel_username, needed_joins, current_joins FROM campaigns WHERE id=?", (camp_id,))
            inf = c.fetchone()
            if inf and inf[3] >= inf[2]:
                c.execute("UPDATE campaigns SET status='COMPLETED' WHERE id=?", (camp_id,))
                try:
                    bot.send_message(inf[0], f"🎉 Target complete for {inf[1]} ({inf[3]}/{inf[2]})")
                except Exception:
                    pass
            conn.commit()
            bot.answer_callback_query(call.id, f"✅ +{jr} Coins added!", show_alert=True)
            call.data = f"earn_{offset}"
            earn_sys(call)
        else:
            bot.answer_callback_query(call.id, "❌ Join nahi kiya!", show_alert=True)
    except Exception:
        bot.answer_callback_query(call.id, "⚠️ Verification error.")

@bot.callback_query_handler(func=lambda call: call.data == "add_camp")
def add_camp(call):
    uid = call.from_user.id
    cost = get_setting('cost_per_member', 15)
    if get_coins(uid) < cost:
        bot.answer_callback_query(call.id, f"Kam se kam {cost} coins chahiye!", show_alert=True)
        return
    msg = bot.send_message(call.message.chat.id, f"1. Bot @{BOT_USERNAME} ko channel me ADMIN banao.\n2. Username bhejo (@MyChannel):")
    bot.register_next_step_handler(msg, step_verify_admin)

def step_verify_admin(m):
    ch_u = m.text.strip()
    if not ch_u.startswith("@"):
        bot.send_message(m.chat.id, "❌ '@' se likho.")
        return
    try:
        b = bot.get_chat_member(ch_u, bot.get_me().id)
        if b.status != "administrator":
            bot.send_message(m.chat.id, "❌ Bot Admin nahi hai!")
            return
    except Exception:
        bot.send_message(m.chat.id, "❌ Bot channel read nahi kar pa raha.")
        return
    cost = get_setting('cost_per_member', 15)
    msg = bot.send_message(m.chat.id, f"✅ Verified! Kitne members chahiye? (1 = {cost} Coins):")
    bot.register_next_step_handler(msg, step_save_camp, ch_u)

def step_save_camp(m, ch_u):
    try:
        cnt = int(m.text.strip())
        cost = get_setting('cost_per_member', 15)
        tot = cnt * cost
        uid = m.from_user.id
        if get_coins(uid) < tot:
            bot.send_message(m.chat.id, f"❌ Balance kam hai! Chahiye: {tot}")
            return
        c.execute("UPDATE users SET coins=coins-? WHERE user_id=?", (tot, uid))
        c.execute("INSERT INTO campaigns (owner_id, channel_username, needed_joins) VALUES (?, ?, ?)", (uid, ch_u, cnt))
        conn.commit()
        bot.send_message(m.chat.id, f"🚀 Campaign Live: {cnt} members")
        t, k = menu(uid)
        bot.send_message(m.chat.id, t, reply_markup=k)
    except Exception:
        bot.send_message(m.chat.id, "❌ Invalid number.")

@bot.callback_query_handler(func=lambda call: call.data == "my_stats")
def stats_show(call):
    uid = call.from_user.id
    coins = get_coins(uid)
    c.execute("SELECT COUNT(*) FROM history WHERE user_id=?", (uid,))
    j = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE referred_by=? AND is_verified=1", (uid,))
    r = c.fetchone()[0]
    txt = f"📊 <b>STATS</b>\n\n💰 Coins: {coins}\n👥 Referrals: {r}\n✅ Joined: {j}"
    bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Back", callback_data="refresh")))

@bot.callback_query_handler(func=lambda call: call.data == "adm_panel")
def adm_panel(call):
    if int(call.from_user.id) != ADMIN_ID:
        return
    c.execute("SELECT COUNT(*) FROM users")
    u_c = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM campaigns WHERE status='ACTIVE'")
    c_c = c.fetchone()[0]
    txt = f"⚡ <b>ADMIN CONSOLE</b> ⚡\n\nUsers: {u_c} | Campaigns: {c_c}"
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("🎁 Gift Coins", callback_data="adm_gift"),
        types.InlineKeyboardButton("📢 Broadcast", callback_data="adm_broad"),
        types.InlineKeyboardButton("✏️ Join Reward", callback_data="adm_j"),
        types.InlineKeyboardButton("✏️ Refer Reward", callback_data="adm_r"),
        types.InlineKeyboardButton("🔙 Back", callback_data="refresh")
    )
    bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data == "adm_gift")
def adm_gift_step(call):
    if int(call.from_user.id) != ADMIN_ID:
        return
    msg = bot.send_message(ADMIN_ID, "Format: <code>UserID Coins</code> (Example: <code>7161571409 50</code>):")
    bot.register_next_step_handler(msg, process_gift)

def process_gift(m):
    try:
        p = m.text.strip().split()
        target, amt = int(p[0]), int(p[1])
        c.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (amt, target))
        conn.commit()
        try:
            bot.send_message(target, f"🎉 Admin ne aapko +{amt} coins diye!")
        except Exception:
            pass
        bot.send_message(ADMIN_ID, f"✅ Credited {amt} coins to {target}")
    except Exception:
        bot.send_message(ADMIN_ID, "❌ Format galat tha.")

@bot.callback_query_handler(func=lambda call: call.data == "adm_broad")
def adm_broad_step(call):
    if int(call.from_user.id) != ADMIN_ID:
        return
    msg = bot.send_message(ADMIN_ID, "Broadcast message likho:")
    bot.register_next_step_handler(msg, process_broad)

def process_broad(m):
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    cnt = 0
    for u in users:
        try:
            bot.send_message(u[0], f"📢 <b>ADMIN:</b>\n\n{m.text}")
            cnt += 1
        except Exception:
            pass
    bot.send_message(ADMIN_ID, f"✅ Broadcast sent to {cnt} users.")

@bot.callback_query_handler(func=lambda call: call.data == "adm_j")
def adm_j_set(call):
    if int(call.from_user.id) != ADMIN_ID:
        return
    msg = bot.send_message(ADMIN_ID, "Naya Join Reward amount:")
    bot.register_next_step_handler(msg, lambda m: save_rate_key(m, "join_reward"))

@bot.callback_query_handler(func=lambda call: call.data == "adm_r")
def adm_r_set(call):
    if int(call.from_user.id) != ADMIN_ID:
        return
    msg = bot.send_message(ADMIN_ID, "Naya Refer Reward amount:")
    bot.register_next_step_handler(msg, lambda m: save_rate_key(m, "refer_reward"))

def save_rate_key(m, key):
    try:
        v = int(m.text.strip())
        set_setting(key, v)
        bot.send_message(ADMIN_ID, f"✅ {key} set to {v}")
    except Exception:
        bot.send_message(ADMIN_ID, "❌ Invalid number.")

print("Bot started...")
bot.infinity_polling()
                      
