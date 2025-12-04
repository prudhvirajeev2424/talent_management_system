from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List,Union
from models import Job, ResourceRequest
from routers.jobs import jobs_crud
from utils.security import get_current_user


# Create a router with the prefix /jobs
jobs_router = APIRouter(prefix="/jobs")


# Endpoint to get all jobs with optional location filter
# Accessible by any authenticated user
@jobs_router.get("/", response_model=List[dict])
async def get_all_jobs(location: Optional[str] = None, current_user=Depends(get_current_user)):
    # Delegates job fetching logic to jobs_crud
    return await jobs_crud.get_jobs(location, current_user)


# Endpoint to create a new job
# Only HM (Hiring Manager) is authorized
@jobs_router.post("/create")
async def create_new_job(new_job: ResourceRequest, current_user=Depends(get_current_user)):
    # Check role-based access
    if current_user["role"] != "HM":
        raise HTTPException(status_code=403, detail="Not Authorized")
    try:
        # Call CRUD function to create both job and resource request
        await jobs_crud.create_job_and_resource_request(new_job, current_user)
        return {"detail": "Job Created Successfully"}
    except Exception as e:
        # Handle errors during creation
        raise HTTPException(status_code=400, detail=f"Error: {e}")


# Endpoint to update an existing job
# Only HM is allowed to modify
@jobs_router.put("/modify")
async def update_job(request_id: str, updated_job: ResourceRequest, current_user=Depends(get_current_user)):
    # Check if user is HM
    if current_user["role"] != "HM":
        raise HTTPException(status_code=403, detail="Not Authorized")
    try:
        # Update both job and resource request based on ID
        await jobs_crud.update_job_and_resource_request(request_id, updated_job, current_user)
        return {"detail": "Job Updated Successfully"}
    except Exception as e:
        # Handle errors during update
        raise HTTPException(status_code=400, detail=f"Error: {e}")
