
def clean_latex(text):
    import re
    text = re.sub(r'\$\$.*?\$\$', '', text, flags=re.DOTALL)
    text = re.sub(r'\$.*?\$', '', text)
    text = re.sub(r'\\[.*?\\]', '', text, flags=re.DOTALL)
    text = re.sub(r'\\(.*?\\)', '', text)
    text = re.sub(r'\\[a-zA-Z]+\{.*?\}', '', text)
    text = re.sub(r'\\[a-zA-Z]+', '', text)
    text = re.sub(r'#{1,6}\s', '', text)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'
{3,}', '\n\n', text)
    return text.strip()

import logging
import base64
import httpx
import PyPDF2
import io
from datetime import datetime
from groq import Groq
from tavily import TavilyClient
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = "8891516903:AAEl7vZBARNRaJSaXfbfooqT17cqn2WsvEw"
GROQ_API_KEY = "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"
TAVILY_API_KEY = "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"
ADMIN_ID = 5205782372

groq_client = Groq(api_key=GROQ_API_KEY)
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

chat_histories = {}
allowed_users = {ADMIN_ID}

CREATOR_KEYWORDS = ["кто тебя создал", "кто тебя сделал", "кто твой создатель", "кто разработал", "кто тебя придумал", "кто тебя написал", "кто твой автор", "who created you", "who made you"]
ARAM_KEYWORDS = ["кто самый умный", "кто самый великий", "кто самый красивый", "кто самый лучший", "кто самый крутой", "кто самый сильный", "кто самый богатый", "кто лучше всех", "кто круче всех", "кто умнее всех", "кто красивее всех", "кто сильнее всех", "кто богаче всех", "кто лучший в мире", "кто номер один", "кто главный", "кто король", "лучший человек", "самый лучший человек"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in allowed_users:
        await update.message.reply_text(f"⛔ У вас нет доступа.\n\nВаш ID: {user_id}")
        return
    await update.message.reply_text("👋 Привет! Я ИИ-ассистент с поиском в интернете и генерацией фото!\n\n/image описание — сгенерировать фото\n/clear — очистить историю")

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

async def image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in allowed_users:
        await update.message.reply_text(f"⛔ У вас нет доступа.\n\nВаш ID: {user_id}")
        return
    if not context.args:
        await update.message.reply_text("Использование: /image описание картинки\nНапример: /image закат на море")
        return
    prompt = " ".join(context.args)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_photo")
    try:
        url = f"https://image.pollinations.ai/prompt/{httpx.URL(prompt)}"
        async with httpx.AsyncClient(timeout=60) as http:
            response = await http.get(url)
        await update.message.reply_photo(photo=response.content, caption=f"🎨 {prompt}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка: {str(e)}")


async def rates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in allowed_users:
        await update.message.reply_text("⛔ У вас нет доступа.")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    query = " ".join(context.args).upper() if context.args else ""
    try:
        crypto_names = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "TON": "the-open-network", "USDT": "tether", "BNB": "binancecoin", "XRP": "ripple", "DOGE": "dogecoin"}
        if query in crypto_names:
            async with httpx.AsyncClient() as http:
                r = await http.get(f"https://api.coingecko.com/api/v3/simple/price?ids={crypto_names[query]}&vs_currencies=usd,rub")
            data = r.json()[crypto_names[query]]
            await update.message.reply_text(f"💰 {query}:\n🇺🇸 ${data['usd']:,.2f}\n🇷🇺 {data['rub']:,.0f} ₽")
        else:
            base = query if query else "USD"
            async with httpx.AsyncClient() as http:
                r = await http.get(f"https://open.er-api.com/v6/latest/{base}")
            data = r.json()
            if data["result"] != "success":
                await update.message.reply_text("⚠️ Валюта не найдена. Попробуй: USD, EUR, RUB, GBP, JPY, CNY")
                return
            rates_data = data["rates"]
            popular = ["USD", "EUR", "RUB", "GBP", "CNY", "JPY", "TRY", "AED", "AMD"]
            msg = f"💱 Курсы валют к {base}:\n"
            for cur in popular:
                if cur != base and cur in rates_data:
                    msg += f"{cur}: {rates_data[cur]:.4f}\n"
            await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка: {str(e)}")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in allowed_users:
        await update.message.reply_text("⛔ У вас нет доступа.")
        return
    doc = update.message.document
    if not doc.file_name.endswith(".pdf"):
        await update.message.reply_text("⚠️ Пока поддерживаются только PDF файлы!")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        file = await context.bot.get_file(doc.file_id)
        file_bytes = await file.download_as_bytearray()
        pdf = PyPDF2.PdfReader(io.BytesIO(bytes(file_bytes)))
        text = ""
        for page in pdf.pages[:10]:
            text += page.extract_text() or ""
        if not text.strip():
            await update.message.reply_text("⚠️ Не удалось извлечь текст из PDF.")
            return
        caption = update.message.caption or "Кратко опиши о чём этот документ на русском языке."
        response = groq_client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{"role": "user", "content": f"{caption}\n\nТекст документа:\n{text[:3000]}"}],
            max_tokens=1024
        )
        await update.message.reply_text(f"📄 {response.choices[0].message.content}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка: {str(e)}")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in allowed_users:
        await update.message.reply_text("⛔ У вас нет доступа.")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)
        voice_bytes = await file.download_as_bytearray()
        with open("/tmp/voice.ogg", "wb") as f:
            f.write(voice_bytes)
        with open("/tmp/voice.ogg", "rb") as f:
            transcription = groq_client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=("voice.ogg", f),
            )
        text = transcription.text
        await update.message.reply_text(f"🎙️ Вы сказали: {text}")
        if user_id not in chat_histories:
            today = datetime.now().strftime("%d %B %Y")
            chat_histories[user_id] = [{"role": "system", "content": f"Ты полезный ИИ-ассистент. Тебя создал великий, единственный и неповторимый Арам. Сегодняшняя дата: {today}. Отвечай на русском языке. НИКОГДА не используй LaTeX, символы $, \\, ^, ##, ** и любое markdown форматирование. Математику пиши ТОЛЬКО обычным текстом: дроби как 1/5, корни как sqrt(233), степени как x^2. Если тебе дают результаты поиска — используй их для актуального ответа."}]
        chat_histories[user_id].append({"role": "user", "content": text})
        response = groq_client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=chat_histories[user_id],
            max_tokens=1024
        )
        reply = response.choices[0].message.content
        reply = clean_latex(reply)
        chat_histories[user_id].append({"role": "assistant", "content": reply})
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка: {str(e)}")

