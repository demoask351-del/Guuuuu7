import sqlite3
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot import types

# ==================== CONFIGURATION ====================
BOT_TOKEN = "7657021317:AAH0yKQqbrQw2OMnxJCokSP9jYXtTi_BKyw"
ADMIN_ID = 7161571409

# Fetch actual bot credentials dynamically from Telegram server
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
BOT_INFO = bot.get_me()
BOT_USERNAME = BOT_INFO.username
BOT_ID = BOT_INFO.id

# Mandatory channels that users must join before using the bot
REQUIRED_CHANNELS = [
    {"name": "Proof Channel", "username": "@botlikeproof"},
    {"name": "Earning Channel 1", "username": "@eraningwithask"},
    {"name": "Earning Channel 2", "username": "@eraningwithask9"}
]

# ==================== DATABASE INITIALIZATION ====================
conn = sqlite3.connect("promotion.db", check_same_thread=False)
c = conn.cursor()

def init_database():
    """Initializes all required SQLite tables and default settings."""
    c.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, name TEXT, coins INTEGER DEFAULT 30, referred_by INTEGER DEFAULT 0, is_verified INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS campaigns (id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER, channel_username TEXT, needed_joins INTEGER, current_joins INTEGER DEFAULT 0, status TEXT DEFAULT 'ACTIVE')")
    c.execute("CREATE TABLE IF NOT EXISTS history (user_id INTEGER, campaign_id INTEGER, UNIQUE(user_id, campaign_id))")
    c.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value INTEGER)")
    
    # Default system rates configuration
    c.execute("INSERT OR IGNORE INTO settings VALUES ('join_reward', 15)")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('refer_reward', 20)")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('cost_per_member', 15)")
    conn.commit()

init_database()

# ==================== HELPER FUNCTIONS ====================
def get_setting(key, default=15):
    """Retrieves dynamic configuration values from the database."""
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = c.fetchone()
    return row[0] if row else default

def set_setting(key, value):
    """Updates dynamic configuration values in the database."""
    c.execute("UPDATE settings SET value=? WHERE key=?", (value, key))
    conn.commit()

