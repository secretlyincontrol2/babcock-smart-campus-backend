from pydantic import BaseModel, Field, field_validator
from typing import Optional, Annotated, List
from datetime import datetime
from bson import ObjectId
from enum import Enum

class PyObjectId(str):
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        return handler(str)

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(v)

class ChatRoomType(str, Enum):
    DIRECT = "direct"
    GROUP = "group"
    DEPARTMENT = "department"
    COURSE = "course"
    ANNOUNCEMENT = "announcement"

class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    LOCATION = "location"
    SYSTEM = "system"

class ChatRoom(BaseModel):
    id: Annotated[PyObjectId, Field(default_factory=PyObjectId, alias="_id")]
    name: str
    description: Optional[str] = None
    room_type: ChatRoomType
    created_by: str
    members: List[str]  # List of user IDs
    admins: List[str]  # List of admin user IDs
    is_active: bool = True
    is_private: bool = False
    max_members: Optional[int] = None
    avatar_url: Optional[str] = None
    last_message: Optional[dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ChatRoomCreate(BaseModel):
    name: str
    description: Optional[str] = None
    room_type: ChatRoomType
    members: List[str]
    admins: Optional[List[str]] = None
    is_private: bool = False
    max_members: Optional[int] = None
    avatar_url: Optional[str] = None

class ChatRoomUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    members: Optional[List[str]] = None
    admins: Optional[List[str]] = None
    is_private: Optional[bool] = None
    max_members: Optional[int] = None
    avatar_url: Optional[str] = None
    is_active: Optional[bool] = None

class ChatMessage(BaseModel):
    id: Annotated[PyObjectId, Field(default_factory=PyObjectId, alias="_id")]
    room_id: str
    sender_id: str
    sender_name: str
    sender_avatar: Optional[str] = None
    message_type: MessageType = MessageType.TEXT
    content: str
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    location: Optional[dict] = None
    reply_to: Optional[str] = None
    is_edited: bool = False
    edited_at: Optional[datetime] = None
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    read_by: List[str] = []  # List of user IDs who read the message
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class MessageCreate(BaseModel):
    room_id: str
    content: str
    message_type: MessageType = MessageType.TEXT
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    location: Optional[dict] = None
    reply_to: Optional[str] = None

class MessageUpdate(BaseModel):
    content: str
    is_edited: bool = True

class MessageDelete(BaseModel):
    is_deleted: bool = True

class ChatStats(BaseModel):
    total_rooms: int
    total_messages: int
    active_rooms: int
    messages_by_type: dict
    popular_rooms: List[dict]
    recent_activity: List[dict]

class RoomMember(BaseModel):
    user_id: str
    username: str
    full_name: str
    avatar_url: Optional[str] = None
    role: str = "member"  # member, admin, owner
    joined_at: datetime
    last_seen: Optional[datetime] = None
    is_online: bool = False

class DirectMessage(BaseModel):
    user_id: str
    username: str
    full_name: str
    avatar_url: Optional[str] = None
    last_message: Optional[str] = None
    last_message_time: Optional[datetime] = None
    unread_count: int = 0
    is_online: bool = False 