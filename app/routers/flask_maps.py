"""
Flask Maps Router - Placeholder
"""

from flask import Blueprint

maps_bp = Blueprint('maps', __name__)

@maps_bp.route('/', methods=['GET'])
def get_maps():
    return {"message": "Maps endpoint - coming soon"}
