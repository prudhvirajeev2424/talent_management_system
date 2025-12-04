from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from models import ResourceRequest
from pymongo import ReturnDocument
import csv
import os
from datetime import datetime,date

# Define the path for the CSV file
CSV_PATH = os.path.join(os.path.dirname(__file__), "../updated/updated_jobs.csv")

# Create MongoDB async client connection using the provided connection string
client = AsyncIOMotorClient(
    "mongodb+srv://303391_db_user:5IhrghdRaiXTR22b@cluster0.i0ih74y.mongodb.net/talent_management?retryWrites=true&w=majority&appName=Cluster0"
)
db = client.talent_management

# List of job grade bands for comparison
BANDS = ['A1','A2','A3','B1','B2','B3','C1','C2','C3','D1','D2','D3']

#Map resource_request doc to job-like response
async def map_job(doc):
        
        return {
            "rr_id": doc.get("resource_request_id"),
            "title": doc.get("project_name"),
            "city": doc.get("city"),
            "state": doc.get("state"),
            "country": doc.get("country"),
            "required_skills": (doc.get("mandatory_skills") or []) + (doc.get("optional_skills") or []),
            "description": doc.get("job_description") or doc.get("ust_role_description"),
            "rr_start_date": doc.get("rr_start_date"),
            "rr_end_date": doc.get("rr_end_date"),
            "job_grade": doc.get("job_grade"),
            "account_name": doc.get("account_name"),
            "project_id": doc.get("project_id")
        }


# Role-based job access:
#     - Admin: all jobs
#     - Employee (TP): jobs in band ±1, matching skills, optional location
#     - Employee (non-TP): all jobs
#     - WFM: jobs where wfm_id == current_user.id
#     - HM: jobs where hm_id == current_user.id
 
async def get_jobs(location: Optional[str], current_user):
   
    role = current_user["role"] # Get the role of the current user (Admin, Employee, WFM, HM)
 
    # Admin has access to all jobs
    if role == "Admin":
        cursor = db.resource_request.find({}) 
        # Fetch the jobs as a list
        docs = await cursor.to_list(length=100)
        for d in docs:
            d["_id"] = str(d["_id"])
        return [await map_job(d) for d in docs]

     # Employee role-based access
    elif role in ["TP", "Non TP"]:
       
        emp = await db.employees.find_one({"employee_id": int(current_user["employee_id"])})
        emp = await db.employees.find_one({"employee_id": int(current_user["employee_id"])})
        #Role - TP
        if emp and role == "TP":
            curr_band = emp["band"]
            curr_skills = emp.get("detailed_skills)", [])

             # Find the index of the current band
            indx = BANDS.index(curr_band)
            above_band = BANDS[indx+1] if indx < len(BANDS)-1 else BANDS[indx]
            below_band = BANDS[indx-1] if indx > 0 else BANDS[indx]
 
            query = {
                "job_grade": {"$in": [curr_band, above_band, below_band]},  # Filter jobs based on bands ±1
                "mandatory_skills": {"$in": curr_skills},  # Filter jobs based on required skills
                "flag":True,
            }
             # Optional filter by location (city)
            if location:
                query["city"] = location
 
            # Execute the query to find jobs
            cursor = db.resource_request.find(query)
            cursor = db.resource_request.find(query)
            docs = await cursor.to_list(length=100)
            for d in docs:
                d["_id"] = str(d["_id"])
            
            return [await map_job(d) for d in docs]
        
        else:
            #Role - Non TP
            query = {}
            if location:
                query["city"] = location
            query["flag"]=True
            cursor = db.resource_request.find(query)
            query["flag"]=True
            cursor = db.resource_request.find(query)
            docs = await cursor.to_list(length=100)
            for d in docs:
                d["_id"] = str(d["_id"])
           
            return [await map_job(d) for d in docs]

    # WFM role can access jobs based on WFM ID
    elif role == "WFM":
        query = {"wfm_id": {"$ne":current_user["employee_id"]}}
        cursor = db.resource_request.find(query)
        docs = await cursor.to_list(length=100)
        for d in docs:
            d["_id"] = str(d["_id"])
        return [await map_job(d) for d in docs]

     # HM role can access jobs based on HM ID
    elif role == "HM":
        query = {"hm_id": {"$ne":current_user["employee_id"]}}
        cursor = db.resource_request.find(query)
        docs = await cursor.to_list(length=100)
        for d in docs:
            d["_id"] = str(d["_id"])
        return [await map_job(d) for d in docs]

