import os
import logging
import datetime
import random
from telebot import TeleBot, types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if not BOT_TOKEN:
    logging.error("TELEGRAM_BOT_TOKEN environment variable not set!")
    exit(1)

bot = TeleBot(BOT_TOKEN)

# Simple in-memory storage (for production, use a database)
user_data = {}  # user_id: {"boosts": 0, "last_claim": None, "streak": 0, "total_claimed": 0}

# Boost amounts
BOOST_RANGES = {"min": 10, "max": 100}

# Streak multipliers
STREAK_MULTIPLIERS = {
    0: 1.0, 1: 1.0, 2: 1.1, 3: 1.2, 4: 1.3,
    5: 1.5, 7: 2.0, 10: 2.5, 15: 3.0, 30: 5.0
}

# Boost levels
BOOST_LEVELS = {
    0: "⚡ Starter",
    100: "🚀 Bronze",
    300: "💪 Silver",
    600: "🔥 Gold",
    1000: "⭐ Platinum",
    1500: "💎 Diamond",
    2500: "👑 Legendary"
}

# --- Helper Functions ---

def get_streak_multiplier(streak):
    """Get multiplier based on streak length"""
    if streak >= 30:
        return STREAK_MULTIPLIERS[30]
    elif streak >= 15:
        return STREAK_MULTIPLIERS[15]
    elif streak >= 10:
        return STREAK_MULTIPLIERS[10]
    elif streak >= 7:
        return STREAK_MULTIPLIERS[7]
    elif streak >= 5:
        return STREAK_MULTIPLIERS[5]
    elif streak >= 3:
        return STREAK_MULTIPLIERS[3]
    elif streak >= 2:
        return STREAK_MULTIPLIERS[2]
    else:
        return STREAK_MULTIPLIERS[0]

def get_boost_level(total_boosts):
    """Get user level based on total boosts"""
    level = "⚡ Starter"
    for threshold, name in sorted(BOOST_LEVELS.items(), reverse=True):
        if total_boosts >= threshold:
            level = name
            break
    return level

def can_claim_boost(user_id):
    """Check if user can claim boost today"""
    if user_id not in user_data:
        return True, None
    
    last_claim = user_data[user_id].get("last_claim")
    if not last_claim:
        return True, None
    
    today = datetime.datetime.now().date()
    last_date = datetime.datetime.fromisoformat(last_claim).date()
    
    if today > last_date:
        return True, None
    elif today == last_date:
        return False, "✅ You already claimed today's boost!"
    else:
        return True, None

def calculate_boost(user_id):
    """Calculate boost amount with streak multiplier"""
    base_boost = random.randint(BOOST_RANGES["min"], BOOST_RANGES["max"])
    streak = user_data.get(user_id, {}).get("streak", 0)
    multiplier = get_streak_multiplier(streak)
    boost = int(base_boost * multiplier)
    
    # Random bonus (15% chance)
    if random.random() < 0.15:
        boost = boost * 2
        return boost, "🎉 DOUBLE BOOST!"
    
    return boost, ""

def format_boost_message(user_id, boost_amount, boost_type):
    """Format the boost claiming message"""
    user_name = user_data[user_id].get("name", "User")
    total_boosts = user_data[user_id]["boosts"]
    streak = user_data[user_id]["streak"]
    level = get_boost_level(total_boosts)
    
    message = (
        f"⚡ **Boost Claimed!**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **User:** {user_name}\n"
        f"💪 **Boost:** +{boost_amount} points\n"
        f"{boost_type}\n"
        f"🔥 **Streak:** {streak} days\n"
        f"📊 **Total:** {total_boosts} points\n"
        f"🏅 **Level:** {level}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
    )
    
    # Motivational messages
    if streak >= 30:
        message += "\n🏆 **LEGENDARY!** 30-day streak!"
    elif streak >= 15:
        message += "\n🌟 **AMAZING!** 15 days strong!"
    elif streak >= 7:
        message += "\n⭐ **GREAT!** One week streak!"
    elif streak >= 3:
        message += "\n💪 **Keep boosting!**"
    elif streak == 1:
        message += "\n🎯 **Day 1!** Come back tomorrow!"
    
    return message

def get_leaderboard():
    """Get top 10 users by boosts"""
    sorted_users = sorted(user_data.items(), key=lambda x: x[1]["boosts"], reverse=True)
    return sorted_users[:10]

