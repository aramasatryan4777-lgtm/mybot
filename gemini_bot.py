import logging
from groq import Groq
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = "8891516903:AAGRLtLPWbFvPEP1Z0VDnFxK9U2xzKw6JXA"
GROQ_API_KEY = "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"

client = Groq(api_key=GROQ_API_KEY)

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

chat_histories = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Привет! Я ИИ-ассистент. Напиши мне что-нибудь!\n\n/clear — очистить историю")

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_histories.pop(update.effective_user.id, None)
    await update.message.reply_text("🗑️ История очищена!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    if user_id not in chat_histories:
        chat_histories[user_id] = [{"role": "system", "content": "Ты полезный ИИ-ассистент. Отвечай на русском языке."}]

    chat_histories[user_id].append({"role": "user", "content": user_text})

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
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
