import os
import asyncio
from aiohttp import web
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# ==========================================
# 1. Environment Variables 
# ==========================================
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "waiyanphyo99")

bot = Client("movie_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Channel မှတ်သားရန်
settings = {"target_channel": None, "is_active": False}

# ==========================================
# 2. ခလုတ်များ (Inline Keyboards)
# ==========================================
def get_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📡 Channel သတ်မှတ်ရန်", callback_data="set_channel")],
        [InlineKeyboardButton("🎬 Auto Forward စတင်မည်", callback_data="start_forward")],
        [InlineKeyboardButton("⏹️ ခေတ္တရပ်မည်", callback_data="stop_forward")],
        [InlineKeyboardButton("ℹ️ လုပ်ဆောင်နိုင်စွမ်းများ", callback_data="help_info")]
    ])

# ==========================================
# 3. Bot အလုပ်လုပ်မည့် လုပ်ငန်းစဉ်များ
# ==========================================
@bot.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    if message.from_user.username == ADMIN_USERNAME:
        await message.reply_text(
            "🎬 **Movie Auto Forward Bot မှ ကြိုဆိုပါတယ်။**\n\nအောက်ပါခလုတ်များကို အသုံးပြု၍ Channel များကို အလွယ်တကူ ထိန်းချုပ်နိုင်ပါသည်။",
            reply_markup=get_main_menu()
        )
    else:
        await message.reply_text("⛔ သင်သည် ဤ Bot ကို အသုံးပြုခွင့် မရှိပါ။")

@bot.on_callback_query()
async def callback_handler(client, callback_query: CallbackQuery):
    data = callback_query.data
    
    if data == "set_channel":
        await callback_query.message.edit_text(
            "📡 **Target Channel သတ်မှတ်ခြင်း**\n\nသင် Forward လုပ်လိုသော Channel ၏ Username (ဥပမာ - `@my_movie_channel`) သို့မဟုတ် Channel ID (`-100...`) ကို ယခု ရိုက်ထည့်ပေးပါ။\n\n*(မှတ်ချက်: Bot အား ထို Channel တွင် Admin ပေးထားရန် လိုအပ်ပါသည်)*"
        )
        settings["waiting_for_channel"] = True

    elif data == "start_forward":
        if not settings.get("target_channel"):
            await callback_query.answer("⚠️ ကျေးဇူးပြု၍ Channel ကို အရင်သတ်မှတ်ပါ။", show_alert=True)
            return
        settings["is_active"] = True
        await callback_query.message.edit_text(
            f"✅ **Auto Forward စတင်ပါပြီ**\n\nယခု အခြား Channel များမှ ဇာတ်ကား Video နှင့် ပုံများကို ဤ Bot ထံသို့ တိုက်ရိုက် Forward ပို့ပေးလိုက်ရုံဖြင့် သတ်မှတ်ထားသော {settings['target_channel']} သို့ Auto လှမ်းတင်ပေးပါမည်။",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 နောက်သို့", callback_data="back_main")]])
        )

    elif data == "stop_forward":
        settings["is_active"] = False
        await callback_query.message.edit_text(
            "⏹️ **Auto Forward ရပ်တန့်ထားပါသည်။**",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 နောက်သို့", callback_data="back_main")]])
        )

    elif data == "help_info":
        info = (
            "🤖 **Bot ၏ လုပ်ဆောင်နိုင်စွမ်းများ:**\n\n"
            "၁။ **Channel သတ်မှတ်ရန်** - မိမိ ဇာတ်ကားတင်မည့် Channel နာမည်ကို လွယ်ကူစွာ ချိတ်ဆက်နိုင်ခြင်း။\n"
            "၂။ **Auto Forward** - အခြား Channel မှ ဇာတ်ကားများကို လက်ဖြင့် ရိုက်ထည့်စရာမလိုဘဲ Bot ဆီ Forward ပို့လိုက်ရုံဖြင့် မိမိ Channel သို့ အလိုအလျောက် ပြန်တင်ပေးခြင်း။\n"
            "၃။ **Admin Control** - ခလုတ်များဖြင့် လွယ်ကူစွာ ထိန်းချုပ်နိုင်ခြင်း။"
        )
        await callback_query.message.edit_text(info, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 နောက်သို့", callback_data="back_main")]]))
        
    elif data == "back_main":
        await callback_query.message.edit_text(
            "🎬 **Movie Auto Forward Bot**\n\nအောက်ပါခလုတ်များကို အသုံးပြုပါ။",
            reply_markup=get_main_menu()
        )

@bot.on_message(filters.text & filters.private)
async def text_handler(client, message):
    if settings.get("waiting_for_channel"):
        settings["target_channel"] = message.text
        settings["waiting_for_channel"] = False
        await message.reply_text(
            f"✅ Target Channel အား **{message.text}** အဖြစ် သတ်မှတ်ပြီးပါပြီ။\n\nယခု 'Auto Forward စတင်မည်' ခလုတ်ကို နှိပ်၍ အသုံးပြုနိုင်ပါပြီ။",
            reply_markup=get_main_menu()
        )

# Media များကို ဖမ်းယူ၍ Forward လုပ်ခြင်း (အဓိက အလုပ်လုပ်သောအပိုင်း)
@bot.on_message((filters.video | filters.photo | filters.document) & filters.private)
async def auto_forward_media(client, message):
    if message.from_user.username == ADMIN_USERNAME and settings.get("is_active"):
        target = settings.get("target_channel")
        try:
            # Bot ထံသို့ တိုက်ရိုက် ပို့လာသော အကြောင်းအရာများကို Target Channel သို့ ပို့ပေးခြင်း
            await message.copy(chat_id=target)
            await message.reply_text("✅ သင့် Channel သို့ အောင်မြင်စွာ တင်ပြီးပါပြီ။", quote=True)
        except Exception as e:
            await message.reply_text(f"❌ Error ဖြစ်နေပါသည်: {e}\nChannel နာမည်မှန်ကန်မှုရှိမရှိနှင့် Bot အား Admin ပေးထားခြင်း ရှိမရှိ စစ်ဆေးပါ။")

# ==========================================
# 4. Dummy Web Server (Render တွင် Timeout မဖြစ်စေရန်)
# ==========================================
async def web_server():
    async def handle(request):
        return web.Response(text="Bot is running smoothly on Render!")
    
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Web server started on port {port}")

async def main():
    # Web server နှင့် Bot အား တစ်ပြိုင်နက်တည်း Run ခြင်း
    await web_server()
    await bot.start()
    import pyrogram
    await pyrogram.idle()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
