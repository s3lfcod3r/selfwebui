"""Fehler-Anzeige (nur lesen): meldet Chats, deren letzte Antwort mit einem Fehler endete.

Es wird nichts gesendet und nichts angestoßen. Die Arbeiter-Spalte zeigt diese Chats rot an; Sven schreibt dann
"weiter" in den Chat und Bonsai analysiert und macht weiter (Regel in direkt_agents.md).
"""
import json
import logging
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from cptr.routers.admin import require_admin

log = logging.getLogger('fehlerchats')
router = APIRouter(prefix='/api/selfwebui')

FENSTER_MS = 24 * 3600 * 1000      # Fehler der letzten 24 Stunden
CACHE_S = 4
IGNORIEREN = ('cancel', 'abort', 'stopp', 'user request')
LEERE_ANTWORT = 'Bonsai hat mitten in der Arbeit aufgehört, ohne Abschlussmeldung. Schreib "weiter".'
_cache = {'zeit': 0.0, 'daten': {}}
_aktiv_cache = {'zeit': 0.0, 'daten': []}


def fehler_text(meta):
    """Fehlertext aus den Metadaten einer Antwort, sonst leerer Text."""
    value = meta.get('error') if isinstance(meta, dict) else None
    return str(value).strip() if value else ''


def leere_antwort(content, output):
    """Antwort, die beim Denken endet (Bonsai hat sich festgedacht oder wurde mitten im Gedanken beendet).

    Auch mit Text davor: ein normaler Zug endet mit einer Nachricht, nicht mit einem Gedanken (Vorfall 04.10.2026: Chat
    erzählte seine Schritte, endete im Gedanken, kein Weiter-Knopf, weil schon Text da war).
    """
    try:
        items = json.loads(output) if isinstance(output, str) else output
    except ValueError:
        return False
    if not isinstance(items, list) or not items or not all(isinstance(i, dict) for i in items):
        return False
    letztes = items[-1]
    return letztes.get('type') == 'reasoning' and letztes.get('status') == 'completed'


ABSCHLUSS_MARKE = 'antworte mit der nummer'
ABSICHTLICH_OFFEN = ('bild_auftrag',)      # nach einem Bildauftrag endet der Zug absichtlich kurz


def ohne_abschluss(output):
    """True, wenn der Zug Werkzeuge benutzt hat, mit einer Nachricht endet, aber keine Empfehlung zum Anklicken enthält."""
    try:
        items = json.loads(output) if isinstance(output, str) else output
    except ValueError:
        return False
    if not isinstance(items, list) or not items or not all(isinstance(i, dict) for i in items):
        return False
    aufrufe = [i for i in items if i.get('type') == 'function_call']
    if not aufrufe or any(str(i.get('name') or '').endswith(ABSICHTLICH_OFFEN) for i in aufrufe):
        return False
    letztes = items[-1]
    if letztes.get('type') != 'message':
        return False
    text = ' '.join(str(t.get('text') or '') for t in (letztes.get('content') or []) if isinstance(t, dict))
    return bool(text.strip()) and ABSCHLUSS_MARKE not in text.lower()


def ignorierbar(text):
    """Vom Nutzer gewollte Abbrüche sind kein Fehler."""
    low = text.lower()
    return any(wort in low for wort in IGNORIEREN)


def ist_fehlerfall(msg_role, msg_done, msg_meta, msg_id, current_message_id):
    """Eine Antwort ist ein offener Fehler, wenn sie die aktuelle des Chats ist, fertig ist und einen Fehler trägt."""
    if msg_role != 'assistant' or not msg_done or current_message_id != msg_id:
        return ''
    text = fehler_text(msg_meta)
    return '' if not text or ignorierbar(text) else text


