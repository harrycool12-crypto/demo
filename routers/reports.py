import io
import os
from datetime import date
from fastapi import APIRouter, Request, Query
from fastapi.responses import StreamingResponse, JSONResponse
import database as db
from config import templates

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/active")
async def active_members(request: Request):
    members = db.report_active_members()
    return templates.TemplateResponse("reports/active.html", {"request": request, "members": members})


@router.get("/inactive")
async def inactive_members(request: Request):
    members = db.report_inactive_members()
    return templates.TemplateResponse("reports/inactive.html", {"request": request, "members": members})


@router.get("/expiry")
async def expiry_report(request: Request, days: int = 30):
    members = db.report_expiry(days)
    return templates.TemplateResponse("reports/expiry.html", {
        "request": request, "members": members, "days": days
    })


@router.get("/collection")
async def collection_report(
    request: Request,
    period: str = "monthly",
    year: int = None,
    month: int = None,
):
    today = date.today()
    year  = year  or today.year
    month = month or today.month
    data  = db.report_collection(period, year, month)
    return templates.TemplateResponse("reports/collection.html", {
        "request": request, "data": data, "period": period, "year": year, "month": month,
        "years": list(range(today.year - 3, today.year + 1)),
        "months": [(i, date(2000, i, 1).strftime("%B")) for i in range(1, 13)],
    })


# ─── Excel export helpers ─────────────────────────────────────────────────────

def _excel_response(wb, filename: str):
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/export/active")
async def export_active():
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    members = db.report_active_members()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Active Members"
    headers = ["Member ID", "Name", "Mobile", "Father's Name", "Address", "Join Date", "Plan", "Expiry Date"]
    col_widths = [12, 25, 15, 25, 35, 14, 14, 14]
    for col, (h, w) in enumerate(zip(headers, col_widths), 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1a6b3a")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.column_dimensions[cell.column_letter].width = w
    ws.row_dimensions[1].height = 20
    for m in members:
        ws.append([
            m["member_id"], m["name"], m["mobile"],
            m.get("father_name", "") or "", m.get("address", "") or "",
            m["join_date"], m.get("plan", "") or "", m.get("expiry_date", "") or "",
        ])
    return _excel_response(wb, "active_members.xlsx")


@router.get("/export/inactive")
async def export_inactive():
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    members = db.report_inactive_members()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Inactive Members"
    headers = ["Member ID", "Name", "Mobile", "Father's Name", "Address", "Join Date", "Last Expiry"]
    col_widths = [12, 25, 15, 25, 35, 14, 14]
    for col, (h, w) in enumerate(zip(headers, col_widths), 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1a6b3a")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.column_dimensions[cell.column_letter].width = w
    ws.row_dimensions[1].height = 20
    for m in members:
        ws.append([
            m["member_id"], m["name"], m["mobile"],
            m.get("father_name", "") or "", m.get("address", "") or "",
            m["join_date"], m.get("last_expiry", "") or "",
        ])
    return _excel_response(wb, "inactive_members.xlsx")


@router.get("/export/expiry")
async def export_expiry(days: int = 30):
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    members = db.report_expiry(days)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Expiry Report"
    headers = ["Member ID", "Name", "Mobile", "Plan", "Expiry Date", "Days Remaining"]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1a6b3a")
    for m in members:
        ws.append([m["member_id"], m["name"], m["mobile"], m.get("plan", ""), m["expiry_date"], m["days_remaining"]])
    return _excel_response(wb, "expiry_report.xlsx")


@router.get("/export/collection")
async def export_collection(period: str = "monthly", year: int = None, month: int = None):
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    today = date.today()
    year  = year  or today.year
    month = month or today.month
    data  = db.report_collection(period, year, month)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Collection Report"
    headers = ["Period", "Amount (INR)"]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1a6b3a")
    for row in data["rows"]:
        ws.append([row["label"], row["amount"]])
    ws.append(["TOTAL", data["total"]])
    return _excel_response(wb, "collection_report.xlsx")


@router.get("/export/all-members")
async def export_all_members():
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    members = db.search_members()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "All Members"
    headers = ["Member ID", "Name", "Mobile", "Father's Name", "Address", "Join Date", "Status", "Plan", "Expiry Date"]
    col_widths = [12, 25, 15, 25, 35, 14, 12, 14, 14]
    for col, (h, w) in enumerate(zip(headers, col_widths), 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1a6b3a")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.column_dimensions[cell.column_letter].width = w
    ws.row_dimensions[1].height = 20
    for m in members:
        ws.append([
            m["member_id"], m["name"], m["mobile"],
            m.get("father_name", "") or "", m.get("address", "") or "",
            m["join_date"], m["status"], m.get("plan", "") or "", m.get("expiry_date", "") or "",
        ])
    return _excel_response(wb, "all_members.xlsx")
