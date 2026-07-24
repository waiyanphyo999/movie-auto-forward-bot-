import os
import asyncio
from aiohttp import web
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import google.generativeai as genai

# ==========================================
# 1. Configuration & Security (.env)
# ==========================================
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "waiyanphyo99")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Gemini AI Setup
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    ai_model = genai.GenerativeModel("gemini-1.5-flash")
else:
    ai_model = None

bot = Client("gemini_router_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# System State Memory
settings = {
    "channels": [],
    "current_index": 0,
    "is_active": False,
    "waiting_for_channels": False
}

# ==========================================
# 2. Keyboards
# ==========================================
def get_menu():
    ch_count = len(settings["channels"])
    status = "✅ အလုပ်လုပ်နေသည် (ON)" if settings["is_active"] else "⏸️ ရပ်နားထားသည် (OFF)"
    ai_status = "✅ ချိတ်ဆက်ပြီး" if ai_model else "❌ API Key မရှိပါ"
    
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📡 Channel များ ထည့်ရန် ({ch_count} ခု)", callback_data="add_channels")],
        [InlineKeyboardButton(f"🚀 Auto Distribute: {status}", callback_data="toggle_routing")],
        [InlineKeyboardButton(f"🤖 Gemini AI Status: {ai_status}", callback_data="ai_info")],
        [InlineKeyboardButton("🗑 Channel စာရင်းဖျက်မည်", callback_data="clear_channels")],
        [InlineKeyboardButton("ℹ️ အသုံးပြုနည်း", callback_data="help")]
    ])

# ==========================================
# 3. Gemini AI Synopsis Helper
# ==========================================
def generate_ai_review(movie_name):
    if not ai_model:
        return f"🎬 **{movie_name}**\n\nဇာတ်ကားသစ် ရောက်ရှိလာပါပြီ။"
    
    prompt = f"အောက်ပါ ရုပ်ရှင်အမည်အတွက် ဆွဲဆောင်မှုရှိပြီး စိတ်ဝင်စားဖွယ် မြန်မာလို ဇာတ်ညွှန်းအကျဉ်း (Review/Synopsis) ကို အီမိုဂျီများပါဝင်၍ အတိုချုံး ရေးပေးပါ။\n\nရုပ်ရှင်အမည်: {movie_name}"
    try:
        response = ai_model.generate_content(prompt)
        return response.text
    except Exception as e:
        print("Gemini AI Error:", e)
        return f"🎬 **{movie_name}**\n\nစိတ်ဝင်စားဖွယ် ဇာတ်ကားသစ်ကို ကြည့်ရှုနိုင်ပါပြီ။"

# ==========================================
# 4. Commands & Callbacks
# ==========================================
@bot.on_message(filters.command("start") & filters.private)
async def start(client, message):
    if message.from_user.username == ADMIN_USERNAME:
        await message.reply_text(
            "🎬 **Gemini AI Multi-Channel Bulk Bot**\n\n"
            "သူများ Channel မှ ပို့စ်များကို Bulk Forward လုပ်လိုက်ရုံဖြင့် Gemini AI ဖြင့် ဇာတ်ညွှန်းအသစ်ဖန်တီးပေးပြီး Hashtag (`#`) ထည့်ကာ Channel (၂၅) ခုသို့ အလှည့်ကျ တင်ပေးမည့် စနစ်ဖြစ်ပါသည်။",
            reply_markup=get_menu()
        )
    else:
        await message.reply_text("⛔ သင်သည် ဤ Bot ကို အသုံးပြုခွင့် မရှိပါ။")

