import shutil
from pathlib import Path
from datetime import datetime
import sys


BACKUPS_DIR = Path(__file__).resolve().parent.parent / 'backups'
DB_PATH = Path('transactions.db')


def list_backups():
    if not BACKUPS_DIR.exists():
        return []
    files = sorted(BACKUPS_DIR.glob('transactions.db.*.bak'), key=lambda p: p.stat().st_mtime, reverse=True)
    return files


def choose_backup(files):
    if not files:
        print('No backups found in', BACKUPS_DIR)
        return None
    print('Available backups:')
    for i, f in enumerate(files, start=1):
        ts = datetime.utcfromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%SZ')
        print(f'  {i}) {f.name}  ({ts})')
    print('Enter the number to restore (default 1 = latest), or 0 to cancel: ', end='')
    try:
        val = input().strip() or '1'
        idx = int(val)
    except Exception:
        print('Invalid selection')
        return None
    if idx == 0:
        return None
    if 1 <= idx <= len(files):
        return files[idx-1]
    print('Selection out of range')
    return None


def restore(backup_path: Path):
    print(f'Restoring {backup_path} -> {DB_PATH}')
    confirm = input('Type RESTORE to confirm and overwrite the current DB: ')
    if confirm != 'RESTORE':
        print('Aborted')
        return
    try:
        shutil.copy2(backup_path, DB_PATH)
        print('Restore complete. You may want to restart the server to ensure it reopens the DB file.')
    except PermissionError as e:
        print('Permission error while restoring. The DB file may be in use by the server.')
        print('Please stop the running server (uvicorn) and re-run this script.')
        print('Error:', e)
    except Exception as e:
        print('Failed to restore:', e)


def main():
    files = list_backups()
    b = choose_backup(files)
    if not b:
        print('No backup selected. Exiting.')
        return
    restore(b)


if __name__ == '__main__':
    main()
