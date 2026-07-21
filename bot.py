import asyncio
# Render အတွက် Event Loop ပြဿနာ မဖြစ်စေရန်
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

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SESSION_STRING = os.getenv("SESSION_STRING")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ==========================================
# CHECK REQUIRED VARIABLES
# ==========================================

if not API_ID:
    raise Exception("Missing API_ID")
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

def rewrite_text(text):
    if not text:
        return ""
    prompt = f"""
အောက်ပါစာသားကို မြန်မာလိုပဲ အဓိပ္ပာယ်မပြောင်းဘဲ ပိုမိုဆွဲဆောင်မှုရှိအောင် ပြန်ရေးပေးပါ။

{text}
"""
    if gemini_model:
        try:
            result = gemini_model.generate_content(prompt)
            return result.text
        except Exception as e:
            print("Gemini Error:", e)
    return text

# ==========================================
# DATABASE
# ==========================================

DB_FILE = "config.json"

def load_channels():
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_channels(data):
    with open(DB