# --- Command Handlers ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Welcome message"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    if user_id not in user_data:
        user_data[user_id] = {
            "boosts": 0,
            "last_claim": None,
            "streak": 0,
            "total_claimed": 0,
            "name": user_name
        }
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("⚡ Get Boost", callback_data="claim_boost"),
        InlineKeyboardButton("📊 My Stats", callback_data="my_stats")
    )
    markup.add(
        InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard"),
        InlineKeyboardButton("ℹ️ About", callback_data="about")
    )
    
    welcome_text = (
        f"👋 Welcome, {user_name}!\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ **Boost Bot**\n\n"
        f"Get free virtual boosts daily!\n"
        f"• ⚡ Daily boost claims\n"
        f"• 🔥 Streak multipliers\n"
        f"• 🏅 Level up system\n"
        f"• 🏆 Leaderboard competition\n\n"
        f"**Start boosting now:**"
    )
    
    bot.send_message(
        message.chat.id,
        welcome_text,
        parse_mode='Markdown',
        reply_markup=markup
    )

@bot.message_handler(commands=['boost'])
def claim_boost_command(message):
    """Claim boost via command"""
    handle_claim_boost(message.chat.id, message.from_user.id)

@bot.message_handler(commands=['stats'])
def stats_command(message):
    """Show stats via command"""
    handle_stats(message.chat.id, message.from_user.id)

@bot.message_handler(commands=['leaderboard'])
def leaderboard_command(message):
    """Show leaderboard via command"""
    handle_leaderboard(message.chat.id)

@bot.message_handler(commands=['help'])
def send_help(message):
    """Help command"""
    help_text = (
        "📖 **Commands**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "• `/start` - Main menu\n"
        "• `/boost` - Claim daily boost\n"
        "• `/stats` - Your stats\n"
        "• `/leaderboard` - Top users\n"
        "• `/help` - This message\n\n"
        "⚡ **How it works:**\n"
        "Claim daily boost points\n"
        "Build streaks for multipliers\n"
        "Level up through ranks\n"
        "Compete on leaderboard\n\n"
        "📌 **No real money. Just fun!**"
    )
    bot.reply_to(message, help_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_other_messages(message):
    """Handle any other messages"""
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📂 Menu", callback_data="start"))
    
    response = (
        "💡 **Use commands or buttons:**\n\n"
        "• `/start` - Main menu\n"
        "• `/boost` - Claim boost\n"
        "• `/stats` - Your stats\n"
        "• `/leaderboard` - Top users"
    )
    bot.reply_to(message, response, parse_mode='Markdown', reply_markup=markup)

# --- Handler Functions ---

def handle_claim_boost(chat_id, user_id):
    """Handle boost claiming"""
    if user_id not in user_data:
        bot.send_message(chat_id, "⚠️ Use /start first!", parse_mode='Markdown')
        return
    
    can_claim, message = can_claim_boost(user_id)
    if not can_claim:
        last_claim = user_data[user_id]["last_claim"]
        last_date = datetime.datetime.fromisoformat(last_claim).date()
        next_date = last_date + datetime.timedelta(days=1)
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📊 My Stats", callback_data="my_stats"))
        
        bot.send_message(
            chat_id,
            f"⏰ {message}\n"
            f"📅 **Next boost:** {next_date.strftime('%B %d, %Y')}",
            parse_mode='Markdown',
            reply_markup=markup
        )
        return
    
    boost_amount, boost_type = calculate_boost(user_id)
    
    user_data[user_id]["boosts"] += boost_amount
    user_data[user_id]["total_claimed"] += boost_amount
    user_data[user_id]["last_claim"] = datetime.datetime.now().isoformat()
    user_data[user_id]["streak"] += 1
    user_data[user_id]["name"] = user_data[user_id].get("name", "User")
    
    result_message = format_boost_message(user_id, boost_amount, boost_type)
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("📊 My Stats", callback_data="my_stats"),
        InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")
    )
    markup.add(InlineKeyboardButton("⚡ Boost Again Tomorrow", callback_data="claim_boost"))
    
    bot.send_message(
        chat_id,
        result_message,
        parse_mode='Markdown',
        reply_markup=markup
    )

