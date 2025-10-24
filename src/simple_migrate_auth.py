"""
Simple migration helper to add auth-related tables (users, sessions, wallet_nonces) using SQLAlchemy metadata.create_all.
Run this as a script or import it from startup to ensure tables exist.
"""
from .database import engine, Base
from . import models


def run():
    print('Creating auth tables if they do not exist...')
    Base.metadata.create_all(bind=engine)
    print('Done')


if __name__ == '__main__':
    run()
