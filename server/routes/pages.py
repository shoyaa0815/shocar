from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home():
    return "<!doctype html><html><head><title>Shocar</title></head><body></body></html>"


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    return (Path(__file__).resolve().parents[1] / "pages" / "dashboard.html").read_text(encoding="utf-8")


@router.get("/remote", response_class=HTMLResponse)
async def remote_page():
    return (Path(__file__).resolve().parents[1] / "pages" / "remote.html").read_text(encoding="utf-8")

