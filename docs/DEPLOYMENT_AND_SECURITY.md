Deployment & Security Notes
==========================

Date: 2025-10-22
Repo: Tx (FastAPI + SQLite)

Purpose
-------
This document summarizes how to deploy the current FastAPI app to Firebase/Google Cloud (Cloud Run + Firebase Hosting), and proposes practical anti-spam / anti-bot techniques you can add before deployment to prevent malicious actors from flooding the service with fake transactions.

Current repo state (short)
--------------------------
- FastAPI backend (served by uvicorn).
- SQLite DB (transactions.db) in repo root (development only).
- Static Spanish UIs under `src/static/` (submit, observer, ranking, admin).
- Admin protected by an `x-admin-key` header read from `ADMIN_API_KEY` environment variable.
- Server endpoints include a `/submit` endpoint for public submissions and admin endpoints for collect/status/delete.
- Collected weight is enforced as >0 for 'collect' flows; weight on submit is not required.

Quick decision: can we deploy with Firebase?
-------------------------------------------
Yes — but not on Firebase Hosting alone. The recommended path is:
- Build a container for the FastAPI app and deploy it to Google Cloud Run.
- Use Firebase Hosting with a rewrite to the Cloud Run service to serve the public domain (optional but convenient for friendly domains and SSL via Firebase).

Files you'll typically add before deploying
------------------------------------------
- `Dockerfile` (root) — containerize the app.
- `requirements.txt` — ensure all Python deps are listed (uvicorn, fastapi, sqlalchemy, aioredis, fastapi-limiter, google-cloud-storage, etc.).
- `firebase.json` and `.firebaserc` — configure the hosting rewrite to Cloud Run.

Production concerns
-------------------
- Do NOT use SQLite for production. Cloud Run is ephemeral and scales; use Cloud SQL (Postgres) instead.
- Do not store user-uploaded images on the local filesystem. Use Google Cloud Storage (Firebase Storage) and update the app to upload/read from storage.

Anti-spam / Anti-bot recommendations
-----------------------------------
These methods are ordered from easiest to strongest. In production I recommend a layered approach: CAPTCHA (or equivalent) + server-side rate limiting + server-side signature/token + logging/alerts.

1) CAPTCHA on submit (recommended)
  - Add reCAPTCHA v2 (checkbox) or reCAPTCHA v3 / hCaptcha on the `submit` page.
  - Client: obtain token and include as `recaptcha_token` in the POST FormData.
  - Server: verify token against Google's siteverify API using your secret. Reject if verification fails or score is low.
  - Pros: stops most bots; easy to add.
  - Cons: UX friction; attackers can solve if automated.

Server-side verify snippet (Python):
```py
import httpx
async def verify_recaptcha(token: str, secret: str):
    r = await httpx.post('https://www.google.com/recaptcha/api/siteverify', data={'secret': secret, 'response': token}, timeout=5)
    data = r.json()
    return data
```

2) Rate limiting (must-have in addition to CAPTCHA)
  - Production: use a Redis-backed rate limiter (Cloud Memorystore + `fastapi-limiter`).
  - Dev / quick: an in-memory token-bucket limiter (works only per instance; if you scale to multiple Cloud Run instances it won't be global).
  - Protect by IP and also by wallet identifier (limit submissions per wallet address per hour/day).
  - Example (fastapi-limiter + aioredis):
```py
# install: pip install fastapi-limiter aioredis
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
import aioredis

@app.on_event('startup')
async def startup():
    redis = await aioredis.from_url('redis://REDIS_HOST:6379/0', encoding='utf-8', decode_responses=True)
    await FastAPILimiter.init(redis)

@app.post('/submit')
async def submit(payload: TransactionCreate, _=Depends(RateLimiter(times=10, seconds=60))):
    # allows 10 submissions per minute per IP
    ...
```
  - For wallet-based limits: add a short middleware or code path that increments a Redis key like `tx:wallet:{wallet}` with expiry and reject when the count exceeds threshold.

3) Honeypot fields + simple validators (easy, low-friction)
  - Add a hidden input (e.g., `<input name="hp" style="display:none">`). If it's filled, drop the request.
  - Validate required fields and types strictly server-side (you already enforce weight > 0).
  - Require content length or limits on string sizes to avoid oversized payload abuse.

