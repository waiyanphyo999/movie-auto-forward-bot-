import asyncio
import os
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from openai import OpenAI

# ==========================================
# 1. Render အတွက် Web Server အတု
# ==========================================
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Grok AI Movie Bot is Running!")

def keep_alive():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

threading.Thread(target=keep_alive, daemon=True).start()

# ==========================================
# 2. Configuration & Grok Setup
# ==========================================
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
XAI_API_KEY = os.environ.get("XAI_API_KEY", "")

app = Client("ai_movie_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
client_xai = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")

DATA_FILE = "bot_data.json"
user_sessions = {}

def load_target():
    if not os.path.exists(DATA_FILE): return None
    try:
        with open(DATA_FILE, "r") as f: return json.load(f).get("target_channel")
    except: return None

def save_target(channel):
    with open(DATA_FILE, "w") as f: json.dump({"target_channel": channel}, f)

# ==========================================
# 3. ခလုတ်များပါသော UI (/start)
# ==========================================
@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📡 Channel သတ်မှတ်ရန်", callback_data="cmd_set")],
        [InlineKeyboardButton("🎬 ဇာတ်ကားအသစ် စတင်ရန်", callback_data="cmd_start_post")],
        [InlineKeyboardButton("✅ အားလုံးပို့ပြီးပါပြီ (/done)", callback_data="cmd_done")],
        [InlineKeyboardButton("❌ ပယ်ဖျက်မည်", callback_data="cmd_cancel")]
    ])
    await message.reply("🎬 **Grok AI Movie Bot**\n\nအောက်ပါခလုတ်များကို အသုံးပြုပါ။", reply_markup=keyboard)

@app.on_callback_query()
async def callback_handler(client, query):
    user_id = query.from_user.id
    if query.data == "cmd_set":
        await query.message.reply("ကျေးဇူးပြု၍ `/set_channel @channel_name` ဟု ရိုက်ပေးပါ။")
    elif query.data == "cmd_start_post":
        user_sessions[user_id] = {"photo": None, "videos": [], "text": ""}
        await query.message.reply("✅ **စတင်ပါပြီ။**\n\nသူများ Channel မှ ဇာတ်ကားပုံ၊ ဗီဒီယို နှင့် စာသားများကို ဤ Bot သို့ လွတ်လပ်စွာ **Forward (သို့) Copy ကူးပို့ပါ**။\n\nအကုန်ပို့ပြီးပါက အောက်ပါ **✅ အားလုံးပို့ပြီးပါပြီ** ခလုတ် သို့မဟုတ် `/done` ကိုနှိပ်ပါ။")
    elif query.data == "cmd_done":
        await finish_and_post(client, query.message, user_id)
    elif query.data == "cmd_cancel":
        if user_id in user_sessions: del user_sessions[user_id]
        await query.message.reply("❌ လုပ်ဆောင်ဆဲ ဇာတ်ကားကို ပယ်ဖျက်လိုက်ပါပြီ။")
    await query.answer()

@app.on_message(filters.command("set_channel") & filters.private)
async def set_channel_cmd(client, message):
    if len(message.command) < 2: return await message.reply("ဥပမာ - `/set_channel @my_movies`")
    save_target(message.command[1])
    await message.reply(f"✅ Target Channel အား {message.command[1]} သို့ သတ်မှတ်ပြီးပါပြီ။")

# ==========================================
# 4. သူများ Channel မှ Forward လုပ်သမျှကို ဖမ်းယူခြင်း
# ==========================================
@app.on_message(filters.private & ~filters.command(["start", "set_channel", "done", "cancel"]))
async def capture_media(client, message):
    user_id = message.from_user.id
    if user_id not in user_sessions:
        return await message.reply("⚠️ ပထမဦးစွာ **/start** ကိုနှိပ်၍ '🎬 ဇာတ်ကားအသစ် စတင်ရန်' ခလုတ်ကို အရင်နှိပ်ပါ။")

    session = user_sessions[user_id]

    if message.photo:
        session["photo"] = message.photo.file_id
        if message.caption: session["text"] += f"\n{message.caption}"
        await message.reply("✅ ပုံ လက်ခံရရှိပါပြီ။")
    elif message.video or message.document:
        session["videos"].append(message.id)
        if message.caption: session["text"] += f"\n{message.caption}"
        await message.reply(f"✅ ဗီဒီယို/ဖိုင် ({len(session['videos'])}) ခု လက်ခံရရှိပါပြီ။")
    elif message.text:
        session["text"] += f"\n{message.text}"
        await message.reply("✅ စာသား/ဇာတ်လမ်းအကျဉ်း လက်ခံရရှိပါပြီ။")

