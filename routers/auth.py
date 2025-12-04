from fastapi import APIRouter, HTTPException, Depends
from jose import JWTError, jwt, ExpiredSignatureError
from datetime import timedelta, datetime,timezone
from fastapi.security import HTTPBearer
from database import collections
from utils.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    get_current_user,
    SECRET_KEY,
    ALGORITHM
)

router = APIRouter(prefix="/api/auth", tags=["Auth"])
bearer_scheme = HTTPBearer()

@router.post("/login")
async def login(username: str, password: str):
    user = await collections["users"].find_one({"employee_id": username})
    if not user or not verify_password(password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token({"sub": user["employee_id"], "role": user["role"]})
    refresh_token = create_refresh_token({"sub": user["employee_id"], "role": user["role"]})

    await collections["refresh_tokens"].insert_one({
        "token": refresh_token,
        "employee_id": user["employee_id"],
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7)
    })

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": "300 seconds"
    }

@router.post("/refresh")
async def refresh_token(refresh_token: str):
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        emp_id = payload.get("sub")
        token_type = payload.get("type")

        if token_type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        stored = await collections["refresh_tokens"].find_one({"token": refresh_token})
        if not stored:
            raise HTTPException(status_code=401, detail="Refresh token revoked")

    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = await collections["users"].find_one({"employee_id": emp_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_access_token = create_access_token({"sub": emp_id, "role": user["role"]})
    new_refresh_token = create_refresh_token({"sub": emp_id, "role": user["role"]})

    last_token = await collections["refresh_tokens"].find_one(
        {"employee_id": emp_id}, sort=[("created_at", -1)]
    )
    if last_token:
        await collections["refresh_tokens"].delete_one({"_id": last_token["_id"]})

    await collections["refresh_tokens"].insert_one({
        "token": new_refresh_token,
        "employee_id": emp_id,
        "created_at":datetime.now(timezone.utc),
        "expires_at":datetime.now(timezone.utc) + timedelta(days=7)
    })

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "expires_in": "300 seconds"
    }

@router.post("/logout")
async def logout(current_user=Depends(get_current_user)):
    tokens = collections["refresh_tokens"].find({"employee_id": current_user["employee_id"]})
    async for token in tokens:
        await collections["block_list_tokens"].insert_one({
            "token": token["token"],
            "employee_id": token["employee_id"],
            "blacklisted_at":datetime.now(timezone.utc)
        })
    await collections["refresh_tokens"].delete_many({"employee_id": current_user["employee_id"]})
    return {"message": "Logged out successfully"}


# === NEW PATH-BASED RBAC ENDPOINTS ===

# def serialize_doc(doc):
#     if "_id" in doc:
#         doc["_id"] = str(doc["_id"])
#     return doc

# @router.get("/employees/tp")
# async def get_tp_employees(current_user=Depends(get_current_user)):
#     role = current_user["role"]
#     if role not in ["TP Manager", "HM"]:
#         raise HTTPException(status_code=403, detail="Not authorized for TP employees")

#     employees = await collections["users"].find({"role": "TP"}).to_list(length=None)
#     employees = [serialize_doc(emp) for emp in employees]
#     return {"employees": employees}

# @router.get("/employees/non-tp")
# async def get_non_tp_employees(current_user=Depends(get_current_user)):
#     role = current_user["role"]
#     if role not in ["WFM", "HM"]:
#         raise HTTPException(status_code=403, detail="Not authorized for Non TP employees")

#     employees = await collections["users"].find({"role": "Non TP"}).to_list(length=None)
#     employees = [serialize_doc(emp) for emp in employees]
#     return {"employees": employees}

# @router.get("/employees/all")
# async def get_all_employees(current_user=Depends(get_current_user)):
#     role = current_user["role"]
#     if role != "HM":
#         raise HTTPException(status_code=403, detail="Only HR Manager can view all employees")

#     employees = await collections["users"].find({}).to_list(length=None)
#     employees = [serialize_doc(emp) for emp in employees]
#     return {"employees": employees}