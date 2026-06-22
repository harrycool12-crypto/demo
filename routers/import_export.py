import io
import os
from datetime import datetime, date
from fastapi import APIRouter, Request, UploadFile, File
from fastapi.responses import JSONResponse
import database as db
from config import templates

router = APIRouter(prefix="/import-export", tags=["import-export"])

PLAN_MONTHS = {"Monthly": 1, "Quarterly": 3, "Half Yearly": 6, "Annual": 12}


@router.get("")
async def import_export_page(request: Request):
    return templates.TemplateResponse("import_export.html", {"request": request})


def _parse_date(val) -> str:
    if not val:
        return date.today().isoformat()
    if isinstance(val, (date, datetime)):
        return val.strftime("%Y-%m-%d")
    s = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return date.today().isoformat()


def _rows_from_sheet(ws, source: str):
    """Extract header + data rows from various sheet objects."""
    rows = []
    if source == "xlsx":
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            rows.append([str(c) if c is not None else "" for c in row])
    elif source == "ods":
        for row in ws.rows():
            rows.append([str(c.value) if c.value is not None else "" for c in row])
    elif source == "csv":
        rows = ws  # already list-of-lists
    return rows


def _import_rows(all_rows):
    errors = []
    imported = 0
    skipped  = 0

    if not all_rows:
        return {"imported": 0, "skipped": 0, "errors": ["Empty file"]}

    # Detect header
    header = [h.lower().strip() for h in all_rows[0]]
    data_rows = all_rows[1:]

    def col(row, *names):
        for n in names:
            if n in header:
                return row[header.index(n)].strip()
        return ""

    from dateutil.relativedelta import relativedelta  # type: ignore

    for i, row in enumerate(data_rows, 2):
        if len(row) < 2:
            continue
        name   = col(row, "name", "member name", "fullname")
        mobile = col(row, "mobile", "phone", "mobile number", "contact")
        if not name or not mobile:
            errors.append(f"Row {i}: Missing name or mobile")
            skipped += 1
            continue

        # Check duplicate
        existing = db.search_members(mobile)
        if any(m["mobile"] == mobile for m in existing):
            errors.append(f"Row {i}: Duplicate mobile {mobile} — skipped")
            skipped += 1
            continue

        join_date_raw = col(row, "join date", "joindate", "joining date", "date")
        join_date     = _parse_date(join_date_raw) if join_date_raw else date.today().isoformat()

        plan_raw    = col(row, "plan", "membership", "membership plan")
        plan        = plan_raw if plan_raw in PLAN_MONTHS else "Monthly"
        amount_raw  = col(row, "amount", "fee", "fees")
        try:
            amount  = float(amount_raw) if amount_raw else 0.0
        except ValueError:
            amount  = 0.0

        start_raw   = col(row, "start date", "start", "startdate")
        start_date  = _parse_date(start_raw) if start_raw else join_date

        months      = PLAN_MONTHS.get(plan, 1)
        start_dt    = datetime.strptime(start_date, "%Y-%m-%d").date()
        expiry_dt   = start_dt + relativedelta(months=months)
        expiry_date = expiry_dt.isoformat()

        try:
            db.add_member({
                "name": name, "mobile": mobile,
                "father_name": col(row, "father name", "father", "fathername"),
                "address": col(row, "address"),
                "join_date": join_date, "plan": plan, "amount": amount,
                "start_date": start_date, "expiry_date": expiry_date,
                "payment_mode": "Cash",
            })
            imported += 1
        except Exception as e:
            errors.append(f"Row {i}: {e}")
            skipped += 1

    return {"imported": imported, "skipped": skipped, "errors": errors[:50]}


@router.post("/import")
async def import_file(file: UploadFile = File(...)):
    content  = await file.read()
    filename = file.filename.lower()

    try:
        if filename.endswith(".xlsx"):
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
            ws = wb.active
            rows = []
            for row in ws.iter_rows(values_only=True):
                rows.append([str(c) if c is not None else "" for c in row])
            result = _import_rows(rows)

        elif filename.endswith(".ods"):
            from odf.opendocument import load as ods_load
            from odf.table import Table, TableRow, TableCell
            from odf.text import P
            doc = ods_load(io.BytesIO(content))
            sheet = doc.spreadsheet.getElementsByType(Table)[0]
            rows = []
            for tr in sheet.getElementsByType(TableRow):
                row = []
                for tc in tr.getElementsByType(TableCell):
                    ps = tc.getElementsByType(P)
                    row.append(str(ps[0]) if ps else "")
                rows.append(row)
            result = _import_rows(rows)

        elif filename.endswith(".csv"):
            import csv
            text = content.decode("utf-8-sig")
            reader = csv.reader(io.StringIO(text))
            rows = list(reader)
            result = _import_rows(rows)

        else:
            return JSONResponse({"error": "Unsupported file type. Use XLSX, ODS, or CSV."}, status_code=400)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    return JSONResponse(result)
