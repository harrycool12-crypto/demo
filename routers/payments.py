from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from datetime import date
import database as db
from config import templates

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/renew")
async def renew_form(request: Request, member_id: int = None):
    member = None
    if member_id:
        member = db.get_member(member_id)
    today = date.today().isoformat()
    return templates.TemplateResponse("payments/renew.html", {
        "request": request, "member": member, "today": today
    })


@router.post("/renew")
async def renew(
    request: Request,
    member_id: int = Form(...),
    plan: str = Form(...),
    amount: float = Form(...),
    start_date: str = Form(...),
    payment_mode: str = Form("Cash"),
):
    try:
        expiry = db.renew_membership(member_id, {
            "plan": plan, "amount": amount,
            "start_date": start_date, "payment_mode": payment_mode,
        })
        return RedirectResponse(url=f"/members/{member_id}/view?renewed=1&expiry={expiry}", status_code=303)
    except Exception as e:
        member = db.get_member(member_id)
        today  = date.today().isoformat()
        return templates.TemplateResponse("payments/renew.html", {
            "request": request, "member": member, "today": today, "error": str(e)
        })


@router.get("/history")
async def payment_history(request: Request, member_id: int = None):
    payments = db.get_payment_history(member_id)
    member   = db.get_member(member_id) if member_id else None
    return templates.TemplateResponse("payments/history.html", {
        "request": request, "payments": payments, "member": member
    })


@router.get("/api/history/{member_id}")
async def api_history(member_id: int):
    return JSONResponse(db.get_payment_history(member_id))
