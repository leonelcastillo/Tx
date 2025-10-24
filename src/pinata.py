import os
from typing import Optional
import requests

PINATA_JWT = os.environ.get('PINATA_JWT')
PINATA_API_KEY = os.environ.get('PINATA_API_KEY')
PINATA_SECRET = os.environ.get('PINATA_SECRET_API_KEY')
PINATA_ENDPOINT = os.environ.get('PINATA_ENDPOINT', 'https://api.pinata.cloud/pinning/pinFileToIPFS')


def _build_headers():
    headers = {}
    if PINATA_JWT:
        headers['Authorization'] = f'Bearer {PINATA_JWT}'
    else:
        # pinata supports api key/secret as headers as well
        if PINATA_API_KEY and PINATA_SECRET:
            headers['pinata_api_key'] = PINATA_API_KEY
            headers['pinata_secret_api_key'] = PINATA_SECRET
    return headers


def pin_file(path: str, filename: Optional[str] = None) -> dict:
    """Pin a local file to Pinata. Returns Pinata JSON response.

    Raises requests.HTTPError on failure.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    files = {}
    with open(path, 'rb') as fh:
        fname = filename or os.path.basename(path)
        files = {'file': (fname, fh)}
        headers = _build_headers()
        resp = requests.post(PINATA_ENDPOINT, files=files, headers=headers, timeout=60)
        resp.raise_for_status()
        return resp.json()
