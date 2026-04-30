import os
import asyncio
import threading
from flask import Flask
from pyrogram import Client, filters
from pytgcalls import PyTgCalls, idle
from pytgcalls.types import MediaStream
import yt_dlp

# --- Environment Variables ---
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
PORT = int(os.environ.get("PORT", 8080))

# --- Initialize Clients ---
# We need a Bot to listen to commands, and a User Account (Session) to play the music in the Voice Chat.
app = Client("music_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
user = Client("user_session", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
call_py = PyTgCalls(user)

# --- Dummy Web Server for Render ---
# Render requires a web service to bind to a port, otherwise it marks the deployment as failed.
web_app = Flask(__name__)

@web_app.route('/')
def index():
    return "Music Bot is up and running!"

def run_web():
    web_app.run(host="0.0.0.0", port=PORT)

# --- YT-DLP Configuration ---
ydl_opts = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
}

# --- Bot Commands ---
@app.on_message(filters.command("play") & filters.group)
async def play_command(client, message):
    query = message.text.split(" ", 1)[1] if len(message.text.split()) > 1 else None
    
    if not query:
        return await message.reply_text("❌ Please provide a song name. Usage: `/play [song name]`")
    
    m = await message.reply_text("🔎 Searching...")
    
    try:
        # Fetch audio URL using yt-dlp
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            audio_url = info['url']
            title = info['title']
        
        # Play the audio in the Voice Chat
        await call_py.play(
            message.chat.id,
            MediaStream(audio_url)
        )
        await m.edit_text(f"▶️ **Playing:** {title}")
        
    except Exception as e:
        await m.edit_text(f"❌ **Error:** `{str(e)}`\n\n*(Make sure the Voice Chat is active before playing!)*")

@app.on_message(filters.command("stop") & filters.group)
async def stop_command(client, message):
    try:
        await call_py.leave_call(message.chat.id)
        await message.reply_text("⏹ **Stopped playing and left the voice chat.**")
    except Exception as e:
        await message.reply_text(f"❌ **Error:** `{str(e)}`")

# --- Main Startup Function ---
async def main():
    await app.start()
    await user.start()
    await call_py.start()
    print("Bot and PyTgCalls are up and running!")
    await idle()

if __name__ == "__main__":
    # 1. Start the Flask server in a background thread for Render
    threading.Thread(target=run_web, daemon=True).start()
    
    # 2. Start the Pyrogram & PyTgCalls asyncio loop
    asyncio.run(main())
