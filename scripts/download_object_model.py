"""Fetch the official prompt-free YOLOE Small weights once, with a pinned hash."""
import hashlib
from pathlib import Path
import urllib.request

DESTINATION = Path(__file__).resolve().parents[1] / 'models/yoloe-v8s-seg-pf.pt'
URL = 'https://github.com/ultralytics/assets/releases/download/v8.3.0/yoloe-v8s-seg-pf.pt'
SHA256 = 'df213f389d69a0df544cc1a3e500f567176468e4b4ed2ce933b8073c27539ac1'


def checksum(path):
    with path.open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()


def main():
    if DESTINATION.is_file() and checksum(DESTINATION) == SHA256:
        print('YOLOE Small is ready (SHA256 verified).')
        return
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    temporary = DESTINATION.with_suffix('.pt.part')
    print('Downloading official YOLOE Small prompt-free checkpoint (30 MB)…', flush=True)
    try:
        with urllib.request.urlopen(URL, timeout=120) as response, temporary.open('wb') as file:
            while chunk := response.read(1024 * 1024):
                file.write(chunk)
        if checksum(temporary) != SHA256:
            raise ValueError('Checkpoint checksum mismatch; existing model was not replaced')
        temporary.replace(DESTINATION)
    finally:
        temporary.unlink(missing_ok=True)
    print('YOLOE Small is ready (SHA256 verified).')


if __name__ == '__main__':
    main()