async def lese_fehler(jetzt_ms=None):
    from sqlalchemy import select
    from cptr.models.chats import Chat, ChatMessage, is_internal_chat
    from cptr.utils.db import get_db
    jetzt_ms = jetzt_ms or int(time.time() * 1000)
    async with await get_db() as db:
        rows = (await db.execute(select(ChatMessage).where(
            ChatMessage.role == 'assistant', ChatMessage.created_at > jetzt_ms - FENSTER_MS))).scalars().all()
    chats = {}
    for msg in rows:
        leer = msg.done and leere_antwort(msg.content, msg.output)
        if not fehler_text(msg.meta) and not leer:
            continue
        chat = await Chat.get_by_id(msg.chat_id)
        if not chat or is_internal_chat(chat.meta):
            continue
        text = ist_fehlerfall(msg.role, msg.done, msg.meta, msg.id, chat.current_message_id)
        if not text and leer and chat.current_message_id == msg.id:
            text = LEERE_ANTWORT
        if text:
            chats[chat.id] = {'fehler': text[:200], 'zeit': max(msg.created_at or 0, chat.updated_at or 0)}
    return chats


async def lese_ohne_abschluss():
    from sqlalchemy import select
    from cptr.models.chats import Chat, ChatMessage, is_internal_chat
    from cptr.utils.db import get_db
    jetzt_ms = int(time.time() * 1000)
    async with await get_db() as db:
        rows = (await db.execute(select(ChatMessage).where(
            ChatMessage.role == 'assistant', ChatMessage.done == True,  # noqa: E712
            ChatMessage.created_at > jetzt_ms - 6 * 3600 * 1000))).scalars().all()
    chats = {}
    for msg in rows:
        if not ohne_abschluss(msg.output):
            continue
        chat = await Chat.get_by_id(msg.chat_id)
        if chat and not is_internal_chat(chat.meta) and chat.current_message_id == msg.id:
            chats[chat.id] = {'zeit': msg.created_at or 0}
    return chats


def laufende_chats(zeilen):
    """[(chat_id, titel)] für Chats, deren letzte Antwort noch läuft (nicht fertig). Reine Funktion für den Test."""
    return [{'id': chat_id, 'titel': (titel or 'Chat')[:80]} for chat_id, titel in zeilen]


async def lese_laufende():
    from sqlalchemy import select
    from cptr.models.chats import Chat, ChatMessage, is_internal_chat
    from cptr.utils.db import get_db
    jetzt_ms = int(time.time() * 1000)
    async with await get_db() as db:
        rows = (await db.execute(select(ChatMessage).where(
            ChatMessage.role == 'assistant', ChatMessage.done == False,  # noqa: E712
            ChatMessage.created_at > jetzt_ms - 6 * 3600 * 1000))).scalars().all()
    zeilen, gesehen = [], set()
    for msg in rows:
        if msg.chat_id in gesehen:
            continue
        chat = await Chat.get_by_id(msg.chat_id)
        if not chat or is_internal_chat(chat.meta) or chat.current_message_id != msg.id:
            continue
        gesehen.add(msg.chat_id)
        zeilen.append((chat.id, chat.title))
    return laufende_chats(zeilen)


@router.get('/aktiv')
async def aktiv(request: Request):
    require_admin(request)
    jetzt = time.monotonic()
    if jetzt - _aktiv_cache['zeit'] > 2:
        try:
            _aktiv_cache.update(zeit=jetzt, daten=await lese_laufende())
        except Exception:
            log.exception('Laufende Chats nicht lesbar')
            _aktiv_cache.update(zeit=jetzt, daten=[])
    return JSONResponse({'laufend': _aktiv_cache['daten']}, headers={'Cache-Control': 'no-store'})


@router.get('/fehler/status')
async def status(request: Request):
    require_admin(request)
    jetzt = time.monotonic()
    if jetzt - _cache['zeit'] > CACHE_S:
        try:
            _cache.update(zeit=jetzt, daten=await lese_fehler())
        except Exception:
            log.exception('Fehlerchats nicht lesbar')
            _cache.update(zeit=jetzt, daten={})
        try:
            _cache['abschluss'] = await lese_ohne_abschluss()
        except Exception:
            log.exception('Chats ohne Abschluss nicht lesbar')
            _cache['abschluss'] = {}
    return JSONResponse({'chats': _cache['daten'], 'abschluss': _cache.get('abschluss', {})}, headers={'Cache-Control': 'no-store'})
