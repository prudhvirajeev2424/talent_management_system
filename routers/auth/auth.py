from fastapi import APIRouter, HTTPException, Depends
from jose import JWTError, jwt, ExpiredSignatureError
from datetime import timedelta, datetime
from fastapi.security import HTTPBearer
from database import collections
from utils.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    get_current_user,
    SECRET_KEY,
    ALGORITHM,
)

router = APIRouter(prefix="/api/auth", tags=["Auth"])
bearer_scheme = HTTPBearer()

@router.post("/login")
async def login(username: str, password: str):
    user = await collections["users"].find_one({"employee_id": username})
    if not user or not verify_password(password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Access token expires in 1 minute (configured in utils/security.py)
    access_token = create_access_token({"sub": user["employee_id"], "role": user["role"]})
    refresh_token = create_refresh_token({"sub": user["employee_id"], "role": user["role"]})

    # Store refresh token (7 days expiry)
    await collections["refresh_tokens"].insert_one({
        "token": refresh_token,
        "employee_id": user["employee_id"],
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=7)
    })

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 60  # 1 minute = 60 seconds
    }

@router.post("/refresh")
async def refresh_token(refresh_token: str):
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        emp_id = payload.get("sub")
        
        
        token_type = payload.get("type")

        if token_type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        # Validate token exists in DB
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

    # Issue new access + refresh tokens
    new_access_token = create_access_token({"sub": emp_id, "role": user["role"]})
    new_refresh_token = create_refresh_token({"sub": emp_id, "role": user["role"]})

    # Delete the most recent refresh token for a user
    last_token = await collections["refresh_tokens"].find_one(
        {"employee_id": emp_id},              # filter by user
        sort=[("created_at", -1)]             # sort descending by created_at
    )

    if last_token:
        await collections["refresh_tokens"].delete_one({"_id": last_token["_id"]})

    # Store new refresh token (7 days expiry)
    await collections["refresh_tokens"].insert_one({
        "token": new_refresh_token,
        "employee_id": emp_id,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=7)
    })

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "expires_in": 60  # 1 minute = 60 seconds
    }

@router.post("/logout")
async def logout(current_user=Depends(get_current_user)):
    # Find all refresh tokens for this user
    tokens = collections["refresh_tokens"].find({"employee_id": current_user["employee_id"]})

    async for token in tokens:
        # Insert each token into blacklisted_tokens
        await collections["block_list_tokens"].insert_one({
            "token": token["token"],
            "employee_id": token["employee_id"],
            "blacklisted_at": datetime.utcnow()
        })

    # Remove them from refresh_tokens collection
    await collections["refresh_tokens"].delete_many({"employee_id": current_user["employee_id"]})

    return {"message": "Logged out successfully"}
