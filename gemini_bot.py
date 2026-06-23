import logging
import base64
from google import genai
from google.genai import types
from tavily import TavilyClient
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = "8891516903:AAGRLtLPWbFvPEP1Z0VDnFxK9U2xzKw6JXA"
GEMINI_API_KEY = "AQ.Ab8RN6KQ2LJB9s4Dpx8JtyHmEpOim2D5VFnXMuxHOh2fSoiELw"
TAVILY_API_KEY = "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"
ADMIN_ID = 5205782372

client = genai.Client(api_key=GEMINI_API_KEY)
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

chat_sessions = {}
allowed_users = {ADMIN_ID}

def needs_search(text):
    keywords = [
        "сейчас", "сегодня", "вчера", "новости", "последн", "актуальн",
        "2025", "2026", "курс", "погода", "цена", "стоимость", "когда",
        "кто выиграл", "что случилось", "евро", "доллар", "рубль", "биткоин",
        "матч", "счёт", "результат", "вышел", "вышла", "выборы", "война",
        "произошло", "случилось", "где", "сколько стоит"
    ]
    return any(k in text.lower() for k in keywords)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in allowed_users:
        await update.message.reply_text(f"⛔ У вас нет доступа.\n\nВаш ID: {user_id}")
        return
    await update.message.reply_text("👋 Привет! Я ИИ-ассистент на базе Gemini 2.0 Flash с поиском в интернете!\n\n/clear — очистить историю")

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in allowed_users:
        return
    chat_sessions.pop(user_id, None)
    await update.message.reply_text("🗑️ История очищена!")

async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Использование: /add 123456789")
        return
    allowed_users.add(int(context.args[0]))
    await update.message.reply_text(f"✅ Пользователь {context.args[0]} добавлен!")

async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Использование: /remove 123456789")
        return
    allowed_users.discard(int(context.args[0]))
    await update.message.reply_text(f"✅ Пользователь {context.args[0]} удалён!")

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text(f"👥 Пользователи: {allowed_users}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in allowed_users:
        await update.message.reply_text(f"⛔ У вас нет доступа.\n\nВаш ID: {user_id}")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    image_bytes = await file.download_as_bytearray()
    caption = update.message.caption or "Опиши что на этом фото подробно на русском языке."
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                types.Part.from_bytes(data=bytes(image_bytes), mime_type="image/jpeg"),
                caption
            ]
        )
        await update.message.reply_text(response.text)
    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in allowed_users:
        await update.message.reply_text(f"⛔ У вас нет доступа.\n\nВаш ID: {user_id}")
        return
    user_text = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    if user_id not in chat_sessions:
        chat_sessions[user_id] = client.chats.create(model="gemini-2.0-flash")

    search_context = ""
    if needs_search(user_text):
        try:
            results = tavily_client.search(user_text, max_results=3)
            search_context = "\n\nРезультаты поиска:\n"
            for r in results["results"]:
                search_context += f"- {r['title']}: {r['content'][:300]}\n"
        except:
            pass

    try:
        response = chat_sessions[user_id].send_message(user_text + search_context)
        await update.message.reply_text(response.text)
    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка: {str(e)}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CommandHandler("add", add_user))
    app.add_handler(CommandHandler("remove", remove_user))
    app.add_handler(CommandHandler("users", users))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Бот запущен! Нажми Ctrl+C для остановки.")
    app.run_polling()

if __name__ == "__main__":
    main()
