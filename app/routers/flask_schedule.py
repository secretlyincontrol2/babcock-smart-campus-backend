"""
Flask Schedule Router - Placeholder
"""

from flask import Blueprint

schedule_bp = Blueprint('schedule', __name__)

@schedule_bp.route('/', methods=['GET'])
def get_schedule():
    return {"message": "Schedule endpoint - coming soon"}
