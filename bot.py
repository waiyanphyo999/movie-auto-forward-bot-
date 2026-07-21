import asyncio
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
á€¡á€±á€¬á€€á€ºá€•á€«á€…á€¬á€žá€¬á€¸á€€á€­á€¯ á€™á€¼á€”á€ºá€™á€¬á€œá€­á€¯á€•á€²
á€¡á€“á€­á€•á€¹á€•á€¬á€šá€ºá€™á€•á€¼á€±á€¬á€„á€ºá€¸á€˜á€²
á€•á€­á€¯á€™á€­á€¯á€†á€½á€²á€†á€±á€¬á€„á€ºá€™á€¾á€¯á€›á€¾á€­á€¡á€±á€¬á€„á€º á€•á€¼á€”á€ºá€›á€±á€¸á€•á€«á‹

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
# DATABASE & SETTINGS STORAGE
# ==========================================

DB_FILE = "config.json"
SETTING_FILE = "settings.json"


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


def load_destination():
    if os.path.exists(SETTING_FILE):
        try:
            with open(SETTING_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                dest = data.get("destination_channel")
                if dest:
                    return dest
        except Exception:
            pass
    
    DEST_RAW = os.getenv("DESTINATION_CHANNEL", "")
    if DEST_RAW.startswith("-100") or DEST_RAW.isdigit() or (DEST_RAW.startswith("-") and DEST_RAW[1:].isdigit()):
        return int(DEST_RAW)
    return DEST_RAW


def save_destination(channel):
    with open(SETTING_FILE, "w", encoding="utf-8") as f:
        json.dump({"destination_channel": channel}, f, ensure_ascii=False, indent=2)


bot_app = Client("control_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
user_app = Client("userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
movie_states = {}
admin_input_states = {}


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
    
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"âœ… Web Server started on port {port}")


# ==========================================
# MENU
# ==========================================

def main_menu():
    current_dest = load_destination()
    dest_text = str(current_dest) if current_dest else "Not Set"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("ðŸŽ¬ Movie á€¡á€žá€…á€ºá€á€„á€ºá€›á€”á€º", callback_data="start_movie")],
        [InlineKeyboardButton("ðŸ“‹ á€žá€°á€™á€»á€¬á€¸ Source Channels á€™á€»á€¬á€¸á€€á€­á€¯á€€á€¼á€Šá€·á€ºá€›á€”á€º", callback_data="list_channels")],
        [
            InlineKeyboardButton("âž• Add Source", callback_data="add_channel"),
            InlineKeyboardButton("âž– Del Source (Channel á€‘á€¯á€á€ºá€›á€”á€º)", callback_data="remove_channel")
        ],
        [InlineKeyboardButton(f"ðŸŽ¯ á€€á€»á€”á€±á€¬á€·á€º Channel á€€á€¼á€Šá€·á€ºá€›á€”á€º/á€•á€¼á€±á€¬á€„á€ºá€¸á€›á€”á€º: {dest_text}", callback_data="set_destination")]
    ])


