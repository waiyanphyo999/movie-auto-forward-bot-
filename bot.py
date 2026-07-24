import os
import asyncio
from aiohttp import web
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# ==========================================
# 1. Configuration & Security (.env)
# ==========================================
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "waiyanphyo99")

bot = Client("bulk_router_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

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
    
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📡 Channel များ ထည့်ရန် ({ch_count} ခု)", callback_data="add_channels")],
        [InlineKeyboardButton(f"🚀 Auto Distribute: {status}", callback_data="toggle_routing")],
        [InlineKeyboardButton("🗑 Channel စာရင်းဖျက်မည်", callback_data="clear_channels")],
        [InlineKeyboardButton("ℹ️ အသုံးပြုနည်း", callback_data="help")]
    ])

# ==========================================
# 3. Commands & Callbacks
# ==========================================
@bot.on_message(filters.command("start") & filters.private)
async def start(client, message):
    if message.from_user.username == ADMIN_USERNAME:
        await message.reply_text(
            "🎬 **Multi-Channel Bulk Auto-Router Bot**\n\n"
            "သူများ Channel မှ ပို့စ်များကို အများကြီး တစ်ပြိုင်တည်း Forward လုပ်လိုက်ရုံဖြင့် သင်၏ Channel (၂၅) ခုသို့ တစ်လှည့်စီ အလိုအလျောက် ခွဲဝေတင်ပေးမည်ဖြစ်ပြီး ဇာတ်ကားနာမည်များကို `#` (Hashtag) အလိုအလျောက် ထည့်ပေးမည့် စနစ်ဖြစ်ပါသည်။",
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
            "Channel Username သို့မဟုတ် ID များကို **တစ်ကြောင်းလျှင် တစ်ခုကျစီ ခွဲ၍** တစ်ပြိုင်တည်း ရိုက်ထည့်ပေးပါ (၂၅ ခုစလုံး တစ်ခါတည်း ထည့်နိုင်ပါသည်):\n\n"
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
        
    elif data == "clear_channels":
        settings["channels"] = []
        settings["current_index"] = 0
        settings["is_active"] = False
        await callback_query.answer("🗑 ရှင်းလင်းပြီးပါပြီ။", show_alert=True)
        await callback_query.message.edit_text("လုပ်ဆောင်ချက် ပြောင်းလဲမှု အောင်မြင်ပါသည်။", reply_markup=get_menu())
        
    elif data == "back":
        settings["waiting_for_channels"] = False
        await callback_query.message.edit_text("🎬 **Multi-Channel Bulk Auto-Router Bot**", reply_markup=get_menu())
        
    elif data == "help":
        msg = (
            "ℹ️ **အသုံးပြုနည်း (Bulk Forward Mode)**\n\n"
            "၁။ Channel များကို စာကြောင်းခွဲပြီး ထည့်ပါ။\n"
            "၂။ `🚀 Auto Distribute` ကို နှိပ်၍ (✅ အလုပ်လုပ်နေသည်) ဖြစ်အောင် ဖွင့်ပါ။\n"
            "၃။ သူများ Channel မှ ဇာတ်ကားများကို Select မှတ်ပြီး Bot ဆီသို့ တိုက်ရိုက် Forward ပို့လိုက်ပါ။\n"
            "၄။ Bot မှ ဇာတ်ကားနာမည်များကို `#` (Hashtag) အလိုအလျောက် ထည့်သွင်းပေးပြီး Channel ၂၅ ခုသို့ အလှည့်ကျ ချက်ချင်း လိုက်တင်ပေးသွားပါမည်။"
        )
        await callback_query.message.edit_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 နောက်သို့", callback_data="back")]]))

# ==========================================
# 4. Channel List Setup
# ==========================================
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
# 5. Bulk Auto-Router & Hashtag Engine
# ==========================================
@bot.on_message(filters.private & ~filters.command("start") & ~filters.text)
async def auto_router(client, message):
    if settings["is_active"] and settings["channels"]:
        target_ch = settings["channels"][settings["current_index"]]
        
        try:
            # မူလ Caption သို့မဟုတ် Text ကို ယူခြင်း
            caption = message.caption if message.caption else ""
            
            if caption:
                # ဇာတ်ကားနာမည်တွင် Hashtag အလိုအလျောက် ထည့်သွင်းခြင်း (ဥပမာ - #MovieName)
                # ပထမဆုံး စာကြောင်းကို ဇာတ်ကားနာမည်အဖြစ် ယူ၍ Hashtag ခံပေးခြင်း
                lines = caption.split("\n")
                movie_title = lines[0].replace("#", "").strip() # မူလ ပါပြီးသား # များကို ရှင်းထုတ်ခြင်း
                hashtag_title = f"#{movie_title.replace(' ', '_')}" # နေရာလပ်များကို _ ဖြင့်အစားထိုး၍ Hashtag ဖန်တီးခြင်း
                
                # ကျန်တဲ့ စာသားများနှင့် ပေါင်းစပ်ခြင်း
                lines[0] = f"🎬 {hashtag_title}"
                new_caption = "\n".join(lines)
                
                # ပို့စ်တင်ခြင်း (Caption အသစ်ဖြင့်)
                await message.copy(chat_id=target_ch, caption=new_caption)
            else:
                # စာသားမပါက ပုံ/ဗီဒီယို သက်သက် Copy ကူးပေးခြင်း
                await message.copy(chat_id=target_ch)
            
            # နောက်ထပ် Channel သို့ အလှည့်ရွှေ့ခြင်း (Round-Robin)
            settings["current_index"] = (settings["current_index"] + 1) % len(settings["channels"])
            
            # Telegram FloodWait မဖြစ်စေရန် ခေတ္တစောင့်ခြင်း
            await asyncio.sleep(0.8) 
            
        except Exception as e:
            await message.reply_text(f"❌ Error in {target_ch}: `{e}`")

# ==========================================
# 6. Dummy Web Server (For Render)
# ==========================================
async def web_server():
    async def handle(request):
        return web.Response(text="Bot is running smoothly!")
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
