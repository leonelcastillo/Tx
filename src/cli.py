import typer
from typing import Optional
from . import database, crud, schemas

app = typer.Typer()


@app.command()
def init():
    """Init the database file"""
    database.init_db()
    typer.echo("Database initialized")


@app.command()
def add(
    name: str = typer.Option(..., help="Person name, e.g. 'Juan'"),
    phone: Optional[str] = typer.Option(None, help="Phone number"),
    wallet: Optional[str] = typer.Option(None, help="Wallet address"),
    weight: float = typer.Option(..., help="Weight in kg", show_default=False),
):
    """Add a transaction"""
    db = database.SessionLocal()
    try:
        tx_in = schemas.TransactionCreate(name=name, phone=phone, wallet=wallet, weight_kg=weight)
        tx = crud.create_transaction(db, tx_in)
        typer.echo(f"Added transaction id={tx.id} name={tx.name} weight={tx.weight_kg}kg status={tx.status}")
    finally:
        db.close()


@app.command()
def list(skip: int = 0, limit: int = 100):
    """List transactions"""
    db = database.SessionLocal()
    try:
        items = crud.list_transactions(db, skip=skip, limit=limit)
        if not items:
            typer.echo("No transactions found")
            return
        for t in items:
            typer.echo(f"{t.id}: {t.name} {t.weight_kg}kg {t.status} {t.date}")
    finally:
        db.close()


if __name__ == "__main__":
    app()