def get_coins(user_id):
    """Fetches the current coin balance of a specific user."""
    c.execute("SELECT coins FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    return row[0] if row else 0

def check_channels(user_id):
    """Verifies if a user has joined all mandatory channels."""
    for ch in REQUIRED_CHANNELS:
        try:
            member = bot.get_chat_member(ch["username"], user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except Exception:
            return False
    return True

# ==================== KEYBOARDS & MENUS ====================
def force_markup():
    """Generates inline buttons for mandatory channel subscription verification."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    for ch in REQUIRED_CHANNELS:
        clean_name = ch["username"].replace("@", "")
        markup.add(types.InlineKeyboardButton(f"📢 Join {ch['name']}", url=f"https://t.me/{clean_name}"))
    markup.add(types.InlineKeyboardButton("✨ Verify Channels", callback_data="check_force"))
    return markup

def main_menu(user_id):
    """Generates the main dashboard interface with live user stats and rewards."""
    coins = get_coins(user_id)
    join_reward = get_setting('join_reward', 15)
    refer_reward = get_setting('refer_reward', 20)
    promo_cost = get_setting('cost_per_member', 15)
    
    text = (
        "╔════════════════════════╗\n"
        "   ⚡ <b>PROMO BOOST NETWORK</b> ⚡\n"
        "╚════════════════════════╝\n"
        f"💎 <b>Wallet Balance:</b> <code>{coins} Coins</code>\n"
        "────────────────────────\n"
        f"🎁 <b>Per Join Reward:</b> <code>+{join_reward} Coins</code>\n"
        f"👥 <b>Per Refer Bonus:</b> <code>+{refer_reward} Coins</code>\n"
        f"🚀 <b>Promotion Cost:</b> <code>{promo_cost} Coins / Sub</code>\n"
        "────────────────────────\n"
        "<i>Apne channels promote karein aur organic members earn karein!</i>"
    )
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🎯 Earn Coins", callback_data="earn_0"),
        types.InlineKeyboardButton("📢 Promote Channel", callback_data="add_camp"),
        types.InlineKeyboardButton("👥 Refer & Earn", callback_data="ref_sys"),
        types.InlineKeyboardButton("📊 Dashboard", callback_data="my_stats"),
        types.InlineKeyboardButton("🔄 Refresh Stats", callback_data="refresh")
    )
    
    # Inject Master Admin Console button dynamically if user matches ADMIN_ID
    if int(user_id) == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("⚡ Master Admin Panel ⚡", callback_data="adm_panel"))
        
    return text, markup

# ==================== HANDLERS: START & VERIFICATION ====================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    """Handles the /start command, registers new users, and processes referral tags."""
    uid = message.from_user.id
    name = message.from_user.first_name
    referrer_id = 0
    
    # Parse Deep-Linking referral arguments (e.g., /start ref_123456)
    parts = message.text.split()
    if len(parts) > 1 and parts[1].startswith("ref_"):
        try:
            parsed_ref = int(parts[1].replace("ref_", ""))
            if parsed_ref != uid:
                referrer_id = parsed_ref
        except Exception:
            pass
            
    # Register user in database if not already present
    c.execute("SELECT user_id FROM users WHERE user_id=?", (uid,))
    if not c.fetchone():
        c.execute("INSERT INTO users (user_id, name, coins, referred_by, is_verified) VALUES (?, ?, 30, ?, 0)", (uid, name, referrer_id))
        conn.commit()
        
    # Check if user has completed mandatory channel subscriptions
    if not check_channels(uid):
        warning_msg = (
            "╔════════════════════════╗\n"
            "   🔒 <b>ACCESS RESTRICTED</b> 🔒\n"
            "╚════════════════════════╝\n"
            "Bot ke sabhi features unlock karne ke liye niche diye gaye channels join karein:"
        )
        bot.send_message(message.chat.id, warning_msg, reply_markup=force_markup())
        return
        
    text, markup = main_menu(uid)
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_force")
def verify_force_subscription(call):
    """Verifies channel join status and distributes referral bonuses accordingly."""
    uid = call.from_user.id
    if check_channels(uid):
        c.execute("SELECT is_verified, referred_by FROM users WHERE user_id=?", (uid,))
        user_row = c.fetchone()
        
        if user_row and user_row[0] == 0:
            c.execute("UPDATE users SET is_verified=1 WHERE user_id=?", (uid,))
            ref_by = user_row[1]
            
            # Distribute referral commission if valid referrer exists
            if ref_by != 0:
                referral_bonus = get_setting('refer_reward', 20)
                c.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (referral_bonus, ref_by))
                try:
                    bot.send_message(ref_by, f"🎉 <b>Referral Verified!</b>\nAapke invited user ne verify kiya: <b>+{referral_bonus} Coins</b> add ho gaye!")
                except Exception:
                    pass
            conn.commit()
            
        bot.answer_callback_query(call.id, "✅ Verification Successful!")
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
            
        text, markup = main_menu(uid)
        bot.send_message(call.message.chat.id, text, reply_markup=markup)
    else:
        bot.answer_callback_query(call.id, "❌ Pehle saare mandatory channels join karein!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "refresh")
def refresh_dashboard(call):
    """Refreshes the main control panel UI safely."""
    if not check_channels(call.from_user.id):
        bot.send_message(call.message.chat.id, "🔒 Pehle channels join karein:", reply_markup=force_markup())
        return
    text, markup = main_menu(call.from_user.id)
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception:
        pass

# ==================== HANDLERS: REFERRAL & EARN TASKS ====================
@bot.callback_query_handler(func=lambda call: call.data == "ref_sys")
def display_referral_system(call):
    """Displays the user's personal invitation link and referral earnings system info."""
    uid = call.from_user.id
    referral_reward = get_setting('refer_reward', 20)
    invite_link = f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"
    
    text = (
        "╔════════════════════════╗\n"
        "   👥 <b>REFER & EARN SYSTEM</b>\n"
        "╚════════════════════════╝\n"
        f"🎁 <b>Per Verified Invite:</b> <code>+{referral_reward} Coins</code>\n"
        "────────────────────────\n"
        "🔗 <b>Aapka Personal Invite Link:</b>\n"
        f"<code>{invite_link}</code>\n\n"
        "<i>Apne link ko doston ke sath share karein aur unlimited earnings karein!</i>"
    )
    markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Back to Main Menu", callback_data="refresh"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("earn_"))
def handle_earning_tasks_pagination(call):
    """Handles pagination and display of active promotional channel tasks."""
    offset = int(call.data.split("_")[1])
    uid = call.from_user.id
    join_reward = get_setting('join_reward', 15)
    
    # Fetch active campaigns excluding user's own campaigns and already completed tasks
    query = "SELECT id, channel_username FROM campaigns WHERE status='ACTIVE' AND owner_id!=? AND id NOT IN (SELECT campaign_id FROM history WHERE user_id=?) LIMIT 1 OFFSET ?"
    c.execute(query, (uid, uid, offset))
    task = c.fetchone()
    
    c.execute("SELECT COUNT(*) FROM campaigns WHERE status='ACTIVE' AND owner_id!=? AND id NOT IN (SELECT campaign_id FROM history WHERE user_id=?)", (uid, uid))
    total_tasks = c.fetchone()[0]
    
    if not task or offset >= total_tasks:
        completion_text = (
            "╔════════════════════════╗\n"
            "   ✨ <b>ALL TASKS COMPLETED</b> ✨\n"
            "╚════════════════════════╝\n"
            "Abhi ke liye sabhi promotional tasks complete ho chuke hain.\n"
            "Naye campaigns aate hi yahan live ho jayenge!"
        )
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Back to Main Menu", callback_data="refresh"))
        bot.edit_message_text(completion_text, call.message.chat.id, call.message.message_id, reply_markup=markup)
        return
        
    campaign_id, channel_handle = task
    clean_handle = channel_handle.replace("@", "")
    
    task_card = (
        f"🎯 <b>PROMO TASK QUEUE: [{offset+1}/{total_tasks}]</b>\n"
        "────────────────────────\n"
        f"📢 <b>Channel:</b> <code>@{clean_handle}</code>\n"
        f"💰 <b>Reward:</b> <code>+{join_reward} Coins</code>\n"
        "────────────────────────\n"
        "1. Open karke channel join karein.\n"
        "2. Wapas aakar Verify par tap karein."
    )
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔗 Open Channel", url=f"https://t.me/{clean_handle}"),
        types.InlineKeyboardButton("✅ Verify Join", callback_data=f"v_{campaign_id}_{clean_handle}_{offset}")
    )
    markup.add(
        types.InlineKeyboardButton("➡️ Next Task", callback_data=f"earn_{offset+1}"),
        types.InlineKeyboardButton("🔙 Back", callback_data="refresh")
    )
    bot.edit_message_text(task_card, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("v_"))
def verify_earning_task(call):
    """Validates user membership in campaign channels and credits reward coins."""
    _, campaign_id, clean_handle, offset = call.data.split("_")
    campaign_id, offset, uid = int(campaign_id), int(offset), call.from_user.id
    join_reward = get_setting('join_reward', 15)
    
    try:
        member_status = bot.get_chat_member(f"@{clean_handle}", uid)
        if member_status.status in ['member', 'administrator', 'creator']:
            c.execute("SELECT 1 FROM history WHERE user_id=? AND campaign_id=?", (uid, campaign_id))
            if c.fetchone():
                bot.answer_callback_query(call.id, "Reward pehle hi claim kiya ja chuka hai!", show_alert=True)
                return
                
            # Credit reward and record transaction history
            c.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (join_reward, uid))
            c.execute("INSERT INTO history VALUES (?, ?)", (uid, campaign_id))
            c.execute("UPDATE campaigns SET current_joins=current_joins+1 WHERE id=?", (campaign_id,))
            
            # Check if campaign target has been fulfilled
            c.execute("SELECT owner_id, channel_username, needed_joins, current_joins FROM campaigns WHERE id=?", (campaign_id,))
            campaign_info = c.fetchone()
            if campaign_info and campaign_info[3] >= campaign_info[2]:
                c.execute("UPDATE campaigns SET status='COMPLETED' WHERE id=?", (campaign_id,))
                try:
                    bot.send_message(
                        campaign_info[0],
                        f"🎯 <b>PROMOTION TARGET COMPLETED!</b>\n"
                        "────────────────────────\n"
                        f"📢 Channel: <b>{campaign_info[1]}</b>\n"
                        f"👥 Progress: <b>{campaign_info[3]}/{campaign_info[2]} Members</b>\n\n"
                        "Aapka campaign successfully finish ho chuka hai!"
                    )
                except Exception:
                    pass
                    
            conn.commit()
            bot.answer_callback_query(call.id, f"🎉 Verified! +{join_reward} Coins added!", show_alert=True)
            
            # Automatically load the next task in queue
            call.data = f"earn_{offset}"
            earn_sys(call)
        else:
            bot.answer_callback_query(call.id, "❌ Channel join nahi kiya gaya hai! Pehle join karein.", show_alert=True)
    except Exception:
        bot.answer_callback_query(call.id, "⚠️ Verification check fail ho gaya. Kripya punah prayas karein.", show_alert=True)

