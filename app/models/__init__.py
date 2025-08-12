# MongoDB models - only import what's needed and compatible
from .user import UserModel

# Note: Other models are SQLAlchemy-based and not compatible with MongoDB setup
# They will be imported individually when needed

__all__ = [
    "UserModel"
] 