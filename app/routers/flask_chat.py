"""
Flask Chat Router - Placeholder
"""

from flask import Blueprint

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/', methods=['GET'])
def get_chat():
    return {"message": "Chat endpoint - coming soon"}