def channel_keyboard(prefix, channels):
    buttons = []
    row = []
    for i, ch in enumerate(channels):
        row.append(InlineKeyboardButton(ch, callback_data=f"{prefix}_{i}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("ðŸ”™ Main Menu á€žá€­á€¯á€·", callback_data="back_home")])
    return InlineKeyboardMarkup(buttons)


# ==========================================
# START COMMAND
# ==========================================

@bot_app.on_message(filters.command("start") & filters.user(ADMIN_ID))
async def start(client, message):
    admin_input_states.pop(ADMIN_ID, None)
    await message.reply(
        "ðŸ¤– **Movie Auto Bot Control Panel**

á€¡á€±á€¬á€€á€ºá€•á€« á€á€œá€¯á€á€ºá€™á€»á€¬á€¸á€™á€¾á€á€…á€ºá€†á€„á€·á€º á€œá€­á€¯á€¡á€•á€ºá€žá€Šá€ºá€™á€»á€¬á€¸á€€á€­á€¯ á€…á€®á€™á€¶á€”á€­á€¯á€„á€ºá€•á€«á€žá€Šá€º -",
        reply_markup=main_menu()
    )


# ==========================================
# CALLBACK HANDLER (BUTTONS)
# ==========================================

@bot_app.on_callback_query(filters.user(ADMIN_ID))
async def buttons(client, query):
    data = query.data

    if data == "back_home":
        admin_input_states.pop(ADMIN_ID, None)
        await query.message.edit_text(
            "ðŸ¤– **Movie Auto Bot Control Panel**

á€¡á€±á€¬á€€á€ºá€•á€« á€á€œá€¯á€á€ºá€™á€»á€¬á€¸á€™á€¾á€á€…á€ºá€†á€„á€·á€º á€œá€­á€¯á€¡á€•á€ºá€žá€Šá€ºá€™á€»á€¬á€¸á€€á€­á€¯ á€…á€®á€™á€¶á€”á€­á€¯á€„á€ºá€•á€«á€žá€Šá€º -",
            reply_markup=main_menu()
        )

    elif data == "list_channels":
        channels = load_channels()
        text = "ðŸ“‹ **á€žá€°á€™á€»á€¬á€¸ Source Channels á€…á€¬á€›á€„á€ºá€¸á€™á€»á€¬á€¸:**

" + ("
".join(f"â€¢ {ch}" for ch in channels) if channels else "âš ï¸ á€‘á€Šá€·á€ºá€‘á€¬á€¸á€žá€±á€¬ Channel á€á€…á€ºá€á€¯á€™á€¾ á€™á€›á€¾á€­á€žá€±á€¸á€•á€«á‹")
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("ðŸ”™ Back", callback_data="back_home")]])
        await query.message.edit_text(text, reply_markup=kb)

    elif data == "add_channel":
        admin_input_states[ADMIN_ID] = "waiting_add_source"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("âŒ Cancel", callback_data="back_home")]])
        await query.message.edit_text(
            "âž• **Source Channel á€¡á€žá€…á€ºá€‘á€Šá€·á€ºá€›á€”á€º**

á€‘á€Šá€·á€ºá€œá€­á€¯á€žá€±á€¬ Channel Username (á€žá€­á€¯á€·) ID á€€á€­á€¯ á€•á€­á€¯á€·á€•á€±á€¸á€•á€« (á€¥á€•á€™á€¬: `@source_channel`):",
            reply_markup=kb
        )

    elif data == "remove_channel":
        channels = load_channels()
        if not channels:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("ðŸ”™ Back", callback_data="back_home")]])
            return await query.message.edit_text("âš ï¸ á€–á€¼á€á€ºá€‘á€¯á€á€ºá€›á€”á€º Channel á€á€…á€ºá€á€¯á€™á€¾ á€™á€›á€¾á€­á€žá€±á€¸á€•á€«á‹", reply_markup=kb)
        
        await query.message.edit_text(
            "ðŸ—‘ **á€‘á€¯á€á€ºá€•á€…á€ºá€œá€­á€¯á€žá€±á€¬ Source Channel á€€á€­á€¯ á€›á€½á€±á€¸á€•á€« -**",
            reply_markup=channel_keyboard("del_ch", channels)
        )

    elif data.startswith("del_ch_"):
        idx = int(data.split("_")[2])
        channels = load_channels()
        if idx < len(channels):
            removed = channels.pop(idx)
            save_channels(channels)
            await query.answer(f"ðŸ—‘ á€‘á€¯á€á€ºá€•á€…á€ºá€œá€­á€¯á€€á€ºá€•á€«á€•á€¼á€®: {removed}", show_alert=True)
        
        channels = load_channels()
        if not channels:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("ðŸ”™ Back", callback_data="back_home")]])
            await query.message.edit_text("ðŸ“‹ Source Channels á€…á€¬á€›á€„á€ºá€¸ á€šá€á€¯ á€•à·ƒà·Šá€…á€•á€ºá€žá€½á€¬á€¸á€•á€«á€•á€¼á€® (Empty)á‹", reply_markup=kb)
        else:
            await query.message.edit_text(
                "ðŸ—‘ **á€‘á€¯á€á€ºá€•á€…á€ºá€œá€­á€¯á€žá€±á€¬ Source Channel á€€á€­á€¯ á€‘á€•á€ºá€™á€¶á€›á€½á€±á€¸á€•á€« -**",
                reply_markup=channel_keyboard("del_ch", channels)
            )

    elif data == "set_destination":
        admin_input_states[ADMIN_ID] = "waiting_destination"
        current_dest = load_destination()
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("âŒ Cancel", callback_data="back_home")]])
        await query.message.edit_text(
            f"ðŸŽ¯ **á€€á€»á€”á€±á€¬á€·á€º Channel (Destination Channel) á€á€»á€­á€á€ºá€›á€”á€º/á€•á€¼á€±á€¬á€„á€ºá€¸á€›á€”á€º**

á€œá€€á€ºá€›á€¾á€­ Channel: `{current_dest}`

á€¡á€žá€…á€ºá€•á€¼á€±á€¬á€„á€ºá€¸á€œá€­á€¯á€•á€«á€€ Channel á Username (á€žá€­á€¯á€·) ID á€€á€­á€¯ á€•á€­á€¯á€·á€•á€±á€¸á€•á€« (á€¥á€•á€™á€¬: `@my_channel` á€žá€­á€¯á€·á€™á€Ÿá€¯á€á€º `-100xxxxxxxx`):",
            reply_markup=kb
        )

    elif data == "start_movie":
        channels = load_channels()
        if not channels:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("ðŸ”™ Back", callback_data="back_home")]])
            return await query.message.edit_text("âš ï¸ á€•á€‘á€™á€†á€¯á€¶á€¸ Source Channel á€á€…á€ºá€á€¯á€á€¯á€€á€­á€¯ á€¡á€›á€„á€ºá€‘á€Šá€·á€ºá€•á€«á‹", reply_markup=kb)
        await query.message.edit_text(
            "ðŸ“¸ **Poster á€á€„á€ºá€™á€Šá€·á€º Channel á€€á€­á€¯ á€›á€½á€±á€¸á€•á€« -**",
            reply_markup=channel_keyboard("poster", channels)
        )

    elif data.startswith("poster_"):
        idx = int(data.split("_")[1])
        ch = load_channels()[idx]
        movie_states[ADMIN_ID] = {"poster": ch, "step": 1}
        await query.message.edit_text(
            "ðŸŽ¥ **Video á€á€„á€ºá€™á€Šá€·á€º Channel á€€á€­á€¯ á€›á€½á€±á€¸á€•á€« -**",
            reply_markup=channel_keyboard("video", channels)
        )

    elif data.startswith("video_"):
        idx = int(data.split("_")[1])
        ch = load_channels()[idx]
        movie_states[ADMIN_ID]["video"] = ch
        movie_states[ADMIN_ID]["step"] = 2
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("âŒ Cancel", callback_data="back_home")]])
        await query.message.edit_text(
            "ðŸ“¤ **Video á€–á€­á€¯á€„á€ºá€€á€­á€¯ á€¤ Bot á€‘á€¶á€žá€­á€¯á€· á€•á€­á€¯á€·á€•á€±á€¸á€•á€« (Send Video File) -**",
            reply_markup=kb
        )


