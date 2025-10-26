from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, Form, Request
import time
import threading
from typing import Optional
import uuid
import traceback
from fastapi.staticfiles import StaticFiles
import shutil
import os
from sqlalchemy.orm import Session
from . import database, models, schemas, crud
from sqlalchemy.sql import func
from sqlalchemy import case

app = FastAPI(title="Plastic Bottle Transactions")

# ensure static/upload dirs
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Simple in-memory rate limiter (per-IP) for basic anti-spam protection in dev.
# Not suitable for multi-process production; use Redis or a proper rate-limiter there.
RATE_LIMIT_STORE: dict = {}
RATE_LIMIT_LOCK = threading.Lock()
RATE_LIMIT_MAX = int(os.environ.get('RATE_LIMIT_MAX', 6))  # max requests
RATE_LIMIT_WINDOW = int(os.environ.get('RATE_LIMIT_WINDOW', 60))  # seconds


def rate_limiter(request: Request):
    """Basic sliding-window limiter keyed by client IP. Raises 429 when exceeded."""
    # determine client ip (best-effort)
    client_host = None
    try:
        client_host = request.client.host if request and getattr(request, 'client', None) else 'unknown'
    except Exception:
        client_host = 'unknown'

    now = time.time()
    with RATE_LIMIT_LOCK:
        lst = RATE_LIMIT_STORE.get(client_host, [])
        # remove old timestamps
        lst = [ts for ts in lst if now - ts <= RATE_LIMIT_WINDOW]
        if len(lst) >= RATE_LIMIT_MAX:
            # still over limit
            raise HTTPException(status_code=429, detail=f"Rate limit exceeded: up to {RATE_LIMIT_MAX} submissions per {RATE_LIMIT_WINDOW}s allowed")
        # record this request
        lst.append(now)
        RATE_LIMIT_STORE[client_host] = lst



def require_admin(request: Request):
    """Raise 403 if ADMIN_API_KEY is configured and the request doesn't provide it in x-admin-key header."""
    ADMIN_KEY = os.environ.get('ADMIN_API_KEY')
    if not ADMIN_KEY:
        # no admin key configured — treat as open (MVP)
        return
    # accept header 'x-admin-key'
    provided = request.headers.get('x-admin-key')
    if not provided or provided != ADMIN_KEY:
        raise HTTPException(status_code=403, detail='admin api key required')



@app.on_event("startup")
def on_startup():
    database.init_db()


@app.post("/transactions", response_model=schemas.TransactionOut)
def create_transaction(tx_in: schemas.TransactionCreate, db: Session = Depends(get_db)):
    return crud.create_transaction(db, tx_in)





# Authentication removed for MVP: identification will use the `wallet` field on submissions.


@app.get('/ranking')
def ranking(limit: int = 50, db: Session = Depends(get_db)):
    """
    Return top identities ranked by total kilograms.
    Identification logic (MVP): prefer `wallet` when present, otherwise fall back to `phone`.
    The `display` field contains the first 4 characters of the wallet when available, or the phone number.
    """
    # Build an identity expression: prefer wallet when non-empty, else phone
    identity_expr = case(
        (((models.Transaction.wallet != None) & (models.Transaction.wallet != '')), models.Transaction.wallet),
        else_=models.Transaction.phone,
    ).label('identity')

    # Aggregate totals from collected transactions only and capture the latest collected row id per identity
    agg_sub = (
        db.query(
            identity_expr.label('ident'),
            func.sum(models.Transaction.collected_weight_kg).label('total_kg'),
            func.max(models.Transaction.id).label('last_id'),
        )
        .filter(models.Transaction.status == models.StatusEnum.collected)
        .group_by(identity_expr)
        .subquery()
    )

    # Join back to transactions on last_id to obtain the most recent name and other fields
    joined = (
        db.query(
            agg_sub.c.ident,
            agg_sub.c.total_kg,
            models.Transaction.name,
            models.Transaction.wallet,
            models.Transaction.phone,
        )
        .join(models.Transaction, models.Transaction.id == agg_sub.c.last_id)
        .order_by(agg_sub.c.total_kg.desc())
        .limit(limit)
    ).all()

    def mask_phone(p: str) -> str:
        if not p:
            return p
        digits = ''.join([c for c in p if c.isdigit()])
        if len(digits) <= 4:
            return '****' + digits
        return '****' + digits[-4:]

    items = []
    for ident, total_kg, name, wallet, phone in joined:
        kind = 'wallet' if wallet and str(wallet).strip() != '' else 'phone'
        rep_name = (name or '').strip()
        if kind == 'wallet':
            wallet_prefix = str(ident)[:4]
            display_name = f"{rep_name or 'anonymous'} ({wallet_prefix})"
            identifier = ident
        else:
            wallet_prefix = None
            masked = mask_phone(ident)
            display_name = f"{rep_name or 'anonymous'} ({masked})"
            identifier = ident
        items.append({
            'type': kind,
            'identifier': identifier,
            'display_name': display_name,
            'rep_name': rep_name,
            'wallet_prefix': wallet_prefix,
            'total_kg': float(total_kg or 0),
        })

    return items


