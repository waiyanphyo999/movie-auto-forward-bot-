import asyncio
# Render တွင် Event Loop Error မတက်စေရန် Pyrogram မတိုင်မီ အရင်ဆုံး ရေးရပါမည်
asyncio.set_event_loop(asyncio.new_event_loop())

import json
import os
import requests
from aiohttp import web

from pyrogram import Client, filters, compose
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import google.generativeai as genai


# ==========================================
# ENVIRONMENT VARIABLES
# ==========================================

try:
    API_ID = int(os.getenv("API_ID", "0"))
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
except ValueError:
    raise Exception("API_ID / ADMIN_ID must be numbers")

API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SESSION_STRING = os.getenv("SESSION_STRING")

DEST_RAW = os.getenv("DESTINATION_CHANNEL", "")
if DEST_RAW.startswith("-100") or DEST_RAW.isdigit() or (DEST_RAW.startswith("-") and DEST_RAW[1:].isdigit()):
    DESTINATION_CHANNEL = int(DEST_RAW)
else:
    DESTINATION_CHANNEL = DEST_RAW

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
XAI_API_KEY = os.getenv("XAI_API_KEY")


# ==========================================
# CHECK REQUIRED VARIABLES
# ==========================================

if not API_ID:
    raise Exception("Missing API_ID")
if not ADMIN_ID:
    raise Exception("Missing ADMIN_ID")
if not API_HASH:
    raise Exception("Missing API_HASH")
if not BOT_TOKEN:
    raise Exception("Missing BOT_TOKEN")
if not SESSION_STRING:
    raise Exception("Missing SESSION_STRING")
if not DESTINATION_CHANNEL:
    raise Exception("Missing DESTINATION_CHANNEL")


# ==========================================
# AI SETUP
# ==========================================

gemini_model = None

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel("gemini-1.5-flash")
    except Exception as e:
        print("Gemini Error:", e)
        gemini_model = None


def rewrite_text(text):
    if not text:
        return ""
    prompt = f"""
အောက်ပါစာသားကို မြန်မာလိုပဲ
အဓိပ္ပာယ်မပြောင်းဘဲ
ပိုမိုဆွဲဆောင်မှုရှိအောင် ပြန်ရေးပါ။

{text}
"""
    if gemini_model:
        try:
            result = gemini_model.generate_content(prompt)
            return result.text
        except Exception as e:
            print("Gemini Error:", e)

    if XAI_API_KEY:
        try:
            url = "https://api.x.ai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {XAI_API_KEY}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "grok-beta",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7
            }
            r = requests.post(url, headers=headers, json=data, timeout=30)
            return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print("xAI Error:", e)

    return text


# ==========================================
# DATABASE & CLIENTS
# ==========================================

DB_FILE = "config.json"

def load_channels():
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_channels(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

bot_app = Client("control_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
user_app = Client("userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
movie_states = {}


# ==========================================
# DUMMY WEB SERVER (To Fix Render Port Timeout)
# ==========================================
async def start_web_server():
    async def handle(request):

return web.Response(text="Movie Bot is Running Successfully!")
    
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render သည် PORT Environment Variable ကို အလိုအလျောက် ပေးပို့ပါသည်
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"✅ Web Server started on port {port}")


# ==========================================
# MENU
# ==========================================

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Movie အသစ်တင်ရန်", callback_data="start_movie")],
        [InlineKeyboardButton("📋 Channel List", callback_data="list_channels")],
        [
            InlineKeyboardButton("➕ Add Channel", callback_data="add_channel"),
            InlineKeyboardButton("➖ Delete Channel", callback_data="remove_channel")
        ]
    ])

