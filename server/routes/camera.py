import asyncio
from urllib.parse import urlsplit

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket('/ws/viewer')
async def camera_viewer(websocket: WebSocket):
    await websocket.accept()
    origin = websocket.headers.get('origin', '')
    if origin and urlsplit(origin).netloc != websocket.headers.get('host'):
        await websocket.close(code=1008)
        return
    sequence = vision_sequence = object_sequence = -1
    try:
        while True:
            message = await asyncio.wait_for(websocket.receive_text(), timeout=10)
            if message != 'next':
                await websocket.close(code=1008)
                return
            snapshot = websocket.app.state.camera.snapshot(sequence)
            snapshot['vision'] = websocket.app.state.vision.snapshot(vision_sequence)
            snapshot['objects'] = websocket.app.state.objects.snapshot(object_sequence)
            await websocket.send_json(snapshot)
            sequence = snapshot['sequence']
            vision_sequence = snapshot['vision']['sequence']
            object_sequence = snapshot['objects']['sequence']
            await asyncio.sleep(1 / 15)
    except (WebSocketDisconnect, RuntimeError):
        pass
    except (TimeoutError, KeyError):
        await websocket.close(code=1008)