# ==========================================
# TEXT INPUT LISTENER (FOR CHANNELS)
# ==========================================

@bot_app.on_message(filters.text & filters.user(ADMIN_ID))
async def handle_admin_text(client, message):
    state = admin_input_states.get(ADMIN_ID)
    if not state:
        return

    text = message.text.strip()

    if state == "waiting_add_source":
        channels = load_channels()
        if text not in channels:
            channels.append(text)
            save_channels(channels)
            await message.reply(f"âœ… **Source Channel á€¡á€žá€…á€ºá€‘á€Šá€·á€ºá€•á€¼á€®á€¸á€•á€«á€•á€¼á€®:** {text}", reply_markup=main_menu())
        else:
            await message.reply(f"âš ï¸ á€šá€á€¯ Channel á€™á€¾á€¬ á€…á€¬á€›á€„á€ºá€¸á€‘á€²á€á€½á€„á€º á€›á€¾á€­á€•á€¼á€®á€¸á€žá€¬á€¸ á€–á€¼á€…á€ºá€•á€«á€žá€Šá€ºá‹", reply_markup=main_menu())
        admin_input_states.pop(ADMIN_ID, None)

    elif state == "waiting_destination":
        if text.startswith("-100") or text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
            dest = int(text)
        else:
            dest = text
        
        save_destination(dest)
        await message.reply(f"âœ… **á€€á€»á€”á€±á€¬á€·á€º Channel (Destination) á€¡á€žá€…á€º á€á€»á€­á€á€ºá€†á€€á€ºá€•á€¼á€®á€¸á€•á€«á€•á€¼á€®:** {dest}", reply_markup=main_menu())
        admin_input_states.pop(ADMIN_ID, None)


