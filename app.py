"""

Main Flask Application

WhatsApp Cloud API Webhook Handler



Production-ready with:

- Proper error handling

- Request validation

- Logging

- Health checks

- WhatsApp Flows support

"""



import os

import json

import logging

import time

import hmac

import hashlib

import requests

from flask import Flask, request, jsonify

from flask_cors import CORS

from dotenv import load_dotenv



# Load environment variables FIRST (before other imports that use env vars)

load_dotenv()



# =============================================================================

# IMPORTS - Using new state machine based router

# =============================================================================

# The old intent_router had a critical bug where numbers were interpreted

# globally instead of based on current state. The new message_router fixes this

# by ALWAYS routing based on (current_state + message).

# =============================================================================

from message_router import route_message

from whatsapp_client import send_text_message, mark_as_read, send_interactive_buttons

from dashboard_api import dashboard_bp

from auth_api import auth_bp

from database import init_database, create_crm_user, is_patient_automation_paused



# Configure logging

logging.basicConfig(

    level=logging.INFO,

    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',

    handlers=[

        logging.StreamHandler(),

        logging.FileHandler('app.log', encoding='utf-8')

    ]

)

logger = logging.getLogger(__name__)



# Log Flow PEM status at startup (so production logs show if private key is missing)

def _log_flow_pem_status():

    try:

        from flow_handler import load_private_key

        if load_private_key():

            logger.info("Flow: private key loaded (PRIVATE_KEY_PATH) - Flow decryption OK")

        else:

            logger.warning("Flow: private key NOT loaded - deploy private_key.pem and set PRIVATE_KEY_PATH")

    except Exception as e:

        logger.warning("Flow: private key check failed: %s", e)

_log_flow_pem_status()



# Dedupe: skip same message id (mid) processed recently to avoid echo/retry loops (Instagram/Page)

_MAX_RECENT_MIDS = 500

_recent_mids_instagram = set()

_recent_mids_page = set()



