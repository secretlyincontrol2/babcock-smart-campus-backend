"""
Flask Attendance Router - Placeholder
"""

from flask import Blueprint

attendance_bp = Blueprint('attendance', __name__)

@attendance_bp.route('/', methods=['GET'])
def get_attendance():
    return {"message": "Attendance endpoint - coming soon"}
