from pydantic import BaseModel, field_validator, model_validator, Field, AwareDatetime
import re
from typing import List, Optional,Literal
from datetime import datetime,date,timedelta
from enum import Enum
import uuid
from bson import ObjectId
from pydantic import BaseModel, field_validator, Field, AwareDatetime
import re
from typing import List, Optional,Literal
from datetime import date, datetime, timezone
 
 
class UserRole(str, Enum):
    ADMIN = "Admin"
    TP_MANAGER = "TP Manager"
    WFM = "WFM"
    HM = "HM"
    EMPLOYEE_TP = "TP"
    EMPLOYEE_NON_TP = "Non TP"
 
class ApplicationStatus(str, Enum):
    DRAFT = "Draft"
    SUBMITTED = "Submitted"
    SHORTLISTED = "Shortlisted"
    INTERVIEW = "Interview"
    SELECTED = "Selected"
    REJECTED = "Rejected"
    ALLOCATED = "Allocated"
    WITHDRAWN = "Withdrawn"
 
class Employee(BaseModel):
    employee_id: int = Field(..., alias="Employee ID")
    employee_name: str = Field(..., alias="Employee Name")
    employment_type: str = Field(..., alias="Employment Type")
    designation: str = Field(..., alias="Designation")
    band: str = Field(..., alias="Band")
    city: str = Field(..., alias="City")
    location_description: str = Field(..., alias="Location Description")
    primary_technology: str = Field(..., alias="Primary Technology")
    secondary_technology: Optional[str] = Field(None, alias="Secondary Technology")
    detailed_skills: List[str] = Field(default_factory=list, alias="Detailed Skill Set (List of top skills on profile)")
    type: Literal["TP", "Non TP"] = Field(..., alias="Type")
    resume_text: Optional[str] = Field(None)
   
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
 
    # -------------------------------------------------
    # 1. Normalize Type (TP / Non TP) – case insensitive
    # -------------------------------------------------
    @field_validator("type", mode="before")
    @classmethod
    def normalize_type(cls, v):
        if not v:
            return "Non TP"
        val = str(v).strip().upper()
        return "TP" if val == "TP" else "Non TP"
 
    # -------------------------------------------------
    # 2. Accept ALL real bands seen in your data:
    #     A0–A9, B1–B9, C1–C9, D1–D9
    #     T1–T9, E1–E9, P1–P9
    # -------------------------------------------------
    @field_validator("band", mode="before")
    @classmethod
    def normalize_band(cls, v):
        if not v or str(v).strip() == "":
            return "A0"
 
        value = str(v).strip().upper()
 
        # All valid patterns
        if re.match(r"^[A-D][0-9]$", value):    # A0–D9
            return value
        if re.match(r"^[TEP][1-9]$", value):    # T1–T9, E1–E9, P1–P9
            return value
 
        raise ValueError(f"Invalid band format: '{v}' → '{value}'")
 
    # -------------------------------------------------
    # 3. Handle "Not Available" gracefully
    # -------------------------------------------------
    @field_validator("primary_technology", "secondary_technology", mode="before")
    @classmethod
    def handle_not_available(cls, v, info):
        if not v or str(v or "").strip().upper() in ("NOT AVAILABLE", "NA", "NULL", ""):
            return "" if info.field_name == "primary_technology" else None
        return str(v).strip()
 
    # -------------------------------------------------
    # 4. Split skills (handles commas, question marks, etc.)
    # -------------------------------------------------
    @field_validator("detailed_skills", mode="before")
    @classmethod
    def split_detailed_skills(cls, v):
        if not v or str(v).strip().upper() in ("NA", "NOT AVAILABLE", "NULL", ""):
            return []
        skills = [s.strip() for s in re.split(r'[,?]', str(v)) if s.strip()]
        return skills
 
    class Config:
        populate_by_name = True
        extra = "ignore"
 
class Job(BaseModel):
    rr_id: str
    title: str
    city: str
    state: Optional[str] = None
    country: str
    required_skills: List[str]
    description: Optional[str]
    rr_start_date: date
    rr_end_date: date
    wfm_id: str
    hm_id: str
    status: bool = True
    job_grade: str
    account_name: str
    project_id: str
    created_at: datetime = datetime.now(timezone.utc)
   
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
 
# model.py → FINAL VERSION – ZERO ERRORS ON REAL FILE
 
