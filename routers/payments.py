from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from datetime import date, timedelta
import database as db
from config import templates

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/api/next-receipt")
async def api_next_receipt():
    return JSONResponse(db.get_next_receipt())


@router.get("/renew")
async def renew_form(request: Request, member_id: int = None):
    member = None
    if member_id:
        member = db.get_member(member_id)
    today      = date.today().isoformat()
    next_rcpt  = db.get_next_receipt()
    return templates.TemplateResponse("payments/renew.html", {
        "request": request, "member": member, "today": today,
        "next_book": next_rcpt["book_no"], "next_receipt": next_rcpt["receipt_no"],
    })


@router.post("/renew")
async def renew(
    request: Request,
    member_id: int = Form(...),
    plan: str = Form(...),
    amount: float = Form(...),
    start_date: str = Form(...),
    payment_mode: str = Form("Cash"),
    book_no: int = Form(1),
    receipt_no: int = Form(None),
):
    try:
        expiry = db.renew_membership(member_id, {
            "plan": plan, "amount": amount,
            "start_date": start_date, "payment_mode": payment_mode,
            "book_no": book_no, "receipt_no": receipt_no,
        })
        return RedirectResponse(url=f"/members/{member_id}/view?renewed=1&expiry={expiry}", status_code=303)
    except Exception as e:
        member     = db.get_member(member_id)
        today      = date.today().isoformat()
        next_rcpt  = db.get_next_receipt()
        return templates.TemplateResponse("payments/renew.html", {
            "request": request, "member": member, "today": today, "error": str(e),
            "next_book": next_rcpt["book_no"], "next_receipt": next_rcpt["receipt_no"],
        })


@router.get("/history")
async def payment_history(
    request: Request,
    member_id: int = None,
    month: str = "",
    start_date: str = "",
    end_date: str = "",
):
    payments = db.get_payment_history(
        member_id,
        month or None,
        start_date or None,
        end_date or None,
    )
    member = db.get_member(member_id) if member_id else None

    # Build last 13 months for the month dropdown
    months = []
    today  = date.today()
    from datetime import datetime
    for i in range(13):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        months.append({"value": f"{y}-{m:02d}", "label": datetime(y, m, 1).strftime("%b %Y")})

    total = sum(p["amount"] for p in payments)
    return templates.TemplateResponse("payments/history.html", {
        "request": request, "payments": payments, "member": member,
        "months": months, "selected_month": month,
        "start_date": start_date, "end_date": end_date,
        "total": total,
    })


@router.get("/api/history/{member_id}")
async def api_history(member_id: int):
    return JSONResponse(db.get_payment_history(member_id))
