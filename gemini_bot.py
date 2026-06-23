import logging
import base64
import httpx
from groq import Groq
from tavily import TavilyClient
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = "8891516903:AAGRLtLPWbFvPEP1Z0VDnFxK9U2xzKw6JXA"
GROQ_API_KEY = "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"
TAVILY_API_KEY = "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"
ADMIN_ID = 5205782372

groq_client = Groq(api_key=GROQ_API_KEY)
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

chat_histories = {}
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
    await update.message.reply_text("👋 Привет! Я ИИ-ассистент с поиском в интернете и анализом фото.\n\nПросто отправь мне фото и я его опишу!\n\n/clear — очистить историю")

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in allowed_users:
        return
    chat_histories.pop(user_id, None)
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
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    caption = update.message.caption or "Опиши что на этом фото подробно на русском языке."

    try:
        response = groq_client.chat.completions.create(
            model="qwen/qwen3.6-27b",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": caption},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                ]
            }],
            max_tokens=1024
        )
        reply = response.choices[0].message.content
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in allowed_users:
        await update.message.reply_text(f"⛔ У вас нет доступа.\n\nВаш ID: {user_id}")
        return
    user_text = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    if user_id not in chat_histories:
        chat_histories[user_id] = [{"role": "system", "content": "Ты полезный ИИ-ассистент. Отвечай на русском языке. Никогда не используй LaTeX, формулы в скобках или символы типа $, \, ^. Пиши математику простым текстом, например: x = (11 + 15.3) / 2 = 13.15. Если тебе дают результаты поиска — используй их для актуального ответа."}]

    search_context = ""
    if needs_search(user_text):
        try:
            results = tavily_client.search(user_text, max_results=3)
            search_context = "\n\nРезультаты поиска:\n"
            for r in results["results"]:
                search_context += f"- {r['title']}: {r['content'][:300]}\n"
        except:
            pass

    message = user_text + search_context
    chat_histories[user_id].append({"role": "user", "content": message})

    try:
        response = groq_client.chat.completions.create(
            model="qwen/qwen3.6-27b",
            messages=chat_histories[user_id],
            max_tokens=1024
        )
        reply = response.choices[0].message.content
        chat_histories[user_id].append({"role": "assistant", "content": reply})
        await update.message.reply_text(reply)
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