# ==========================================
# MANUAL MOVIE UPLOAD: VIDEO & POSTER
# ==========================================

@bot_app.on_message(filters.video & filters.user(ADMIN_ID))
async def upload_video(client, message):
    state = movie_states.get(ADMIN_ID)
    if not state or state.get("step") != 2:
        return

    channel = state["video"]
    msg = await message.copy(channel)
    if msg.chat.username:
        link = f"https://t.me/{msg.chat.username}/{msg.id}"
    else:
        link = f"https://t.me/c/{str(msg.chat.id)[4:]}/{msg.id}"
    
    movie_states[ADMIN_ID]["video_link"] = link
    movie_states[ADMIN_ID]["step"] = 3

    await message.reply("âœ… **Video á€á€„á€ºá€•á€¼á€®á€¸á€•á€«á€•á€¼á€®á‹**
ðŸ“¸ á€†á€€á€ºá€œá€€á€ºá **Poster á€•á€¯á€¶ + Caption** á€€á€­á€¯ á€•á€­á€¯á€·á€•á€±á€¸á€•á€«á€›á€¾á€„á€ºá‹")


@bot_app.on_message(filters.photo & filters.user(ADMIN_ID))
async def upload_poster(client, message):
    state = movie_states.get(ADMIN_ID)
    if not state or state.get("step") != 3:
        return

    channel = state["poster"]
    video_link = state.get("video_link")
    if not video_link:
        return

    caption = message.caption if message.caption else "ðŸŽ¬ New Movie"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("ðŸŽ¬ Watch / Download", url=video_link)]])
    await message.copy(channel, caption=caption, reply_markup=keyboard)
    
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("ðŸ  Control Panel á€žá€­á€¯á€· á€•á€¼á€”á€ºá€›á€”á€º", callback_data="back_home")]])
    await message.reply("âœ… **Movie á€á€„á€ºá€á€¼á€„á€ºá€¸ á€¡á€±á€¬á€„á€ºá€™á€¼á€„á€ºá€•á€«á€žá€Šá€ºá‹**", reply_markup=kb)

    movie_states.pop(ADMIN_ID, None)


# ==========================================
# USERBOT AUTO FORWARD
# ==========================================

@user_app.on_message(filters.channel)
async def auto_forward(client, message):
    channels = load_channels()
    username = f"@{message.chat.username}" if message.chat.username else None
    
    if username not in channels and message.chat.id not in channels:
        return

    destination_channel = load_destination()
    if not destination_channel:
        return

    try:
        if message.text:
            text = rewrite_text(message.text)
            await client.send_message(destination_channel, text)
        elif message.photo or message.video:
            caption = message.caption or ""
            new_caption = rewrite_text(caption) if caption else ""
            await message.copy(destination_channel, caption=new_caption)
    except Exception as e:
        print("Forward Error:", e)


# ==========================================
# START SYSTEM
# ==========================================

async def main():
    print("ðŸš€ Bot Starting...")
    await start_web_server()
    await compose([bot_app, user_app])

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()