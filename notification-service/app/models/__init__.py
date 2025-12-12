"""
Notification service models package.
Exports both SQLAlchemy database models and Pydantic models.
"""

from .database import (
    UserNetworkNotificationPrefs,
    UserGlobalNotificationPrefs,
    DiscordUserLink,
    NotificationPriorityEnum,
)

# Import Pydantic models from the parent models.py file
# We need to import from the actual module file using importlib
import importlib.util
import os

# Get the path to the parent models.py file
_current_dir = os.path.dirname(__file__)
_parent_dir = os.path.dirname(_current_dir)
_models_py_path = os.path.join(_parent_dir, 'models.py')

# Load the models.py module directly
if os.path.exists(_models_py_path):
    spec = importlib.util.spec_from_file_location("app_models_pydantic", _models_py_path)
    _pydantic_models = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_pydantic_models)
    
    # Explicitly re-export all the Pydantic models and functions we need
    # This avoids exporting internal imports like BaseModel, Field, etc.
    _pydantic_exports = [
        'NotificationChannel', 'NotificationPriority', 'NotificationType',
        'EmailConfig', 'DiscordConfig', 'DiscordDeliveryMethod', 'DiscordChannelConfig',
        'NotificationPreferences', 'NotificationPreferencesUpdate',
        'GlobalUserPreferences', 'GlobalUserPreferencesUpdate',
        'NetworkEvent', 'NotificationRecord',
        'NotificationHistoryResponse', 'NotificationStatsResponse',
        'TestNotificationRequest', 'TestNotificationResponse',
        'DiscordBotInfo', 'DiscordGuild', 'DiscordChannel',
        'DiscordGuildsResponse', 'DiscordChannelsResponse',
        'AnomalyType', 'DeviceBaseline', 'AnomalyDetectionResult',
        'MLModelStatus', 'ScheduledBroadcastStatus', 'ScheduledBroadcast',
        'ScheduledBroadcastCreate', 'ScheduledBroadcastResponse',
        'DiscordOAuthState', 'DiscordUserInfo',
        'DEFAULT_NOTIFICATION_TYPE_PRIORITIES', 'get_default_priority_for_type',
    ]
    
    for attr_name in _pydantic_exports:
        if hasattr(_pydantic_models, attr_name):
            globals()[attr_name] = getattr(_pydantic_models, attr_name)
    
    _pydantic_all = _pydantic_exports
else:
    raise ImportError(f"Could not find models.py at {_models_py_path}")

__all__ = [
    # Database models
    "UserNetworkNotificationPrefs",
    "UserGlobalNotificationPrefs",
    "DiscordUserLink",
    "NotificationPriorityEnum",
] + _pydantic_all
