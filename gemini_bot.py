import logging
from groq import Groq
from tavily import TavilyClient
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = "8891516903:AAGRLtLPWbFvPEP1Z0VDnFxK9U2xzKw6JXA"
GROQ_API_KEY = "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"
TAVILY_API_KEY = "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"

groq_client = Groq(api_key=GROQ_API_KEY)
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

chat_histories = {}

def needs_search(text):
    keywords = ["сейчас", "сегодня", "новости", "последн", "актуальн", "2024", "2025", "2026", "курс", "погода", "цена", "когда", "кто выиграл", "что случилось"]
    return any(k in text.lower() for k in keywords)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Привет! Я ИИ-ассистент с поиском в интернете.\nМогу отвечать на актуальные вопросы!\n\n/clear — очистить историю")

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_histories.pop(update.effective_user.id, None)
    await update.message.reply_text("🗑️ История очищена!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    if user_id not in chat_histories:
        chat_histories[user_id] = [{"role": "system", "content": "Ты полезный ИИ-ассистент. Отвечай на русском языке. Если тебе дают результаты поиска — используй их для актуального ответа."}]

    search_context = ""
    if needs_search(user_text):
        try:
            results = tavily_client.search(user_text, max_results=3)
            search_context = "\n\nРезультаты поиска:\n"
            for r in results["results"]:
                search_context += f"- {r['title']}: {r['content'][:200]}\n"
        except:
            pass

    message = user_text + search_context
    chat_histories[user_id].append({"role": "user", "content": message})

    try:
        response = groq_client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Бот запущен! Нажми Ctrl+C для остановки.")
    app.run_polling()

if __name__ == "__main__":
    main()
