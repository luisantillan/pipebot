import os
import requests
import anthropic
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")
PIPEDRIVE_API_KEY = os.environ.get("PIPEDRIVE_API_KEY")
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
        titulo = d.get("title", "Sin titulo")
        valor = d.get("value", 0)
        contacto = d.get("person_name", "N/A")
        org = d.get("org_name", "N/A")
        etapa = d.get("stage_id", "?")
        deals.append("- " + titulo + " | Etapa: " + str(etapa) + " | Valor: $" + str(valor) + " | Contacto: " + contacto + " | Org: " + org)
    return "\n".join(deals)

def get_pipedrive_persons():
    url = "https://api.pipedrive.com/v1/persons?api_token=" + PIPEDRIVE_API_KEY + "&limit=50"
    r = requests.get(url)
    data = r.json()
    if not data.get("data"):
        return "No se encontraron contactos."
    persons = []
    for p in data["data"]:
        nombre = p.get("name", "Sin nombre")
        phones = p.get("phone", [])
        phone = phones[0]["value"] if phones else "Sin telefono"
        emails = p.get("email", [])
        email = emails[0]["value"] if emails else "Sin email"
        org = p.get("org_name", "Sin organizacion")
        persons.append("- " + nombre + " | Tel: " + phone + " | Email: " + email + " | Org: " + org)
    return "\n".join(persons)

def get_pipedrive_organizations():
    url = "https://api.pipedrive.com/v1/organizations?api_token=" + PIPEDRIVE_API_KEY + "&limit=50"
    r = requests.get(url)
    data = r.json()
    if not data.get("data"):
        return "No se encontraron organizaciones."
    orgs = []
    for o in data["data"]:
        nombre = o.get("name", "Sin nombre")
        deals = str(o.get("open_deals_count", 0))
        orgs.append("- " + nombre + " | Deals abiertos: " + deals)
    return "\n".join(orgs)

def search_pipedrive(query):
    url = "https://api.pipedrive.com/v1/itemSearch?term=" + query + "&api_token=" + PIPEDRIVE_API_KEY + "&limit=10"
    r = requests.get(url)
    data = r.json()
    if not data.get("data") or not data["data"].get("items"):
        return "No encontre resultados para: " + query
    results = []
    for item in data["data"]["items"]:
        i = item["item"]
        tipo = i.get("type", "?")
        nombre = i.get("title", i.get("name", "Sin nombre"))
        results.append("- [" + tipo + "] " + nombre)
    return "\n".join(results)

def build_context(user_message):
    context_parts = []
    msg_lower = user_message.lower()

    if any(w in msg_lower for w in ["trato", "deal", "pipeline", "etapa", "negociaci", "cotizaci", "contrato", "llamada"]):
        context_parts.append("=== TRATOS EN PIPEDRIVE ===\n" + get_pipedrive_deals())

    if any(w in msg_lower for w in ["contacto", "persona", "tel", "numero", "email", "whatsapp"]):
        context_parts.append("=== CONTACTOS EN PIPEDRIVE ===\n" + get_pipedrive_persons())

    if any(w in msg_lower for w in ["organizacion", "empresa", "marca", "cliente"]):
        context_parts.append("=== ORGANIZACIONES EN PIPEDRIVE ===\n" + get_pipedrive_organizations())

    if any(w in msg_lower for w in ["busca", "buscar", "encuentra", "busco"]):
        words = user_message.split()
        if len(words) > 1:
            term = words[-1]
            context_parts.append("=== BUSQUEDA ===\n" + search_pipedrive(term))

    if not context_parts:
        context_parts.append("=== TRATOS RECIENTES ===\n" + get_pipedrive_deals())

    return "\n\n".join(context_parts)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id != ALLOWED_CHAT_ID:
        await update.message.reply_text("No tienes acceso a este bot.")
        return

    user_message = update.message.text
    await update.message.reply_text("Consultando tu informacion...")

    try:
        data_context = build_context(user_message)

        response = claude.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            system="Eres el asistente personal de Luis de la agencia TA. Tienes acceso a su Pipedrive y Trello. Etapas del pipeline: Llamada, Cotizacion, Negociacion, Contrato y factura. Responde siempre en español, claro y conciso. Usa emojis para facilitar la lectura en Telegram.",
            messages=[
                {
                    "role": "user",
                    "content": "Pregunta: " + user_message + "\n\nDatos:\n" + data_context
                }
            ]
        )

        answer = response.content[0].text
        await update.message.reply_text(answer)

    except Exception as e:
        await update.message.reply_text("Error: " + str(e))

def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN no encontrado")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot corriendo...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
