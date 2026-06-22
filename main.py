import socket
import threading
import time
import webbrowser
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from database import init_db, get_dashboard_stats
from config import templates
from routers import members, payments, reports, import_export, backup
from routers.auth_router import router as auth_router
import auth

# Paths that don't require authentication
_PUBLIC_PATHS = {"/login", "/logout"}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        # Allow static files and public pages through
        if path.startswith("/static") or path in _PUBLIC_PATHS:
            return await call_next(request)
        token = request.cookies.get("session_token", "")
        if not auth.get_session_user(token):
            return RedirectResponse(url="/login", status_code=303)
        return await call_next(request)


def _free_port(preferred: int = 8000) -> int:
    for port in range(preferred, preferred + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No free port found in range 8000-8019")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Fit Zone Gym Management System",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(AuthMiddleware)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth_router)
app.include_router(members.router)
app.include_router(payments.router)
app.include_router(reports.router)
app.include_router(import_export.router)
app.include_router(backup.router)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/dashboard")


@app.get("/dashboard")
async def dashboard(request: Request):
    stats = get_dashboard_stats()
    return templates.TemplateResponse("dashboard.html", {"request": request, "stats": stats})


if __name__ == "__main__":
    port = _free_port(8000)
    url  = f"http://127.0.0.1:{port}"

    if port != 8000:
        print(f"  Port 8000 busy — using port {port} instead.")

    def _open_browser():
        time.sleep(1.5)
        webbrowser.open(url)

    t = threading.Thread(target=_open_browser, daemon=True)
    t.start()

    print(f"  Opening {url}")
    uvicorn.run(app, host="127.0.0.1", port=port)
