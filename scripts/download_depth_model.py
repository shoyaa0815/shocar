"""Download the official Small checkpoint once; inference never uses the network."""
import hashlib
from pathlib import Path
import urllib.request

REVISION = "03876f8651c73a60fe4c2c48294e09fcb6838fcf"
SHA256 = "715fade13be8f229f8a70cc02066f656f2423a59effd0579197bbf57860e1378"
DESTINATION = Path(__file__).resolve().parents[1] / "models/depth_anything_v2_vits.pth"
URL = ("https://huggingface.co/depth-anything/Depth-Anything-V2-Small/resolve/"
       + REVISION + "/depth_anything_v2_vits.pth?download=true")


def checksum(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def main():
    if DESTINATION.is_file() and checksum(DESTINATION) == SHA256:
        print("Depth Anything V2 Small is ready (SHA256 verified).")
        return
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    temporary = DESTINATION.with_suffix(".pth.part")
    print("Downloading official Depth Anything V2 Small checkpoint (99 MB)…", flush=True)
    try:
        with urllib.request.urlopen(URL, timeout=120) as response, temporary.open("wb") as file:
            while chunk := response.read(1024 * 1024):
                file.write(chunk)
        if checksum(temporary) != SHA256:
            raise ValueError("Checkpoint checksum mismatch; existing model was not replaced")
        temporary.replace(DESTINATION)
    finally:
        temporary.unlink(missing_ok=True)
    print("Depth Anything V2 Small is ready (SHA256 verified).")


if __name__ == "__main__":
    main()
