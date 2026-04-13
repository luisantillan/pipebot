import os
import requests
import anthropic
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")
PIPEDRIVE_API_KEY = os.environ.get("PIPEDRIVE_API_KEY")
TRELLO_API_KEY = os.environ.get("TRELLO_API_KEY")
TRELLO_TOKEN = os.environ.get("TRELLO_TOKEN")
ALLOWED_CHAT_ID = int(os.environ.get("ALLOWED_CHAT_ID", "0"))

claude = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

def get_pipedrive_deals():
    url = f"https://api.pipedrive.com/v1/deals?api_token={PIPEDRIVE_API_KEY}&status=open&limit=50"
    r = requests.get(url)
    data = r.json()
    if not data.get("data"):
        return "No se encontraron tratos."
    deals = []
    for d in data["data"]:
        deal = f"- {d['title']} | Etapa: {d.get('stage_id','?')} | Valor: ${d.get('value', 0):,} | Contacto: {d.get('person_name', 'N/A')} | Org: {d.get('org_name', 'N/A')}"
        deals.append(deal)
    return "\n".join(deals)

def get_pipedrive_persons():
    url = f"https://api.pipedrive.com/v1/persons?api_token={PIPEDRIVE_API_KEY}&limit=50"
    r = requests.get(url)
    data = r.json()
    if not data.get("data"):
        return "No se encontraron contactos."
    persons = []
    for p in data["data"]:
        phones = p.get("phone", [])
        phone = phones[0]["value"] if phones else "Sin teléfono"
        emails = p.get("email", [])
        email = emails[0]["value"] if emails else "Sin email"
        org = p.get("org_name", "Sin organización")
        persons.append(f"- {p['name']} | Tel: {phone} | Email: {email} | Org:
