from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from routers.jobs.jobs_api import jobs_router
from routers.auth.auth import router

# from routers import auth, file_upload, job, employee, application, manager_workflow, admin

app = FastAPI(title="Talent Management System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB Connection
client = AsyncIOMotorClient("mongodb+srv://303391_db_user:5IhrghdRaiXTR22b@cluster0.i0ih74y.mongodb.net/?appName=Cluster0")
db = client.talent_management

app.include_router(router, tags=["Auth"])


app.include_router(jobs_router, tags=["Jobs"])