def channel_keyboard(prefix):
    channels = load_channels()
    buttons = []
    row = []
    for i, ch in enumerate(channels):
        row.append(InlineKeyboardButton(ch, callback_data=f"{prefix}_{i}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


# ==========================================
# START & COMMANDS
# ==========================================

@bot_app.on_message(filters.command("start") & filters.user(ADMIN_ID))
async def start(client, message):
    await message.reply("🤖 Movie Auto Bot\n\nControl Panel", reply_markup=main_menu())

@bot_app.on_message(filters.command("add") & filters.user(ADMIN_ID))
async def add_channel(client, message):
    if len(message.command) < 2: return
    channel = message.command[1]
    channels = load_channels()
    if channel not in channels:
        channels.append(channel)
        save_channels(channels)
    await message.reply(f"✅ Added {channel}")

@bot_app.on_message(filters.command("del") & filters.user(ADMIN_ID))
async def delete_channel(client, message):
    if len(message.command) < 2: return
    channel = message.command[1]
    channels = load_channels()
    if channel in channels:
        channels.remove(channel)
        save_channels(channels)
    await message.reply(f"🗑 Removed {channel}")


# ==========================================
# CALLBACK
# ==========================================

@bot_app.on_callback_query(filters.user(ADMIN_ID))
async def buttons(client, query):
    data = query.data
    if data == "list_channels":
        channels = load_channels()
        text = "📋 Channels\n\n" + ("\n".join(channels) if channels else "Empty")
        await query.message.edit_text(text, reply_markup=main_menu())
    elif data == "add_channel":
        await query.message.reply("Use:\n/add @channel")
    elif data == "remove_channel":
        await query.message.reply("Use:\n/del @channel")
    elif data == "start_movie":
        if not load_channels():
            return await query.message.reply("No channel added")
        await query.message.edit_text("📸 Select Poster Channel", reply_markup=channel_keyboard("poster"))
    elif data.startswith("poster_"):
        idx = int(data.split("_")[1])
        ch = load_channels()[idx]
        movie_states[ADMIN_ID] = {"poster": ch, "step": 1}
        await query.message.edit_text("🎥 Select Video Channel", reply_markup=channel_keyboard("video"))
    elif data.startswith("video_"):
        idx = int(data.split("_")[1])
        ch = load_channels()[idx]
        movie_states[ADMIN_ID]["video"] = ch
        movie_states[ADMIN_ID]["step"] = 2
        await query.message.edit_text("📤 Send Video File")


# ==========================================
# VIDEO UPLOAD
# ==========================================

@bot_app.on_message(filters.video & filters.user(ADMIN_ID))
async def upload_video(client, message):
    state = movie_states.get(ADMIN_ID)
    if not state or state.get("step") != 2: return
    channel = state["video"]
    msg = await message.copy(channel)
    if msg.chat.username:
        link = f"https://t.me/{msg.chat.username}/{msg.id}"
    else:
        link = f"https://t.me/c/{str(msg.chat.id)[4:]}/{msg.id}"
    movie_states[ADMIN_ID]["video_link"] = link
    movie_states[ADMIN_ID]["step"] = 3
    await message.reply("✅ Video Uploaded\n📸 Send Poster + Caption")


# ==========================================
# POSTER UPLOAD
# ==========================================

@bot_app.on_message(filters.photo & filters.user(ADMIN_ID))
async def upload_poster(client, message):
    state = movie_states.get(ADMIN_ID)
    if not state or state.get("step") != 3: return
    channel = state["poster"]
    video_link = state.get("video_link")
    if not video_link: return
    caption = message.caption if message.caption else "🎬 New Movie"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🎬 Watch / Download", url=video_link)]])
    await message.copy(channel, caption=caption, reply_markup=keyboard)
    await message.reply("✅ Movie Posted Successfully\n\nUse /start for next movie")
    movie_states.pop(ADMIN_ID, None)


# ==========================================
# USERBOT AUTO FORWARD
# ==========================================

@user_app.on_message(filters.channel)
async def auto_forward(client, message):
    channels = load_channels()
    username = f"@{message.chat.username}" if message.chat.username else None
    if username not in channels: return
    try:
        if message.text:
            text = rewrite_text(message.text)
            await client.send_message(DESTINATION_CHANNEL, text)
        elif message.photo or message.video:
            caption = message.caption or ""
            new_caption = rewrite_text(caption) if caption else ""
            await message.copy(DESTINATION_CHANNEL, caption=new_caption)
    except Exception as e:
        print("Forward Error:", e)


# ==========================================
# START SYSTEM
# ==========================================

async def main():
    print("🚀 Bot Starting...")
    await start_web_server()
    await compose([bot_app, user_app])

if name == "main":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()