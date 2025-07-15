import os
import time as _time_module
os.environ['TZ'] = 'Europe/Madrid'
try:
    _time_module.tzset()
except AttributeError:
    pass
import requests
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from datetime import datetime, time, timedelta
import json
import threading
from flask import Flask
from zoneinfo import ZoneInfo
TIMEZONE = ZoneInfo("Europe/Madrid")


load_dotenv()

# Set DEBUG_MODE based on environment variable (default: 0)
DEBUG_MODE = int(os.getenv("DEBUG_MODE", "1"))

# Health endpoint and state persistence
health_app = Flask(__name__)

@health_app.route("/")
def health():
    return "OK"

STATE_FILE = "state.json"
HISTORY_FILE = "history.json"

def load_state():
    global fichado_hoy
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
            dt_str = data.get("datetime", data.get("date"))
            # Parse ISO datetime or fallback date string
            try:
                dt = datetime.fromisoformat(dt_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=TIMEZONE)
                else:
                    dt = dt.astimezone(TIMEZONE)
            except ValueError:
                dt = datetime.strptime(dt_str, "%Y-%m-%d")
            if dt.date() == datetime.now(TIMEZONE).date() and data.get("fichado"):
                fichado_hoy = True
            else:
                fichado_hoy = False
        else:
            fichado_hoy = False
    except Exception:
        fichado_hoy = False

def save_state():
    try:
        with open(STATE_FILE, "w") as f:
            json.dump({
                "datetime": datetime.now(TIMEZONE).astimezone(TIMEZONE).isoformat(),
                "fichado": fichado_hoy
            }, f)
    except Exception:
        pass

def log_checkin():
    """Append current timestamp to history file."""
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r") as f:
                data = json.load(f)
        else:
            data = {"history": []}
        data["history"].append({"timestamp": datetime.now(TIMEZONE).astimezone(TIMEZONE).isoformat()})
        with open(HISTORY_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"❌ Error logging check-in: {e}")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID"))
SESAME_EMAIL = os.getenv("SESAME_EMAIL")
SESAME_PASSWORD = os.getenv("SESAME_PASSWORD")
EMPLOYEE_ID = os.getenv("SESAME_EMPLOYEE_ID")

fichado_hoy = False  # Estado diario

# Función para hacer login en Sesame
def sesame_login():
    url = "https://back-eu1.sesametime.com/api/v3/security/login"
    response = requests.post(url, json={
        "email": SESAME_EMAIL,
        "password": SESAME_PASSWORD
    })
    response.raise_for_status()
    return response.json()["data"]

# Función para hacer check-in
def sesame_check_in(token):
    url = f"https://back-eu1.sesametime.com/api/v3/employees/{EMPLOYEE_ID}/check-in"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "origin": "web",
        "timezone": "Europe/Madrid"
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return True
    else:
        raise Exception(f"Error al hacer check-in: {response.status_code} {response.text}")

# Reset del estado cada día a medianoche
def reset_estado_diario(context=None):
    global fichado_hoy
    fichado_hoy = False
    save_state()

# Comando /start
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["✅ Fichar ahora"]]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="📌 Bienvenido. Pulsa el botón para fichar cuando quieras:",
        reply_markup=markup
    )

# Comando /fichar o botón
async def cmd_fichar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global fichado_hoy
    if fichado_hoy:
        await update.message.reply_text("⚠️ Ya has fichado hoy, no es necesario volver a fichar.")
        return
    try:
        await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="🔄 Realizando fichaje...")
        token = sesame_login()
        sesame_check_in(token)
        fichado_hoy = True
        save_state()
        log_checkin()
        await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="✅ Fichaje realizado correctamente.")
    except Exception as e:
        await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"❌ Error al fichar:\n{str(e)}")

# Función para enviar recordatorio solo si no se ha fichado
async def enviar_recordatorio(context):
    # If already fichado or cancelled, remove this repeating job
    if fichado_hoy:
        try:
            context.job.schedule_removal()
        except Exception:
            pass
        return

    print("DEBUG: enviar_recordatorio triggered")
    buttons = [
        [InlineKeyboardButton("✅ Fichar ahora", callback_data="fichar")],
        [InlineKeyboardButton("⛔️ Cancelar", callback_data="cancelar")]
    ]
    markup = InlineKeyboardMarkup(buttons)
    try:
        await context.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text="⏰ ¿Te has olvidado de fichar hoy? Elige una opción:",
            reply_markup=markup
        )
    except Exception as e:
        print(f"❌ Error enviando recordatorio: {e}")

# Manejador de los botones inline del recordatorio
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global fichado_hoy
    query = update.callback_query
    await query.answer()
    if fichado_hoy:
        await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="⚠️ Ya has fichado hoy, recordatorios detenidos.")
        try:
            context.job.schedule_removal()
        except Exception:
            pass
        return
    data = query.data
    print("DEBUG: Received callback data:", data)
    if data == "fichar":
        await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="🔄 Realizando fichaje...")
        try:
            token = sesame_login()
            sesame_check_in(token)
            fichado_hoy = True
            save_state()
            log_checkin()
            await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="✅ Fichaje realizado correctamente.")
        except Exception as e:
            await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"❌ Error al fichar:\n{e}")
    elif data == "cancelar":
        fichado_hoy = True
        save_state()
        await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="⚠️ Recordatorios cancelados para hoy.")

def main():
    global app
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    load_state()
    threading.Thread(
        target=lambda: health_app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000))),
        daemon=True
    ).start()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("fichar", cmd_fichar))
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Schedule reset at midnight every day
    app.job_queue.run_daily(reset_estado_diario, time=time(0, 0))

    if DEBUG_MODE:
        # PRUEBA: Recordatorios cada 20 segundos
        app.job_queue.run_repeating(enviar_recordatorio, interval=5, first=10)
        print("🧪 Bot escuchando en modo PRUEBA...")
    else:
        # PRODUCCIÓN: Recordatorio inicial a las 07:30 de lunes a viernes
        app.job_queue.run_daily(enviar_recordatorio, time=time(7, 30), days=(0,1,2,3,4))

        # PRODUCCIÓN: Reintentos cada 10 minutos desde las 07:40
        now = datetime.now(TIMEZONE)
        first_run = now.replace(hour=7, minute=40, second=0, microsecond=0)
        if now > first_run:
            first_run += timedelta(days=1)
        app.job_queue.run_repeating(enviar_recordatorio, interval=600, first=first_run)
        print("🤖 Bot escuchando en modo PRODUCCIÓN...")
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()