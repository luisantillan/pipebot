import os
import requests
import anthropic
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY", "")
PIPEDRIVE_API_KEY = os.environ.get("PIPEDRIVE_API_KEY", "")
ALLOWED_CHAT_ID = int(os.environ.get("ALLOWED_CHAT_ID", "0"))

claude = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

def get_pipedrive_deals():
    url = "https://api.pipedrive.com/v1/deals?api_token=" + PIPEDRIVE_API_KEY + "&status=open&limit=50"
    r = requests.get(url)
    data = r.json()
    if not data.get("data"):
        return "No se encontraron tratos."
    deals = []
    for d in data["data"]:
        titulo = str(d.get("title") or "Sin titulo")
        valor = str(d.get("value") or 0)
        contacto = str(d.get("person_name") or "N/A")
        org = str(d.get("org_name") or "N/A")
        etapa = str(d.get("stage_id") or "?")
        deals.append("- " + titulo + " | Etapa: " + etapa + " | Valor: $" + valor + " | Contacto: " + contacto + " | Org: " + org)
    return "\n".join(deals)

def get_pipedrive_persons():
    url = "https://api.pipedrive.com/v1/persons?api_token=" + PIPEDRIVE_API_KEY + "&limit=50"
    r = requests.get(url)
    data = r.json()
    if not data.get("data"):
        return "No se encontraron contactos."
    persons = []
    for p in data["data"]:
        nombre = str(p.get("name") or "Sin nombre")
        phones = p.get("phone") or []
        phone = phones[0]["value"] if phones else "Sin telefono"
        emails = p.get("email") or []
        email = emails[0]["value"] if emails else "Sin ema
