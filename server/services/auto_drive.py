import asyncio
from contextlib import suppress
import logging
import os
import time

import httpx

from server.ai_brain.navigation import DEFAULT_SPIN_SECONDS, Navigation
from server.services.camera_stream import FRESH_SECONDS

logger = logging.getLogger(__name__)
HEARTBEAT_SECONDS = 0.6


class AutoDrive:
    def __init__(self, camera, vision, control):
        self.camera, self.vision, self.control = camera, vision, control
        self.navigation = Navigation(float(os.getenv('AUTO_SPIN_SECONDS', str(DEFAULT_SPIN_SECONDS))))
        self.owner = None
        self.enabled = False
        self.reason = 'ปิดโหมดอัตโนมัติ'
        self.last_heartbeat = 0
        self.lock = asyncio.Lock()
        self.client = None
        self.task = None

    async def start(self):
        if self.task is None:
            self.client = httpx.AsyncClient(timeout=0.4, trust_env=False)
            self.task = asyncio.create_task(self._run(), name='auto-drive')

    async def stop(self):
        if self.task is not None:
            self.task.cancel()
            with suppress(asyncio.CancelledError):
                await self.task
            self.task = None
        if self.client is not None:
            await self.disable('Server หยุดทำงาน')
            await self.client.aclose()
            self.client = None

    def observation(self):
        result = self.vision.snapshot()
        now = time.monotonic()
        fresh = (self.camera.connected and self.camera.last_frame_at is not None
                 and now - self.camera.last_frame_at < FRESH_SECONDS
                 and result.get('state') in ('ready', 'unknown')
                 and result.get('age_seconds') is not None
                 and 0 <= result['age_seconds'] < FRESH_SECONDS
                 and result.get('sequence', -1) >= 0)
        return result, fresh

    def status(self, viewer):
        _, fresh = self.observation()
        robot = self.control.robot
        return {
            'enabled': self.enabled,
            'is_owner': self.owner is viewer,
            'can_start': bool(robot.url) and fresh and self.control.owner is None,
            'configured': bool(robot.url),
            'robot_online': robot.online,
            'command': robot.command,
            'reason': self.reason,
            'search_phase': self.navigation.search_phase,
            'busy': self.control.owner is not None,
        }

    async def enable(self, owner):
        async with self.lock:
            if self.enabled:
                return 'โหมดอัตโนมัติถูกใช้งานอยู่'
            _, fresh = self.observation()
            if not fresh:
                return 'ต้องมีภาพและผลวิเคราะห์สดก่อนเริ่ม'
            if not self.control.robot.url:
                return 'ยังไม่ตั้งค่า ROBOT_URL'
            if not self.control.claim(owner):
                return 'มีผู้ควบคุมรถอยู่แล้ว'
            if not await self.control.send(owner, self.client, 'stop'):
                await self.control.release(owner, self.client)
                self.reason = 'บอร์ดไม่ยืนยันหยุด · เริ่มโหมดไม่ได้'
                return self.reason
            observation, fresh = self.observation()
            if not fresh:
                await self.control.release(owner, self.client)
                return 'ผลวิเคราะห์เก่าระหว่างเริ่ม · กรุณาลองใหม่'
            self.navigation.reset()
            self.navigation.sequence = observation['sequence']
            self.owner = owner
            self.enabled = True
            self.last_heartbeat = time.monotonic()
            self.reason = 'เปิดโหมด · รอยืนยันทิศทาง 3 เฟรมใหม่'
            return None

    def heartbeat(self, owner):
        if self.owner is owner:
            self.last_heartbeat = time.monotonic()

    async def _disable(self, reason):
        owner = self.owner
        self.enabled = False
        self.owner = None
        self.navigation.reset()
        self.reason = reason
        if owner is not None:
            confirmed = await self.control.release(owner, self.client)
            if confirmed is False:
                self.reason += ' · ส่งหยุดไม่ได้ ยังไม่ยืนยันว่ารถหยุดแล้ว'

    async def disable(self, reason, owner=None):
        async with self.lock:
            if owner is None or self.owner is owner:
                await self._disable(reason)

    async def emergency_stop(self):
        async with self.lock:
            await self._disable('กดหยุด · ปิดโหมดอัตโนมัติ')
            success = await self.control.emergency_stop(self.client)
            if not success:
                self.reason = 'ส่งหยุดไม่ได้ · ยังไม่ยืนยันว่ารถหยุดแล้ว'

    async def tick(self):
        async with self.lock:
            if not self.enabled:
                return
            if time.monotonic() - self.last_heartbeat >= HEARTBEAT_SECONDS:
                await self._disable('Dashboard ขาดการติดต่อ · ต้องกดเริ่มใหม่')
                return
            result, fresh = self.observation()
            if not fresh or self.control.owner is not self.owner:
                await self._disable('ภาพ/ผลวิเคราะห์ไม่พร้อม · ต้องกดเริ่มใหม่')
                return
            command = self.navigation.decide(
                result.get('sides', {}), result['sequence'],
                scores=result.get('obstacle_scores'), now=time.monotonic(),
                received_at=result.get('received_at'), fresh_seconds=FRESH_SECONDS)
            if self.navigation.failure:
                await self._disable(self.navigation.failure)
                return
            if not await self.control.send(self.owner, self.client, command):
                await self._disable('บอร์ดไม่ตอบรับ · ต้องกดเริ่มใหม่')
                return
            if command == 'stop':
                self.navigation.acknowledge_stop(time.monotonic())
            if self.navigation.search_phase is not None:
                self.reason = self.navigation.search_reason
                return
            sides = result.get('sides', {})
            if command == 'stop':
                if any(type(sides.get(side)) is not bool for side in ('left', 'right')):
                    self.reason = ('เหลืองทั้งสองข้าง · หยุดรอครบ 3 วินาทีก่อนหาทาง'
                                   if self.navigation.yellow_since is not None else
                                   'หยุดรอ · ยังประเมินไม่ได้')
                elif sides.get('left') and sides.get('right'):
                    self.reason = 'หยุดรอ · พบสิ่งกีดขวางทั้งสองด้าน'
                else:
                    self.reason = 'หยุดรอ · ยืนยันทิศทาง 3 เฟรมใหม่'
            else:
                self.reason = {'forward': 'เดินหน้า · ยังไม่พบสิ่งกีดขวางในกรอบ',
                               'left': 'เลี้ยวซ้าย · พบสิ่งกีดขวางด้านขวา',
                               'right': 'เลี้ยวขวา · พบสิ่งกีดขวางด้านซ้าย'}[command]

    async def _run(self):
        try:
            while True:
                try:
                    await self.tick()
                except Exception:
                    logger.exception('Automatic driving failed')
                    await self.disable('ระบบขับผิดพลาด · ต้องกดเริ่มใหม่')
                await asyncio.sleep(0.1)
        finally:
            await self.disable('ระบบขับหยุดทำงาน')
