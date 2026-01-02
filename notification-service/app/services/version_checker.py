"""
Version Checker Service

Periodically checks GitHub for new Cartographer versions and sends
SYSTEM_STATUS notifications to subscribed users when updates are available.
"""

import asyncio
import json
import logging
from datetime import datetime

import httpx

from ..config import settings
from ..models import NetworkEvent, NotificationPriority, NotificationType

logger = logging.getLogger(__name__)

# Configuration
GITHUB_RAW_URL = "https://raw.githubusercontent.com/DevArtech/cartographer/main/VERSION"
CHANGELOG_URL = "https://github.com/DevArtech/cartographer/blob/main/CHANGELOG.md"
CHECK_INTERVAL_SECONDS = 60 * 60  # Check every hour
VERSION_STATE_FILE = settings.data_dir / "version_state.json"


def parse_version(version: str) -> tuple[int, int, int] | None:
    """Parse version string into (major, minor, patch) tuple"""
    import re

    match = re.match(r"^v?(\d+)\.(\d+)\.(\d+)", version.strip())
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def compare_versions(current: str, latest: str) -> tuple[bool, str | None]:
    """
    Compare two versions.

    Returns:
        (has_update, update_type) where update_type is 'major', 'minor', 'patch', or None
    """
    current_parsed = parse_version(current)
    latest_parsed = parse_version(latest)

    if not current_parsed or not latest_parsed:
        return False, None

    if latest_parsed[0] > current_parsed[0]:
        return True, "major"
    if latest_parsed[0] == current_parsed[0] and latest_parsed[1] > current_parsed[1]:
        return True, "minor"
    if (
        latest_parsed[0] == current_parsed[0]
        and latest_parsed[1] == current_parsed[1]
        and latest_parsed[2] > current_parsed[2]
    ):
        return True, "patch"

    return False, None


def get_update_priority(update_type: str | None) -> NotificationPriority:
    """Get notification priority based on update type"""
    if update_type == "major":
        return NotificationPriority.HIGH
    elif update_type == "minor":
        return NotificationPriority.MEDIUM
    else:
        return NotificationPriority.LOW


def get_update_title(update_type: str | None, version: str) -> str:
    """Get notification title based on update type"""
    if update_type == "major":
        return f"🚀 Major Update Available: Cartographer v{version}"
    elif update_type == "minor":
        return f"✨ New Features Available: Cartographer v{version}"
    else:
        return f"🔧 Bug Fixes Available: Cartographer v{version}"


def get_update_message(update_type: str | None, current: str, latest: str) -> str:
    """Get notification message based on update type"""
    base_message = f"A new version of Cartographer is available. You are running v{current}, and v{latest} is now available."

    if update_type == "major":
        return f"{base_message}\n\nThis is a major release with significant new features and improvements. We recommend updating soon."
    elif update_type == "minor":
        return f"{base_message}\n\nThis release includes new features and improvements."
    else:
        return f"{base_message}\n\nThis release includes bug fixes and minor improvements."


