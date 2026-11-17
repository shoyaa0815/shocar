import asyncio
import base64
from contextlib import suppress
import os
import time
from urllib.parse import urlsplit, urlunsplit

import cv2
import httpx
import numpy as np

FRESH_SECONDS = 3.0
RETRY_SECONDS = 2.0
MAX_FRAME_BYTES = 4 * 1024 * 1024


def camera_url(value: str) -> str:
    """Accept the app's base address or its explicit MJPEG endpoint."""
    value = value.strip()
    if not value:
        return ""
    try:
        parsed = urlsplit(value)
        if (parsed.scheme not in ("http", "https") or not parsed.hostname
                or parsed.fragment or parsed.port == 0):
            raise ValueError
    except ValueError:
        raise ValueError("CAMERA_URL must be an http(s) camera address") from None
    path = "/video" if parsed.path in ("", "/") else parsed.path
    return urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, ""))


async def latest_jpegs(chunks):
    """Extract JPEGs across arbitrary HTTP chunks, discarding older complete frames."""
    buffer = bytearray()
    async for chunk in chunks:
        buffer.extend(chunk)
        latest = None
        while True:
            start = buffer.find(b"\xff\xd8")
            if start < 0:
                # Keep a possible first byte of a split SOI marker.
                buffer[:] = buffer[-1:]
                break
            if start:
                del buffer[:start]
            end = buffer.find(b"\xff\xd9", 2)
            if end < 0:
                if len(buffer) > MAX_FRAME_BYTES:
                    raise ValueError("Camera frame exceeds limit")
                break
            if end + 2 > MAX_FRAME_BYTES:
                raise ValueError("Camera frame exceeds limit")
            latest = bytes(buffer[:end + 2])
            del buffer[:end + 2]
        if latest is not None:
            yield latest


def valid_jpeg(data: bytes) -> bool:
    try:
        image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
        return image is not None and image.size > 0
    except cv2.error:
        return False


class CameraStream:
    def __init__(self, url: str | None = None):
        self.url = camera_url(os.getenv("CAMERA_URL", "") if url is None else url)
        self.task = None
        self.image = None
        self.updated_at = None
        self.last_frame_at = None
        self.sequence = 0
        self.fps = 0.0
        self.connected = False
        self.error = None
        self.state = "connecting" if self.url else "unconfigured"

    async def start(self):
        if self.url and self.task is None:
            self.task = asyncio.create_task(self._run(), name="ip-webcam")

    async def stop(self):
        if self.task is not None:
            self.task.cancel()
            with suppress(asyncio.CancelledError):
                await self.task
            self.task = None
        self.connected = False

    def snapshot(self, after_sequence: int = -1) -> dict:
        age = None if self.last_frame_at is None else time.monotonic() - self.last_frame_at
        fresh = self.connected and age is not None and age < FRESH_SECONDS
        state = "stale" if self.connected and not fresh else self.state
        return {
            "configured": bool(self.url), "state": state, "connected": fresh,
            "updated_at": self.updated_at, "age_seconds": age,
            "sequence": self.sequence, "fps": self.fps if fresh else 0.0,
            "error": self.error,
            "image": (base64.b64encode(self.image).decode("ascii")
                      if self.image and self.sequence != after_sequence else None),
        }

    async def _run(self):
        async with httpx.AsyncClient(timeout=FRESH_SECONDS, trust_env=False) as client:
            while True:
                self.state = "connecting"
                try:
                    async with client.stream("GET", self.url) as response:
                        response.raise_for_status()
                        content_type = response.headers.get("content-type", "").lower()
                        if not content_type.startswith(("multipart/x-mixed-replace", "image/jpeg")):
                            raise ValueError("Not an MJPEG response")
                        frames = latest_jpegs(response.aiter_bytes())
                        deadline = time.monotonic() + FRESH_SECONDS
                        while True:
                            remaining = max(0.001, deadline - time.monotonic())
                            data = await asyncio.wait_for(anext(frames), remaining)
                            if not await asyncio.to_thread(valid_jpeg, data):
                                if time.monotonic() >= deadline:
                                    raise TimeoutError
                                continue
                            now = time.monotonic()
                            interval = None if self.last_frame_at is None else now - self.last_frame_at
                            self.fps = 1 / interval if self.connected and interval and interval > 0 else 0.0
                            self.image = data
                            self.updated_at = time.time()
                            self.last_frame_at = now
                            self.sequence += 1
                            self.connected = True
                            self.state = "online"
                            self.error = None
                            deadline = now + FRESH_SECONDS
                except (httpx.HTTPError, ValueError, TimeoutError, StopAsyncIteration):
                    self.connected = False
                    self.state = "disconnected"
                    self.fps = 0.0
                    # Do not expose camera addresses or credentials in errors.
                    self.error = "รับภาพไม่ได้ · ตรวจสอบ IP Webcam และเครือข่าย · กำลังลองใหม่"
                await asyncio.sleep(RETRY_SECONDS)
