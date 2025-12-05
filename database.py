from motor.motor_asyncio import AsyncIOMotorClient
import pymongo
import gridfs

client = AsyncIOMotorClient("mongodb+srv://303391_db_user:5IhrghdRaiXTR22b@cluster0.i0ih74y.mongodb.net/?appName=Cluster0")
db = client.talent_management

sync_client = pymongo.MongoClient("mongodb+srv://303391_db_user:5IhrghdRaiXTR22b@cluster0.i0ih74y.mongodb.net/?appName=Cluster0")
sync_db = sync_client.talent_management

# Use synchronous GridFS with pymongo
fs = gridfs.GridFS(sync_db,collection="files")

collections = {
    "employees": db.employees,
    "applications": db.applications,
    "users": db.users,
    "refresh_tokens": db.refresh_tokens,
    "audit_logs": db.audit_logs,
    "block_list_tokens":db.block_list_tokens,
    "resource_request":db.resource_request,
    "files":db.files.files
}

def get_gridfs():
    return fs
 
applications = db.applications
resource_request= db.resource_request
employees = db.employees
files=db.files.files
