"""Shared object worker with frame-paired boxes; never an input to AutoDrive."""
import asyncio
from contextlib import suppress
import logging
import time

import cv2
import numpy as np

from server.ai_brain.object_model import ObjectModel
from server.ai_brain.range import CameraGeometry
from server.services.camera_stream import FRESH_SECONDS
from server.services.vision_preview import encode

logger = logging.getLogger(__name__)


def unavailable(state, reason):
    return dict(state=state, reason=reason, sequence=-1, age_seconds=None,
                image=None, frame_size=None, objects=[], farthest_floor=None,
                processing_ms=None, depth_overlay=None)


class ObjectPreview:
    def __init__(self, camera, vision, model=None, geometry=None):
        self.camera, self.vision = camera, vision
        self.model = model if model is not None else ObjectModel()
        self.geometry = geometry if geometry is not None else CameraGeometry()
        self.task = None
        self.frame_at = None
        self.last_sequence = -1
        self.result = unavailable('waiting', 'รอภาพจากกล้อง')

    async def start(self):
        if self.task is None:
            self.task = asyncio.create_task(self._run(), name='object-preview')

    async def stop(self):
        if self.task is not None:
            self.task.cancel()
            with suppress(asyncio.CancelledError):
                await self.task
            self.task = None
        self.result = unavailable('waiting', 'หยุดตรวจจับแล้ว')
        self.frame_at = None
        self.last_sequence = -1

    def snapshot(self, after_sequence=-1):
        now = time.monotonic()
        if (not self.camera.connected or self.camera.last_frame_at is None
                or now - self.camera.last_frame_at >= FRESH_SECONDS):
            return unavailable('stale', 'ภาพไม่สด · รอภาพจากกล้อง')
        result = self.result.copy()
        if self.frame_at is not None:
            result['age_seconds'] = now - self.frame_at
            if result['age_seconds'] >= FRESH_SECONDS:
                return unavailable('stale', 'ผลตรวจจับเก่า · กำลังรอผลใหม่')
        if result['sequence'] == after_sequence:
            result['image'] = None
        return result

    def process(self, jpeg, floor=None):
        started = time.monotonic()
        image = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
        if image is None or min(image.shape[:2]) < 32:
            raise ValueError('Invalid camera image')
        # Keep more source detail than the depth preview. Model output boxes
        # use these image coordinates, as does the JPEG returned to the viewer.
        h, w = image.shape[:2]
        scale = min(1280 / w, 1280 / h, 1)
        image = cv2.resize(image, (round(w * scale), round(h * scale)))
        h, w = image.shape[:2]
        boxes = self.model.predict(image)
        objects = self.geometry.objects(boxes, (h, w), estimate=bool(floor and floor['floor_support'] > 0))
        farthest = None
        depth_overlay = None
        if floor:
            fw, fh = floor['frame_size']
            depth_overlay = dict(
                boxes=[[x * w / fw, y * h / fh, bw * w / fw, bh * h / fh]
                       for x, y, bw, bh in floor.get('boxes', [])],
                sides=floor.get('sides', {'left': None, 'right': None}),
                zone=floor.get('zone', [0, .5, 1, .95]),
            )
        if floor and floor['farthest_floor']:
            fw, fh = floor['frame_size']
            point = floor['farthest_floor']['point']
            farthest = dict(point=[point[0] * w / fw, point[1] * h / fh],
                            distance_cm=floor['farthest_floor']['distance_cm'])
        return dict(state='ready', reason='ตรวจจับสิ่งของโดยไม่กรองระยะ',
                    image=encode(image), frame_size=[w, h], objects=objects,
                    farthest_floor=farthest,
                    depth_overlay=depth_overlay,
                    processing_ms=round((time.monotonic() - started) * 1000, 1))

    async def _run(self):
        loaded = False
        while True:
            camera = self.camera
            if (not camera.connected or camera.last_frame_at is None
                    or time.monotonic() - camera.last_frame_at >= FRESH_SECONDS):
                self.last_sequence = -1
                self.result = unavailable('waiting', 'รอภาพสดจากกล้อง')
                self.frame_at = None
                await asyncio.sleep(.1)
                continue
            if not loaded:
                self.result = unavailable('loading', 'กำลังโหลดตัวตรวจจับสิ่งของในเครื่อง')
                self.frame_at = None
                try:
                    await asyncio.to_thread(self.model.load)
                    loaded = True
                except Exception:
                    logger.exception('Object model could not be loaded')
                    self.result = unavailable('error', 'ตัวตรวจจับไม่พร้อม · รัน scripts/download_object_model.py แล้วเริ่ม server ใหม่')
                    await asyncio.sleep(10)
                    continue
            jpeg, sequence, frame_at = camera.image, camera.sequence, camera.last_frame_at
            floor = None
            # Reuse a fresh depth source when available, so optional floor lines
            # and boxes refer to exactly the same frame. Depth is optional:
            # missing/slow/failed depth still permits detection on raw frames.
            paired = self.vision.preview_frame
            if (paired and paired['sequence'] > self.last_sequence
                    and time.monotonic() - paired['frame_at'] < FRESH_SECONDS):
                jpeg, sequence, frame_at = paired['jpeg'], paired['sequence'], paired['frame_at']
                floor = paired['floor']
            if sequence == self.last_sequence:
                await asyncio.sleep(.04)
                continue
            self.last_sequence = sequence
            started = time.monotonic()
            try:
                result = await asyncio.to_thread(self.process, jpeg, floor)
                if not camera.connected or time.monotonic() - frame_at >= FRESH_SECONDS:
                    self.result = unavailable('stale', 'ประมวลผลไม่ทันภาพสด · กำลังรอผลใหม่')
                    self.frame_at = None
                else:
                    result.update(sequence=sequence)
                    self.result, self.frame_at = result, frame_at
            except Exception:
                logger.exception('Object frame processing failed')
                self.result = unavailable('error', 'ตรวจจับสิ่งของไม่สำเร็จ · กำลังลองใหม่')
                self.frame_at = None
            await asyncio.sleep(max(.02, .5 - (time.monotonic() - started)))