def _dedupe_mid(platform: str, mid: str) -> bool:

    """Return True if already seen (skip). Else add and return False (process)."""

    if not mid:

        return False

    s = _recent_mids_page if platform == 'page' else _recent_mids_instagram

    if mid in s:

        return True

    s.add(mid)

    if len(s) > _MAX_RECENT_MIDS:

        # Drop oldest half (set has no order; we just shrink)

        for _ in range(_MAX_RECENT_MIDS // 2):

            s.pop()

    return False



# Initialize Flask app

def _is_automation_paused_for_sender(external_id: str, platform: str) -> bool:

    """Return True if automation is paused for this sender on given platform."""

    try:

        return bool(is_patient_automation_paused(external_id, platform))

    except Exception as e:

        logger.error("Automation pause check failed for %s (%s): %s", external_id, platform, e)

        return False


app = Flask(__name__)

CORS(app, resources={r"/api/*": {"origins": ["https://crm.sudhahospital.com", "http://localhost:5173"]}}, supports_credentials=True)



# Initialize database

init_database()

# Create default admin user if it doesn't exist

create_crm_user('admin', 'sudha123', 'Administrator', 'admin')



# Register Dashboard & Auth APIs

app.register_blueprint(dashboard_bp)

app.register_blueprint(auth_bp)





@app.route('/health', methods=['GET'])

def health_check():

    """Health check endpoint for monitoring."""

    return jsonify({

        'status': 'healthy',

        'service': 'whatsapp-clinic-bot'

    }), 200


# Serve built CRM dashboard (dashboard/dist) at /crm
_DASHBOARD_DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dashboard', 'dist')


@app.route('/crm', defaults={'path': ''})
@app.route('/crm/<path:path>')
def serve_crm_dashboard(path: str):
    from flask import send_from_directory

    if not os.path.isdir(_DASHBOARD_DIST):
        return jsonify({
            'error': 'Dashboard not built',
            'hint': 'cd dashboard && npm install && npm run build'
        }), 404

    target = path or 'index.html'
    full = os.path.join(_DASHBOARD_DIST, target)
    if path and os.path.isfile(full):
        return send_from_directory(_DASHBOARD_DIST, path)
    return send_from_directory(_DASHBOARD_DIST, 'index.html')





@app.route('/webhook', methods=['GET', 'POST'])

def webhook():

    """

    Single webhook endpoint for Meta (WhatsApp + Instagram).

    GET = verification; POST = events. Full debug logging, never crashes, always returns 200 on POST.

    """

    ts = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

    logger.info("\n==============================")

    logger.info("WEBHOOK HIT")

    logger.info("TIMESTAMP: %s", ts)

    logger.info("METHOD: %s", request.method)

    logger.info("HEADERS: %s", dict(request.headers))

    logger.info("==============================\n")



    # ---------- GET: Verification ----------

    if request.method == 'GET':

        mode = request.args.get('hub.mode')

        token = request.args.get('hub.verify_token')

        challenge = request.args.get('hub.challenge')

        verify_token = os.getenv('WEBHOOK_VERIFY_TOKEN')



        logger.info("[WEBHOOK] Verification Request - Mode: %s, Token: %s", mode, token)



        if not verify_token:

            logger.error("[WEBHOOK] WEBHOOK_VERIFY_TOKEN not configured")

            return 'Server configuration error', 500



        if mode == 'subscribe' and token == verify_token:

            logger.info("[WEBHOOK] WEBHOOK VERIFIED")

            return challenge, 200

        else:

            logger.warning("[WEBHOOK] VERIFICATION FAILED")

            return 'Forbidden', 403



    # ---------- POST: Events (same flow as WhatsApp: log raw JSON, branch by object, 200 OK) ----------

    if request.method != 'POST':

        return jsonify({'status': 'ok'}), 200



    logger.info("=== WEBHOOK POST received (Instagram/WhatsApp/FB) ===")

    raw_body = request.get_data()

    raw_str = raw_body.decode('utf-8', errors='replace') if raw_body else ''

    logger.info("RAW BODY (len=%s): %s", len(raw_str), raw_str[:2000] + ('...' if len(raw_str) > 2000 else ''))



    data = None

    try:

        data = json.loads(raw_str) if raw_str.strip() else None

    except Exception as parse_err:

        logger.warning("JSON PARSE FAILED: %s - returning 200 anyway", str(parse_err))



    if data is not None:

        try:

            json_preview = json.dumps(data, indent=2)

            logger.info("PARSED JSON: %s", json_preview[:3000] + ('...' if len(json_preview) > 3000 else ''))

        except Exception:

            pass



    obj = (data.get('object', '') if isinstance(data, dict) else '') or ''

    obj_lower = str(obj).strip().lower()

    logger.info("OBJECT: %s (keys: %s)", obj, list(data.keys())[:20] if isinstance(data, dict) else [])



    # Log first event type so we can see why "messages" test may not log (affiliation test does)

    if data and isinstance(data, dict):

        entries = data.get('entry', [])

        if entries:

            first_messaging = entries[0].get('messaging', [])

            if first_messaging:

                ev_keys = list(first_messaging[0].keys())

                event_kind = 'message' if 'message' in first_messaging[0] else ('affiliation' if 'affiliation' in first_messaging[0] else ('optin' if 'optin' in first_messaging[0] else 'other'))

                logger.info("WEBHOOK first event type: %s (ev keys: %s)", event_kind, ev_keys)

            else:

                logger.info("WEBHOOK first entry has no messaging[] (entry keys: %s)", list(entries[0].keys())[:15])



    if data and isinstance(data, dict):

        try:

            if obj_lower == 'whatsapp_business_account':

                logger.info("WEBHOOK -> _handle_whatsapp")

                _handle_whatsapp(data)

            elif obj_lower == 'instagram':

                logger.info("WEBHOOK -> handle_instagram_login (Instagram Login API)")

                handle_instagram_login(data)

            elif obj_lower == 'page':

                logger.info("WEBHOOK -> handle_facebook (MESSENGER/Page). If Messenger never works: Messenger > Webhooks = same URL as Instagram, Page subscribed to 'messages', FACEBOOK_PAGE_ACCESS_TOKEN in .env")

                handle_facebook(data)

            else:

                logger.info("Unknown object '%s' - no handler. Add URL in Meta Dashboard for this product?", obj)

        except Exception as e:

            logger.error("Webhook processing error: %s", str(e), exc_info=True)



    return jsonify({'status': 'ok'}), 200





# Guard against duplicate webhook deliveries (Meta retries / double Flask workers)
_PROCESSED_MESSAGE_IDS = {}
_PROCESSED_TTL_SECONDS = 600


def _is_duplicate_webhook_message(message_id: str) -> bool:
    """True if this WhatsApp wamid was already handled."""
    if not message_id:
        return False
    now = time.time()
    expired = [mid for mid, ts in _PROCESSED_MESSAGE_IDS.items() if now - ts > _PROCESSED_TTL_SECONDS]
    for mid in expired:
        _PROCESSED_MESSAGE_IDS.pop(mid, None)
    if message_id in _PROCESSED_MESSAGE_IDS:
        return True
    try:
        from database import was_webhook_message_processed
        if was_webhook_message_processed(message_id):
            _PROCESSED_MESSAGE_IDS[message_id] = now
            return True
    except Exception as e:
        logger.debug("DB message dedupe check failed: %s", e)
    return False


def _mark_webhook_message_done(message_id: str):
    if not message_id:
        return
    _PROCESSED_MESSAGE_IDS[message_id] = time.time()
    try:
        from database import mark_webhook_message_processed
        mark_webhook_message_processed(message_id)
    except Exception as e:
        logger.debug("DB message dedupe mark failed: %s", e)


def _handle_whatsapp(data: dict):

    """WhatsApp: entry[].changes[].value.messages[] - existing flow."""

    for entry in data.get('entry', []):

        for change in entry.get('changes', []):

            value = change.get('value', {}) or {}

            if 'statuses' in value:

                continue

            messages = value.get('messages', [])

            metadata = value.get('metadata', {})

            for message in messages:

                try:
                    mid = message.get('id')
                    if _is_duplicate_webhook_message(mid):
                        logger.info("Skipping duplicate WhatsApp message id=%s", (mid or '')[:40])
                        continue

                    _process_message(message, metadata)
                    _mark_webhook_message_done(mid)

                except Exception as e:

                    logger.error("Error processing WhatsApp message: %s", str(e), exc_info=True)





def handle_instagram_login(data: dict):

    """Instagram Login API: object=instagram, entry[].messaging[], sender.id = IG Scoped ID, message.text. Same flow as WhatsApp."""

    entries = data.get('entry', [])

    logger.info("INSTAGRAM HANDLER: entry_count=%s", len(entries))

    for i, entry in enumerate(entries):

        messaging = entry.get('messaging', [])

        logger.info("  entry[%s] id=%s messaging_count=%s", i, entry.get('id', '?'), len(messaging))

        if not messaging:

            logger.warning("  INSTAGRAM: no messaging events in this entry. In Meta Dashboard: App > Instagram > Webhook > Subscribe to 'messages'?")

        entry_id = str(entry.get('id', '') or '')

        for ev in messaging:

            try:

                # Only process message events; skip read receipts, delivery, reaction, etc.

                if 'message' not in ev:

                    logger.info("INSTAGRAM: skipping non-message event (read/delivery/reaction)")

                    continue

                message = ev.get('message', {}) or {}

                sender = ev.get('sender', {}) or {}

                sender_id = str(sender.get('id', ''))

                # Skip echo: our own sent message (is_echo true, or sender = our account = entry id)

                is_echo = message.get('is_echo')

                if is_echo in (True, 'true', '1') or (isinstance(is_echo, str) and is_echo.lower() == 'true'):

                    logger.info("INSTAGRAM: skipping echo (is_echo=true)")

                    continue

                if entry_id and sender_id == entry_id:

                    logger.info("INSTAGRAM: skipping echo (sender is us, entry id=%s)", entry_id[:8] + '****' if len(entry_id) > 8 else entry_id)

                    continue

                text = message.get('text', '')

                if isinstance(text, dict):

                    text = text.get('text', '') or ''

                text = (text or '').strip()

                quick_reply = message.get('quick_reply') or {}

                payload = quick_reply.get('payload') if isinstance(quick_reply, dict) else None

                is_button_click = bool(payload)

                if is_button_click:

                    message_for_route = str(payload).strip()

                else:

                    message_for_route = text

                if not sender_id:

                    continue

                mid = message.get('mid') or ''

                if _dedupe_mid('instagram', mid):

                    logger.info("INSTAGRAM: skipping duplicate mid=%s", (str(mid)[:20] + '..') if len(str(mid)) > 20 else mid)

                    continue

                masked = sender_id[:8] + '****' if len(sender_id) > 8 else '****'

                logger.info("Message from %s: %s", masked, (message_for_route[:100] + '...') if len(message_for_route) > 100 else message_for_route or '(no text)')

                from crm_handler import process_crm_message

                process_crm_message(sender_id, 'instagram', message_for_route or '[non-text]', direction='inbound')

                if _is_automation_paused_for_sender(sender_id, 'instagram'):

                    logger.info("INSTAGRAM: automation paused for sender %s****, skipping bot reply", sender_id[:8])

                    continue

                session_user_id = f"instagram_{sender_id}"

                response = route_message(user_id=session_user_id, message=message_for_route, clinic_id=None, platform='instagram', is_button_click=is_button_click)

                if response:

                    success = _send_instagram_response(sender_id, response)

                    if success:

                        from crm_handler import log_interaction, get_patient

                        patient = get_patient(sender_id, 'instagram')

                        if patient:

                            log_interaction(patient['id'], 'outbound', 'instagram', _format_message_for_crm(response), user_id=sender_id)

            except Exception as e:

                logger.error("Instagram message error: %s", str(e), exc_info=True)





def handle_facebook(data: dict):

    """Facebook Messenger (object=page): entry[].messaging[], sender.id, message.text. Same flow and logs as Instagram."""

    entries = data.get('entry', [])

    page_token_ok = bool(os.getenv('FACEBOOK_PAGE_ACCESS_TOKEN', '').strip())

    logger.info("MESSENGER HANDLER: object=page, entry_count=%s, FACEBOOK_PAGE_ACCESS_TOKEN=%s", len(entries), "set" if page_token_ok else "MISSING")

    for i, entry in enumerate(entries):

        messaging = entry.get('messaging', [])

        entry_id = str(entry.get('id', '') or '')

        logger.info("  entry[%s] id=%s messaging_count=%s", i, entry_id or '?', len(messaging))

        if not messaging:

            logger.warning("  MESSENGER: no messaging events in this entry. In Meta Dashboard: Messenger > Webhooks > Subscribe Page to 'messages'?")

        for ev in messaging:

            try:

                if 'message' not in ev:

                    ev_keys = list(ev.keys())

                    logger.info(

                        "MESSENGER: non-message event (affiliation/optin/read/delivery). ev keys=%s. "

                        "Messages test in Meta often does NOT send a webhook POST; send a real user message to your Page to see message logs.",

                        ev_keys

                    )

                    continue

                message = ev.get('message', {}) or {}

                sender = ev.get('sender', {}) or {}

                sender_id = str(sender.get('id', ''))

                is_echo = message.get('is_echo')

                if is_echo in (True, 'true', '1') or (isinstance(is_echo, str) and is_echo.lower() == 'true'):

                    logger.info("MESSENGER: skipping echo (is_echo=true)")

                    continue

                if entry_id and sender_id == entry_id:

                    logger.info("MESSENGER: skipping echo (sender is us, entry id=%s)", entry_id[:8] + '****' if len(entry_id) > 8 else entry_id)

                    continue

                is_instagram = (ev.get('messaging_product') or '').lower() == 'instagram'

                text = message.get('text', '')

                if isinstance(text, dict):

                    text = text.get('text', '') or ''

                text = (text or '').strip()

                quick_reply = message.get('quick_reply') or {}

                payload = quick_reply.get('payload') if isinstance(quick_reply, dict) else None

                is_button_click = bool(payload)

                message_for_route = str(payload).strip() if is_button_click else text



                if not sender_id:

                    logger.warning("MESSENGER: message missing sender.id")

                    continue

                mid = message.get('mid') or ''

                if _dedupe_mid('page', mid):

                    logger.info("MESSENGER: skipping duplicate mid=%s", (str(mid)[:20] + '..') if len(str(mid)) > 20 else mid)

                    continue

                masked = sender_id[:8] + '****' if len(sender_id) > 8 else '****'

                platform = 'instagram' if is_instagram else 'facebook'

                logger.info("Message from %s (%s): %s", masked, platform, (message_for_route[:100] + '...') if len(message_for_route) > 100 else message_for_route or '(no text)')



                from crm_handler import process_crm_message

                process_crm_message(sender_id, platform, message_for_route or '[non-text]', direction='inbound')

                if _is_automation_paused_for_sender(sender_id, platform):

                    logger.info("MESSENGER: automation paused for sender %s**** (%s), skipping bot reply", sender_id[:8], platform)

                    continue



                session_user_id = "%s_%s" % (platform, sender_id)

                response = route_message(user_id=session_user_id, message=message_for_route, clinic_id=None, platform=platform, is_button_click=is_button_click)

                success = False

                if response:

                    success = _send_platform_response(platform, sender_id, response)

                if success:

                    from crm_handler import log_interaction, get_patient

                    patient = get_patient(sender_id, platform)

                    if patient:

                        log_interaction(patient['id'], 'outbound', platform, _format_message_for_crm(response), user_id=sender_id)

            except Exception as e:

                logger.error("MESSENGER message error: %s", str(e), exc_info=True)





def _format_message_for_crm(response) -> str:

    """Format bot response for CRM display: readable text + option labels (no raw JSON). Newlines rendered properly."""

    if response is None:

        return ""

    if isinstance(response, str):

        raw = response[:1000]

        # If stored string looks like a dict, extract text only (legacy)

        if raw.strip().startswith('{') and "'text'" in raw:

            try:

                import ast

                d = ast.literal_eval(raw[:2000])

                if isinstance(d, dict) and d.get('text'):

                    raw = d.get('text', '')

            except Exception:

                pass

        return _normalize_newlines(raw)

    text = (response.get('text') or '').strip()

    text = _normalize_newlines(text)  # literal \n -> real newline

    parts = [text] if text else []

    buttons = response.get('buttons', [])

    list_data = response.get('list', {})

    if buttons:

        labels = [b.get('title') or b.get('id') or '' for b in buttons[:10] if b.get('title') or b.get('id')]

        if labels:

            parts.append("Options: " + ", ".join(labels))

    elif list_data:

        for sec in (list_data.get('sections') or [])[:2]:

            for row in (sec.get('rows') or [])[:8]:

                parts.append("ΓÇó " + (row.get('title') or row.get('id') or ''))

    return "\n".join(parts).strip() or "Message sent"[:1000]





def _normalize_newlines(s: str) -> str:

    """Replace literal backslash-n with real newlines for CRM display."""

    if not s or not isinstance(s, str):

        return s or ""

    return s.replace("\\n", "\n")





def _flatten_response(response) -> str:

    """Turn router response (str or dict with text/buttons/list) into plain text. Same as WhatsApp helper."""

    if response is None:

        return ""

    if isinstance(response, str):

        return response

    msg_text = response.get('text', '')

    buttons = response.get('buttons', [])

    list_data = response.get('list')

    if list_data:

        for sec in (list_data.get('sections') or []):

            for row in (sec.get('rows') or [])[:10]:

                msg_text += "\nΓÇó " + (row.get('title') or row.get('id', ''))

    elif buttons:

        for i, btn in enumerate(buttons[:10], 1):

            msg_text += "\n%s. %s" % (i, btn.get('title') or btn.get('id', ''))

    return msg_text or "Please choose an option from the menu."





def _response_to_quick_replies(response) -> list:

    """Build Instagram/Facebook quick_replies from response 'buttons' or 'list' (sections/rows). Max 13, title 20 chars."""

    if not isinstance(response, dict):

        return []

    qr_list = []

    buttons = response.get('buttons', [])

    list_data = response.get('list', {})

    if buttons:

        for btn in buttons[:13]:

            title = (btn.get('title') or btn.get('id') or '')[:20]

            payload = str(btn.get('id') or title)

            if title and payload:

                qr_list.append({'content_type': 'text', 'title': title, 'payload': payload})

    elif list_data:

        for sec in (list_data.get('sections') or [])[:3]:

            for row in (sec.get('rows') or [])[:13]:

                if len(qr_list) >= 13:

                    break

                title = (row.get('title') or row.get('id') or '')[:20]

                payload = str(row.get('id') or title)

                if title and payload:

                    qr_list.append({'content_type': 'text', 'title': title, 'payload': payload})

            if len(qr_list) >= 13:

                break

    return qr_list[:13]





def _send_instagram_response(recipient_id: str, response) -> bool:

    """Send router response to Instagram: text + quick_replies from buttons OR list (dates, times, etc.)."""

    if response is None:

        return False

    text = response.get('text', '') if isinstance(response, dict) else str(response)

    qr_list = _response_to_quick_replies(response)

    if qr_list:

        return send_message_instagram_quick_replies(recipient_id, text or "Choose an option:", qr_list)

    return send_message_instagram(recipient_id, _flatten_response(response))





def _send_platform_response(platform: str, recipient_id: str, response) -> bool:

    """Send router response to Facebook or Instagram (Page): text + quick_replies from buttons OR list."""

    if response is None:

        return False

    text = response.get('text', '') if isinstance(response, dict) else str(response)

    qr_list = _response_to_quick_replies(response)

    if qr_list:

        if platform == 'instagram':

            return send_message_instagram_quick_replies(recipient_id, text or "Choose an option:", qr_list)

        return send_message_facebook_quick_replies(recipient_id, text or "Choose an option:", qr_list)

    return send_message(platform, recipient_id, _flatten_response(response))





def send_message(platform: str, recipient_id: str, text: str) -> bool:

    """Reusable send helper: routes to Instagram (graph.instagram.com, USER token) or Facebook (graph.facebook.com, PAGE token)."""

    if platform == 'instagram':

        return send_message_instagram(recipient_id, text)

    if platform == 'facebook':

        return send_message_facebook(recipient_id, text)

    logger.error("Unknown platform: %s", platform)

    return False





def send_message_instagram(recipient_id: str, text: str) -> bool:

    """POST graph.instagram.com/v24.0/me/messages, Bearer INSTAGRAM_USER_ACCESS_TOKEN (user token only, no Page token)."""

    token = os.getenv('INSTAGRAM_USER_ACCESS_TOKEN', '').strip()

    if not token:

        logger.error("Instagram credentials not configured (INSTAGRAM_USER_ACCESS_TOKEN)")

        return False

    url = "https://graph.instagram.com/v24.0/me/messages"

    headers = {"Authorization": "Bearer %s" % token, "Content-Type": "application/json"}

    payload = {"recipient": {"id": str(recipient_id)}, "message": {"text": text}}

    try:

        r = requests.post(url, headers=headers, json=payload, timeout=30)

        if r.status_code == 200:

            logger.info("Text message sent to %s***", str(recipient_id)[:8])

            return True

        logger.error("Instagram API error: %s - %s", r.status_code, r.text)

        return False

    except requests.RequestException as e:

        logger.error("Instagram request failed: %s", str(e))

        return False





def send_message_instagram_quick_replies(recipient_id: str, text: str, quick_replies: list) -> bool:

    """Send Instagram message with quick reply buttons (tap like WhatsApp)."""

    token = os.getenv('INSTAGRAM_USER_ACCESS_TOKEN', '').strip()

    if not token:

        logger.error("Instagram credentials not configured (INSTAGRAM_USER_ACCESS_TOKEN)")

        return False

    url = "https://graph.instagram.com/v24.0/me/messages"

    headers = {"Authorization": "Bearer %s" % token, "Content-Type": "application/json"}

    payload = {

        "recipient": {"id": str(recipient_id)},

        "message": {"text": text, "quick_replies": quick_replies}

    }

    try:

        r = requests.post(url, headers=headers, json=payload, timeout=30)

        if r.status_code == 200:

            logger.info("Quick reply buttons sent to %s***", str(recipient_id)[:8])

            return True

        logger.error("Instagram API error: %s - %s", r.status_code, r.text)

        return False

    except requests.RequestException as e:

        logger.error("Instagram request failed: %s", str(e))

        return False





def send_message_facebook(recipient_id: str, text: str) -> bool:

    """POST graph.facebook.com/v24.0/me/messages, Bearer FACEBOOK_PAGE_ACCESS_TOKEN. Per Meta: recipient.id, message.text, messaging_type=RESPONSE."""

    token = os.getenv('FACEBOOK_PAGE_ACCESS_TOKEN', '').strip()

    if not token:

        logger.error("MESSENGER: FACEBOOK_PAGE_ACCESS_TOKEN not set")

        return False

    url = "https://graph.facebook.com/v24.0/me/messages"

    headers = {"Authorization": "Bearer %s" % token, "Content-Type": "application/json"}

    payload = {

        "messaging_type": "RESPONSE",

        "recipient": {"id": str(recipient_id)},

        "message": {"text": text}

    }

    try:

        r = requests.post(url, headers=headers, json=payload, timeout=30)

        if r.status_code == 200:

            logger.info("MESSENGER: text message sent to %s***", str(recipient_id)[:8])

            return True

        logger.error("MESSENGER API error: %s - %s", r.status_code, r.text)

        return False

    except requests.RequestException as e:

        logger.error("MESSENGER request failed: %s", str(e))

        return False





def send_message_facebook_quick_replies(recipient_id: str, text: str, quick_replies: list) -> bool:

    """Send Messenger message with quick reply buttons (same API as text + quick_replies)."""

    token = os.getenv('FACEBOOK_PAGE_ACCESS_TOKEN', '').strip()

    if not token:

        logger.error("MESSENGER: FACEBOOK_PAGE_ACCESS_TOKEN not set")

        return False

    url = "https://graph.facebook.com/v24.0/me/messages"

    headers = {"Authorization": "Bearer %s" % token, "Content-Type": "application/json"}

    payload = {

        "messaging_type": "RESPONSE",

        "recipient": {"id": str(recipient_id)},

        "message": {"text": text, "quick_replies": quick_replies}

    }

    try:

        r = requests.post(url, headers=headers, json=payload, timeout=30)

        if r.status_code == 200:

            logger.info("MESSENGER: quick reply buttons sent to %s***", str(recipient_id)[:8])

            return True

        logger.error("MESSENGER API error: %s - %s", r.status_code, r.text)

        return False

    except requests.RequestException as e:

        logger.error("MESSENGER request failed: %s", str(e))

        return False





def _process_message(message: dict, metadata: dict):

    """

    Process a single incoming WhatsApp message.

    

    ==========================================================================

    ENTERPRISE-GRADE MESSAGE PROCESSING

    ==========================================================================

    

    This function:

    1. Extracts message content (text OR button payload)

    2. Handles WhatsApp Flow completions

    3. Routes based on payload_id for buttons, text for messages

    4. Sends response (buttons or text)

    

    CRITICAL: Button clicks are routed by payload_id, NOT display text.

    ==========================================================================

    """

    try:

        message_id = message.get('id')

        from_number = message.get('from')

        message_type = message.get('type')

        phone_number_id = metadata.get('phone_number_id')

        

        if not from_number:

            logger.warning("Message missing 'from' field")

            return

        

        # Extract message content including button payload IDs

        content = _extract_message_content(message, message_type)

        text = content['text']

        payload_id = content.get('payload_id')

        is_button = content.get('is_button', False)

        is_flow_response = content.get('is_flow_response', False)

        flow_token = content.get('flow_token')

        

        media = content.get('media')

        if not text and not media:

            logger.info(f"Unsupported or empty message type: {message_type}")

            return

        

        # Log received message (mask phone for privacy)

        masked_number = from_number[:4] + '****' + from_number[-2:] if len(from_number) > 6 else '****'

        

        if is_button:

            logger.info(f"Button click from {masked_number}: payload={payload_id}")

        else:

            logger.info(f"Message from {masked_number}: {text[:100]}...")

        if _is_automation_paused_for_sender(from_number, 'whatsapp'):

            from crm_handler import process_crm_message

            crm_text = f"[BUTTON: {payload_id}]" if is_button else text

            process_crm_message(from_number, 'whatsapp', crm_text)

            if message_id:

                mark_as_read(message_id, phone_number_id)

            logger.info("WHATSAPP: automation paused for %s, inbound logged and no bot reply sent", masked_number)

            return

        

        # CRITICAL: Handle Flow completion FIRST

        if is_flow_response or text == '__FLOW_COMPLETED__':

            _handle_flow_completion(from_number, phone_number_id, flow_token)

            

            # Log to CRM

            from crm_handler import process_crm_message

            process_crm_message(from_number, 'whatsapp', 'Flow completed - Appointment booked')

            

            # Mark as read

            if message_id:

                mark_as_read(message_id, phone_number_id)

            return

        

        # 1. CRM Interaction Logging

        from crm_handler import process_crm_message

        crm_text = f"[BUTTON: {payload_id}]" if is_button else text

        process_crm_message(from_number, 'whatsapp', crm_text)

        

        # 2. Mark message as read

        if message_id:

            mark_as_read(message_id, phone_number_id)

        

        # 3. Route message and get response

        # CRITICAL: Pass payload_id for buttons, text for regular messages

        response = route_message(

            user_id=from_number,

            message=payload_id if is_button else (text or '__MEDIA__'),

            clinic_id=phone_number_id,

            platform='whatsapp',

            is_button_click=is_button,

            media=media

        )

        

        # 4. Handle response and log outbound

        # Response can be:

        # - None: Flow active (ignore) or Flow was sent

        # - str: Text message

        # - dict with 'text' + 'buttons': Interactive button message

        # - dict with 'text' + 'list': Interactive list message

        if response:

            success = _send_response(from_number, response, phone_number_id)

                

            if success:

                # Log outbound interaction to CRM

                from crm_handler import log_interaction, get_patient

                patient = get_patient(from_number, 'whatsapp')

                if patient:

                    log_interaction(patient['id'], 'outbound', 'whatsapp', _format_message_for_crm(response), user_id=from_number)

            else:

                logger.error(f"Failed to send response to {masked_number}")

        else:

            # Response is None - either Flow active (ignored) or Flow was sent

            session = get_session(from_number)

            if session.current_state == 'APPOINTMENT_FLOW':

                logger.info(f"Message ignored - Flow active for {masked_number}")

                

    except Exception as e:

        logger.error(f"Error processing message: {str(e)}", exc_info=True)





def _send_response(to: str, response: any, phone_number_id: str) -> bool:

    """

    Send response based on its type.

    

    Handles:

    - str: Text message

    - dict with 'buttons': Interactive button message

    - dict with 'list': Interactive list message

    """

    from whatsapp_client import (

        send_text_message, send_interactive_buttons, send_interactive_list

    )

    

    if isinstance(response, dict):

        msg_text = response.get('text', '')

        buttons = response.get('buttons', [])

        list_data = response.get('list')

        header = response.get('header')

        footer = response.get('footer')

        

        if list_data:

            # Send interactive list (WhatsApp: max 10 rows per section)

            ok = send_interactive_list(

                to=to,

                body=msg_text,

                button_text=list_data.get('button_text', 'Select'),

                sections=list_data.get('sections', []),

                phone_number_id=phone_number_id,

                header=header,

                footer=footer

            )

            if not ok and msg_text:

                # Fallback: send as text so user gets a reply

                logger.warning("Interactive list send failed, sending as text fallback")

                return send_text_message(to, msg_text, phone_number_id)

            return ok

        elif buttons:

            # Send interactive buttons (WhatsApp: max 3 buttons)

            ok = send_interactive_buttons(

                to=to,

                body=msg_text,

                buttons=buttons,

                phone_number_id=phone_number_id,

                header=header,

                footer=footer

            )

            if not ok and msg_text:

                logger.warning("Interactive buttons send failed, sending as text fallback")

                return send_text_message(to, msg_text, phone_number_id)

            return ok

        else:

            # Just text

            return send_text_message(to, msg_text, phone_number_id)

    else:

        # Simple string response

        return send_text_message(to, str(response), phone_number_id)





def _extract_message_content(message: dict, message_type: str) -> dict:

    """

    Extract message content including button payload IDs.

    

    ==========================================================================

    CRITICAL: PAYLOAD-BASED ROUTING

    ==========================================================================

    

    For interactive messages (button clicks), we extract:

    - payload_id: The button's ID (e.g., MENU_APPOINTMENT, DIAG_ECG)

    - display_text: The button's display text (for logging)

    

    The payload_id is used for routing, NOT the display text.

    This ensures deterministic behavior regardless of button text changes.

    

    ==========================================================================

    

    Returns:

        dict with keys:

        - text: The message text (for text messages) or payload_id (for buttons)

        - payload_id: The button payload ID (None for text messages)

        - is_button: True if this is a button click

        - is_flow_response: True if this is a WhatsApp Flow completion

    """

    result = {

        'text': '',

        'payload_id': None,

        'is_button': False,

        'is_flow_response': False

    }

    

    if message_type == 'text':

        result['text'] = message.get('text', {}).get('body', '').strip()

        return result

    elif message_type == 'image':

        image = message.get('image', {}) or {}

        media_id = image.get('id', '')

        result['text'] = '__MEDIA__'

        result['media'] = {

            'type': 'image',

            'media_id': media_id,

            'mime_type': image.get('mime_type'),

            'caption': image.get('caption', ''),

        }

        logger.info(f"Image received: media_id={media_id}")

        return result

    elif message_type == 'document':

        document = message.get('document', {}) or {}

        media_id = document.get('id', '')

        result['text'] = '__MEDIA__'

        result['media'] = {

            'type': 'document',

            'media_id': media_id,

            'mime_type': document.get('mime_type'),

            'filename': document.get('filename', ''),

        }

        logger.info(f"Document received: media_id={media_id}")

        return result

    

    elif message_type == 'interactive':

        interactive = message.get('interactive', {})

        interactive_type = interactive.get('type')

        

        if interactive_type == 'button_reply':

            # CRITICAL: Extract the payload ID, not just the title

            button_reply = interactive.get('button_reply', {})

            payload_id = button_reply.get('id', '')  # This is the routing key

            display_text = button_reply.get('title', '')

            

            result['text'] = payload_id  # Use payload_id for routing

            result['payload_id'] = payload_id

            result['is_button'] = True

            

            logger.info(f"Button click: payload={payload_id}, display={display_text}")

            return result

        

        elif interactive_type == 'list_reply':

            # Same for list selections - extract the row ID

            list_reply = interactive.get('list_reply', {})

            payload_id = list_reply.get('id', '')

            display_text = list_reply.get('title', '')

            

            result['text'] = payload_id

            result['payload_id'] = payload_id

            result['is_button'] = True

            

            logger.info(f"List selection: payload={payload_id}, display={display_text}")

            return result

        

        elif interactive_type == 'nfm_reply':

            # WhatsApp Flow completion

            nfm_reply = interactive.get('nfm_reply', {})

            response_json_str = nfm_reply.get('response_json', '{}')

            

            try:

                response_json = json.loads(response_json_str)

                result['flow_token'] = response_json.get('flow_token')

            except Exception:

                result['flow_token'] = None

                

            result['text'] = '__FLOW_COMPLETED__'

            result['is_flow_response'] = True

            return result

    

    return result





def _extract_message_text(message: dict, message_type: str) -> str:

    """

    Legacy wrapper for backwards compatibility.

    

    DEPRECATED: Use _extract_message_content() for new code.

    """

    content = _extract_message_content(message, message_type)

    return content['text']





def _handle_flow_completion(from_number: str, phone_number_id: str, flow_token: str = None):
    """
    Handle Flow completion - Reverted to working version.
    """
    try:
        if flow_token:
            logger.info(f"Flow completion received with token: {flow_token}")
            from flow_handler import process_flow_booking
            success = process_flow_booking(flow_token, phone_number_id, from_number)
            
            if success:
                from state_machine import reset_to_main_menu
                reset_to_main_menu(from_number)
                logger.info(f"Flow booking processed and session reset for {from_number}")
        else:
            logger.warning(f"Flow completion received without token for {from_number}")
            from state_machine import reset_to_main_menu
            reset_to_main_menu(from_number)

    except Exception as e:
        logger.error(f"Error handling flow completion: {e}", exc_info=True)
        from state_machine import reset_to_main_menu
        reset_to_main_menu(from_number)


@app.route('/flow', methods=['GET', 'HEAD', 'POST'])
def handle_flow():
    """
    Handle WhatsApp Flow requests - Reverted to working version.
    """
    if request.method in ['GET', 'HEAD']:
        logger.info(f"Flow endpoint health check: {request.method}")
        return jsonify({"status": "ok"}), 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data"}), 400
        
        from flow_handler import handle_encrypted_flow_request, handle_flow_request
        
        if 'encrypted_flow_data' in data:
            encrypted_response = handle_encrypted_flow_request(data)
            if not encrypted_response:
                return "", 421
            return encrypted_response, 200, {'Content-Type': 'text/plain'}
        
        response = handle_flow_request(data)
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Flow handler error: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.errorhandler(404)

def not_found(e):

    return jsonify({'error': 'Not found'}), 404





@app.errorhandler(500)

def server_error(e):

    logger.error(f"Server error: {str(e)}")

    return jsonify({'error': 'Internal server error'}), 500





if __name__ == '__main__':

    port = int(os.getenv('PORT', 8000))

    debug = os.getenv('DEBUG', 'false').lower() == 'true'

    ig_token = os.getenv('INSTAGRAM_USER_ACCESS_TOKEN')

    fb_token = os.getenv('FACEBOOK_PAGE_ACCESS_TOKEN')



    logger.info(f"Starting WhatsApp Clinic Bot on port {port}")

    logger.info(f"Debug mode: {debug}")

    logger.info(f"Instagram Login API: {'configured' if ig_token else 'not configured (INSTAGRAM_USER_ACCESS_TOKEN)'}")

    logger.info(f"Facebook Messenger: {'configured' if fb_token else 'not configured (FACEBOOK_PAGE_ACCESS_TOKEN)'}")

    

    # use_reloader=False avoids double webhook handling (parent+child both process /webhook)
    app.run(

        host='0.0.0.0',

        port=port,

        debug=debug,

        use_reloader=False,

    )

