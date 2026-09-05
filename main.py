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
    kb.add(types.InlineKeyboardButton("✨ Verify & Unlock Bot", callback_data="check_force"))
    return kb

def menu(uid):
    coins = get_coins(uid)
    jr = get_setting('join_reward', 15)
    rr = get_setting('refer_reward', 20)
    cp = get_setting('cost_per_member', 15)
    
    txt = (
        "╔════════════════════════╗\n"
        "   🚀 <b>ADVANCED PROMO NETWORK</b> 🚀\n"
        "╚════════════════════════╝\n"
        f"💎 <b>Wallet Balance:</b> <code>{coins} Coins</code>\n"
        "────────────────────────\n"
        f"🎁 <b>Per Join Reward:</b> <code>+{jr} Coins</code>\n"
        f"👥 <b>Per Refer Bonus:</b> <code>+{rr} Coins</code>\n"
        f"⚡ <b>Campaign Cost:</b> <code>{cp} Coins / Sub</code>\n"
        "────────────────────────\n"
        "<i>Apne channels promote karein aur unlimited organic members payein!</i>"
    )
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("🎯 Earn Coins", callback_data="earn_0"),
        types.InlineKeyboardButton("📢 Promote Channel", callback_data="add_camp"),
        types.InlineKeyboardButton("👥 Refer & Earn", callback_data="ref_sys"),
        types.InlineKeyboardButton("📊 My Account", callback_data="my_stats"),
        types.InlineKeyboardButton("🔄 Refresh Stats", callback_data="refresh")
    )
    if int(uid) == ADMIN_ID:
        kb.add(types.InlineKeyboardButton("⚡ Master Admin Console ⚡", callback_data="adm_panel"))
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
        txt = (
            "╔════════════════════════╗\n"
            "   🔒 <b>ACCESS RESTRICTED</b> 🔒\n"
            "╚════════════════════════╝\n"
            "Bot ke sabhi features unlock karne ke liye niche diye gaye <b>Mandatory Channels</b> ko join karein:"
        )
        bot.send_message(m.chat.id, txt, reply_markup=force_markup())
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
                    bot.send_message(ref_by, f"🎉 <b>Referral Verified!</b>\nAapke dost ne join kiya: <b>+{reward} Coins</b> add ho gaye!")
                except Exception:
                    pass
            conn.commit()
        bot.answer_callback_query(call.id, "✅ Verification Successful!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        t, k = menu(uid)
        bot.send_message(call.message.chat.id, t, reply_markup=k)
    else:
        bot.answer_callback_query(call.id, "❌ Saare channels join nahi hue! Pehle join karein.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "refresh")
def ref_call(call):
    if not check_channels(call.from_user.id):
        bot.send_message(call.message.chat.id, "🔒 Pehle channels join karein:", reply_markup=force_markup())
        return
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
    txt = (
        "╔════════════════════════╗\n"
        "   👥 <b>REFER & EARN SYSTEM</b>\n"
        "╚════════════════════════╝\n"
        f"🎁 <b>Per Verified Invite:</b> <code>+{rr} Coins</code>\n"
        "────────────────────────\n"
        "🔗 <b>Aapka Personal Link:</b>\n"
        f"<code>{link}</code>\n\n"
        "<i>Apne doston ke sath share karein aur unlimited coins earn karein!</i>"
    )
    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Back to Main Menu", callback_data="refresh"))
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
        empty_text = (
            "╔════════════════════════╗\n"
            "   ✨ <b>ALL TASKS COMPLETED</b> ✨\n"
            "╚════════════════════════╝\n"
            "Filhal sabhi channels complete ho chuke hain.\n"
            "Naye campaigns aate hi yahan live ho jayenge!"
        )
        bot.edit_message_text(empty_text, call.message.chat.id, call.message.message_id, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Back to Main Menu", callback_data="refresh")))
        return
        
    camp_id, ch_u = task
    clean = ch_u.replace("@", "")
    card = (
        f"🎯 <b>TASK QUEUE: [{offset+1}/{tot}]</b>\n"
        "────────────────────────\n"
        f"📢 <b>Channel:</b> <code>@{clean}</code>\n"
        f"💰 <b>Reward:</b> <code>+{jr} Coins</code>\n"
        "────────────────────────\n"
        "1. Open karke channel join karein.\n"
        "2. Wapas aakar Verify par tap karein."
    )
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("🔗 Open Channel", url=f"https://t.me/{clean}"),
        types.InlineKeyboardButton("✅ Verify Join", callback_data=f"v_{camp_id}_{clean}_{offset}")
    )
    kb.add(types.InlineKeyboardButton("➡️ Next Channel", callback_data=f"earn_{offset+1}"), types.InlineKeyboardButton("🔙 Back", callback_data="refresh"))
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
                bot.answer_callback_query(call.id, "Reward pehle hi claim ho chuka hai!", show_alert=True)
                return
            c.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (jr, uid))
            c.execute("INSERT INTO history VALUES (?, ?)", (uid, camp_id))
            c.execute("UPDATE campaigns SET current_joins=current_joins+1 WHERE id=?", (camp_id,))
            c.execute("SELECT owner_id, channel_username, needed_joins, current_joins FROM campaigns WHERE id=?", (camp_id,))
            inf = c.fetchone()
            if inf and inf[3] >= inf[2]:
                c.execute("UPDATE campaigns SET status='COMPLETED' WHERE id=?", (camp_id,))
                try:
                    bot.send_message(
                        inf[0], 
                        f"🎉 <b>PROMOTION TARGET REACHED!</b>\n"
                        "────────────────────────\n"
                        f"📢 Channel: <b>{inf[1]}</b>\n"
                        f"👥 Target: <b>{inf[3]}/{inf[2]} Members</b>\n\n"
                        "Aapka campaign successfully finish ho chuka hai!"
                    )
                except Exception:
                    pass
            conn.commit()
            bot.answer_callback_query(call.id, f"🎉 Verified! +{jr} Coins added!", show_alert=True)
            call.data = f"earn_{offset}"
            earn_sys(call)
        else:
            bot.answer_callback_query(call.id, "❌ Channel join nahi mila! Pehle join karein.", show_alert=True)
    except Exception:
        bot.answer_callback_query(call.id, "⚠️ Verification error. Channel settings check karein.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "add_camp")
def add_camp(call):
    uid = call.from_user.id
    cost = get_setting('cost_per_member', 15)
    if get_coins(uid) < cost:
        bot.answer_callback_query(call.id, f"Kam se kam {cost} coins chahiye!", show_alert=True)
        return
    text = (
        "⚙️ <b>PROMOTION SETUP:</b>\n"
        "────────────────────────\n"
        f"1. Bot <code>@{BOT_USERNAME}</code> ko channel me <b>ADMIN</b> banayein.\n"
        "2. Public Username format me bhejein (Example: <code>@MyChannel</code>):"
    )
    msg = bot.send_message(call.message.chat.id, text)
    bot.register_next_step_handler(msg, step_verify_admin)

def step_verify_admin(m):
    ch_u = m.text.strip()
    if not ch_u.startswith("@"):
        bot.send_message(m.chat.id, "❌ Format galat hai! '@' se start karein.")
        return
    try:
        b = bot.get_chat_member(ch_u, bot.get_me().id)
        if b.status != "administrator":
            bot.send_message(m.chat.id, "❌ Bot channel me Admin nahi hai! Pehle Admin banayein.")
            return
    except Exception:
        bot.send_message(m.chat.id, "❌ Bot channel read nahi kar pa raha. Channel Public ho aur bot Admin ho.")
        return
    cost = get_setting('cost_per_member', 15)
    msg = bot.send_message(m.chat.id, f"✅ <b>Channel Verified!</b>\nKitne subscribers chahiye? (1 = <code>{cost} Coins</code>):")
    bot.register_next_step_handler(msg, step_save_camp, ch_u)

def step_save_camp(m, ch_u):
    try:
        cnt = int(m.text.strip())
        cost = get_setting('cost_per_member', 15)
        tot = cnt * cost
        uid = m.from_user.id
        if get_coins(uid) < tot:
            bot.send_message(m.chat.id, f"❌ Insufficient Coins! Chahiye: <code>{tot} Coins</code>.")
            return
        c.execute("UPDATE users SET coins=coins-? WHERE user_id=?", (tot, uid))
        c.execute("INSERT INTO campaigns (owner_id, channel_username, needed_joins) VALUES (?, ?, ?)", (uid, ch_u, cnt))
        conn.commit()
        bot.send_message(m.chat.id, f"🚀 <b>Campaign Live!</b>\nTarget: <code>{cnt} Members</code>. Pura hone par DM me notification mil jayega.")
        t, k = menu(uid)
        bot.send_message(m.chat.id, t, reply_markup=k)
    except Exception:
        bot.send_message(m.chat.id, "❌ Valid number enter karein!")

@bot.callback_query_handler(func=lambda call: call.data == "my_stats")
def stats_show(call):
    uid = call.from_user.id
    coins = get_coins(uid)
    c.execute("SELECT COUNT(*) FROM history WHERE user_id=?", (uid,))
    j = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE referred_by=? AND is_verified=1", (uid,))
    r = c.fetchone()[0]
    txt = (
        "╔════════════════════════╗\n"
        "   📊 <b>ACCOUNT PERFORMANCE</b>\n"
        "╚════════════════════════╝\n"
        f"💎 <b>Current Balance:</b> <code>{coins} Coins</code>\n"
        f"👥 <b>Active Referrals:</b> <code>{r}</code>\n"
        f"✅ <b>Completed Channels:</b> <code>{j}</code>\n"
        "────────────────────────"
    )
    bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Back to Main Menu", callback_data="refresh")))

@bot.callback_query_handler(func=lambda call: call.data == "adm_panel")
def adm_panel(call):
    if int(call.from_user.id) != ADMIN_ID:
        return
    c.execute("SELECT COUNT(*) FROM users")
    u_c = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM campaigns WHERE status='ACTIVE'")
    c_c = c.fetchone()[0]
    j = get_setting("join_reward", 15)
    r = get_setting("refer_reward", 20)
    cost = get_setting("cost_per_member", 15)
    txt = (
        "╔════════════════════════╗\n"
        "   ⚡ <b>MASTER ADMIN CONSOLE</b> ⚡\n"
        "╚════════════════════════╝\n"
        f"👥 <b>Total Users:</b> <code>{u_c}</code>\n"
        f"📢 <b>Active Campaigns:</b> <code>{c_c}</code>\n"
        "────────────────────────\n"
        f"• Join: <code>{j}</code> | Refer: <code>{r}</code> | Cost: <code>{cost}</code>\n"
        "────────────────────────"
    )
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("🎁 Gift Coins", callback_data="adm_gift"),
        types.InlineKeyboardButton("📢 Broadcast", callback_data="adm_broad"),
        types.InlineKeyboardButton("✏️ Join Reward", callback_data="adm_j"),
        types.InlineKeyboardButton("✏️ Refer Reward", callback_data="adm_r"),
        types.InlineKeyboardButton("📋 Campaigns", callback_data="adm_camps"),
        types.InlineKeyboardButton("📊 User Activity", callback_data="adm_users"),
        types.InlineKeyboardButton("🔙 Back to Main Menu", callback_data="refresh")
    )
    bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data == "adm_gift")
