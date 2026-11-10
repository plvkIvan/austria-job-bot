import hashlib
import hmac
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
from app.core.config import settings
from app.db.models import SessionLocal
from app.services.conversation import respond
from app.whatsapp.client import send_text

router = APIRouter()

class DemoMessage(BaseModel):
    phone: str
    text: str

@router.get('/health')
def health():
    return {'status': 'ok'}

@router.post('/demo/message')
def demo_message(data: DemoMessage):
    with SessionLocal() as db:
        return {'reply': respond(db, data.phone, data.text)}

@router.get('/webhook')
def verify_webhook(request: Request):
    q = request.query_params
    if q.get('hub.mode') == 'subscribe' and hmac.compare_digest(q.get('hub.verify_token', ''), settings.whatsapp_verify_token):
        return Response(content=q.get('hub.challenge', ''), media_type='text/plain')
    raise HTTPException(403, 'Invalid verify token')

@router.post('/webhook')
async def webhook(request: Request):
    if not settings.whatsapp_app_secret:
        raise HTTPException(503, 'Webhook disabled until WHATSAPP_APP_SECRET is configured')
    raw = await request.body()
    signature = request.headers.get('x-hub-signature-256', '')
    expected = 'sha256=' + hmac.new(settings.whatsapp_app_secret.encode(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(403, 'Invalid signature')
    payload = await request.json()
    for entry in payload.get('entry', []):
        for change in entry.get('changes', []):
            for msg in change.get('value', {}).get('messages', []):
                if msg.get('type') != 'text':
                    continue
                phone = msg.get('from')
                if not phone:
                    continue
                with SessionLocal() as db:
                    reply = respond(db, phone, msg.get('text', {}).get('body', ''))
                await send_text(phone, reply)
    return {'ok': True}
