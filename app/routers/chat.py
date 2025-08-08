from fastapi import APIRouter

router = APIRouter()

@router.post("/rooms")
async def create_chat_room():
    return {"message": "Create chat room endpoint - MongoDB implementation coming soon"}

@router.get("/rooms")
async def get_chat_rooms():
    return {"message": "Get chat rooms endpoint - MongoDB implementation coming soon"}

@router.get("/rooms/{room_id}")
async def get_chat_room(room_id: str):
    return {"message": f"Get chat room {room_id} endpoint - MongoDB implementation coming soon"}

@router.get("/rooms/{room_id}/messages")
async def get_chat_messages(room_id: str):
    return {"message": f"Get messages for room {room_id} endpoint - MongoDB implementation coming soon"}

@router.post("/rooms/{room_id}/messages")
async def send_message(room_id: str):
    return {"message": f"Send message to room {room_id} endpoint - MongoDB implementation coming soon"}

@router.get("/messages/unread")
async def get_unread_count():
    return {"message": "Get unread count endpoint - MongoDB implementation coming soon"}

@router.put("/messages/{message_id}/read")
async def mark_message_read(message_id: str):
    return {"message": f"Mark message {message_id} as read endpoint - MongoDB implementation coming soon"}

@router.delete("/messages/{message_id}")
async def delete_message(message_id: str):
    return {"message": f"Delete message {message_id} endpoint - MongoDB implementation coming soon"}

@router.get("/classmates")
async def get_classmates():
    return {"message": "Get classmates endpoint - MongoDB implementation coming soon"} 