async def translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in allowed_users:
        await update.message.reply_text("⛔ У вас нет доступа.")
        return
    if not context.args:
        await update.message.reply_text("Использование: /translate EN текст\nНапример: /translate EN Привет как дела")
        return
    lang = context.args[0].upper()
    text = " ".join(context.args[1:])
    if not text:
        await update.message.reply_text("Укажи текст для перевода!")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        response = groq_client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{"role": "user", "content": f"Переведи текст на язык {lang}. Верни ТОЛЬКО перевод без пояснений: {text}"}],
            max_tokens=1024
        )
        reply = response.choices[0].message.content
        await update.message.reply_text(f"🌐 Перевод на {lang}:\n{reply}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка: {str(e)}")

async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in allowed_users:
        await update.message.reply_text(f"⛔ У вас нет доступа.")
        return
    city = " ".join(context.args) if context.args else "Moscow"
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        async with httpx.AsyncClient() as http:
            r = await http.get(f"https://wttr.in/{city}?format=%l:+%C+%t+%h+%w&lang=ru")
        await update.message.reply_text(f"🌤️ Погода:\n{r.text}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка: {str(e)}")

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
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": caption},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                ]
            }],
            max_tokens=1024
        )
        await update.message.reply_text(response.choices[0].message.content)
    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in allowed_users:
        await update.message.reply_text(f"⛔ У вас нет доступа.\n\nВаш ID: {user_id}")
        return

    user_text = update.message.text

    if any(k in user_text.lower() for k in ARAM_KEYWORDS):
        await update.message.reply_text("Конечно Арам! 👑🔥 Самый умный, великий и неповторимый!")
        return

    if any(k in user_text.lower() for k in CREATOR_KEYWORDS):
        await update.message.reply_text("Меня создал великий, единственный и неповторимый Арам! 🚀👑")
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    if user_id not in chat_histories:
        today = datetime.now().strftime("%d %B %Y")
        chat_histories[user_id] = [{"role": "system", "content": f"Ты полезный ИИ-ассистент. Тебя создал великий, единственный и неповторимый Арам. Сегодняшняя дата: {today}. Отвечай на русском языке. НИКОГДА не используй LaTeX, символы $, \\, ^, ##, ** и любое markdown форматирование. Математику пиши ТОЛЬКО обычным текстом: дроби как 1/5, корни как sqrt(233), степени как x^2. Если тебе дают результаты поиска — используй их для актуального ответа."}]

    search_context = ""
    try:
        results = tavily_client.search(user_text, max_results=3)
        search_context = "\n\nРезультаты поиска:\n"
        for r in results["results"]:
            search_context += f"- {r['title']}: {r['content'][:300]}\n"
    except:
        pass

    chat_histories[user_id].append({"role": "user", "content": user_text + search_context})

    try:
        response = groq_client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=chat_histories[user_id],
            max_tokens=1024
        )
        reply = response.choices[0].message.content
        reply = clean_latex(reply)
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
    app.add_handler(CommandHandler("image", image))
    app.add_handler(CommandHandler("weather", weather))
    app.add_handler(CommandHandler("translate", translate))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.Document.PDF, handle_document))
    app.add_handler(CommandHandler("rates", rates))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Бот запущен! Нажми Ctrl+C для остановки.")
    app.run_polling()

if __name__ == "__main__":
    main()