class ResourceRequest(BaseModel):
    resource_request_id: str = Field(..., alias="Resource Request ID")
    rr_fte: float = Field(..., alias="RR FTE")
    allocated_fte: Optional[float] = Field(None, alias="Allocated FTE")
    rr_status: Literal["Approved", "Cancelled", "Closed", "EDIT REQUEST APPROVED"] = Field(..., alias="RR Status")
    rr_type: Literal["New Project", "Existing Project","Replacement","Attrition"] = Field(..., alias="RR Type")
    priority: str = Field(..., alias="Priority")
    ust_role: str = Field(..., alias="UST - Role")
    city: str = Field(..., alias="City")
    state: Optional[str] = Field(None, alias="State")
    country: str = Field(..., alias="Country")
    alternate_location: Optional[str] = Field(None, alias="Altenate Location")
    campus: str = Field(..., alias="Campus")
    job_grade: str = Field(..., alias="Job Grade")
    rr_start_date: date = Field(..., alias="RR Start Date")
    rr_end_date: date = Field(..., alias="RR End Date")
    account_name: str = Field(..., alias="Account Name")
    project_id: str = Field(..., alias="Project ID")
    project_name: str = Field(..., alias="Project Name")
    wfm: str = Field(..., alias="WFM")
    wfm_id: str = Field(..., alias="WFM ID")
    hm: str = Field(..., alias="HM")
    hm_id: str = Field(..., alias="HM ID")
    am: str = Field(..., alias="AM")
    am_id: str = Field(..., alias="AM ID")
    billable: Literal["Yes", "No"] = Field(..., alias="Billable")
    actual_bill_rate: Optional[float] = Field(None, alias="Actual Bill Rate")
    actual_currency: Optional[str] = Field(None, alias="Actual Currency")
    bill_rate: Optional[float] = Field(None, alias="Bill Rate")
    billing_frequency: Optional[Literal["H", "D", "M","Y"]] = Field(None, alias="Billing Frequency")
    currency: Optional[str] = Field(None, alias="Currency")
    target_ecr: Optional[float] = Field(None, alias="Target ECR")
    accepted_resource_type: Optional[str] = Field("Any", alias="Accepted Resource Type")
    replacement_type: Optional[str] = Field(None, alias="Replacement Type")
    exclusive_to_ust: bool = Field(..., alias="Exclusive to UST")
    contract_to_hire: bool = Field(..., alias="Contract to Hire")
    client_job_title: Optional[str] = Field(None, alias="Client Job Title")
    ust_role_description: Optional[str] = Field(..., alias="UST Role Description")
    job_description: Optional[str] = Field(..., alias="Job Description")
    notes_for_wfm_or_ta: Optional[str] = Field(None, alias="Notes for WFM or TA")
    client_interview_required: Literal["Yes", "No"] = Field(..., alias="Client Interview Required")
    obu_name: str = Field(..., alias="OBU Name")
    project_start_date: date = Field(..., alias="Project Start Date")
    project_end_date: date = Field(..., alias="Project End Date")
    raised_on: date = Field(..., alias="Raised On")
    rr_finance_approved_date: Optional[date] = Field(None, alias="RR Finance Approved Date")
    wfm_approved_date: Optional[date] = Field(alias="WFM Approved Date")
    cancelled_reasons: Optional[str] = Field(None, alias="Cancelled Reasons")
    edit_requested_date: Optional[date] = Field(None, alias="Edit Requested Date")
    resubmitted_date: Optional[date] = Field(None, alias="Resubmitted Date")
    duration_in_edit_days: Optional[int] = Field(None, alias="Duration in Edit(Days)")
    number_of_edits: Optional[int] = Field(None, alias="# of Edits")
    resubmitted_reason: Optional[str] = Field(None, alias="Resubmitted Reason")
    comments: Optional[str] = Field(None, alias="Comments")
    recruiter_name: Optional[str] = Field(None, alias="Recruiter Name")
    recruiter_id: Optional[str] = Field(None, alias="Recruiter ID")
    recruitment_type: Optional[str] = Field(None, alias="Recruitment Type")
    project_type: Literal["T&M", "Non T&M"] = Field(..., alias="Project Type")
    last_updated_on: date = Field(..., alias="Last Updated On")
    last_activity_date: AwareDatetime = Field(..., alias="Last Activity Date")
    last_activity: Optional[str] = Field(None, alias="Last Activity")
    contract_category: Optional[str] = Field(None, alias="Contract Category")
    mandatory_skills: str = Field(..., alias="Mandatory Skills")
    optional_skills: Optional[str] = Field(..., alias="Optional Skills")
    rr_skill_group: Optional[str] = Field(None, alias="RR Skill Group")
    rr_status:bool = True
   
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
 
    # ------------------------------------------------------------
    # PRIORITY NORMALIZATION
    # ------------------------------------------------------------
    @field_validator("priority", mode="after")
    @classmethod
    def normalize_priority(cls, v):
        if not v:
            return "P4"
        val = str(v).strip().upper()
        return val if val in ("P1", "P2", "P3", "P4") else "P4"
 
    # ------------------------------------------------------------
    # YES/NO → BOOL
    # ------------------------------------------------------------
    @field_validator("exclusive_to_ust", "contract_to_hire", mode="before")
    @classmethod
    def str_to_bool(cls, v):
        if isinstance(v, bool):
            return v
        return str(v).strip().upper() in ("TRUE", "YES", "Y", "1")
 
    # ------------------------------------------------------------
    # SKILL STRING SPLIT
    # ------------------------------------------------------------
    @field_validator("mandatory_skills", "optional_skills", mode="after")
    @classmethod
    def split_skills_from_string(cls, v):
        if v is None:
            return []
        text = str(v).strip()
        if text in ("", "NA", "N/A"):
            return []
        return [item.strip() for item in text.split(",") if item.strip()]
 
    # ------------------------------------------------------------
    # CLEAN DATE PARSING USING ONLY strptime (Your Request)
    # ------------------------------------------------------------
    @field_validator(
        "rr_start_date", "rr_end_date", "project_start_date", "project_end_date",
        "raised_on", "last_updated_on", "rr_finance_approved_date", "wfm_approved_date",
        "edit_requested_date", "resubmitted_date",
        mode="before", check_fields=False
    )
    @classmethod
    def validate_rr_start_date(cls, v):
        if isinstance(v, date):
            return v  # Already a date
       
        v = str(v).strip()
        if v == "" or v.lower() == "none":
            return None   # allow null dates
 
        # Try expected format: 06 Jan 2025
        try:
            return datetime.strptime(v, "%d %b %Y").date()
        except:
            pass
 
        # Try DB format: 2024-04-01 00:00:00 or 2024-04-01
        try:
            return datetime.fromisoformat(v.replace(" ", "T")).date()
        except:
            pass
 
        raise ValueError(
            f"Invalid date format '{v}'. Expected formats: 'DD Mon YYYY' (e.g., 06 Jan 2025) or ISO format (YYYY-MM-DD)."
        )
 
    # ------------------------------------------------------------
    # CLEAN DATETIME PARSE FOR LAST ACTIVITY DATE
    # ------------------------------------------------------------
    @field_validator("last_activity_date", mode="before")
    @classmethod
    def parse_last_activity_date(cls, v):
        if not v or str(v).strip().lower() == "none":
            return None
 
        if isinstance(v, datetime):
            # If datetime is naive, attach UTC
            if v.tzinfo is None:
                return v.replace(tzinfo=timezone.utc)
            return v
 
        raw = str(v).strip()
 
        # Remove timezone label like (PT)
        cleaned = raw.split("(")[0].strip().rstrip(",")
 
        # Try: 27 Jan 2025, 10:13 AM
        try:
            dt = datetime.strptime(cleaned, "%d %b %Y, %I:%M %p")
            return dt.replace(tzinfo=timezone.utc)
        except:
            pass
 
        # Try: 27 Jan 2025 10:13 AM
        try:
            dt = datetime.strptime(cleaned, "%d %b %Y %I:%M %p")
            return dt.replace(tzinfo=timezone.utc)
        except:
            pass
 
        # Try: 06 Jan 2025 14:45:22
        try:
            dt = datetime.strptime(cleaned, "%d %b %Y %H:%M:%S")
            return dt.replace(tzinfo=timezone.utc)
        except:
            pass
 
        # Try ISO
        try:
            dt = datetime.fromisoformat(cleaned)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except:
            pass
 
        raise ValueError(
            f"Invalid datetime '{v}'. Supported formats: "
            "'DD Mon YYYY, HH:MM AM/PM', 'DD Mon YYYY HH:MM:SS', ISO."
        )
 
 
    class Config:
        populate_by_name = True
        extra = "ignore"
 
