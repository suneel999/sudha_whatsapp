# Instagram webhook – no response / no logs

If you message from your **real Instagram account** and see **no logs** and **no response**, Meta is not reaching your server.

**Most common causes:** (1) Webhook URL verified but **not subscribed to "messages"**, (2) Sender account is **not an Instagram Tester** for the app, (3) ngrok or app not running.

**Continuous welcome loop:** If the bot keeps sending the same welcome message over and over, Meta is sending your own messages back (echoes). The app now skips echoes. You can also **unsubscribe from "message_echoes"** in Meta (Instagram and/or Page webhooks) so Meta stops sending echoes; keep **messages** subscribed.

---

## Instagram works, Messenger doesn’t — “object is page”

Messenger (Facebook Page messages) uses **object=page** in the webhook. The app **does** handle it in `handle_facebook`. If Messenger still doesn’t work:

1. **No logs when you message the Page** → Meta is not sending events to your server. In **Messenger** (not Instagram) → **Webhooks**: set the **same** Callback URL as Instagram, verify, then **subscribe your Page** to **messages**.
2. **Logs show “Message from … (facebook)” but no reply** → Check `.env`: **FACEBOOK_PAGE_ACCESS_TOKEN** must be set to the **Page** access token (with `pages_messaging`) for the same Page. App startup logs show “Facebook Messenger: configured” or “not configured”.

---

## Facebook Messenger not working (same webhook URL as Instagram)

Instagram and Facebook use **different products** in Meta. The **same** callback URL is correct, but you must **configure it in both places**:

1. **Instagram** (product) → Webhooks → your URL → messages subscribed → **Instagram DMs work**.
2. **Messenger / Facebook** (product) → Webhooks → **subscribe your Page** with the **same** URL → **Page DMs work**.

If you only configured the webhook under **Instagram**, Meta will **not** send Facebook Page messages to your server (no POST when someone messages your Page). The Page token in `.env` is only for **sending** replies; it does not make Meta **send** events to you.

---

### Messenger: "Same webhook, token correct, but no logs and no reply"

**Symptom:** Instagram works; you pasted `FACEBOOK_PAGE_ACCESS_TOKEN` correctly; when someone messages your **Facebook Page** you get no logs and no reply.

**Cause:** The **Page** is not subscribed to your webhook. Meta only sends Messenger events to your URL if the **Messenger** (or Facebook) product has the webhook set **and** your **Page** is subscribed to it.

**Checklist – do every step:**

1. **Open the Messenger product**  
   Meta for Developers → your app → left sidebar → **Messenger** (or **Facebook**). Not Instagram.

2. **Open Webhooks**  
   Under Messenger, click **Webhooks** (or **Settings** → Webhooks).

3. **Set callback URL**  
   In "Callback URL" (or "Edit" / "Configure"), set the **exact same** URL as Instagram, e.g.  
   `https://your-ngrok-url.ngrok-free.app/webhook`  
   Set **Verify token** = value of `WEBHOOK_VERIFY_TOKEN` in `.env`.  
   Click **Verify and save**. (You should see a GET in your app logs when you verify.)

4. **Subscribe your Page**  
   This is the step that is often missed:
   - On the same Webhooks page, find **"Subscribe to this app"** or **"Webhook fields"** or a list of **Pages**.
   - You must **subscribe your Page** to the webhook. There may be a dropdown "Select a Page" or "Add subscription" → choose your Page.
   - For that Page, ensure **messages** (and optionally **messaging_postbacks**) is **Subscribed** (toggle on).
   - If you see "Webhook fields" with toggles (messages, messaging_postbacks, etc.), turn **messages** on and ensure the subscription is tied to **your Page**, not just the app.

