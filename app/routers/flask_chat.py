"""
Flask Chat Router
Basic chat functionality
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
from datetime import datetime
from bson import ObjectId

from ..database import get_database
from ..core.exceptions import CustomHTTPException

logger = logging.getLogger(__name__)

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/rooms', methods=['POST'])
@jwt_required()
def create_chat_room():
    """Create a new chat room"""
    try:
        current_user_email = get_jwt_identity()
        data = request.get_json()
        
        if not data.get('name'):
            raise CustomHTTPException(400, "Room name is required")
        
        db = get_database()
        
        # Get current user
        current_user = db.users.find_one({"email": current_user_email})
        if not current_user:
            raise CustomHTTPException(404, "User not found")
        
        # Check if room name already exists
        existing_room = db.chat_rooms.find_one({"name": data['name']})
        if existing_room:
            raise CustomHTTPException(409, "Chat room with this name already exists")
        
        # Create chat room
        room = {
            "name": data['name'],
            "description": data.get('description', ''),
            "created_by": ObjectId(current_user['_id']),
            "creator_name": current_user['full_name'],
            "is_public": data.get('is_public', True),
            "max_members": data.get('max_members', 100),
            "members": [ObjectId(current_user['_id'])],
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = db.chat_rooms.insert_one(room)
        room['_id'] = str(result.inserted_id)
        room['created_by'] = str(room['created_by'])
        room['members'] = [str(member) for member in room['members']]
        
        logger.info(f"Chat room created: {data['name']} by user {current_user_email}")
        
        return jsonify({
            "message": "Chat room created successfully",
            "room": room
        }), 201
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Create chat room error: {e}")
        raise CustomHTTPException(500, "Internal server error")

@chat_bp.route('/rooms', methods=['GET'])
@jwt_required()
def get_chat_rooms():
    """Get available chat rooms"""
    try:
        current_user_email = get_jwt_identity()
        db = get_database()
        
        # Get current user
        current_user = db.users.find_one({"email": current_user_email})
        if not current_user:
            raise CustomHTTPException(404, "User not found")
        
        # Get query parameters
        is_public = request.args.get('is_public')
        search = request.args.get('search')
        
        # Build filter query
        filter_query = {"is_active": True}
        
        if is_public is not None:
            filter_query["is_public"] = is_public.lower() == 'true'
        
        if search:
            filter_query["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}}
            ]
        
        # Get chat rooms
        rooms_cursor = db.chat_rooms.find(filter_query).sort("created_at", -1)
        rooms = []
        
        for room in rooms_cursor:
            room['_id'] = str(room['_id'])
            room['created_by'] = str(room['created_by'])
            room['members'] = [str(member) for member in room['members']]
            room['member_count'] = len(room['members'])
            rooms.append(room)
        
        return jsonify({
            "rooms": rooms,
            "total_rooms": len(rooms)
        })
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Get chat rooms error: {e}")
        raise CustomHTTPException(500, "Internal server error")

@chat_bp.route('/rooms/<room_id>/join', methods=['POST'])
@jwt_required()
def join_chat_room(room_id):
    """Join a chat room"""
    try:
        if not ObjectId.is_valid(room_id):
            raise CustomHTTPException(400, "Invalid room ID format")
        
        current_user_email = get_jwt_identity()
        db = get_database()
        
        # Get current user
        current_user = db.users.find_one({"email": current_user_email})
        if not current_user:
            raise CustomHTTPException(404, "User not found")
        
        # Get chat room
        room = db.chat_rooms.find_one({"_id": ObjectId(room_id), "is_active": True})
        if not room:
            raise CustomHTTPException(404, "Chat room not found")
        
        # Check if user is already a member
        if ObjectId(current_user['_id']) in room['members']:
            raise CustomHTTPException(409, "Already a member of this room")
        
        # Check if room is full
        if len(room['members']) >= room.get('max_members', 100):
            raise CustomHTTPException(409, "Chat room is full")
        
        # Add user to room
        result = db.chat_rooms.update_one(
            {"_id": ObjectId(room_id)},
            {
                "$addToSet": {"members": ObjectId(current_user['_id'])},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        if result.modified_count == 0:
            raise CustomHTTPException(400, "Failed to join room")
        
        logger.info(f"User {current_user_email} joined chat room {room_id}")
        
        return jsonify({
            "message": "Successfully joined chat room",
            "room_id": room_id
        })
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Join chat room error: {e}")
        raise CustomHTTPException(500, "Internal server error")

@chat_bp.route('/rooms/<room_id>/messages', methods=['POST'])
@jwt_required()
def send_message(room_id):
    """Send a message to a chat room"""
    try:
        if not ObjectId.is_valid(room_id):
            raise CustomHTTPException(400, "Invalid room ID format")
        
        current_user_email = get_jwt_identity()
        data = request.get_json()
        
        if not data.get('content'):
            raise CustomHTTPException(400, "Message content is required")
        
        db = get_database()
        
        # Get current user
        current_user = db.users.find_one({"email": current_user_email})
        if not current_user:
            raise CustomHTTPException(404, "User not found")
        
        # Get chat room
        room = db.chat_rooms.find_one({"_id": ObjectId(room_id), "is_active": True})
        if not room:
            raise CustomHTTPException(404, "Chat room not found")
        
        # Check if user is a member
        if ObjectId(current_user['_id']) not in room['members']:
            raise CustomHTTPException(403, "You must be a member to send messages")
        
        # Create message
        message = {
            "room_id": ObjectId(room_id),
            "user_id": ObjectId(current_user['_id']),
            "user_name": current_user['full_name'],
            "content": data['content'],
            "message_type": data.get('message_type', 'text'),
            "is_edited": False,
            "is_deleted": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = db.messages.insert_one(message)
        message['_id'] = str(result.inserted_id)
        message['room_id'] = str(message['room_id'])
        message['user_id'] = str(message['user_id'])
        
        logger.info(f"Message sent to room {room_id} by user {current_user_email}")
        
        return jsonify({
            "message": "Message sent successfully",
            "message_data": message
        }), 201
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Send message error: {e}")
        raise CustomHTTPException(500, "Internal server error")

@chat_bp.route('/rooms/<room_id>/messages', methods=['GET'])
@jwt_required()
def get_messages(room_id):
    """Get messages from a chat room"""
    try:
        if not ObjectId.is_valid(room_id):
            raise CustomHTTPException(400, "Invalid room ID format")
        
        current_user_email = get_jwt_identity()
        db = get_database()
        
        # Get current user
        current_user = db.users.find_one({"email": current_user_email})
        if not current_user:
            raise CustomHTTPException(404, "User not found")
        
        # Get chat room
        room = db.chat_rooms.find_one({"_id": ObjectId(room_id), "is_active": True})
        if not room:
            raise CustomHTTPException(404, "Chat room not found")
        
        # Check if user is a member
        if ObjectId(current_user['_id']) not in room['members']:
            raise CustomHTTPException(403, "You must be a member to view messages")
        
        # Get query parameters
        limit = min(int(request.args.get('limit', 50)), 100)
        before_id = request.args.get('before_id')
        
        # Build filter query
        filter_query = {
            "room_id": ObjectId(room_id),
            "is_deleted": False
        }
        
        if before_id and ObjectId.is_valid(before_id):
            filter_query["_id"] = {"$lt": ObjectId(before_id)}
        
        # Get messages
        messages_cursor = db.messages.find(filter_query).sort("created_at", -1).limit(limit)
        messages = []
        
        for msg in messages_cursor:
            msg['_id'] = str(msg['_id'])
            msg['room_id'] = str(msg['room_id'])
            msg['user_id'] = str(msg['user_id'])
            messages.append(msg)
        
        # Reverse to get chronological order
        messages.reverse()
        
        return jsonify({
            "messages": messages,
            "total_messages": len(messages),
            "room_id": room_id
        })
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Get messages error: {e}")
        raise CustomHTTPException(500, "Internal server error")

@chat_bp.route('/messages/<message_id>', methods=['PUT'])
@jwt_required()
def edit_message(message_id):
    """Edit a message"""
    try:
        if not ObjectId.is_valid(message_id):
            raise CustomHTTPException(400, "Invalid message ID format")
        
        current_user_email = get_jwt_identity()
        data = request.get_json()
        
        if not data.get('content'):
            raise CustomHTTPException(400, "New content is required")
        
        db = get_database()
        
        # Get current user
        current_user = db.users.find_one({"email": current_user_email})
        if not current_user:
            raise CustomHTTPException(404, "User not found")
        
        # Get message
        message = db.messages.find_one({"_id": ObjectId(message_id), "is_deleted": False})
        if not message:
            raise CustomHTTPException(404, "Message not found")
        
        # Check if user owns this message
        if str(message['user_id']) != str(current_user['_id']):
            raise CustomHTTPException(403, "You can only edit your own messages")
        
        # Update message
        result = db.messages.update_one(
            {"_id": ObjectId(message_id)},
            {
                "$set": {
                    "content": data['content'],
                    "is_edited": True,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count == 0:
            raise CustomHTTPException(400, "Failed to update message")
        
        logger.info(f"Message {message_id} edited by user {current_user_email}")
        
        return jsonify({
            "message": "Message updated successfully"
        })
        
    except CustomHTTPException:
        raise
    except Exception as e:
        logger.error(f"Edit message error: {e}")
        raise CustomHTTPException(500, "Internal server error")
