"""
Flask Users Router - Placeholder
"""

from flask import Blueprint

users_bp = Blueprint('users', __name__)

@users_bp.route('/', methods=['GET'])
def get_users():
    return {"message": "Users endpoint - coming soon"}
