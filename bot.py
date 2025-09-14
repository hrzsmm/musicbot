import os
import tempfile
import requests
from urllib.parse import quote_plus
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.environ["TELEGRAM_TOKEN"]
JAMENDO_CLIENT_ID = os.environ["JAMENDO_CLIENT_ID"]

JAMENDO_TRACKS = "https://api.jamendo.com/v3.0/tracks/?client_id={cid}&format=json&limit=8&search={q}&include=audio_download,license"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Напиши название песни или исполнителя.")

async def search_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    url = JAMENDO_TRACKS.format(cid=JAMENDO_CLIENT_ID, q=quote_plus(query))
    r = requests.get(url, timeout=10)
    data = r.json().get("results", [])
    if not data:
        await update.message.reply_text("Ничего не нашёл.")
        return
    buttons = []
    context.user_data["last_results"] = data
    for i, t in enumerate(data):
        title = f"{t.get('name')} — {t.get('artist_name')}"
        buttons.append([InlineKeyboardButton(title[:40], callback_data=str(i))])
    keyboard = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("Нашёл вот такие треки:", reply_markup=keyboard)

async def choose_track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    idx = int(q.data)
    results = context.user_data.get("last_results") or []
    track = results[idx]
    title = f"{track.get('name')} — {track.get('artist_name')}"
    audio_url = track.get("audio") or track.get("audiodownload")
    page_url = track.get("url")
    if audio_url:
        try:
            with requests.get(audio_url, stream=True, timeout=30) as r2:
                r2.raise_for_status()
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                    for chunk in r2.iter_content(chunk_size=16*1024):
                        if chunk:
                            tmp.write(chunk)
                    tmp_path = tmp.name
            await context.bot.send_audio(chat_id=q.message.chat_id, audio=open(tmp_path, "rb"),
                                         title=track.get("name"), performer=track.get("artist_name"))
        finally:
            try:
                os.unlink(tmp_path)
            except:
                pass
    else:
        await q.edit_message_text(f"{title}\nСлушать тут: {page_url}")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_text))
    app.add_handler(CallbackQueryHandler(choose_track))
    app.run_polling()

if __name__ == "__main__":
    main()
