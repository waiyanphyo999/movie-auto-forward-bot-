import json
import asyncio
from pyrogram import Client, filters

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
