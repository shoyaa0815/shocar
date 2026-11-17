import asyncio
from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from server.services.robot_control import COMMANDS

router = APIRouter()


@router.websocket("/ws/remote")
async def remote_socket(websocket: WebSocket):
    await websocket.accept()
    origin = websocket.headers.get("origin", "")
    if (origin and urlsplit(origin).netloc != websocket.headers.get("host")) or websocket.app.state.remote is not None:
        await websocket.close(code=1008)
        return

    control = websocket.app.state.robot
    if not control.claim(websocket):
        await websocket.close(code=1008)
        return
    websocket.app.state.remote = websocket
    robot = control.robot
    try:
        async with httpx.AsyncClient(timeout=0.4, trust_env=False) as client:
            try:
                released = await control.send(websocket, client, "stop")
                await websocket.send_json(robot.status(not released))
                while True:
                    try:
                        command = await asyncio.wait_for(websocket.receive_text(), timeout=0.6)
                    except asyncio.TimeoutError:
                        await websocket.close(code=1000)
                        break
                    except KeyError:
                        await websocket.close(code=1003)
                        break
                    if command not in COMMANDS:
                        await websocket.close(code=1008)
                        break
                    if control.owner is not websocket:
                        await websocket.close(code=1008)
                        break
                    if not released and command != "stop":
                        await control.send(websocket, client, "stop")
                    else:
                        success = await control.send(websocket, client, command)
                        released = success and (released or command == "stop")
                    await websocket.send_json(robot.status(not released))
            except WebSocketDisconnect:
                pass
            finally:
                await control.release(websocket, client)
    finally:
        websocket.app.state.remote = None

