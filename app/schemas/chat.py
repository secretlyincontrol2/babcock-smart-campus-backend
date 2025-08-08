from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ChatRoomBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_group_chat: bool = False

class ChatRoomCreate(ChatRoomBase):
    pass

class ChatRoomResponse(ChatRoomBase):
    id: int
    created_by: int
    created_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True

class ChatMessageBase(BaseModel):
    message: str
    message_type: str = "text"
    file_url: Optional[str] = None

class ChatMessageCreate(ChatMessageBase):
    pass

class ChatMessageResponse(ChatMessageBase):
    id: int
    chat_room_id: int
    sender_id: int
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True 