class VersionChecker:
    """
    Checks for new Cartographer versions and notifies users.
    """

    def __init__(self):
        self._checker_task: asyncio.Task | None = None
        self._last_notified_version: str | None = None
        self._last_check_time: datetime | None = None
        self._http_client: httpx.AsyncClient | None = None

        # Load previous state
        self._load_state()

    def _load_state(self):
        """Load version checker state from disk"""
        try:
            if VERSION_STATE_FILE.exists():
                with open(VERSION_STATE_FILE, "r") as f:
                    state = json.load(f)
                self._last_notified_version = state.get("last_notified_version")
                last_check = state.get("last_check_time")
                if last_check:
                    self._last_check_time = datetime.fromisoformat(last_check)
                logger.info(f"Loaded version state: last notified={self._last_notified_version}")
        except Exception as e:
            logger.warning(f"Failed to load version state: {e}")

    def _save_state(self):
        """Save version checker state to disk"""
        try:
            settings.data_dir.mkdir(parents=True, exist_ok=True)
            state = {
                "last_notified_version": self._last_notified_version,
                "last_check_time": (
                    self._last_check_time.isoformat() if self._last_check_time else None
                ),
                "current_version": settings.cartographer_version,
            }
            with open(VERSION_STATE_FILE, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save version state: {e}")

    async def start(self):
        """Start the background version checker"""
        if self._checker_task is not None:
            return

        self._http_client = httpx.AsyncClient(timeout=30.0)
        self._checker_task = asyncio.create_task(self._checker_loop())
        logger.info(f"Version checker started (current version: {settings.cartographer_version})")

    async def stop(self):
        """Stop the background version checker"""
        if self._checker_task is not None:
            self._checker_task.cancel()
            try:
                await self._checker_task
            except asyncio.CancelledError:
                pass
            self._checker_task = None

        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

        logger.info("Version checker stopped")

    async def _checker_loop(self):
        """Background loop to periodically check for updates"""
        # Initial delay to let services fully start
        await asyncio.sleep(10)

        while True:
            try:
                await self._check_for_updates()
                await asyncio.sleep(CHECK_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in version checker loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

    async def _fetch_latest_version(self) -> str | None:
        """Fetch the latest version from GitHub"""
        if not self._http_client:
            return None

        try:
            response = await self._http_client.get(GITHUB_RAW_URL)
            response.raise_for_status()
            return response.text.strip()
        except Exception as e:
            logger.warning(f"Failed to fetch latest version from GitHub: {e}")
            return None

    async def _check_for_updates(self):
        """Check for updates and send notifications if needed (called by background loop)"""
        latest_version = await self._fetch_latest_version()
        if not latest_version:
            return

        self._last_check_time = datetime.utcnow()

        # Compare versions
        has_update, update_type = compare_versions(settings.cartographer_version, latest_version)

        if not has_update:
            logger.debug(
                f"No update available (current: {settings.cartographer_version}, latest: {latest_version})"
            )
            self._save_state()
            return

        # Check if we already notified about this version
        if self._last_notified_version == latest_version:
            logger.debug(f"Already notified about version {latest_version}")
            return

        logger.info(
            f"New version available: {latest_version} (current: {settings.cartographer_version}, type: {update_type})"
        )

        # Send the notification using the shared helper
        await self._send_update_notification(latest_version, update_type)

        self._save_state()

    async def check_now(self, send_notification: bool = False, force: bool = False) -> dict:
        """
        Manually trigger a version check.

        Args:
            send_notification: If True and an update is found, send notifications
                             to all networks with SYSTEM_STATUS enabled.
            force: If True, send notifications even if already notified about this version.

        Returns dict with check results.
        """
        # Create a temporary HTTP client if the background checker isn't running
        temp_client = None
        if not self._http_client:
            temp_client = httpx.AsyncClient(timeout=30.0)
            self._http_client = temp_client

        try:
            latest_version = await self._fetch_latest_version()
        finally:
            # Clean up temp client if we created one
            if temp_client:
                await temp_client.aclose()
                self._http_client = None

        if not latest_version:
            return {
                "success": False,
                "error": "Failed to fetch latest version from GitHub",
                "current_version": settings.cartographer_version,
            }

        self._last_check_time = datetime.utcnow()
        has_update, update_type = compare_versions(settings.cartographer_version, latest_version)

        notification_sent = False
        notification_results = None
        skipped_already_notified = False

        # Send notification if requested and there's an update
        if send_notification and has_update:
            # Check if we already notified about this version (unless forcing)
            if not force and self._last_notified_version == latest_version:
                logger.info(
                    f"Already notified about version {latest_version}, skipping notification"
                )
                skipped_already_notified = True
            else:
                notification_results = await self._send_update_notification(
                    latest_version, update_type
                )
                notification_sent = (
                    notification_results is not None and len(notification_results) > 0
                )

        self._save_state()

        result = {
            "success": True,
            "current_version": settings.cartographer_version,
            "latest_version": latest_version,
            "has_update": has_update,
            "update_type": update_type,
            "changelog_url": CHANGELOG_URL if has_update else None,
            "last_notified_version": self._last_notified_version,
            "last_check_time": self._last_check_time.isoformat() if self._last_check_time else None,
        }

        if send_notification:
            result["notification_sent"] = notification_sent
            result["skipped_already_notified"] = skipped_already_notified
            if notification_results:
                result["networks_notified"] = len(notification_results)

        return result

    async def _send_update_notification(self, latest_version: str, update_type: str) -> dict:
        """
        Send version update notification to all subscribed networks.

        Returns dict of network_id -> notification records, or None on failure.
        """
        from .notification_manager import notification_manager

        logger.info(f"Sending version update notification: {latest_version} (type: {update_type})")

        # Create notification event
        event = NetworkEvent(
            event_type=NotificationType.SYSTEM_STATUS,
            priority=get_update_priority(update_type),
            title=get_update_title(update_type, latest_version),
            message=get_update_message(update_type, settings.cartographer_version, latest_version),
            details={
                "update_type": update_type,
                "current_version": settings.cartographer_version,
                "latest_version": latest_version,
                "changelog_url": CHANGELOG_URL,
                "is_version_update": True,
            },
        )

        # Broadcast to all networks with SYSTEM_STATUS notifications enabled
        results = await notification_manager.broadcast_notification(event)

        if results:
            total_networks = len(results)
            total_channels = sum(len(records) for records in results.values())
            logger.info(
                f"Sent version update notification to {total_networks} networks ({total_channels} channels)"
            )
            self._last_notified_version = latest_version
        else:
            logger.warning(
                f"No networks to notify about version update. "
                f"Networks need to have SYSTEM_STATUS in their enabled_notification_types. "
                f"Current enabled networks: {notification_manager.get_all_networks_with_notifications_enabled()}"
            )

        return results

    def get_status(self) -> dict:
        """Get current version checker status"""
        return {
            "current_version": settings.cartographer_version,
            "last_notified_version": self._last_notified_version,
            "last_check_time": self._last_check_time.isoformat() if self._last_check_time else None,
            "check_interval_seconds": CHECK_INTERVAL_SECONDS,
            "is_running": self._checker_task is not None and not self._checker_task.done(),
        }


# Singleton instance
version_checker = VersionChecker()
