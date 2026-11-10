from datetime import datetime, timezone
from sqlalchemy import delete
from sqlalchemy.orm import Session
from app.db.models import User, Delivery
from app.i18n.messages import t

YES = {"так", "yes", "ja", "start"}
NO = {"ні", "no", "nein"}

def respond(db: Session, phone: str, message: str) -> str:
    value = message.strip()
    cmd = value.lower()
    user = db.query(User).filter_by(phone=phone).first()
    if user is None:
        user = User(phone=phone)
        db.add(user)
        db.commit()
        return t('en', 'welcome')
    lang = user.language
    if cmd in {'delete', 'видалити', 'löschen'}:
        db.execute(delete(Delivery).where(Delivery.user_id == user.id))
        db.delete(user)
        db.commit()
        return t(lang, 'deleted')
    if cmd in {'stop', 'стоп'}:
        user.notifications_enabled = False
        db.commit()
        return t(lang, 'stopped')
    if cmd in {'profile', 'профіль', 'profil'}:
        return t(lang, 'profile', city=user.city, query=user.query, level=user.german_level, employment=user.employment, enabled=user.notifications_enabled)
    if cmd == 'help':
        return t(lang, 'help')
    if cmd == 'start' and user.state == 'done':
        if user.consent_at is None:
            user.state = 'consent'
            db.commit()
            return t(lang, 'consent')
        user.notifications_enabled = True
        db.commit()
        return t(lang, 'started')
    if user.state == 'language':
        if cmd not in {'uk', 'de', 'en'}:
            return t('en', 'welcome')
        user.language, user.state = cmd, 'city'
        answer = t(cmd, 'city')
    elif user.state == 'city':
        user.city, user.state = value[:120], 'query'
        answer = t(lang, 'query')
    elif user.state == 'query':
        user.query, user.state = value[:240], 'level'
        answer = t(lang, 'level')
    elif user.state == 'level':
        if value.upper() not in {'A1','A2','B1','B2','C1','C2','-'}:
            return t(lang, 'invalid')
        user.german_level, user.state = value.upper(), 'employment'
        answer = t(lang, 'employment')
    elif user.state == 'employment':
        if cmd not in {'vollzeit', 'teilzeit', '-', 'any', 'beliebig', 'будь-який'}:
            return t(lang, 'invalid')
        user.employment, user.state = cmd, 'consent'
        answer = t(lang, 'consent')
    elif user.state == 'consent':
        if cmd not in YES | NO:
            return t(lang, 'invalid')
        user.notifications_enabled = cmd in YES
        user.consent_at = datetime.now(timezone.utc) if cmd in YES else None
        user.state = 'done'
        answer = t(lang, 'done')
    else:
        return t(lang, 'help')
    db.commit()
    return answer
