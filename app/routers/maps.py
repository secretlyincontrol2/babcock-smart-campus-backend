from fastapi import APIRouter

router = APIRouter()

@router.get("/locations")
async def get_locations():
    return {"message": "Get locations endpoint - MongoDB implementation coming soon"}

@router.get("/directions")
async def get_directions():
    return {"message": "Get directions endpoint - MongoDB implementation coming soon"}

@router.get("/nearby")
async def get_nearby():
    return {"message": "Get nearby places endpoint - MongoDB implementation coming soon"}

@router.get("/campus-info")
async def get_campus_info():
    return {"message": "Get campus info endpoint - MongoDB implementation coming soon"} 