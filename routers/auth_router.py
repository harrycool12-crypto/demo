from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse

import auth
import database as db
from config import templates

router = APIRouter()


@router.get("/login", include_in_schema=False)
async def login_page(request: Request, error: str = ""):
    return templates.TemplateResponse("login.html", {"request": request, "error": error})


@router.post("/login", include_in_schema=False)
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    user = db.get_user(username.strip())
    if user and auth.verify_password(password, user["password_hash"]):
        token = auth.create_session(username.strip())
        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(
            key="session_token",
            value=token,
            httponly=True,
            samesite="lax",
            max_age=86400 * 30,  # 30 days
        )
        return response
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "Invalid username or password."},
        status_code=401,
    )


@router.get("/logout", include_in_schema=False)
async def logout(request: Request):
    token = request.cookies.get("session_token", "")
    auth.destroy_session(token)
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("session_token")
    return response
