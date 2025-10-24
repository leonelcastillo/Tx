from sqlalchemy.orm import Session
from . import models, schemas
from typing import List, Optional


def create_transaction(db: Session, tx: schemas.TransactionCreate) -> models.Transaction:
    db_tx = models.Transaction(
        name=tx.name,
        phone=tx.phone,
        wallet=tx.wallet,
        weight_kg=tx.weight_kg,
        address=tx.address,
        photo=tx.photo,
    )
    db.add(db_tx)
    db.commit()
    db.refresh(db_tx)
    return db_tx


def get_transaction(db: Session, tx_id: int) -> Optional[models.Transaction]:
    return db.query(models.Transaction).filter(models.Transaction.id == tx_id).first()


def list_transactions(db: Session, skip: int = 0, limit: int = 100) -> List[models.Transaction]:
    return db.query(models.Transaction).offset(skip).limit(limit).all()


def update_status(db: Session, tx_id: int, status: models.StatusEnum) -> Optional[models.Transaction]:
    tx = get_transaction(db, tx_id)
    if not tx:
        return None
    tx.status = status
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def collect_transaction(db: Session, tx_id: int, collected_weight: Optional[float], collected_photo: Optional[str]):
    tx = get_transaction(db, tx_id)
    if not tx:
        return None
    tx.collected_weight_kg = collected_weight
    tx.collected_photo = collected_photo
    from datetime import datetime
    tx.collected_at = datetime.utcnow()
    tx.status = models.StatusEnum.collected
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx
