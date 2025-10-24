import os
from pathlib import Path

DB = os.environ.get('DATABASE_URL', 'sqlite:///./transactions.db')

def reset():
    # only support default local sqlite path format here
    if DB.startswith('sqlite:///'):
        path = DB.replace('sqlite:///', '')
        p = Path(path)
        # create backups folder
        backups_dir = Path(__file__).resolve().parent.parent / 'backups'
        backups_dir.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            print('DB file does not exist, creating schema...')
        else:
            # make a timestamped copy
            from datetime import datetime
            ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
            dest = backups_dir / f'transactions.db.{ts}.bak'
            print(f'Creating backup: {dest}')
            import shutil
            shutil.copy2(p, dest)
            print(f'Removing DB file: {p} (this will erase all data)')
            p.unlink()
        # now call init_db
        from src import database
        database.init_db()
        print('Database reset and schema recreated. Backup stored in backups/ if one existed.')
    else:
        print('Reset currently only supports the default local sqlite database.')

if __name__ == '__main__':
    confirm = input('This will erase your local sqlite DB and recreate schema. Type YES to continue: ')
    if confirm == 'YES':
        reset()
    else:
        print('Aborted')
