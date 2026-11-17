from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

from server.routes import auto_drive, camera as camera_routes, pages, remote
from server.ai_brain.range import CameraGeometry
from server.services.auto_drive import AutoDrive
from server.services.robot_control import RobotCoordinator
from server.services.camera_stream import CameraStream
from server.services.vision_preview import VisionPreview
from server.services.object_preview import ObjectPreview

DOTENV_PATH = Path(__file__).resolve().parents[1] / ".env"


def create_app() -> FastAPI:
    load_dotenv(DOTENV_PATH, override=False)
    camera = CameraStream()
    vision = VisionPreview(camera, geometry=CameraGeometry.from_env())
    objects = ObjectPreview(camera, vision, geometry=vision.geometry)
    robot = RobotCoordinator()
    auto = AutoDrive(camera, vision, robot)

    @asynccontextmanager
    async def lifespan(app):
        await camera.start()
        await vision.start()
        await objects.start()
        await auto.start()
        try:
            yield
        finally:
            await auto.stop()
            await objects.stop()
            await vision.stop()
            await camera.stop()

    app = FastAPI(lifespan=lifespan)
    app.state.camera = camera
    app.state.vision = vision
    app.state.objects = objects
    app.state.remote = None
    app.state.robot = robot
    app.state.auto_drive = auto
    app.include_router(pages.router)
    app.include_router(camera_routes.router)
    app.include_router(remote.router)
    app.include_router(auto_drive.router)
    return app
