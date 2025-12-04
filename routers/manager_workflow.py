from fastapi import APIRouter, Depends, HTTPException, Query
from database import collections
from utils.security import get_current_user
from datetime import datetime
from typing import List,Literal,Dict,Any,Optional

manager_router = APIRouter(prefix="/api/manager", tags=["Manager Workflow"])

# Audit logging: every status change is recorded for traceability
async def log_audit(action: str, app_id: str, performed_by: str, details: dict = None):
    log_entry = {
        "action": action,
        "application_id": app_id,
        "performed_by": performed_by,
        "performed_by_role": (await collections["users"].find_one({"employee_id": performed_by}))["role"],
        "timestamp": datetime.utcnow(),
        "details": details or {}
    }
    await collections["audit_logs"].insert_one(log_entry)

# Role-based filtering of applications
async def get_manager_applications(current_user: dict):
    role = current_user["role"]
    emp_id = current_user["employee_id"]

    if role == "TP Manager":  # TP Managers see TP employee submissions
        tp_emp_ids = [str(e["Employee ID"]) async for e in collections["employees"].find({"Type": "TP"}, {"Employee ID": 1})]
        query = {"employee_id": {"$in": tp_emp_ids}, "status": "Submitted"}

    elif role == "WFM":  # WFM sees their jobs + Non-TP employees
        job_rr_ids = [j["rr_id"] async for j in collections["jobs"].find({"wfm_id": emp_id}, {"rr_id": 1})]
        non_tp_emp_ids = [str(e["Employee ID"]) async for e in collections["employees"].find({"Type": "Non TP"}, {"Employee ID": 1})]
        query = {
            "job_rr_id": {"$in": job_rr_ids or ["__none__"]},  # prevent empty $in
            "employee_id": {"$in": non_tp_emp_ids},
            "status": {"$nin": ["Draft", "Allocated", "Selected", "Rejected", "Withdrawn"]}
        }

    elif role == "HM":  # Hiring Managers see Selected candidates for their jobs
        job_rr_ids = [j["rr_id"] async for j in collections["jobs"].find({"hm_id": emp_id}, {"rr_id": 1})]
        query = {"job_rr_id": {"$in": job_rr_ids or ["__none__"]}, "status": "Selected"}

    else:
        raise HTTPException(status_code=403, detail="Unauthorized")

    cursor = collections["applications"].find(query).sort("updated_at", -1)
    return await cursor.to_list(200)


@manager_router.get("/applications")
async def list_applications(current_user: dict = Depends(get_current_user)):
    return await get_manager_applications(current_user)


# --- Status Transition Endpoints ---

@manager_router.patch("/applications/{app_id}/shortlist")
async def shortlist(app_id: str, current_user: dict = Depends(get_current_user)):
    app = await collections["applications"].find_one({"_id": app_id})
    if not app:
        raise HTTPException(404, "Application not found")

    emp = await collections["employees"].find_one({"Employee ID": int(app["employee_id"])})

    # TP Manager shortlists TP candidates
    if current_user["role"] == "TP Manager" and emp["Type"] == "TP" and app["status"] == "Submitted":
        result = await collections["applications"].update_one({"_id": app_id}, {"$set": {"status": "Shortlisted", "updated_at": datetime.utcnow()}})
        if result.modified_count:
            await log_audit("shortlist_tp", app_id, current_user["employee_id"], {"from": "Submitted"})
        return {"message": "Shortlisted by TP Manager"}

    # WFM shortlists Non-TP candidates
    if current_user["role"] == "WFM" and emp["Type"] == "Non TP" and app["status"] == "Submitted":
        result = await collections["applications"].update_one({"_id": app_id}, {"$set": {"status": "Shortlisted", "updated_at": datetime.utcnow()}})
        if result.modified_count:
            await log_audit("shortlist_non_tp", app_id, current_user["employee_id"], {"from": "Submitted"})
        return {"message": "Shortlisted by WFM"}

    raise HTTPException(403, "Not authorized")