def adm_gift_step(call):
    if int(call.from_user.id) != ADMIN_ID:
        return
    msg = bot.send_message(ADMIN_ID, "🎁 <b>Gift Coins Console:</b>\nFormat bhejein: <code>UserID Coins</code>\nExample: <code>7161571409 100</code>")
    bot.register_next_step_handler(msg, process_gift)

def process_gift(m):
    try:
        p = m.text.strip().split()
        target, amt = int(p[0]), int(p[1])
        c.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (amt, target))
        conn.commit()
        try:
            bot.send_message(target, f"🎉 <b>ADMIN BONUS RECEIVED!</b>\nAdmin ne aapke wallet me <b>+{amt} Coins</b> credit kiye hain!")
        except Exception:
            pass
        bot.send_message(ADMIN_ID, f"✅ Successfully added {amt} coins to <code>{target}</code>")
    except Exception:
        bot.send_message(ADMIN_ID, "❌ Format galat tha! Example: <code>7161571409 50</code>")

@bot.callback_query_handler(func=lambda call: call.data == "adm_broad")
def adm_broad_step(call):
    if int(call.from_user.id) != ADMIN_ID:
        return
    msg = bot.send_message(ADMIN_ID, "📢 <b>Global Broadcast Console:</b>\nSabhi users ko jo message bhejna hai, wo type karke bhejein:")
    bot.register_next_step_handler(msg, process_broad)

