import json
import asyncio
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pyrogram import Client, filters

# ==========================================
# Render အား လှည့်စားရန် Web Server အတု ဖန်တီးခြင်း
# ==========================================
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive and running!")

def keep_alive():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

threading.Thread(target=keep_alive, daemon=True).start()

# ==========================================
# Bot Main Code 
# ==========================================
# .env (သို့) Render Environment မှ တန်ဖိုးများ ယူခြင်း
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Client("movie_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# json ဖိုင်မှ Channel List များကို ဖတ်ခြင်း
def get_channels():
    try:
        with open("channels.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

@app.on_message(filters.command("forward_movie") & filters.user("သင့်ရဲ့Admin_Username"))
async def auto_forward(client, message):
    channels = get_channels()
    if not channels:
        await message.reply("Channel list အလွတ်ဖြစ်နေပါသည်။")
        return
    
    await message.reply(f"Channel စုစုပေါင်း {len(channels)} ခုသို့ စတင် ပေးပို့နေပါပြီ...")
    
    # ရုပ်ရှင် Post ကို Channel များဆီ တစ်ခုပြီးတစ်ခု ပို့ခြင်း
    for channel_id in channels:
        try:
            # message.reply_to_message ကနေတဆင့် ရုပ်ရှင် Post ကို ယူပြီး Forward လုပ်ခြင်း
            await message.reply_to_message.copy(chat_id=channel_id)
            await asyncio.sleep(2) # Telegram က Ban မခံရအောင် ၂ စက္ကန့် နားပေးခြင်း
        except Exception as e:
            print(f"Error sending to {channel_id}: {e}")
            
    await message.reply("✅ Channel အားလုံးသို့ ပေးပို့ပြီးပါပြီ။")

print("🚀 Movie Bot is starting...")
app.run()