@manager_router.patch("/applications/{app_id}/interview")
async def to_interview(app_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "WFM":
        raise HTTPException(403, "Only WFM can move to Interview")

    # Only Shortlisted → Interview
    result = await collections["applications"].update_one({"_id": app_id, "status": "Shortlisted"}, {"$set": {"status": "Interview", "updated_at": datetime.utcnow()}})
    if result.modified_count:
        await log_audit("move_to_interview", app_id, current_user["employee_id"])
    else:
        raise HTTPException(400, "Invalid status transition")
    return {"message": "Moved to Interview"}


@manager_router.patch("/applications/{app_id}/select")
async def select_candidate(app_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "WFM":
        raise HTTPException(403)

    # Only Interview → Selected
    result = await collections["applications"].update_one({"_id": app_id, "status": "Interview"}, {"$set": {"status": "Selected", "updated_at": datetime.utcnow()}})
    if result.modified_count:
        await log_audit("select_candidate", app_id, current_user["employee_id"])
    else:
        raise HTTPException(400, "Must be in Interview stage")
    return {"message": "Candidate Selected"}


@manager_router.patch("/applications/{app_id}/reject")
async def reject_candidate(app_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "WFM":
        raise HTTPException(403)

    app = await collections["applications"].find_one({"_id": app_id})
    # Cannot reject after allocation/selection
    if app["status"] in ["Allocated", "Selected"]:
        raise HTTPException(400, "Cannot reject after selection/allocation")

    result = await collections["applications"].update_one({"_id": app_id}, {"$set": {"status": "Rejected", "updated_at": datetime.utcnow()}})
    if result.modified_count:
        await log_audit("reject_candidate", app_id, current_user["employee_id"], {"from_status": app["status"]})
    return {"message": "Candidate Rejected"}


@manager_router.patch("/applications/{app_id}/allocate")
async def allocate(app_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "HM":
        raise HTTPException(403)

    # Only Selected → Allocated by Hiring Manager
    app = await collections["applications"].find_one({"_id": app_id, "status": "Selected"})
    if not app:
        raise HTTPException(400, "Application not in Selected state")

    job = await collections["jobs"].find_one({"rr_id": app["job_rr_id"], "hm_id": current_user["employee_id"]})
    if not job:
        raise HTTPException(403, "You don't own this job")

    result = await collections["applications"].update_one({"_id": app_id}, {"$set": {"status": "Allocated", "updated_at": datetime.utcnow()}})
    if result.modified_count:
        await log_audit("allocate_candidate", app_id, current_user["employee_id"], {"job_rr_id": app["job_rr_id"]})
    return {"message": "Allocated Successfully"}

@manager_router.patch("/bulk/applications/{action}")
async def bulk_manual_action(
    action: Literal["shortlist", "interview", "select", "reject", "allocate"],
    app_ids: List[str] = Query(..., description="List of application IDs to process"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    
    if not app_ids:
        raise HTTPException(status_code=400, detail="app_ids cannot be empty")
    
    role = current_user.get("role")
    if not role:
        raise HTTPException(status_code=401, detail="User role not found")
    
    allowed_actions = {
        "TP Manager": {"shortlist"},
        "WFM": {"shortlist", "interview", "select", "reject"},
        "HM": {"allocate"},
        "Admin": {"shortlist", "interview", "select", "reject", "allocate"}
    }

    if action not in allowed_actions.get(role, set()):
        raise HTTPException(
            status_code=403,
            detail=f"{role} is not authorized to perform bulk '{action}' action"
        )

    results = []
    for app_id in app_ids:
        try:
            # Call the appropriate action based on the action type
            if action == "shortlist":
                resp = await shortlist(app_id, current_user)
            elif action == "interview":
                resp = await to_interview(app_id, current_user)
            elif action == "select":
                resp = await select_candidate(app_id, current_user)
            elif action == "reject":
                resp = await reject_candidate(app_id, current_user)
            elif action == "allocate":
                resp = await allocate(app_id, current_user)
            
            results.append({
                "app_id": app_id,
                "status": "success",
                "message": resp.get("message", "Operation completed successfully")
            })
        except HTTPException as e:
            results.append({
                "app_id": app_id,
                "status": "failed",
                "error": e.detail,
                "status_code": e.status_code
            })
        except Exception as e:
            results.append({
                "app_id": app_id,
                "status": "failed",
                "error": f"Unexpected error: {str(e)}"
            })

    successful_count = len([r for r in results if r["status"] == "success"])
    failed_count = len(app_ids) - successful_count

    await log_audit(
        f"bulk_{action}",
        "multiple",
        current_user["employee_id"],
        {
            "action": action,
            "role": role,
            "total_count": len(app_ids),
            "successful_count": successful_count,
            "failed_count": failed_count,
            "app_ids": app_ids
        }
    )

    return {
        "action": action,
        "performed_by": role,
        "total": len(app_ids),
        "successful": successful_count,
        "failed": failed_count,
        "results": results
    }
    
@manager_router.get("/skill-matches/applications/{job_rr_id}")
async def get_skill_matches(
    job_rr_id: str,
    min_match: Optional[float] = Query(
        None,
        ge=0.0,
        le=100.0,
        description="Only return candidates with skill match ≥ this percentage",
        example=70.0
    ),
    current_user: dict = Depends(get_current_user)
):

    # Fetch job
    job = await collections["jobs"].find_one({"rr_id": job_rr_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job RR not found")

    required_skills = job.get("required_skills", [])
    if not required_skills:
        return {"message": "No required skills defined for this job"}

    # Normalize required skills once
    req_skills = {skill.strip().lower() for skill in required_skills}

    # Fetch all submitted applications
    applications = await collections["applications"].find({
        "job_rr_id": job_rr_id,
        "status": "Submitted"
    }).to_list(1000)

    results = []

    for app in applications:
        employee_id = app["employee_id"]

        # Fetch employee profile
        employee = await collections["employees"].find_one({"Employee ID": int(employee_id)})
        if not employee:
            continue

        emp_skills = {
            skill.strip().lower()
            for skill in employee.get("Detailed Skill Set (List of top skills on profile)", [])
        }

        # Calculate match percentage
        matched_count = len(emp_skills.intersection(req_skills))
        match_percentage = (matched_count / len(req_skills)) * 100 if req_skills else 0

        # Apply filter if min_match is provided
        if min_match is not None and match_percentage < min_match:
            continue

        results.append({
            "application_id": str(app["_id"]),
            "employee_id": employee_id,
            "employee_name": employee.get("Employee Name", "Unknown"),
            "current_designation": employee.get("Designation"),
            "location": employee.get("City"),
            "match_percentage": round(match_percentage, 2),
            "matched_skills": list(emp_skills.intersection(req_skills)),
            "missing_skills": list(req_skills - emp_skills),
            "total_required_skills": len(req_skills),
            "skills_matched_count": matched_count
        })

    # Sort by highest match first
    results.sort(key=lambda x: x["match_percentage"], reverse=True)

    return {
        "job_rr_id": job_rr_id,
        "job_title": job.get("title"),
        "total_applications": len(applications),
        "candidates_returned": len(results),
        "required_skills": list(req_skills),
        "min_match_filter_applied": min_match,
        "candidates": results
    }