4) Proof-of-work / submission token (stronger, low UX cost)
  - Issue short-lived signed tokens to clients (e.g., via Firebase Authentication or a pre-flight request that returns a temporary token tied to session/IP). Token required to submit.
  - Or require reCAPTCHA token + server-side short-lived signed nonce to make automated farm attacks harder.

5) Email/SMS verification (strong but heavyweight)
  - Only if you want real human tracing; increases friction and cost.

6) Monitoring & alerts
  - Log submission volume, IP distribution, and top wallet addresses.
  - Set an alert when submissions/hour exceeds normal thresholds.
  - Consider short auto-blocking: when an IP exceeds a high threshold, add it to a temporary denylist in Redis.

Implementation plan & code hints
-------------------------------
A) Short-term (fast):
  - Add a hidden honeypot field and server check.
  - Add reCAPTCHA v2 on `submit_es.html` and a server-side verification step.
  - Add an in-memory rate-limiter in the app to throttle obvious floods while keeping UX simple.

B) Production-ready (recommended):
  - Add Cloud Memorystore (Redis) and `fastapi-limiter`.
  - Implement wallet-based counting in Redis: increment a key per wallet with TTL (1 hour) and enforce daily cap.
  - Add reCAPTCHA (v3 or hCaptcha) and require the token on submission.
  - Move DB to Cloud SQL and uploads to Cloud Storage.

Sample wallet-based limiter (Redis pseudo-code):
```py
# pseudo
count = await redis.incr(f"wallet:{wallet}")
if count == 1:
    await redis.expire(f"wallet:{wallet}", 3600)
if count > WALLET_LIMIT_PER_HOUR:
    raise HTTPException(429, "Too many submissions for this wallet")
```

Testing plan (what we'll run tomorrow)
--------------------------------------
- Unit test: validation logic rejects invalid weights and honeypot-filled submissions.
- Integration test: submit a valid transaction and assert it appears in `/transactions`.
- Rate-limit test: run a small script that POSTs to `/submit` rapidly and confirm server responds with 429 after threshold.
- reCAPTCHA test: simulate client submit including a token (or mock verification in tests) and assert behaviour.
- Load test (optional): run a short load script (veget a / hey / python requests loop) to ensure service rate-limits appropriately.

Example local rate-limit test script (python):
```py
import requests
url = 'http://localhost:8080/submit'
for i in range(40):
    r = requests.post(url, data={'name':f't{i}','phone':'000','wallet':'W','weight_kg':1}, timeout=5)
    print(i, r.status_code, r.text[:200])
```

Deployment checklist (short)
----------------------------
- [ ] Add Dockerfile
- [ ] Add requirements.txt (ensure all libs listed)
- [ ] Replace SQLite with Cloud SQL (migrate data)
- [ ] Replace local uploads with Google Cloud Storage
- [ ] Add Redis (Cloud Memorystore) and configure rate limiter
- [ ] Add reCAPTCHA + client & server verification
- [ ] Deploy to Cloud Run and ensure env vars set (ADMIN_API_KEY, DB URL, RECAPTCHA_SECRET)
- [ ] Configure Firebase Hosting rewrite (optional)
- [ ] Run integration tests and a small load test

Notes & trade-offs
------------------
- In-memory limiters are easy but don't work across scaled instances. Use Redis for global limits.
- CAPTCHAs add friction; combine with rate limiting to reduce human friction while blocking bots.
- Wallet-based limits are effective for this domain (bots tend to reuse wallets); however, attackers can rotate wallets.
- Monitoring and automatic temporary denylisting gives a good operational balance.

Next steps (for tomorrow)
-------------------------
- Review this doc and confirm which security measures you want to implement first (I recommend: reCAPTCHA + Redis-backed rate limiter + honeypot).
- If you approve, I will add a working prototype: a) implement reCAPTCHA on `src/static/submit_es.html` and server-side verification, b) add `fastapi-limiter` wiring and sample wallet-limit logic, c) add a small test script that demonstrates the 429 behaviour.


-- End of document