# ==================== HANDLERS: CAMPAIGN CREATION ====================
@bot.callback_query_handler(func=lambda call: call.data == "add_camp")
def initiate_campaign_creation(call):
    """Starts the interactive process for creating a new channel promotion campaign."""
    uid = call.from_user.id
    cost = get_setting('cost_per_member', 15)
    
    if get_coins(uid) < cost:
        bot.answer_callback_query(call.id, f"Kam se kam {cost} coins hone chahiye campaign lagane ke liye!", show_alert=True)
        return
        
    instructions = (
        "⚙️ <b>PROMOTION SETUP INSTRUCTIONS:</b>\n"
        "────────────────────────\n"
        f"1. Bot <b>@{BOT_USERNAME}</b> (ID: <code>{BOT_ID}</code>) ko apne channel me <b>ADMIN</b> banayein.\n"
        "2. Channel ka public username bhejein (Example: <code>@MyChannel</code>):"
    )
    msg = bot.send_message(call.message.chat.id, instructions)
    bot.register_next_step_handler(msg, step_verify_admin_privileges)

def step_verify_admin_privileges(message):
    """Validates that the bot possesses administrator rights in the target channel."""
    channel_user = message.text.strip()
    if not channel_user.startswith("@"):
        bot.send_message(message.chat.id, "❌ Format galat hai! '@' ke sath channel username bhejein (e.g. @MyChannel).")
        return
        
    try:
        bot_member = bot.get_chat_member(channel_user, BOT_ID)
        if bot_member.status not in ["administrator", "creator"]:
            bot.send_message(message.chat.id, f"❌ Bot @{BOT_USERNAME} aapke channel me Admin nahi hai! Pehle Admin banayein fir try karein.")
            return
    except Exception:
        bot.send_message(message.chat.id, "❌ Bot channel ko read nahi kar pa raha! Ensure karein ki channel Public hai aur bot usme Admin added hai.")
        return
        
    cost = get_setting('cost_per_member', 15)
    prompt_msg = bot.send_message(message.chat.id, f"✅ <b>Channel Verified Successfully!</b>\nKitne members chahiye? (1 Member = <code>{cost} Coins</code>):")
    bot.register_next_step_handler(prompt_msg, step_finalize_campaign, channel_user)