# ==========================================
# 5. အားလုံးပို့ပြီး၍ Channel သို့ Auto တင်ခြင်း
# ==========================================
@app.on_message(filters.command("done") & filters.private)
async def done_cmd(client, message):
    await finish_and_post(client, message, message.from_user.id)

async def finish_and_post(client, message, user_id):
    if user_id not in user_sessions: 
        return await message.reply("⚠️ လုပ်ဆောင်ဆဲ Post မရှိပါ။ အသစ်စတင်ရန် ခလုတ်နှိပ်ပါ။")
    
    target_channel = load_target()
    if not target_channel: 
        return await message.reply("⚠️ Channel မသတ်မှတ်ရသေးပါ။ `/set_channel @yourchannel` အရင်လုပ်ပါ။")

    session = user_sessions[user_id]
    if not session["photo"]: return await message.reply("⚠️ ဇာတ်ကားပုံ မပါသေးပါ။ ပုံအရင်ပို့ပေးပါ။")
    if not session["videos"]: return await message.reply("⚠️ ဗီဒီယို တစ်ခုမှ မပါသေးပါ။ ဗီဒီယိုအရင်ပို့ပေးပါ။")

    status_msg = await message.reply("⏳ Grok AI ဖြင့် ဇာတ်ညွှန်းရေးဆွဲကာ Channel သို့ တင်နေပါသည်... ခဏစောင့်ပါ။")

    try:
        video_links = []
        for i, vid_msg_id in enumerate(session["videos"]):
            sent_vid = await client.copy_message(chat_id=target_channel, from_chat_id=user_id, message_id=vid_msg_id)
            video_links.append(f"အပိုင်း ({i+1}) - 🔗 {sent_vid.link}")
            await asyncio.sleep(2)

        formatted_links = "\n".join(video_links)
        original_text = session["text"].strip() or "No info provided."

        prompt = f"""
        Based on the following forwarded movie info: "{original_text}"
        Write a new, clean Telegram movie post in Burmese language.
        Format exactly like this using HTML tags:

        <blockquote>[Movie Name or Genre] ❞</blockquote>
        [1 or 2 catchy sentences introducing the movie in Burmese]

        <blockquote>ဇာတ်လမ်းအကျဉ်း: [A short, engaging synopsis in Burmese]</blockquote>

        <blockquote>👇 အောက်က Link မှာ ဝင်ရောက်ကြည့်ရှုလိုက်ပါ 👇
        {formatted_links}</blockquote>
        """
        
        completion = client_xai.chat.completions.create(
            model="grok-beta",
            messages=[
                {"role": "system", "content": "You are a professional movie channel admin. Output raw HTML only without ```html."},
                {"role": "user", "content": prompt}
            ]
        )
        ai_caption = completion.choices[0].message.content.strip()

        await client.send_photo(chat_id=target_channel, photo=session["photo"], caption=ai_caption, parse_mode=ParseMode.HTML)
        del user_sessions[user_id]
        await status_msg.edit_text("✅ သင့် Channel သို့ အောင်မြင်စွာ တင်ပြီးပါပြီ! 🎉")
        
    except Exception as e:
        await status_msg.edit_text(f"❌ အမှားအယွင်းဖြစ်ပွားခဲ့ပါသည်: {e}")

print("🚀 Grok AI Forwarding Movie Bot is starting...")
app.run()
