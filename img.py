import logging
import os
import io
import httpx 
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- Configuration: Load credentials from Environment Variables ---
# Render will provide these variables securely.
IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# The ImgBB upload URL is stable
IMGBB_UPLOAD_URL = "https://api.imgbb.com/1/upload" 

# Check for essential credentials
if not BOT_TOKEN or not IMGBB_API_KEY:
    raise ValueError("BOT_TOKEN or IMGBB_API_KEY environment variables are not set.")

# --- Configure Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.ERROR 
)
logging.getLogger("httpx").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

# --- Handler Functions ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends the simplified welcome message and deletes the command message."""
    user_data = context.user_data
    chat_id = update.effective_chat.id

    if 'start_sent' not in user_data:
        await update.message.reply_text(
            text="This bot was made by\nt.me/ixeuc",
            disable_web_page_preview=True 
        )
        user_data['start_sent'] = True
    
    try:
        # Note: Deleting messages requires bot admin privileges in a group
        await context.bot.delete_message(chat_id=chat_id, message_id=update.message.message_id)
    except Exception as e:
        logger.warning(f"Could not delete start message {update.message.message_id}: {e}")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles uploaded photos: uploads to ImgBB and replies with the direct link inside the Code Block."""
    message = update.message
    
    # 1. Get the highest quality photo file
    photo_file = await message.photo[-1].get_file()
    
    # 2. Download the photo to an in-memory byte buffer
    photo_bytes = io.BytesIO()
    await photo_file.download_to_memory(photo_bytes)
    photo_bytes.seek(0)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                url=IMGBB_UPLOAD_URL, 
                params={"key": IMGBB_API_KEY},
                files={"image": ("image.jpg", photo_bytes, "image/jpeg")}
            )
            response.raise_for_status() 
            
            data = response.json()
            
            if data["success"]:
                direct_link = data["data"]["url"] 
                
                # Final Formatting: Bold text, followed immediately by the Code Block
                reply_text = (
                    "**Uploaded Successfully!**\n"
                    f"```\n{direct_link}\n```" 
                )
                
                # Send the reply
                await message.reply_text(
                    text=reply_text,
                    parse_mode="Markdown", 
                    reply_to_message_id=message.message_id 
                )
                
            else:
                error_message = data.get("error", {}).get("message", "Unknown ImgBB API Error.")
                logger.error(f"ImgBB Upload failed: {error_message}")
                await message.reply_text(f"Upload failed: {error_message}", reply_to_message_id=message.message_id)

        except httpx.RequestError as e:
            logger.error(f"Request error during ImgBB upload: {e}") 
            await message.reply_text(
                "An error occurred while connecting to the image host.", 
                reply_to_message_id=message.message_id
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            await message.reply_text(
                "An unexpected error occurred during processing.", 
                reply_to_message_id=message.message_id
            )


async def delete_unwanted_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deletes any message that is not a photo or the /start command."""
    message = update.message
    
    if message and not message.photo and not (message.text and message.text.startswith('/start')):
        try:
            await context.bot.delete_message(
                chat_id=message.chat_id, 
                message_id=message.message_id
            )
        except Exception as e:
            logger.warning(f"Could not delete unwanted message {message.message_id}: {e}")


# --- Main Function ---

def main() -> None:
    """Start the bot."""
    application = Application.builder().token(BOT_TOKEN).build()

    # Register Handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_photo))
    
    application.add_handler(
        MessageHandler(~filters.PHOTO & ~filters.COMMAND, delete_unwanted_messages), 
        group=-1
    )
    
    # Using logger.critical as a final start message
    logger.critical("Bot is starting...") 
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
