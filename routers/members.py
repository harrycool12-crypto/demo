import re
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from datetime import date, datetime
from dateutil.relativedelta import relativedelta  # type: ignore
import database as db
from config import templates

router = APIRouter(prefix="/members", tags=["members"])

MOBILE_RE = re.compile(r"^[6-9][0-9]{9}$")


def _validate_mobile(mobile: str) -> str | None:
    """Returns error message if invalid, else None."""
    digits = re.sub(r"\D", "", mobile)
    if len(digits) != 10:
        return "Mobile number must be exactly 10 digits."
    if not MOBILE_RE.match(digits):
        return "Mobile number must start with 6, 7, 8, or 9."
    return None

PLAN_MONTHS = {"Monthly": 1, "Quarterly": 3, "Half Yearly": 6, "Annual": 12}


@router.get("")
async def member_list(request: Request, q: str = "", status: str = ""):
    members = db.search_members(q, status)
    return templates.TemplateResponse("members/list.html", {
        "request": request, "members": members, "q": q, "status": status
    })


@router.get("/add")
async def add_member_form(request: Request):
    today     = date.today().isoformat()
    next_rcpt = db.get_next_receipt()
    return templates.TemplateResponse("members/add.html", {
        "request": request, "today": today,
        "next_book": next_rcpt["book_no"], "next_receipt": next_rcpt["receipt_no"],
    })


@router.post("/add")
async def add_member(
    request: Request,
    name: str = Form(...),
    mobile: str = Form(...),
    father_name: str = Form(""),
    address: str = Form(""),
    join_date: str = Form(...),
    plan: str = Form(...),
    amount: float = Form(...),
    start_date: str = Form(...),
    payment_mode: str = Form("Cash"),
    book_no: int = Form(1),
    receipt_no: int = Form(None),
):
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    months = PLAN_MONTHS.get(plan, 1)
    expiry = (start + relativedelta(months=months)).isoformat()

    mobile_err = _validate_mobile(mobile)
    if mobile_err:
        today = date.today().isoformat()
        return templates.TemplateResponse("members/add.html", {
            "request": request, "today": today, "error": mobile_err,
            "form": {"name": name, "mobile": mobile, "father_name": father_name,
                     "address": address, "join_date": join_date, "plan": plan,
                     "amount": amount, "start_date": start_date, "payment_mode": payment_mode}
        })

    mobile_clean = re.sub(r"\D", "", mobile)
    if db.member_exists(name, mobile_clean):
        today     = date.today().isoformat()
        next_rcpt = db.get_next_receipt()
        return templates.TemplateResponse("members/add.html", {
            "request": request, "today": today,
            "error": f"A member named '{name}' with mobile {mobile_clean} already exists.",
            "next_book": next_rcpt["book_no"], "next_receipt": next_rcpt["receipt_no"],
            "form": {"name": name, "mobile": mobile, "father_name": father_name,
                     "address": address, "join_date": join_date, "plan": plan,
                     "amount": amount, "start_date": start_date, "payment_mode": payment_mode}
        })

    try:
        member_id = db.add_member({
            "name": name, "mobile": mobile_clean,
            "father_name": father_name, "address": address,
            "join_date": join_date, "plan": plan,
            "amount": amount, "start_date": start_date, "expiry_date": expiry,
            "payment_mode": payment_mode,
            "book_no": book_no, "receipt_no": receipt_no,
        })
        return RedirectResponse(url=f"/members/{member_id}/view", status_code=303)
    except Exception as e:
        today     = date.today().isoformat()
        next_rcpt = db.get_next_receipt()
        return templates.TemplateResponse("members/add.html", {
            "request": request, "today": today, "error": str(e),
            "next_book": next_rcpt["book_no"], "next_receipt": next_rcpt["receipt_no"],
            "form": {"name": name, "mobile": mobile, "father_name": father_name,
                     "address": address, "join_date": join_date, "plan": plan,
                     "amount": amount, "start_date": start_date, "payment_mode": payment_mode}
        })


@router.get("/{member_id}/view")
async def view_member(request: Request, member_id: int):
    member = db.get_member(member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    payments = db.get_payment_history(member_id)
    return templates.TemplateResponse("members/view.html", {
        "request": request, "member": member, "payments": payments
    })


@router.get("/{member_id}/edit")
async def edit_member_form(request: Request, member_id: int):
    member = db.get_member(member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return templates.TemplateResponse("members/edit.html", {"request": request, "member": member})


@router.post("/{member_id}/edit")
async def edit_member(
    request: Request,
    member_id: int,
    name: str = Form(...),
    mobile: str = Form(...),
    father_name: str = Form(""),
    address: str = Form(""),
):
    mobile_err = _validate_mobile(mobile)
    if mobile_err:
        member = db.get_member(member_id)
        member["mobile"] = mobile  # keep what user typed
        return templates.TemplateResponse("members/edit.html", {
            "request": request, "member": member, "error": mobile_err
        })

    try:
        db.update_member(member_id, {
            "name": name, "mobile": re.sub(r"\D", "", mobile),
            "father_name": father_name, "address": address,
        })
        return RedirectResponse(url=f"/members/{member_id}/view", status_code=303)
    except Exception as e:
        member = db.get_member(member_id)
        return templates.TemplateResponse("members/edit.html", {
            "request": request, "member": member, "error": str(e)
        })


@router.post("/{member_id}/deactivate")
async def deactivate(member_id: int):
    db.deactivate_member(member_id)
    return RedirectResponse(url=f"/members/{member_id}/view", status_code=303)


@router.post("/{member_id}/reactivate")
async def reactivate(member_id: int):
    db.reactivate_member(member_id)
    return RedirectResponse(url=f"/members/{member_id}/view", status_code=303)


@router.get("/api/search")
async def api_search(q: str = ""):
    members = db.search_members(q, "Active")
    return JSONResponse([{
        "member_id": m["member_id"], "name": m["name"], "mobile": m["mobile"],
        "expiry_date": m["expiry_date"], "plan": m["plan"]
    } for m in members])


@router.get("/api/{member_id}")
async def api_get_member(member_id: int):
    m = db.get_member(member_id)
    if not m:
        raise HTTPException(404)
    return JSONResponse(m)
