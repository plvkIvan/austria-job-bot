import httpx
from app.core.config import settings

async def send_text(phone: str, text: str) -> dict:
    if not settings.whatsapp_access_token or not settings.whatsapp_phone_number_id:
        raise RuntimeError("WhatsApp credentials are not configured")
    url = f"https://graph.facebook.com/v22.0/{settings.whatsapp_phone_number_id}/messages"
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(url, headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"}, json={"messaging_product": "whatsapp", "to": phone, "type": "text", "text": {"body": text}})
        response.raise_for_status()
        return response.json()
# NOTE: Free-form text is allowed only inside the applicable WhatsApp service window.
# Proactive job alerts require approved templates and opt-in; template sending is not implemented.