@bot.on_callback_query()
async def cb_handler(client, callback_query: CallbackQuery):
    data = callback_query.data
    
    if data == "add_channels":
        settings["waiting_for_channels"] = True
        await callback_query.message.edit_text(
            "📡 **Channel များကို ထည့်သွင်းခြင်း**\n\n"
            "Channel Username သို့မဟုတ် ID များကို **တစ်ကြောင်းလျှင် တစ်ခုကျစီ ခွဲ၍** ရိုက်ထည့်ပေးပါ (၂၅ ခုစလုံး တစ်ခါတည်း ထည့်နိုင်သည်):\n\n"
            "**ဥပမာ -**\n"
            "`@channel_A`\n"
            "`@channel_B`\n"
            "`-100123456789`",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 နောက်သို့", callback_data="back")]])
        )
    
    elif data == "toggle_routing":
        if not settings["channels"]:
            await callback_query.answer("⚠️ ကျေးဇူးပြု၍ Channel များကို အရင်ထည့်ပါ။", show_alert=True)
            return
        settings["is_active"] = not settings["is_active"]
        await callback_query.message.edit_text("လုပ်ဆောင်ချက် ပြောင်းလဲမှု အောင်မြင်ပါသည်။", reply_markup=get_menu())
        
    elif data == "ai_info":
        status_text = "Gemini AI အလုပ်လုပ်နေပါသည်။" if ai_model else "Render Environment Variables တွင် GEMINI_API_KEY ထည့်ရန် လိုအပ်ပါသည်။"
        await callback_query.answer(status_text, show_alert=True)
        
    elif data == "clear_channels":
        settings["channels"] = []
        settings["current_index"] = 0
        settings["is_active"] = False
        await callback_query.answer("🗑 ရှင်းလင်းပြီးပါပြီ။", show_alert=True)
        await callback_query.message.edit_text("လုပ်ဆောင်ချက် ပြောင်းလဲမှု အောင်မြင်ပါသည်။", reply_markup=get_menu())
        
    elif data == "back":
        settings["waiting_for_channels"] = False
        await callback_query.message.edit_text("🎬 **Gemini AI Multi-Channel Bulk Bot**", reply_markup=get_menu())
        
    elif data == "help":
        msg = (
            "ℹ️ **အသုံးပြုနည်း**\n\n"
            "၁။ Channel များကို စာကြောင်းခွဲပြီး ထည့်ပါ။\n"
            "၂။ `🚀 Auto Distribute` ကို ON ပါ။\n"
            "၃။ သူများ Channel မှ ဇာတ်ကားများကို Select မှတ်၍ Bot ဆီသို့ Bulk Forward ပို့လိုက်ပါ။\n"
            "၄။ Bot မှ ဇာတ်ကားနာမည်ကို ဖတ်ယူပြီး Gemini AI ဖြင့် ဇာတ်ညွှန်းထုတ်ပေးကာ Hashtag (`#`) ထည့်၍ Channel ၂၅ ခုဆီသို့ အလှည့်ကျ တင်ပေးပါမည်။"
        )
        await callback_query.message.edit_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 နောက်သို့", callback_data="back")]]))

@bot.on_message(filters.text & filters.private & ~filters.command("start"))
async def text_handler(client, message):
    if settings.get("waiting_for_channels"):
        lines = message.text.strip().split("\n")
        new_channels = [line.strip() for line in lines if line.strip()]
        settings["channels"].extend(new_channels)
        settings["waiting_for_channels"] = False
        await message.reply_text(
            f"✅ Channel **{len(new_channels)}** ခု ထည့်သွင်းပြီးပါပြီ!\n"
            f"စုစုပေါင်း: **{len(settings['channels'])}** ခု ရှိပါသည်။\n\n"
            f"ယခု '🚀 Auto Distribute' ကိုဖွင့်၍ စတင် Forward နိုင်ပါပြီ။",
            reply_markup=get_menu()
        )
        return

# ==========================================
# 5. Bulk Auto-Router & Gemini AI Engine
# ==========================================
@bot.on_message(filters.private & ~filters.command("start") & ~filters.text)
async def auto_router(client, message):
    if settings["is_active"] and settings["channels"]:
        target_ch = settings["channels"][settings["current_index"]]
        
        try:
            old_caption = message.caption if message.caption else ""
            movie_title = "Movie"
            
            if old_caption:
                # ပထမစာကြောင်းကို ဇာတ်ကားနာမည်အဖြစ် သတ်မှတ်ခြင်း
                lines = old_caption.split("\n")
                movie_title = lines[0].replace("#", "").replace("🎬", "").strip()
            
            # Gemini AI ဖြင့် ဇာတ်ညွှန်းအသစ်ထုတ်ခြင်း နှင့် Hashtag ဖန်တီးခြင်း
            ai_synopsis = generate_ai_review(movie_title)
            hashtag_title = f"#{movie_title.replace(' ', '_')}"
            
            final_caption = (
                f"🎬 **{hashtag_title}**\n\n"
                f"{ai_synopsis}\n\n"
                f"💬 **Support Group:**\nhttps://t.me/+eDyM64ujw7hhNjll"
            )
            
            # Target Channel သို့ ပို့စ်တင်ခြင်း (Caption အသစ်ဖြင့်)
            if message.photo:
                await client.send_photo(chat_id=target_ch, photo=message.photo.file_id, caption=final_caption)
            elif message.video:
                await client.send_video(chat_id=target_ch, video=message.video.file_id, caption=final_caption)
            elif message.document:
                await client.send_document(chat_id=target_ch, document=message.document.file_id, caption=final_caption)
            else:
                await message.copy(chat_id=target_ch)
            
            # နောက်ထပ် Channel သို့ အလှည့်ရွှေ့ခြင်း (Round-Robin)
            settings["current_index"] = (settings["current_index"] + 1) % len(settings["channels"])
            
            # Telegram FloodWait မဖြစ်စေရန် ခေတ္တစောင့်ခြင်း
            await asyncio.sleep(1.0)
            
        except Exception as e:
            await message.reply_text(f"❌ Error in {target_ch}: `{e}`")

# ==========================================
# 6. Dummy Web Server (For Render)
# ==========================================
async def web_server():
    async def handle(request):
        return web.Response(text="Gemini Bot is running smoothly!")
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    await web_server()
    await bot.start()
    import pyrogram
    await pyrogram.idle()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
