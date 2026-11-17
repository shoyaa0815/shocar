import asyncio
from urllib.parse import urlsplit

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from server.services.auto_drive import HEARTBEAT_SECONDS

router = APIRouter()


@router.websocket('/ws/auto')
async def auto_socket(websocket: WebSocket):
    await websocket.accept()
    origin = websocket.headers.get('origin', '')
    if origin and urlsplit(origin).netloc != websocket.headers.get('host'):
        await websocket.close(code=1008)
        return
    auto = websocket.app.state.auto_drive
    try:
        await websocket.send_json(auto.status(websocket))
        while True:
            action = await asyncio.wait_for(websocket.receive_text(), HEARTBEAT_SECONDS)
            error = None
            if action == 'start':
                error = await auto.enable(websocket)
            elif action == 'stop':
                await auto.emergency_stop()
            elif action == 'heartbeat':
                auto.heartbeat(websocket)
            elif action == 'pause':
                await auto.disable('Dashboard ไม่ได้แสดงอยู่ · ต้องกดเริ่มใหม่', websocket)
            else:
                await websocket.close(code=1008)
                break
            status = auto.status(websocket)
            if error:
                status['error'] = error
            await websocket.send_json(status)
    except TimeoutError:
        await websocket.close(code=1000)
    except KeyError:
        await websocket.close(code=1003)
    except WebSocketDisconnect:
        pass
    finally:
        await auto.disable('Dashboard ขาดการติดต่อ · ต้องกดเริ่มใหม่', websocket)