@app.get('/ranking/{identifier}/contributors')
def ranking_contributors(identifier: str, db: Session = Depends(get_db)):
    """Return breakdown of contributions that roll up into the given identity (wallet or phone).
    The identifier parameter should be the full wallet string or full phone string used as identity.
    """
    # find matching rows where wallet==identifier OR phone==identifier
    rows = (
        db.query(models.Transaction.wallet, models.Transaction.phone, func.sum(models.Transaction.weight_kg).label('kg'))
        .filter((models.Transaction.wallet == identifier) | (models.Transaction.phone == identifier))
        .group_by(models.Transaction.wallet, models.Transaction.phone)
        .all()
    )
    contributions = []
    for w, p, kg in rows:
        contributions.append({'wallet': w, 'phone': p, 'kg': float(kg or 0)})
    return {'identifier': identifier, 'contributors': contributions}


@app.post("/submit", response_model=schemas.TransactionOut)
def submit_transaction(
    name: str = Form(...),
    phone: Optional[str] = Form(None),
    wallet: Optional[str] = Form(None),
    weight_kg: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    hp: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    _rl=Depends(rate_limiter),
):
    """Handle multipart/form uploads from the Spanish form. Saves uploaded photo and stores filename in DB. No sessions/auth for MVP."""
    try:
        # honeypot check: bots often fill hidden fields — reject if populated
        if hp and str(hp).strip() != '':
            raise HTTPException(status_code=400, detail='Invalid submission')
        photo_filename = None
        if photo:
            # sanitize filename and ensure safe extension
            original_name = os.path.basename(photo.filename)
            _, extension = os.path.splitext(original_name)
            extension = extension.lower()
            allowed_ext = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
            if extension not in allowed_ext:
                # fallback to .bin
                extension = '.bin'

            # generate safe filename using uuid
            safe_name = uuid.uuid4().hex + extension
            dest = os.path.join(UPLOAD_DIR, safe_name)
            try:
                with open(dest, "wb") as buffer:
                    shutil.copyfileobj(photo.file, buffer)
            except OSError as e:
                raise HTTPException(status_code=500, detail=f"Error saving uploaded file: {e}")

            photo_filename = safe_name

        # coerce weight_kg which may arrive as an empty string into None, or parse to float
        parsed_weight = None
        if weight_kg is not None and weight_kg != '':
            try:
                parsed_weight = float(weight_kg)
                if parsed_weight <= 0:
                    raise ValueError()
            except Exception:
                raise HTTPException(status_code=400, detail="weight_kg must be a positive number if provided")

        tx_in = schemas.TransactionCreate(
            name=name,
            phone=phone,
            wallet=wallet,
            weight_kg=parsed_weight,
            address=address,
            photo=photo_filename,
        )
        try:
            db_tx = crud.create_transaction(db, tx_in)
            # serialize the SQLAlchemy object to a plain dict (avoid ORM serialization issues)
            return {
                'id': db_tx.id,
                'name': db_tx.name,
                'phone': db_tx.phone,
                'wallet': db_tx.wallet,
                'address': db_tx.address,
                'weight_kg': db_tx.weight_kg,
                'photo': db_tx.photo,
                'collected_weight_kg': db_tx.collected_weight_kg,
                'collected_photo': db_tx.collected_photo,
                'collected_at': db_tx.collected_at if getattr(db_tx, 'collected_at', None) is not None else None,
                'date': db_tx.date if getattr(db_tx, 'date', None) is not None else None,
                'status': db_tx.status.value if hasattr(db_tx.status, 'value') else str(db_tx.status),
            }
        except Exception as e:
            # Handle common DB integrity errors more clearly
            try:
                from sqlalchemy.exc import IntegrityError
                if isinstance(e, IntegrityError):
                    tb = traceback.format_exc()
                    logpath = os.path.join(BASE_DIR, '..', 'transactions_error.log')
                    try:
                        with open(logpath, 'a', encoding='utf-8') as f:
                            f.write('\n---- DB INTEGRITY ERROR at submit: ----\n')
                            f.write(tb)
                    except Exception:
                        pass
                    raise HTTPException(status_code=500, detail="Database integrity error while saving transaction")
            except Exception:
                # fall through to generic handler below
                pass
            # re-raise the original exception to be logged by the outer handler
            raise
    except Exception as e:
        # log full traceback to a file for debugging
        tb = traceback.format_exc()
        logpath = os.path.join(BASE_DIR, '..', 'transactions_error.log')
        try:
            with open(logpath, 'a', encoding='utf-8') as f:
                f.write('\n---- ERROR at submit: ----\n')
                f.write(tb)
        except Exception:
            pass
        # return generic error to client
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.get("/transactions", response_model=list[schemas.TransactionOut])
def list_transactions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    items = crud.list_transactions(db, skip=skip, limit=limit)
    # serialize explicitly to ensure address/photo are included
    out = []
    for t in items:
        out.append({
            'id': t.id,
            'name': t.name,
            'phone': t.phone,
            'wallet': t.wallet,
            'address': t.address,
            'weight_kg': t.weight_kg,
            'collected_weight_kg': t.collected_weight_kg,
            'collected_photo': t.collected_photo,
            'collected_at': t.collected_at if getattr(t, 'collected_at', None) is not None else None,
            'photo': t.photo,
            'date': t.date if getattr(t, 'date', None) is not None else None,
            'status': t.status.value if hasattr(t.status, 'value') else str(t.status),
        })
    return out


