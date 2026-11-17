import asyncio
import os

import httpx

COMMANDS = {"forward", "backward", "left", "right", "stop"}


class RobotControl:
    def __init__(self):
        self.url = os.getenv("ROBOT_URL", "").rstrip("/")
        self.online = False
        self.command = "stop"

    async def send(self, client: httpx.AsyncClient, command: str) -> bool:
        if command not in COMMANDS:
            command = "stop"
        self.online = False
        if self.url:
            try:
                response = await asyncio.wait_for(client.post(
                    f"{self.url}/command", json={"command": command},
                ), timeout=0.4)
                response.raise_for_status()
                self.online = response.text == command
            except (httpx.HTTPError, httpx.InvalidURL, ValueError, AttributeError, TimeoutError):
                pass
        self.command = command if self.online else "stop"
        return self.online

    def status(self, release_required: bool) -> dict:
        return {
            "configured": bool(self.url),
            "robot_online": self.online,
            "command": self.command,
            "release_required": release_required,
        }


class RobotCoordinator:
    """Serialize board requests and keep one controller until its final stop."""

    def __init__(self):
        self.owner = None
        self.robot = RobotControl()
        self.lock = asyncio.Lock()

    def claim(self, owner):
        if self.owner is not None or self.lock.locked():
            return False
        self.owner = owner
        self.robot = RobotControl()
        return True

    async def send(self, owner, client, command):
        async with self.lock:
            if self.owner is not owner:
                return False
            return await self.robot.send(client, command)

    async def release(self, owner, client):
        async with self.lock:
            if self.owner is owner:
                try:
                    return await self.robot.send(client, 'stop')
                finally:
                    self.owner = None

    async def emergency_stop(self, client):
        async with self.lock:
            # Revoke first: queued movement from the previous owner is rejected.
            self.owner = None
            return await self.robot.send(client, 'stop')