5. **Confirm token is for this Page**  
   `FACEBOOK_PAGE_ACCESS_TOKEN` must be a **Page** access token for the **same** Page that receives the messages. In [Graph API Explorer](https://developers.facebook.com/tools/explorer/): select your app → select the Page in "User or Page" → get token with `pages_messaging` → paste in `.env`.

6. **Test**  
   Send a message to your **Facebook Page** from a user account (not from the Page). In the app logs you should see:  
   `METHOD: POST` → `OBJECT: page` → `PAGE HANDLER` → `Message from ... (facebook)`.

If you have a **Test** button next to "messages" on the Messenger webhook page, click it. If a POST appears in your logs, the URL is fine and the problem is that the **Page** is not subscribed. If no POST appears, the callback URL for **Messenger** is wrong or not verified.

---

### "Test message sent" but no logs in app

**Symptom:** You click **Test** next to "messages" in the Messenger webhook; Meta shows "Successfully tested" / "test message sent" – but your app shows **no** new log lines (no `WEBHOOK HIT`, no `METHOD: POST`).

**Cause:** Meta is sending the test POST to the **callback URL you configured for Messenger**. That URL is **not** the one where your app is running. So the request never hits your server (wrong host, old ngrok URL, or typo).

**Fix:**

1. **Copy the exact URL that works for Instagram**  
   Go to **Instagram** → **Webhooks** and copy the **Callback URL** (e.g. `https://xxxx.ngrok-free.app/webhook`). That URL is the one that reaches your app.

2. **Set the same URL for Messenger**  
   Go to **Messenger** → **Webhooks**. Edit the Callback URL and **paste that exact URL** (same as Instagram). No extra path, no different domain. Click **Verify and save**.

3. **Test again**  
   Click **Test** next to "messages" again. Within a few seconds you should see in your app logs:  
   `WEBHOOK HIT` → `METHOD: POST` → `OBJECT: page` (or similar) → `PAGE HANDLER`.

If you restarted ngrok, the URL will have changed – update **both** Instagram and Messenger callback URLs to the **new** ngrok URL.

---

### Why "messages" test shows no log but "affiliation" test does

**What you see:** Clicking **Test** next to **messages** in Messenger Webhooks produces **no** new log lines. Clicking **Test** next to **messaging_affiliations** (or similar) **does** produce logs (`WEBHOOK POST received`, `OBJECT: page`, `MESSENGER: non-message event (affiliation/optin/...)`).

**Why:**

1. **Affiliation test sends a real POST**  
   Meta sends a webhook POST with an `affiliation` (or `optin`) event. Your app receives it and logs it, then skips it because it’s not a `message` event. So you see logs.

2. **Messages test often does not send a POST**  
   For the **messages** subscription, Meta’s "Send test message" / "Test" in the dashboard often **only verifies the subscription** and does **not** send a real message event to your callback. So no request hits your server and you see no log. That is expected in many setups.

3. **Subscription**  
   If the **Page** is not subscribed to **messages** (only to **messaging_affiliations** or similar), then real user messages also won’t be sent to your webhook. In **Messenger → Webhooks**, ensure **messages** (and optionally **messaging_postbacks**) is **checked** for your Page.

**What to do:** To verify message handling end‑to‑end, **send a real message** from a user (or test account) to your **Facebook Page**. You should then see `WEBHOOK POST received`, `OBJECT: page`, `WEBHOOK first event type: message`, and `Message from ... (facebook): ...` in your logs.

---

## 0. Two things that MUST be done (dashboard Section 2 & 3)

- **Section 2 – Generate access tokens:** Add your Instagram **business** account and generate a **User** token. Put it in `.env` as `INSTAGRAM_USER_ACCESS_TOKEN`.  
  **Critical:** The Instagram account that **sends** the DM to your business account must be added as an **Instagram Tester**:
  - In the app: **Roles** → **Roles** (or **App roles**) → find **Instagram Testers** → **Add people** and add the **Instagram account** (username) that will send test DMs.  
  - If the sender is not a Tester, Meta will **not** send their messages to your webhook (no logs).

- **Section 3 – Configure webhooks:** After **Verify and save**, you must **subscribe to webhook fields**:
  - In **Instagram** → **Webhooks** → under your callback URL there is a **Subscribe to this object** or **Webhook fields** section.
  - Ensure **messages** (and optionally **messaging_postbacks**) is **checked**. If nothing is subscribed, Meta will **not** POST message events (no logs).

---

## If you only see GET in logs (verification) but no POST when you send a message

**What you see:** `METHOD: GET` and `[WEBHOOK] WEBHOOK VERIFIED` when you click Verify in Meta, but when you send a real DM from the tester account you get **no new log lines** (no `METHOD: POST`).

**Cause:** Meta is **not** sending message events. That almost always means **"messages" is not subscribed** for the Instagram webhook. Verifying the URL only proves the endpoint exists; it does **not** subscribe to message events.

**Fix – subscribe to "messages":**

1. Go to **Meta for Developers** → your app → **Instagram** (left sidebar).
2. Open **Webhooks** (under Instagram).
3. You should see your **Callback URL** and **Verify token** (and a green check from verification).
4. On the same page, find the **"Subscribe to this object"** or **"Webhook fields"** area. It lists checkboxes for:
   - **messages** ← **check this**
   - **messaging_postbacks** (optional, for button clicks)
   - **message_echoes** (optional)
   - etc.
5. Check **messages**, then **Save** or **Submit**.
6. Send a DM again from the tester account to your Instagram business account. You should now see in the app terminal:
   - `METHOD: POST`
   - `=== WEBHOOK POST received (Instagram/WhatsApp/FB) ===`
   - `OBJECT: instagram`
   - `Message from ... : ...`

If you don’t see a **Subscribe to this object** / **Webhook fields** section, try: **Instagram** → **Webhooks** → **Edit** (or **Configure**) on the existing webhook and look for **Fields** or **Subscriptions** to enable **messages**.

---

## Subscribed to "messages" but still no logs / no response

If **messages** (and others) are already **Subscribed** and you still get no `METHOD: POST` when you send a DM, check the following.

### 1. Is this the **Instagram** product’s webhook?

Meta has **separate** webhook configs per product:

- **Facebook (Page)** → Webhooks → for Messenger (and sometimes Page-linked Instagram)
- **Instagram** → Webhooks → for Instagram API (object=instagram) DMs

The subscription list you see might be for the **Page** webhook. For DMs to your **Instagram business account** (Instagram Login API), the callback must be set under **Instagram**:

- Left sidebar: open **Instagram** (the product), then **Webhooks**.
- Confirm the **Callback URL** there is your ngrok URL (e.g. `https://xxxx.ngrok-free.app/webhook`).
- Confirm **messages** is subscribed **on this Instagram webhook** (not only on the Page webhook).

If the callback is only set under **Facebook** / **Page**, add (or edit) the webhook under **Instagram** with the **same** URL and subscribe to **messages** there.

### 2. Use the **Test** button next to "messages"

On the same page where you see the subscribed fields:

- Click **Test** next to **messages**.
- In the terminal where `app.py` runs you should see almost immediately:
  - `METHOD: POST`
  - `=== WEBHOOK POST received (Instagram/WhatsApp/FB) ===`
  - and a RAW BODY with a test payload.

- **If you see these logs:** Meta can reach your server. The problem is then with **real** DMs (e.g. which account is sending, or conversation not started correctly). Try sending a DM again from the **tester** account **to** the **Instagram business** account.
- **If you still see no new logs:** The callback URL Meta is using is wrong or unreachable. Check:
  - **Callback URL** on that same page: it must be exactly `https://YOUR-CURRENT-NGROK-URL/webhook`.
  - If you restarted ngrok, the URL changed; update the callback in Meta and click **Verify and save** again, then run **Test** again.

### 3. Callback URL = current ngrok URL

- In a browser, open your ngrok URL (e.g. `https://xxxx.ngrok-free.app`). The browser should show your app (or ngrok’s page).
- In Meta, **Instagram** → **Webhooks**, the **Callback URL** must match that base URL + `/webhook` (e.g. `https://xxxx.ngrok-free.app/webhook`).
- If you started a new ngrok session, copy the **new** HTTPS URL and update the callback in Meta, then verify again.

---

## Test button works but real tester DM doesn’t (no POST when you send a message)

If clicking **Test** next to "messages" shows logs (`METHOD: POST`, `WEBHOOK POST received`, etc.) but when a **real** tester sends a DM you get **no new logs**, Meta is not sending real message events to your server. Check the following.

### 1. Recipient = the Instagram account connected to the app

Only DMs **to** the Instagram **business/creator** account that you added in the app (in **Generate access tokens**) will trigger this webhook.

- In the app: **Instagram** → **Generate access tokens** (or similar). The account you added there is **Account B**.
- The tester must send the DM **to Account B** (open Account B’s profile → Message → send).
- If the tester is messaging a **different** Instagram account (e.g. another business or a personal account), Meta will **not** send events to this app. Confirm you’re messaging the **exact** account that’s connected to the app.

### 2. Sender = Instagram Tester (by Instagram account)

Only **Instagram Testers** get their messages delivered to the webhook in development.

- Go to **Roles** → **Instagram Testers** (not “Facebook Testers” or “Test users”).
- The **Instagram account** that sends the DM (by Instagram username) must be in **Instagram Testers**. Add it there if it isn’t.
- After adding, the tester may need to accept an invite (email/Instagram). Until they’re an active tester, their DMs may not be sent to the webhook.

### 3. Real DMs might be coming as Page webhook (object=page)

If your Instagram account is **linked to a Facebook Page**, Meta may send **real** DMs to the **Page** webhook (`object=page`) instead of the Instagram webhook.

- Add the **same** callback URL under **Facebook** (product) → **Webhooks**: select your **Page** → Callback URL = `https://YOUR-NGROK-URL/webhook` → Verify and save → subscribe to **messages**.
- Send a DM again from the tester **to** your Instagram business account. Watch the logs: you might see `METHOD: POST` and `OBJECT: page` (and `PAGE HANDLER`, `Message from ... (instagram)`). The app already handles Instagram messages that arrive via the Page webhook.

### 4. Start a new conversation

- From the **tester’s** Instagram app: search for your **business account** → open profile → **Message** → send a new message (e.g. “Hi”).
- Avoid replying in an old thread that was started before the app was connected. A fresh conversation sometimes fixes delivery.

### 5. Double-check in the dashboard

- **Instagram** → **Generate access tokens**: note the **exact** Instagram account (name/username) shown there. That is the only account whose inbox will trigger this app.
- **Roles** → **Instagram Testers**: note who is listed. The account that **sends** the DM must be in this list.

---

## 1. Meta cannot reach localhost

- Your app runs on `127.0.0.1:8000` (localhost).
- Meta’s servers are on the internet; they **cannot** send POST requests to your PC.
- So: **no request from Meta = no logs.**

## 2. Use a public URL (tunnel)

Expose your local app with a tunnel, e.g. **ngrok**:

1. Install: https://ngrok.com/download  
2. Run your app: `python app.py`  
3. In another terminal: `ngrok http 8000`  
4. Copy the **HTTPS** URL ngrok shows, e.g. `https://abc123.ngrok.io`

## 3. Set this URL in Meta

1. Go to **Meta for Developers** → your app → **Instagram** (product).  
2. **Webhooks** → **Configure** (or Add subscription).  
3. **Callback URL:** `https://YOUR-NGROK-URL/webhook`  
   - Example: `https://abc123.ngrok.io/webhook`  
4. **Verify token:** same as in your `.env` (`WEBHOOK_VERIFY_TOKEN`).  
5. Click **Verify and save**.  
6. Subscribe to **messages**.

## 4. Test again

1. Keep `python app.py` running.  
2. Keep **ngrok** running.  
3. Send a DM from your real Instagram account to your Instagram business account.  
4. In the terminal where `app.py` runs you should see:
   - `=== WEBHOOK POST received (Instagram/WhatsApp/FB) ===`
   - `RAW BODY ...`
   - `OBJECT: instagram ...`
   - `Message from ... : ...`

If you see these logs, the webhook is working and the rest is reply/send logic. If you still see no logs, the callback URL or subscription in Meta is wrong or the tunnel is down.

## 5. Instagram via Page webhook (object=page)

If your Instagram account is linked to a **Facebook Page**, Meta may send DMs as **object=page** (same as Messenger) with `messaging_product: "instagram"` on the event. The app now handles that: you’ll see `PAGE HANDLER` and `Message from ... (instagram)` in the logs. Ensure the **Page** webhook URL in Meta is the same callback (e.g. `https://YOUR-NGROK-URL/webhook`) and that the Page is subscribed to messages.

## 6. Quick checklist when you see no logs

- [ ] App is running: `python app.py`
- [ ] **ngrok** is running (e.g. `ngrok http 8000`) and you use the **HTTPS** URL (not the old one if you restarted ngrok)
- [ ] **.env** has `INSTAGRAM_USER_ACCESS_TOKEN=` set to the **User** token from Section 2 (Generate access tokens)
- [ ] Meta App → **Instagram** → **Webhooks**: Callback URL = `https://YOUR-NGROK-URL/webhook`, Verify token = value of `WEBHOOK_VERIFY_TOKEN` in `.env`, and **Subscribe to this object** → **messages** is checked
- [ ] The Instagram account that **sends** the DM is added as an **Instagram Tester**: App → **Roles** → **Instagram Testers** → Add that account
- [ ] You send the DM **from** the tester account **to** your **Instagram business/professional** account (the one connected to the app)
- [ ] Optional: open `https://YOUR-NGROK-URL/health` in a browser – you should see `{"status":"healthy",...}` (proves ngrok reaches your app)