@app.get("/transactions/{tx_id}", response_model=schemas.TransactionOut)
def get_transaction(tx_id: int, db: Session = Depends(get_db)):
    tx = crud.get_transaction(db, tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {
        'id': tx.id,
        'name': tx.name,
        'phone': tx.phone,
        'wallet': tx.wallet,
        'weight_kg': tx.weight_kg,
        'address': tx.address,
        'photo': tx.photo,
        'date': tx.date if getattr(tx, 'date', None) is not None else None,
        'status': tx.status.value if hasattr(tx.status, 'value') else str(tx.status),
    }


@app.patch("/transactions/{tx_id}/status", response_model=schemas.TransactionOut)
def patch_status(tx_id: int, status_in: schemas.TransactionUpdateStatus, request: Request, db: Session = Depends(get_db)):
    # protect with admin key if configured
    require_admin(request)
    # Disallow directly setting a transaction to 'collected' via this endpoint.
    # Admins should use the dedicated /transactions/{tx_id}/collect endpoint which records collected weight and photo.
    if status_in.status == models.StatusEnum.collected:
        raise HTTPException(status_code=400, detail="Use the /transactions/{tx_id}/collect endpoint to mark as collected and provide collected weight/photo")

    updated = crud.update_status(db, tx_id, status_in.status)
    if not updated:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return updated



@app.patch("/transactions/{tx_id}", response_model=schemas.TransactionOut)
def patch_transaction(tx_id: int, updates: schemas.TransactionUpdate, request: Request, db: Session = Depends(get_db)):
    """Admin-only: update mutable fields on a transaction (name, phone, wallet, weight_kg, address)."""
    require_admin(request)
    data = updates.dict(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No updatable fields provided")

    updated = crud.update_transaction(db, tx_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # serialize response to avoid ORM issues and ensure datetimes are native
    return {
        'id': updated.id,
        'name': updated.name,
        'phone': updated.phone,
        'wallet': updated.wallet,
        'weight_kg': updated.weight_kg,
        'address': updated.address,
        'photo': updated.photo,
        'collected_weight_kg': updated.collected_weight_kg,
        'collected_photo': updated.collected_photo,
        'collected_at': updated.collected_at if getattr(updated, 'collected_at', None) is not None else None,
        'date': updated.date if getattr(updated, 'date', None) is not None else None,
        'status': updated.status.value if hasattr(updated.status, 'value') else str(updated.status),
    }


@app.patch("/transactions/{tx_id}/collect", response_model=schemas.TransactionOut)
def collect_transaction_endpoint(
    tx_id: int,
    collected_weight: Optional[float] = Form(None),
    collected_photo: Optional[UploadFile] = File(None),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """Record the actual collected weight and optional collected photo. Admin only."""
    # protect with admin key if configured
    require_admin(request)

    # validate collected_weight (required)
    if collected_weight is None:
        raise HTTPException(status_code=400, detail="collected_weight is required when marking collected")
    try:
        cw = float(collected_weight)
        if cw <= 0:
            raise ValueError()
    except Exception:
        raise HTTPException(status_code=400, detail="collected_weight must be a positive number")

    filename = None
    if collected_photo:
        # save uploaded file to static/uploads
        import uuid, os
        ext = os.path.splitext(collected_photo.filename)[1] or ".jpg"
        safe_name = f"{uuid.uuid4().hex}{ext}"
        dest = os.path.join(UPLOAD_DIR, safe_name)
        try:
            with open(dest, "wb") as buffer:
                shutil.copyfileobj(collected_photo.file, buffer)
            filename = safe_name
        except OSError as e:
            raise HTTPException(status_code=500, detail=f"Error saving uploaded file: {e}")

    tx = crud.collect_transaction(db, tx_id, cw, filename)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx


@app.delete('/transactions/{tx_id}')
def delete_transaction(tx_id: int, request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    tx = crud.get_transaction(db, tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail='Transaction not found')
    db.delete(tx)
    db.commit()
    return {'ok': True, 'id': tx_id}


@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    # simple aggregates: report total collected kilograms and total transaction count
    # Sum collected_weight_kg (only transactions that were actually collected)
    total_collected = db.query(func.sum(models.Transaction.collected_weight_kg)).scalar() or 0
    total_count = db.query(func.count(models.Transaction.id)).scalar() or 0
    try:
        total_collected = float(total_collected)
    except Exception:
        total_collected = 0.0
    return {"total_kg": total_collected, "total_count": int(total_count)}


@app.get("/export.csv")
def export_csv(api_key: Optional[str] = None, db: Session = Depends(get_db)):
    import csv
    from fastapi.responses import StreamingResponse
    ADMIN_KEY = os.environ.get('ADMIN_API_KEY')
    if ADMIN_KEY and api_key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="admin api key required")

    def iterfile():
        rows = db.query(models.Transaction).all()
        header = ['id','name','phone','wallet','weight_kg','address','photo','date','status']
        out = []
        from io import StringIO
        sio = StringIO()
        writer = csv.writer(sio)
        writer.writerow(header)
        for r in rows:
            writer.writerow([r.id,r.name,r.phone,r.wallet,r.weight_kg,r.address,r.photo,r.date,r.status])
        sio.seek(0)
        yield sio.read()

    return StreamingResponse(iterfile(), media_type='text/csv')