def handle_stats(chat_id, user_id):
    """Show user stats"""
    if user_id not in user_data:
        bot.send_message(chat_id, "⚠️ Use /start first!", parse_mode='Markdown')
        return
    
    data = user_data[user_id]
    streak = data["streak"]
    total_boosts = data["boosts"]
    total_claimed = data["total_claimed"]
    level = get_boost_level(total_boosts)
    multiplier = get_streak_multiplier(streak)
    
    sorted_users = sorted(user_data.items(), key=lambda x: x[1]["boosts"], reverse=True)
    rank = next((i+1 for i, (uid, _) in enumerate(sorted_users) if uid == user_id), "N/A")
    
    # Next level progress
    next_level = None
    next_threshold = None
    for threshold, name in sorted(BOOST_LEVELS.items()):
        if total_boosts < threshold:
            next_level = name
            next_threshold = threshold
            break
    
    progress_text = ""
    if next_level and next_threshold:
        progress = int((total_boosts / next_threshold) * 100)
        progress_text = f"📈 **Next Level:** {next_level} ({progress}%)"
    
    stats_text = (
        f"📊 **Your Stats**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **User:** {data['name']}\n"
        f"⚡ **Total Boosts:** {total_boosts}\n"
        f"📈 **Total Claimed:** {total_claimed}\n"
        f"🏅 **Level:** {level}\n"
        f"{progress_text}\n"
        f"🔥 **Streak:** {streak} days\n"
        f"📈 **Multiplier:** {multiplier}x\n"
        f"🏆 **Rank:** #{rank} of {len(user_data)}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("⚡ Claim Boost", callback_data="claim_boost"),
        InlineKeyboardButton("🔙 Menu", callback_data="start")
    )
    
    bot.send_message(chat_id, stats_text, parse_mode='Markdown', reply_markup=markup)

def handle_leaderboard(chat_id):
    """Show leaderboard"""
    top_users = get_leaderboard()
    
    if not top_users:
        leaderboard_text = "🏆 **Leaderboard**\n━━━━━━━━━━━━━━━━━━━━\n\nNo users yet. Be the first!"
    else:
        leaderboard_text = "🏆 **Leaderboard**\n━━━━━━━━━━━━━━━━━━━━\n\n"
        for i, (user_id, data) in enumerate(top_users, 1):
            medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
            name = data.get("name", "User")
            boosts = data["boosts"]
            level = get_boost_level(boosts)
            streak = data.get("streak", 0)
            leaderboard_text += f"{medal} **{name}** - {boosts} pts ({level} 🔥{streak}d)\n"
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("⚡ Claim Boost", callback_data="claim_boost"),
        InlineKeyboardButton("📊 My Stats", callback_data="my_stats")
    )
    markup.add(InlineKeyboardButton("🔙 Menu", callback_data="start"))
    
    bot.send_message(chat_id, leaderboard_text, parse_mode='Markdown', reply_markup=markup)

# --- Callback Handlers ---

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    """Handle button clicks"""
    try:
        if call.data == "start":
            send_welcome(call.message)
            bot.answer_callback_query(call.id)
            
        elif call.data == "claim_boost":
            handle_claim_boost(call.message.chat.id, call.from_user.id)
            bot.answer_callback_query(call.id)
            
        elif call.data == "my_stats":
            handle_stats(call.message.chat.id, call.from_user.id)
            bot.answer_callback_query(call.id)
            
        elif call.data == "leaderboard":
            handle_leaderboard(call.message.chat.id)
            bot.answer_callback_query(call.id)
            
        elif call.data == "about":
            about_text = (
                "🤖 **About Boost Bot**\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "Free daily virtual boosts!\n\n"
                "✅ Claim daily boosts\n"
                "✅ Build streaks\n"
                "✅ Level up through ranks\n"
                "✅ Compete on leaderboard\n\n"
                "📌 **No real money**\n"
                "🎯 **Just for fun!**\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"👥 {len(user_data)} users"
            )
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔙 Menu", callback_data="start"))
            
            bot.edit_message_text(
                about_text,
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=markup
            )
            bot.answer_callback_query(call.id)
            
    except Exception as e:
        logging.error(f"Callback error: {e}")
        bot.answer_callback_query(call.id, text="❌ Error", show_alert=True)

# --- Main Execution ---

if __name__ == '__main__':
    logging.info("🚀 Boost Bot is starting...")
    logging.info(f"✅ Bot online! Users: {len(user_data)}")
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        logging.error(f"Bot polling failed: {e}")