def process_broad(m):
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    cnt = 0
    for u in users:
        try:
            bot.send_message(u[0], f"📢 <b>ANNOUNCEMENT FROM ADMIN:</b>\n────────────────────────\n\n{m.text}")
            cnt += 1
        except Exception:
            pass
    bot.send_message(ADMIN_ID, f"✅ Broadcast successfully sent to <b>{cnt}</b> users.")

@bot.callback_query_handler(func=lambda call: call.data == "adm_j")
def adm_j_set(call):
    if int(call.from_user.id) != ADMIN_ID:
        return
    msg = bot.send_message(ADMIN_ID, "Naya Join Reward amount dalein:")
    bot.register_next_step_handler(msg, lambda m: save_rate_key(m, "join_reward"))

@bot.callback_query_handler(func=lambda call: call.data == "adm_r")
def adm_r_set(call):
    if int(call.from_user.id) != ADMIN_ID:
        return
    msg = bot.send_message(ADMIN_ID, "Naya Refer Reward amount dalein:")
    bot.register_next_step_handler(msg, lambda m: save_rate_key(m, "refer_reward"))

def save_rate_key(m, key):
    try:
        v = int(m.text.strip())
        set_setting(key, v)
        bot.send_message(ADMIN_ID, f"✅ <code>{key}</code> updated to <b>{v} Coins</b>.")
    except Exception:
        bot.send_message(ADMIN_ID, "❌ Invalid number enter kiya gaya hai!")

@bot.callback_query_handler(func=lambda call: call.data == "adm_camps")
def view_camps(call):
    if int(call.from_user.id) != ADMIN_ID:
        return
    c.execute("SELECT id, channel_username, owner_id, current_joins, needed_joins, status FROM campaigns ORDER BY id DESC LIMIT 10")
    camps = c.fetchall()
    txt = "📢 <b>RECENT CAMPAIGNS QUEUE:</b>\n────────────────────────\n"
    for cp in camps:
        txt += f"<b>#{cp[0]}</b> <code>{cp[1]}</code>\n👤 Owner: <code>{cp[2]}</code> | Progress: <b>{cp[3]}/{cp[4]}</b> | <b>{cp[5]}</b>\n\n"
    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Back to Admin", callback_data="adm_panel"))
    bot.edit_message_text(txt if camps else "Koi campaign active nahi hai.", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data == "adm_users")
def view_users(call):
    if int(call.from_user.id) != ADMIN_ID:
        return
    c.execute("SELECT u.name, u.user_id, u.co
