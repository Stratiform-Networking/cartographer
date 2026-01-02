"""
Notification proxy sub-routers.

This package contains specialized routers for different notification domains:
- preferences: User and network notification preferences
- discord: Discord integration and OAuth
- broadcast: Broadcast notifications and scheduled messages
- email: Email notifications and testing
"""

from .broadcast import router as broadcast_router
from .discord import router as discord_router
from .email import router as email_router
from .preferences import router as preferences_router

__all__ = [
    "preferences_router",
    "discord_router",
    "broadcast_router",
    "email_router",
]