async def jobs_under_manager(current_user):
    
    role = current_user["role"]
    
    # WFM role can access jobs based on WFM ID
    if role == "WFM":
        query = {"wfm_id": current_user["employee_id"]}
        cursor = db.resource_request.find(query)
        docs = await cursor.to_list(length=100)
        for d in docs:
            d["_id"] = str(d["_id"])
        return [await map_job(d) for d in docs]
 
     # HM role can access jobs based on HM ID
    elif role == "HM":
        query = {"hm_id": current_user["employee_id"]}
        cursor = db.resource_request.find(query)
        docs = await cursor.to_list(length=100)
        for d in docs:
            d["_id"] = str(d["_id"])
        return docs
    
    
# Function to create a job and associated resource request, and write to a CSV file
async def create_job_and_resource_request(job_data: ResourceRequest, current_user):
    row = job_data.dict(by_alias=True) # Convert the ResourceRequest data to a dictionary using aliases


    # Check if file exists to decide whether to write header
    file_exists = os.path.isfile(CSV_PATH)

     # Open the CSV file in append mode
    with open(CSV_PATH, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

# Function to normalize dates (convert datetime.date to datetime.datetime for MongoDB compatibility)
def normalize_dates(doc: dict) -> dict:
    # Convert all datetime.date values to datetime.datetime for MongoDB
    for key, value in doc.items():
        if isinstance(value, date) and not isinstance(value, datetime):
            # Convert date → datetime at midnight UTC
            doc[key] = datetime(value.year, value.month, value.day) # If value is a date object but not datetime
    return doc

# Function to update both the ResourceRequest and Job documents in MongoDB

    # Update both ResourceRequest and Job documents.
    # - Only HMs can update.
    # - HM can only update jobs they own (hm_id == current_user["employee_id"]). 
async def update_job_and_resource_request(request_id: str, update_data: ResourceRequest, current_user):
   
    if current_user["role"] != "HM":
        raise PermissionError("You do not have permission to update jobs.")
 
    # Start a session for updates
    async with await db.client.start_session() as session:
        async with session.start_transaction():
            try:
                # Step 1: Find the resource request owned by this HM
                resource_request = await db.resource_request.find_one(
                    {"resource_request_id": request_id, "hm_id": current_user["employee_id"]},
                    {"resource_request_id": request_id, "hm_id": current_user["employee_id"]},
                    session=session  # Pass the session for atomicity
                )
                if not resource_request:
                    raise PermissionError("ResourceRequest not found or you're not authorized to update this job.")
 
                # Step 2: Update ResourceRequest
                update_resource_request_data = update_data.dict(exclude_unset=True, by_alias=False)
                update_resource_request_data = update_data.dict(exclude_unset=True, by_alias=False)
                update_resource_request_data = normalize_dates(update_resource_request_data)
 
                update_result = await db.resource_request.update_one(
                    {"resource_request_id": request_id, "hm_id": current_user["employee_id"]},
                    {"resource_request_id": request_id, "hm_id": current_user["employee_id"]},
                    {"$set": update_resource_request_data},
                    session=session
                )
                if update_result.matched_count == 0:
                    raise Exception("ResourceRequest not found for the job.")

              
                return True
 
            except Exception as e:
                raise Exception(f"Error occurred: {e}")
            