def step_finalize_campaign(message, channel_user):
    """Deducts coins and launches the campaign live into the active database queue."""
    try:
        count = int(message.text.strip())
        if count <= 0:
            bot.send_message(message.chat.id, "❌ Kam se kam 1 member ka target set karein.")
            return
            
        cost = get_setting('cost_per_member', 15)
        total_expense = count * cost
        uid = message.from_user.id
        
        if get_coins(uid) < total_expense:
            bot.send_message(message.chat.id, f"❌ Insufficient Coins! Is target ke liye chahiye: <code>{total_expense} Coins</code>.")
            return
            
        # Deduct wallet balance and save campaign
        c.execute("UPDATE users SET coins=coins-? WHERE user_id=?", (total_expense, uid))
        c.execute("INSERT INTO campaigns (owner_id, channel_username, needed_joins) VALUES (?, ?, ?)", (uid, channel_user, count))
        conn.commit()
        
        bot.send_message(message.chat.id, f"🚀 <b>Campaign Successfully Live!</b>\nTarget: <code>{count} Members</code>. Pura hone par notification mil jayega.")
        text, markup = main_menu(uid)
        bot.send_message(message.chat.id, text, reply_markup=markup)
    except Exception:
        bot.send_message(message.chat.id, "❌ Invalid number enter kiya gaya hai! Setup cancel kar diya gaya hai.")

# ==================== HANDLERS: USER STATS & ADMIN PANEL ====================
@bot.callback_query_handler(func=lambda call: call.data == "my_stats")
def display_user_statistics(call):
    """Displays comprehensive personal performance metrics for the user."""
    uid = call.from_user.id
    coins = get_coins(uid)
    
    c.execute("SELECT COUNT(*) FROM history WHERE user_id=?", (uid,))
    completed_joins = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM users WHERE referred_by=? AND is_verified=1", (uid,))
    active_referrals = c.fetchone()[0]
    
    stats_text = (
        "╔════════════════════════╗\n"
        "   📊 <b>ACCOUNT PERFORMANCE</b>\n"
        "╚════════════════════════╝\n"
        f"💎 <b>Wallet Balance:</b> <code>{coins} Coins</code>\n"
        f"👥 <b>Active Referrals:</b> <code>{active_referrals}</code>\n"
        f"✅ <b>Completed Tasks:</b> <code>{completed_joins}</code>\n"
        "────────────────────────"
    )
    markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Back to Main Menu", callback_data="refresh"))
    bot.edit_message_text(stats_text, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "adm_panel")
def display_admin_master_console(call):
    """Displays the master administration dashboard for managing bot operations."""
    if int(call.from_user.id) != ADMIN_ID:
        return
        
