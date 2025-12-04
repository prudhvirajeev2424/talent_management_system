from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient("mongodb+srv://303391_db_user:5IhrghdRaiXTR22b@cluster0.i0ih74y.mongodb.net/?appName=Cluster0")
db = client.talent_management

collections = {
    "employees": db.employees,
    "applications": db.applications,
    "users": db.users,
    "refresh_tokens": db.refresh_tokens,
    "audit_logs": db.audit_logs,
    "block_list_tokens":db.block_list_tokens,
    "resource_request":db.resource_request
}