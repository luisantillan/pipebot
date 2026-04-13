import os
import requests
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import anthropic

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
        deal = f"- {d['title']} | Etapa: {d['stage_id']} | Valor: ${d.get('value', 0):,} | Contacto: {d.get('person_name', 'N/A')} | Org: {d.get('org_name', 'N/A')}"
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
        persons.append(f"- {p['name']} | Tel: {phone} | Email: {email} | Org: {org}")
    return "\n".join(persons)

def get_pipedrive_organizations():
    url = f"https://api.pipedrive.com/v1/organizations?api_token={PIPEDRIVE_API_KEY}&limit=50"
    r = requests.get(url)
    data = r.json()
    if not data.get("data"):
        return "No se encontraron organizaciones."
    orgs = []
    for o in data["data"]:
        phones = o.get("phone", [])
        phone = phones[0]["value"] if phones else "Sin teléfono"
        orgs.append(f"- {o['name']} | Tel: {phone} | Deals abiertos: {o.get('open_deals_count', 0)}")
    return "\n".join(orgs)

def search_pipedrive(query):
    url = f"https://api.pipedrive.com/v1/itemSearch?term={query}&api_token={PIPEDRIVE_API_KEY}&limit=10"
    r = requests.get(url)
    data = r.json()
    if not data.get("data") or not data["data"].get("items"):
        return f"No encontré resultados para '{query}' en Pipedrive."
    results = []
    for item in data["data"]["items"]:
        i = item["item"]
        results.append(f"- [{i['type']}] {i.get('title', i.get('name', 'Sin nombre'))}")
    return "\n".join(results)

def get_trello_boards():
    url = f"https://api.trello.com/1/members/me/boards?key={TRELLO_API_KEY}&token={TRELLO_TOKEN}"
    r = requests.get(url)
    boards = r.json()
    return [(b["id"], b["name"]) for b in boards]

def get_trello_cards(board_id):
    url = f"https://api.trello.com/1/boards/{board_id}/cards?key={TRELLO_API_KEY}&token={TRELLO_TOKEN}"
    r = requests.get(url)
    cards = r.json()
    if not cards:
        return "Sin tarjetas."
    result = []
    for c in cards[:30]:
        result.append(f"- {c['name']} | {c.get('url', '')}")
    return "\n".join(result)

def get_all_trello_info():
    boards = get_trello_boards()
    info = []
    for board_id, board_name in boards:
        info.append(f"\n📋 TABLERO: {board_name}")
        cards = get_trello_cards(board_id)
        info.append(cards)
    return "\n".join(info)

def build_context(user_message):
    context_parts = []
    msg_lower = user_message.lower()

    if any(w in msg_lower for w in ["trato", "deal", "campaña", "pipeline", "etapa", "negociación", "cotización", "contrato"]):
        context_parts.append("=== TRATOS EN PIPEDRIVE ===\n" + get_pipedrive_deals())

    if any(w in msg_lower for w in ["contacto", "persona", "teléfono", "tel", "número", "email"]):
        context_parts.append("=== CONTACTOS EN PIPEDRIVE ===\n" + get_pipedrive_persons())

    if any(w in msg_lower for w in ["organización", "empresa", "marca", "cliente"]):
        context_parts.append("=== ORGANIZACIONES EN PIPEDRIVE ===\n" + get_pipedrive_organizations())

    if any(w in msg_lower for w in ["trello", "tablero", "tarjeta", "tarea"]):
        context_parts.append("=== TABLEROS TRELLO ===\n" + get_all_trello_info())

    if any(w in msg_lower for w in ["busca", "buscar", "encuentra", "busco"]):
        words = user_message.split()
        if len(words) > 1:
            term = words[-1]
            context_parts.append("=== BÚSQUEDA EN PIPEDRIVE ===\n" + search_pipedrive(term))

    if not context_parts:
        context_parts.append("=== TRATOS RECIENTES ===\n" + get_pipedrive_deals())

    return "\n\n".join(context_parts)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id != ALLOWED_CHAT_ID:
        await update.message.reply_text("No tienes acceso a este bot.")
        return

    user_message = update.message.text
    await update.message.reply_text("🔍 Consultando tu información...")

    try:
        data_context = build_context(user_message)

        response = claude.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            system="""Eres el asistente personal de Luis, especializado en su agencia TA.
Tienes acceso a su Pipedrive y Trello.
Sus etapas de pipeline son: Llamada, Cotización, Negociación, Contrato y factura.
Sus tableros de Trello incluyen: Admin TA, Campañas Ds y Dw, y tableros por talento.
Responde siempre en español, de forma clara, concisa y útil.
Usa emojis para que sea fácil de leer en Telegram.""",
            messages=[
                {
                    "role": "user",
                    "content": f"Pregunta de Luis: {user_message}\n\nDatos actuales:\n{data_context}"
                }
            ]
        )

        answer = response.content[0].text
        await update.message.reply_text(answer)

    except Exception as e:
        await update.message.reply_text(f"Hubo un error: {str(e)}")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot corriendo...")
    app.run_polling()

if __name__ == "__main__":
    main()
