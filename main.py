import re
import logging
import json
import time
import os
from dotenv import load_dotenv
from telegram import Update, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from datetime import timedelta

logging.basicConfig(
    level=logging.WARNING,
    format='%(levelname)s: %(message)s'
)

logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram').setLevel(logging.WARNING)

load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')
SECURITY_FILE = "security_status.json"

def initialize_security():
    try:
        with open(SECURITY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            converted_data = {int(k): v for k, v in data.items()}
            logging.warning(f"Security status loaded: {converted_data}")
            return converted_data
    except FileNotFoundError:
        logging.warning(f"Security file not found")
        return {}
    except json.JSONDecodeError:
        logging.error(f"JSON decode error")
        return {}
    except Exception as e:
        logging.error(f"Error loading security: {e}")
        return {}

def save_security_status():
    try:
        with open(SECURITY_FILE, 'w', encoding='utf-8') as f:
            json.dump(security_enabled, f)
            logging.warning(f"Security status saved: {security_enabled}")
    except Exception as e:
        logging.error(f"Error saving security: {e}")

security_enabled = initialize_security()
restricted_users = {}  
user_message_count = {}  

def is_admin(member):
    return member.status in ("administrator", "creator")

def is_spam(user_id, chat_id):
    if user_id not in user_message_count or chat_id not in user_message_count[user_id]:
        return False
    
    current_time = time.time()
    user_message_count[user_id][chat_id] = [t for t in user_message_count[user_id][chat_id] if current_time - t < 60]
    
    return len(user_message_count[user_id][chat_id]) > 10

async def security_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or not update.effective_user:
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    member = await context.bot.get_chat_member(chat_id, user_id)

    if not is_admin(member):
        await update.message.reply_text("This command is for admins only")
        return

    if context.args and context.args[0].lower() == "on":
        security_enabled[chat_id] = True
        save_security_status()
        await update.message.reply_text("Security enabled")
    elif context.args and context.args[0].lower() == "off":
        if chat_id not in security_enabled or not security_enabled[chat_id]:
            await update.message.reply_text(
                "Security is already disabled\n\n"
                "To enable security use:\n"
                "`/security on`", 
                parse_mode="Markdown"
            )
            return
        security_enabled[chat_id] = False
        save_security_status()
        await update.message.reply_text("Security disabled")
    else:
        status = "Enabled" if security_enabled.get(chat_id, False) else "Disabled"
        await update.message.reply_text(
            f"Security status: {status}\n\n"
            "To enable security use:\n"
            "`/security on`\n\n"
            "To disable security use:\n"
            "`/security off`", 
            parse_mode="Markdown"
        )

def contains_bad_links(text: str) -> bool:
    return bool(re.search(r"(t\.me|telegram\.me|telegram\.dog|tiktok\.com|instagram\.com|youtube\.com|youtu\.be|facebook\.com|porn|onlyfans|xvideos|xnxx|discord(?:\.com|app\.com|\.gg)[/invite/]?(?:[a-zA-Z0-9\-]{2,32}))", text, re.IGNORECASE))

async def apply_timeout(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int, reason: str):
    try:
        user = await context.bot.get_chat_member(chat_id, user_id)
        if not user or not user.user:
            logging.error(f"Could not get user info for {user_id}")
            return

        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=timedelta(minutes=15)
        )
        restricted_users[user_id] = chat_id

        keyboard = InlineKeyboardMarkup.from_button(
            InlineKeyboardButton("Unmute", callback_data=f"unmute:{user_id}")
        )
        await context.bot.send_message(
            chat_id,
            f"User [{user.user.first_name}](tg://user?id={user_id}) has been timed out for {reason}",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Error applying timeout: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message or not update.effective_chat:
        return

    message = update.effective_message
    chat_id = update.effective_chat.id
    
    logging.info(f"Checking message in chat {chat_id}. Security enabled: {security_enabled.get(chat_id, False)}")
    
    if not security_enabled.get(chat_id, False):
        return

    if not message.text:
        return

    user = message.from_user
    if not user:
        return

    user_id = user.id

    if user_id not in user_message_count:
        user_message_count[user_id] = {}
    if chat_id not in user_message_count[user_id]:
        user_message_count[user_id][chat_id] = []
    
    user_message_count[user_id][chat_id].append(time.time())

    if is_spam(user_id, chat_id):
        try:
            await message.delete()
            await apply_timeout(context, chat_id, user_id, "spam")
        except Exception as e:
            logging.error(f"Error handling spam: {e}")
        return

    if contains_bad_links(message.text):
        try:
            await message.delete()
            await apply_timeout(context, chat_id, user_id, "sending prohibited links")
        except Exception as e:
            logging.error(f"Error handling bad links: {e}")
        return

async def unmute_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = int(data.split(":")[1])
    chat_id = restricted_users.get(user_id)

    if not chat_id:
        return

    admin_member = await context.bot.get_chat_member(chat_id, query.from_user.id)
    if not is_admin(admin_member):
        await query.answer("Only admins can use this button", show_alert=True)
        return

    try:
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=ChatPermissions(can_send_messages=True)
        )
        await query.edit_message_text("User has been unmuted")
        restricted_users.pop(user_id, None)
    except TypeError as e:
        logging.error(f"Error unmuting user: {e}")
        if query.message.text != "Error occurred while unmuting":
            await query.edit_message_text("Error occurred while unmuting")

async def handle_private_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or not update.effective_user:
        return

    if update.effective_chat.type != "private":
        return

    await update.message.reply_text(
        "Welcome to Security Bot\n\n"
        "This bot helps protect your groups from spam and prohibited links.\n\n"
        "To use the bot:\n"
        "1. Add the bot to your group\n"
        "2. Make the bot an admin\n"
        "3. Use /security on to enable protection\n\n"
        "Commands:\n"
        "/security on - Enable security\n"
        "/security off - Disable security\n"
        "/security - Check security status\n\n"
        "Features:\n"
        "- Blocks spam (more than 10 messages per minute)\n"
        "- Blocks prohibited links\n"
        "- Automatic timeout for violators\n"
        "- Admin can unmute users\n\n"
        "For support, contact the bot owner",
        parse_mode="Markdown"
    )

def main():
    logging.warning(f"Starting bot with security status: {security_enabled}")
    
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("security", security_command))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, handle_message))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, handle_private_message))
    app.add_handler(CallbackQueryHandler(unmute_callback))

    print("\n" + "="*50)
    print("Bot started successfully")
    print("Security system is ready")
    print("="*50 + "\n")
    
    app.run_polling()

if __name__ == "__main__":
    main()
