from fastapi import APIRouter

router = APIRouter()

@router.get("/profile")
async def get_user_profile():
    return {"message": "User profile endpoint - MongoDB implementation coming soon"}

@router.put("/profile")
async def update_user_profile():
    return {"message": "Update profile endpoint - MongoDB implementation coming soon"}

@router.get("/students")
async def get_students():
    return {"message": "Students list endpoint - MongoDB implementation coming soon"} 