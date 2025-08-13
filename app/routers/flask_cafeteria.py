"""
Flask Cafeteria Router - Placeholder
"""

from flask import Blueprint

cafeteria_bp = Blueprint('cafeteria', __name__)

@cafeteria_bp.route('/', methods=['GET'])
def get_cafeteria():
    return {"message": "Cafeteria endpoint - coming soon"}
