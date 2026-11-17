"""One shared depth worker; no robot commands and no queued camera frames."""
import asyncio
import base64
from contextlib import suppress
import logging
import time

import cv2
import numpy as np

from server.ai_brain.depth_model import DepthModel
from server.ai_brain.detector import Detector, render, WATCH_ZONE
from server.ai_brain.range import CameraGeometry
from server.services.camera_stream import FRESH_SECONDS

logger = logging.getLogger(__name__)


def unavailable(state, reason, *, device=None):
    return {'state': state, 'reason': reason, 'blocked': None,
            'sides': {'left': None, 'right': None}, 'obstacle_scores': None,
            'received_at': None, 'sequence': -1,
            'image': None, 'clean_image': None, 'depth_image': None, 'age_seconds': None,
            'processing_ms': None, 'analysis_fps': 0.0, 'boxes': [],
            'objects': [], 'farthest_floor': None,
            'device': device, 'model': 'Depth Anything V2 Small', 'zone': WATCH_ZONE}


def encode(image):
    ok, data = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ok:
        raise ValueError('Cannot encode preview')
    return base64.b64encode(data).decode('ascii')


class VisionPreview:
    def __init__(self, camera, model=None, geometry=None):
        self.camera = camera
        self.model = model if model is not None else DepthModel()
        self.geometry = geometry if geometry is not None else CameraGeometry()
        self.detector = Detector(self.geometry)
        self.task = None
        self.result = unavailable('waiting', 'รอภาพจากกล้อง')
        self.frame_at = None
        self.last_sequence = -1
        self.preview_frame = None

    async def start(self):
        if self.task is None:
            self.task = asyncio.create_task(self._run(), name='depth-preview')

    async def stop(self):
        if self.task is not None:
            self.task.cancel()
            with suppress(asyncio.CancelledError):
                await self.task
            self.task = None
        self.result = unavailable('waiting', 'หยุดวิเคราะห์แล้ว')
        self.frame_at = None
        self.preview_frame = None

    def snapshot(self, after_sequence=-1):
        camera = self.camera
        now = time.monotonic()
        if not camera.connected or camera.last_frame_at is None or now - camera.last_frame_at >= FRESH_SECONDS:
            state = 'stale' if camera.image else 'waiting'
            return unavailable(state, 'ภาพไม่สด · ยังประเมินไม่ได้' if camera.image else 'รอภาพจากกล้อง')
        result = self.result.copy()
        if self.frame_at is not None:
            result['received_at'] = self.frame_at
            result['age_seconds'] = now - self.frame_at
            if result['age_seconds'] >= FRESH_SECONDS:
                return unavailable('stale', 'ผลวิเคราะห์เก่า · ยังประเมินไม่ได้', device=self.model.device)
        if result['sequence'] == after_sequence:
            result['image'] = result['clean_image'] = result['depth_image'] = None
        return result

    def process(self, jpeg):
        started = time.monotonic()
        image = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
        if image is None or min(image.shape[:2]) < 32:
            raise ValueError('Invalid camera image')
        h, w = image.shape[:2]
        scale = min(640 / w, 640 / h, 1)
        image = cv2.resize(image, (max(32, round(w * scale)), max(32, round(h * scale))))
        depth = self.model.predict(image)
        if depth.shape != image.shape[:2]:
            raise ValueError('Depth shape mismatch')
        result = self.detector.analyze(depth)
        original, heatmap = render(image, result)
        return {'state': 'unknown' if result.blocked is None else 'ready',
                'reason': result.reason, 'blocked': result.blocked, 'sides': result.sides,
                'obstacle_scores': result.obstacle_scores,
                'image': encode(original), 'clean_image': encode(image), 'depth_image': encode(heatmap),
                'processing_ms': round((time.monotonic() - started) * 1000, 1),
                'boxes': result.boxes, 'objects': result.objects,
                'farthest_floor': result.farthest_floor,
                'floor_support': round(result.floor_support, 3),
                'frame_size': [image.shape[1], image.shape[0]],
                'device': self.model.device, 'model': 'Depth Anything V2 Small', 'zone': WATCH_ZONE}

    async def _run(self):
        loaded = False
        while True:
            camera = self.camera
            if (not camera.connected or camera.last_frame_at is None
                    or time.monotonic() - camera.last_frame_at >= FRESH_SECONDS):
                self.last_sequence = -1
                self.preview_frame = None
                await asyncio.sleep(.1)
                continue
            if not loaded:
                self.result = unavailable('loading', 'กำลังโหลดโมเดลความลึกในเครื่อง')
                self.frame_at = None
                try:
                    await asyncio.to_thread(self.model.load)
                    loaded = True
                except Exception:
                    logger.exception('Depth model could not be loaded')
                    self.result = unavailable('error', 'โมเดลไม่พร้อม · รัน scripts/download_depth_model.py แล้วเริ่ม server ใหม่')
                    await asyncio.sleep(10)
                    continue
            if camera.sequence == self.last_sequence:
                await asyncio.sleep(.04)
                continue
            jpeg, sequence, frame_at = camera.image, camera.sequence, camera.last_frame_at
            self.last_sequence = sequence
            started = time.monotonic()
            try:
                result = await asyncio.to_thread(self.process, jpeg)
                if (not camera.connected or time.monotonic() - frame_at >= FRESH_SECONDS):
                    self.result = unavailable('stale', 'ประมวลผลไม่ทันภาพสด · ยังประเมินไม่ได้', device=self.model.device)
                    self.frame_at = None
                    self.preview_frame = None
                else:
                    elapsed = time.monotonic() - started
                    result.update(sequence=sequence, age_seconds=elapsed, analysis_fps=round(1 / max(.2, elapsed), 2))
                    self.result, self.frame_at = result, frame_at
                    self.preview_frame = dict(jpeg=jpeg, sequence=sequence, frame_at=frame_at,
                                              floor=result)
            except Exception:
                logger.exception('Depth frame processing failed')
                self.result = unavailable('error', 'วิเคราะห์ภาพไม่สำเร็จ · ยังประเมินไม่ได้', device=self.model.device)
                self.frame_at = None
                self.preview_frame = None
            await asyncio.sleep(max(.02, .2 - (time.monotonic() - started)))