class Application(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    employee_id: int
    job_rr_id: str
    status: ApplicationStatus = ApplicationStatus.DRAFT
    resume: Optional[str] = None
    cover_letter: Optional[str] = None
    submitted_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
 
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
       
 
from pydantic import BaseModel, field_validator, model_validator, Field, AwareDatetime
import re
from typing import List, Optional,Literal
from datetime import datetime,date,timedelta
from enum import Enum
import uuid
from bson import ObjectId
from pydantic import BaseModel, field_validator, Field, AwareDatetime
import re
from typing import List, Optional,Literal
from datetime import date, datetime, timezone
 
 
class UserRole(str, Enum):
    ADMIN = "Admin"
    TP_MANAGER = "TP Manager"
    WFM = "WFM"
    HM = "HM"
    EMPLOYEE_TP = "TP"
    EMPLOYEE_NON_TP = "Non TP"
 
class ApplicationStatus(str, Enum):
    DRAFT = "Draft"
    SUBMITTED = "Submitted"
    SHORTLISTED = "Shortlisted"
    INTERVIEW = "Interview"
    SELECTED = "Selected"
    REJECTED = "Rejected"
    ALLOCATED = "Allocated"
    WITHDRAWN = "Withdrawn"
 
class Employee(BaseModel):
    employee_id: int = Field(..., alias="Employee ID")
    employee_name: str = Field(..., alias="Employee Name")
    employment_type: str = Field(..., alias="Employment Type")
    designation: str = Field(..., alias="Designation")
    band: str = Field(..., alias="Band")
    city: str = Field(..., alias="City")
    location_description: str = Field(..., alias="Location Description")
    primary_technology: str = Field(..., alias="Primary Technology")
    secondary_technology: Optional[str] = Field(None, alias="Secondary Technology")
    detailed_skills: List[str] = Field(default_factory=list, alias="Detailed Skill Set (List of top skills on profile)")
    type: Literal["TP", "Non TP"] = Field(..., alias="Type")
    resume_text: Optional[str] = Field(None)
   
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
 
    # -------------------------------------------------
    # 1. Normalize Type (TP / Non TP) – case insensitive
    # -------------------------------------------------
    @field_validator("type", mode="before")
    @classmethod
    def normalize_type(cls, v):
        if not v:
            return "Non TP"
        val = str(v).strip().upper()
        return "TP" if val == "TP" else "Non TP"
 
    # -------------------------------------------------
    # 2. Accept ALL real bands seen in your data:
    #     A0–A9, B1–B9, C1–C9, D1–D9
    #     T1–T9, E1–E9, P1–P9
    # -------------------------------------------------
    @field_validator("band", mode="before")
    @classmethod
    def normalize_band(cls, v):
        if not v or str(v).strip() == "":
            return "A0"
 
        value = str(v).strip().upper()
 
        # All valid patterns
        if re.match(r"^[A-D][0-9]$", value):    # A0–D9
            return value
        if re.match(r"^[TEP][1-9]$", value):    # T1–T9, E1–E9, P1–P9
            return value
 
        raise ValueError(f"Invalid band format: '{v}' → '{value}'")
 
    # -------------------------------------------------
    # 3. Handle "Not Available" gracefully
    # -------------------------------------------------
    @field_validator("primary_technology", "secondary_technology", mode="before")
    @classmethod
    def handle_not_available(cls, v, info):
        if not v or str(v or "").strip().upper() in ("NOT AVAILABLE", "NA", "NULL", ""):
            return "" if info.field_name == "primary_technology" else None
        return str(v).strip()
 
    # -------------------------------------------------
    # 4. Split skills (handles commas, question marks, etc.)
    # -------------------------------------------------
    @field_validator("detailed_skills", mode="before")
    @classmethod
    def split_detailed_skills(cls, v):
        if not v or str(v).strip().upper() in ("NA", "NOT AVAILABLE", "NULL", ""):
            return []
        skills = [s.strip() for s in re.split(r'[,?]', str(v)) if s.strip()]
        return skills
 
class Job(BaseModel):
    rr_id: str
    title: str
    city: str
    state: Optional[str] = None
    country: str
    required_skills: List[str]
    description: Optional[str]
    rr_start_date: date
    rr_end_date: date
    wfm_id: str
    hm_id: str
    status: bool = True
    job_grade: str
    account_name: str
    project_id: str

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
 
# model.py → FINAL VERSION – ZERO ERRORS ON REAL FILE
 
class ResourceRequest(BaseModel):
    resource_request_id: str = Field(..., alias="Resource Request ID")
    rr_fte: float = Field(..., alias="RR FTE")
    allocated_fte: Optional[float] = Field(None, alias="Allocated FTE")
    rr_status: Literal["Approved", "Cancelled", "Closed", "EDIT REQUEST APPROVED"] = Field(..., alias="RR Status")
    rr_type: Literal["New Project", "Existing Project","Replacement","Attrition"] = Field(..., alias="RR Type")
    priority: str = Field(..., alias="Priority")
    ust_role: str = Field(..., alias="UST - Role")
    city: str = Field(..., alias="City")
    state: Optional[str] = Field(None, alias="State")
    country: str = Field(..., alias="Country")
    alternate_location: Optional[str] = Field(None, alias="Altenate Location")
    campus: str = Field(..., alias="Campus")
    job_grade: str = Field(..., alias="Job Grade")
    rr_start_date: date = Field(..., alias="RR Start Date")
    rr_end_date: date = Field(..., alias="RR End Date")
    account_name: str = Field(..., alias="Account Name")
    project_id: str = Field(..., alias="Project ID")
    project_name: str = Field(..., alias="Project Name")
    wfm: str = Field(..., alias="WFM")
    wfm_id: str = Field(..., alias="WFM ID")
    hm: str = Field(..., alias="HM")
    hm_id: str = Field(..., alias="HM ID")
    am: str = Field(..., alias="AM")
    am_id: str = Field(..., alias="AM ID")
    billable: Literal["Yes", "No"] = Field(..., alias="Billable")
    actual_bill_rate: Optional[float] = Field(None, alias="Actual Bill Rate")
    actual_currency: Optional[str] = Field(None, alias="Actual Currency")
    bill_rate: Optional[float] = Field(None, alias="Bill Rate")
    billing_frequency: Optional[Literal["H", "D", "M","Y"]] = Field(None, alias="Billing Frequency")
    currency: Optional[str] = Field(None, alias="Currency")
    target_ecr: Optional[float] = Field(None, alias="Target ECR")
    accepted_resource_type: Optional[str] = Field("Any", alias="Accepted Resource Type")
    replacement_type: Optional[str] = Field(None, alias="Replacement Type")
    exclusive_to_ust: bool = Field(..., alias="Exclusive to UST")
    contract_to_hire: bool = Field(..., alias="Contract to Hire")
    client_job_title: Optional[str] = Field(None, alias="Client Job Title")
    ust_role_description: Optional[str] = Field(..., alias="UST Role Description")
    job_description: Optional[str] = Field(..., alias="Job Description")
    notes_for_wfm_or_ta: Optional[str] = Field(None, alias="Notes for WFM or TA")
    client_interview_required: Literal["Yes", "No"] = Field(..., alias="Client Interview Required")
    obu_name: str = Field(..., alias="OBU Name")
    project_start_date: date = Field(..., alias="Project Start Date")
    project_end_date: date = Field(..., alias="Project End Date")
    raised_on: date = Field(..., alias="Raised On")
    rr_finance_approved_date: Optional[date] = Field(None, alias="RR Finance Approved Date")
    wfm_approved_date: Optional[date] = Field(alias="WFM Approved Date")
    cancelled_reasons: Optional[str] = Field(None, alias="Cancelled Reasons")
    edit_requested_date: Optional[date] = Field(None, alias="Edit Requested Date")
    resubmitted_date: Optional[date] = Field(None, alias="Resubmitted Date")
    duration_in_edit_days: Optional[int] = Field(None, alias="Duration in Edit(Days)")
    number_of_edits: Optional[int] = Field(None, alias="# of Edits")
    resubmitted_reason: Optional[str] = Field(None, alias="Resubmitted Reason")
    comments: Optional[str] = Field(None, alias="Comments")
    recruiter_name: Optional[str] = Field(None, alias="Recruiter Name")
    recruiter_id: Optional[str] = Field(None, alias="Recruiter ID")
    recruitment_type: Optional[str] = Field(None, alias="Recruitment Type")
    project_type: Literal["T&M", "Non T&M"] = Field(..., alias="Project Type")
    last_updated_on: date = Field(..., alias="Last Updated On")
    last_activity_date: AwareDatetime = Field(..., alias="Last Activity Date")
    last_activity: Optional[str] = Field(None, alias="Last Activity")
    contract_category: Optional[str] = Field(None, alias="Contract Category")
    mandatory_skills: str = Field(..., alias="Mandatory Skills")
    optional_skills: Optional[str] = Field(..., alias="Optional Skills")
    rr_skill_group: Optional[str] = Field(None, alias="RR Skill Group")
    rr_status:bool = True
   
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
 
    # ------------------------------------------------------------
    # PRIORITY NORMALIZATION
    # ------------------------------------------------------------
    @field_validator("priority", mode="after")
    @classmethod
    def normalize_priority(cls, v):
        if not v:
            return "P4"
        val = str(v).strip().upper()
        return val if val in ("P1", "P2", "P3", "P4") else "P4"
 
    # ------------------------------------------------------------
    # YES/NO → BOOL
    # ------------------------------------------------------------
    @field_validator("exclusive_to_ust", "contract_to_hire", mode="before")
    @classmethod
    def str_to_bool(cls, v):
        if isinstance(v, bool):
            return v
        return str(v).strip().upper() in ("TRUE", "YES", "Y", "1")
 
    # ------------------------------------------------------------
    # SKILL STRING SPLIT
    # ------------------------------------------------------------
    @field_validator("mandatory_skills", "optional_skills", mode="after")
    @classmethod
    def split_skills_from_string(cls, v):
        if v is None:
            return []
        text = str(v).strip()
        if text in ("", "NA", "N/A"):
            return []
        return [item.strip() for item in text.split(",") if item.strip()]
 
    # ------------------------------------------------------------
    # CLEAN DATE PARSING USING ONLY strptime (Your Request)
    # ------------------------------------------------------------
    @field_validator(
        "rr_start_date", "rr_end_date", "project_start_date", "project_end_date",
        "raised_on", "last_updated_on", "rr_finance_approved_date", "wfm_approved_date",
        "edit_requested_date", "resubmitted_date",
        mode="before", check_fields=False
    )
    @classmethod
    def validate_rr_start_date(cls, v):
        if isinstance(v, date):
            return v  # Already a date
       
        v = str(v).strip()
        if v == "" or v.lower() == "none":
            return None   # allow null dates
 
        # Try expected format: 06 Jan 2025
        try:
            return datetime.strptime(v, "%d %b %Y").date()
        except:
            pass
 
        # Try DB format: 2024-04-01 00:00:00 or 2024-04-01
        try:
            return datetime.fromisoformat(v.replace(" ", "T")).date()
        except:
            pass
 
        raise ValueError(
            f"Invalid date format '{v}'. Expected formats: 'DD Mon YYYY' (e.g., 06 Jan 2025) or ISO format (YYYY-MM-DD)."
        )
 
    # ------------------------------------------------------------
    # CLEAN DATETIME PARSE FOR LAST ACTIVITY DATE
    # ------------------------------------------------------------
    @field_validator("last_activity_date", mode="before")
    @classmethod
    def parse_last_activity_date(cls, v):
        if not v or str(v).strip().lower() == "none":
            return None
 
        if isinstance(v, datetime):
            # If datetime is naive, attach UTC
            if v.tzinfo is None:
                return v.replace(tzinfo=timezone.utc)
            return v
 
        raw = str(v).strip()
 
        # Remove timezone label like (PT)
        cleaned = raw.split("(")[0].strip().rstrip(",")
 
        # Try: 27 Jan 2025, 10:13 AM
        try:
            dt = datetime.strptime(cleaned, "%d %b %Y, %I:%M %p")
            return dt.replace(tzinfo=timezone.utc)
        except:
            pass
 
        # Try: 27 Jan 2025 10:13 AM
        try:
            dt = datetime.strptime(cleaned, "%d %b %Y %I:%M %p")
            return dt.replace(tzinfo=timezone.utc)
        except:
            pass
 
        # Try: 06 Jan 2025 14:45:22
        try:
            dt = datetime.strptime(cleaned, "%d %b %Y %H:%M:%S")
            return dt.replace(tzinfo=timezone.utc)
        except:
            pass
 
        # Try ISO
        try:
            dt = datetime.fromisoformat(cleaned)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except:
            pass
 
        raise ValueError(
            f"Invalid datetime '{v}'. Supported formats: "
            "'DD Mon YYYY, HH:MM AM/PM', 'DD Mon YYYY HH:MM:SS', ISO."
        )
 
class Application(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    employee_id: int
    job_rr_id: str
    status: ApplicationStatus = ApplicationStatus.DRAFT
    resume: Optional[str] = None
    cover_letter: Optional[str] = None
    submitted_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
 
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
       
 