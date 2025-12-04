# main.py
import os
import logging
from datetime import datetime

 
import pandas as pd
from io import BytesIO
 
from fastapi import  File, UploadFile, HTTPException,APIRouter,Depends

from models import Employee, ResourceRequest, User
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from utils.security import get_current_user

from utils.file_upload_utils import log_upload_action,detect_encoding,convert_dates_for_mongo,sync_employees_with_db,sync_rr_with_db,read_csv_file
 
# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RRProcessor")
 
# -------------------------------------------------------------------
# Custom Exceptions
# -------------------------------------------------------------------
class FileFormatException(HTTPException):
    def __init__(self, detail="Invalid file format"):
        super().__init__(status_code=400, detail=detail)
 
class ValidationException(HTTPException):
    def __init__(self, detail):
        super().__init__(status_code=422, detail={"validation_error": detail})
 
class DatabaseException(HTTPException):
    def __init__(self, detail="Database operation failed"):
        super().__init__(status_code=500, detail=detail)
 
class ReportProcessingException(HTTPException):
    def __init__(self, detail):
        super().__init__(status_code=400, detail=detail)
 
file_upload_router = APIRouter(prefix="/api/upload")
 


# -------------------------------------------------------------------
# API Endpoints
# -------------------------------------------------------------------
@file_upload_router.post("/upload/employees")
async def upload_career_velocity(file: UploadFile = File(...),current_user=Depends(get_current_user)):
    if current_user["role"] !="Admin":
        return HTTPException(status_code=409,detail="Not Authorized")
    content = await file.read()
    if not file.filename.lower().endswith((".xlsx", ".xls", ".csv")):
        raise FileFormatException("Only .xlsx, .xls, or .csv files allowed")
 
    # Load file
    try:
        df = (pd.read_csv(BytesIO(content), encoding=detect_encoding(content), dtype=str, engine="python", on_bad_lines="skip")
              if file.filename.endswith(".csv") else pd.read_excel(BytesIO(content)))
        df = df.dropna(how="all")
    except Exception as e:
        raise ReportProcessingException(f"Failed to read file: {e}")
 
    required = ["Employee ID", "Employee Name", "Designation", "Band", "City", "Type"]
    if missing := [c for c in required if c not in df.columns]:
        raise ValidationException(f"Missing columns: {missing}")
 
    valid_emps, valid_users, errors = [], [], []
    for idx, row in df.iterrows():
        row_dict = {k: None if pd.isna(v) else str(v).strip() for k, v in row.to_dict().items()}
        try:
            emp = Employee(**row_dict)
            user = User(employee_id=str(emp.employee_id), role=emp.type)
            valid_emps.append(emp)
            valid_users.append(user)
        except Exception as e:
            errors.append({"row": idx + 2, "error": str(e)})
 
    await log_upload_action("employees", file.filename,
                            "CSV" if file.filename.endswith(".csv") else "Excel",
                            "API User", len(df), len(valid_emps), len(errors), errors[:5])
 
    if not valid_emps:
        return {"message": "No valid employees found", "errors_sample": errors[:5]}
 
    result = await sync_employees_with_db(valid_emps, valid_users)
    return {
        "message": "Career Velocity processed successfully",
        "processed": len(valid_emps),
        "failed": len(errors),
        "errors_sample": errors[:5],
        "sync": result
    }
 

@file_upload_router.post("/upload/rr-report")
async def upload_rr_report(file: UploadFile = File(...),current_user=Depends(get_current_user)):
    if current_user["role"] != "HM":
        return HTTPException(status_code=409,detail="Not Authorized")
    content = await file.read()
    if not file.filename.lower().endswith((".xlsx", ".xls", ".csv")):
        raise FileFormatException("Only Excel/CSV files allowed")
 
    try:
        # df = (pd.read_csv(BytesIO(content), skiprows=6, encoding=detect_encoding(content),
        #                   dtype=str, engine="python", on_bad_lines="skip")
        #       if file.filename.endswith(".csv") else pd.read_excel(BytesIO(content), skiprows=6, dtype=str))
        # df = df.dropna(how="all")
        if file.filename.lower().endswith(".csv"):
            df = read_csv_file(content)

            if df is None or df.empty:
                raise ReportProcessingException("CSV file contains no valid rows")

        # ------------------------ EXCEL HANDLING (Pandas) ------------------------
        else:
            df = pd.read_excel(BytesIO(content), skiprows=6, dtype=str)
            df = df.dropna(how="all")
    except Exception as e:
        raise ReportProcessingException(f"Failed to read RR report: {e}")
 
    if "Resource Request ID" not in df.columns:
        raise ValidationException("Column 'Resource Request ID' is required")
 
    valid_rrs, errors = [], []
    for idx, row in df.iterrows():
        rr_id = row.get("Resource Request ID")
        if not rr_id or pd.isna(rr_id):
            continue
        row_dict = {k: None if pd.isna(v) else v for k, v in row.to_dict().items()}
        row_dict["rr_status"] = True
        try:
            valid_rrs.append(ResourceRequest(**row_dict))
        except Exception as e:
            errors.append({"row": idx + 8, "rr_id": str(rr_id), "error": str(e)})
 
    await log_upload_action("rr_report", file.filename,
                            "CSV" if file.filename.endswith(".csv") else "Excel",
                            "API User", len(df), len(valid_rrs), len(errors), errors[:5])
 
    if not valid_rrs:
        return {"message": "No valid RRs found", "errors_sample": errors[:5]}
 
    await sync_rr_with_db(valid_rrs)
    return {
        "message": "RR Report processed successfully",
        "valid_requests": len(valid_rrs),
        "failed": len(errors),
        "errors_sample": errors[:5]
    }

# -------------------------------------------------------------------
# Auto-processing (watch folder)
# -------------------------------------------------------------------
UPLOAD_FOLDER = "updated"
PROCESSED_FOLDER = "processed"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)
 
async def auto_rr():
    files = [f for f in os.listdir(UPLOAD_FOLDER)
             if f.lower().endswith((".xlsx", ".xls", ".csv"))]
    if not files:
        return
 
    latest = sorted(files)[-1]
    src = os.path.join(UPLOAD_FOLDER, latest)
    dst = os.path.join(PROCESSED_FOLDER, f"{datetime.now():%Y%m%d_%H%M%S}_{latest}")
 
    try:
        with open(src, "rb") as f:
            fake_file = UploadFile(filename=latest, file=BytesIO(f.read()))
        await upload_rr_report(fake_file,{"role":"HM"})
        os.rename(src, dst)
        logger.info(f"Auto-processed RR: {latest} → processed/")
    except Exception as e:
        logger.error(f"Auto RR failed for {latest}: {e}")
 
scheduler = AsyncIOScheduler()
scheduler.add_job(auto_rr, "cron", minute="*", id="rr_watcher")
scheduler.start()
 
 
scheduler = AsyncIOScheduler()
scheduler.add_job(auto_rr, "cron", minute="*", id="rr_watcher")
scheduler.start()
print("Scheduler started")
 