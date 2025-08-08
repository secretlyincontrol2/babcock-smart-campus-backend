from fastapi import APIRouter

router = APIRouter()

@router.get("/cafeterias")
async def get_cafeterias():
    return {"message": "Get cafeterias endpoint - MongoDB implementation coming soon"}

@router.get("/cafeterias/{cafeteria_id}/menu")
async def get_cafeteria_menu(cafeteria_id: str):
    return {"message": f"Menu for cafeteria {cafeteria_id} - MongoDB implementation coming soon"}

@router.get("/menu/categories")
async def get_menu_categories():
    return {"message": "Menu categories endpoint - MongoDB implementation coming soon"}

@router.get("/menu/search")
async def search_menu():
    return {"message": "Menu search endpoint - MongoDB implementation coming soon"}

@router.get("/menu/vegetarian")
async def get_vegetarian_menu():
    return {"message": "Vegetarian menu endpoint - MongoDB implementation coming soon"}

@router.get("/menu/halal")
async def get_halal_menu():
    return {"message": "Halal menu endpoint - MongoDB implementation coming soon"} 