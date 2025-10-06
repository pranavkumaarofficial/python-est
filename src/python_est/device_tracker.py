"""
Device Tracking and Statistics Module

Tracks device connections, certificate issuance, and server statistics.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from threading import Lock

from .models import DeviceInfo, ServerStats

logger = logging.getLogger(__name__)


class DeviceTracker:
    """
    Device tracking and statistics manager.

    Tracks all device interactions, certificate issuance,
    and provides comprehensive server statistics.
    """

    def __init__(self, data_dir: Path = Path("data")):
        """Initialize device tracker."""
        self.data_dir = data_dir
        self.data_dir.mkdir(exist_ok=True)

        self.devices_file = self.data_dir / "devices.json"
        self.stats_file = self.data_dir / "server_stats.json"

        # In-memory tracking
        self._devices: Dict[str, DeviceInfo] = {}
        self._stats = {
            "total_requests": 0,
            "bootstrap_requests": 0,
            "enrollment_requests": 0,
            "failed_requests": 0,
            "certificates_issued": 0,
            "bootstrap_certificates": 0,
            "enrollment_certificates": 0,
            "server_start_time": datetime.utcnow().isoformat()
        }

        # Thread safety
        self._lock = Lock()

        # Load existing data
        self._load_data()

        logger.info("Device tracker initialized")

    def _load_data(self) -> None:
        """Load existing device and statistics data."""
        try:
            # Load devices
            if self.devices_file.exists():
                with open(self.devices_file, 'r') as f:
                    devices_data = json.load(f)
                    for device_id, device_dict in devices_data.items():
                        # Convert datetime strings back to datetime objects
                        if 'bootstrap_time' in device_dict:
                            device_dict['bootstrap_time'] = datetime.fromisoformat(device_dict['bootstrap_time'])
                        if 'enrollment_time' in device_dict and device_dict['enrollment_time']:
                            device_dict['enrollment_time'] = datetime.fromisoformat(device_dict['enrollment_time'])
                        if 'last_activity' in device_dict:
                            device_dict['last_activity'] = datetime.fromisoformat(device_dict['last_activity'])

                        self._devices[device_id] = DeviceInfo(**device_dict)

            # Load stats
            if self.stats_file.exists():
                with open(self.stats_file, 'r') as f:
                    stored_stats = json.load(f)
                    self._stats.update(stored_stats)

        except Exception as e:
            logger.warning(f"Failed to load tracking data: {e}")

    def _save_data(self) -> None:
        """Save device and statistics data to disk."""
        try:
            # Save devices
            devices_data = {}
            for device_id, device in self._devices.items():
                device_dict = device.dict()
                # Convert datetime objects to strings for JSON serialization
                device_dict['bootstrap_time'] = device_dict['bootstrap_time'].isoformat()
                if device_dict['enrollment_time']:
                    device_dict['enrollment_time'] = device_dict['enrollment_time'].isoformat()
                device_dict['last_activity'] = device_dict['last_activity'].isoformat()
                devices_data[device_id] = device_dict

            with open(self.devices_file, 'w') as f:
                json.dump(devices_data, f, indent=2)

            # Save stats
            with open(self.stats_file, 'w') as f:
                json.dump(self._stats, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save tracking data: {e}")

    def track_bootstrap(self, device_id: str, username: str, ip_address: str,
                       user_agent: Optional[str] = None,
                       bootstrap_cert_serial: Optional[str] = None) -> None:
        """Track a bootstrap event. Raises ValueError if device already exists."""
        with self._lock:
            # Check for duplicate device ID
            if device_id in self._devices:
                logger.warning(f"Duplicate bootstrap attempt for device: {device_id}")
                raise ValueError(f"Device '{device_id}' is already registered. Delete the device first to re-enroll.")

            device = DeviceInfo(
                device_id=device_id,
                username=username,
                ip_address=ip_address,
                user_agent=user_agent,
                bootstrap_cert_serial=bootstrap_cert_serial,
                status="bootstrap_only"
            )

            self._devices[device_id] = device
            self._stats["bootstrap_requests"] += 1
            self._stats["total_requests"] += 1
            self._stats["bootstrap_certificates"] += 1
            self._stats["certificates_issued"] += 1

            self._save_data()
            logger.info(f"Tracked bootstrap for device: {device_id}")

    def track_enrollment(self, device_id: str, enrolled_cert_serial: str) -> None:
        """Track an enrollment event for an existing device."""
        with self._lock:
            if device_id in self._devices:
                device = self._devices[device_id]
                device.enrollment_time = datetime.utcnow()
                device.enrolled_cert_serial = enrolled_cert_serial
                device.status = "enrolled"
                device.last_activity = datetime.utcnow()

                self._stats["enrollment_requests"] += 1
                self._stats["total_requests"] += 1
                self._stats["enrollment_certificates"] += 1
                self._stats["certificates_issued"] += 1

                self._save_data()
                logger.info(f"Tracked enrollment for device: {device_id}")

    def track_request(self, request_type: str, success: bool = True) -> None:
        """Track a general request."""
        with self._lock:
            self._stats["total_requests"] += 1
            if not success:
                self._stats["failed_requests"] += 1
            self._save_data()

    def get_device_info(self, device_id: str) -> Optional[DeviceInfo]:
        """Get information about a specific device."""
        return self._devices.get(device_id)

    def get_all_devices(self) -> List[DeviceInfo]:
        """Get information about all tracked devices."""
        return list(self._devices.values())

    def get_recent_devices(self, hours: int = 24) -> List[DeviceInfo]:
        """Get devices that were active in the last N hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return [
            device for device in self._devices.values()
            if device.last_activity > cutoff
        ]

    def get_server_stats(self) -> ServerStats:
        """Get comprehensive server statistics."""
        with self._lock:
            now = datetime.utcnow()
            start_time = datetime.fromisoformat(self._stats["server_start_time"])
            uptime = str(now - start_time).split('.')[0]  # Remove microseconds

            recent_devices = self.get_recent_devices(24)

            stats = ServerStats(
                uptime=uptime,
                total_devices=len(self._devices),
                enrolled_devices=len([d for d in self._devices.values() if d.status == "enrolled"]),
                active_devices=len(recent_devices),
                certificates_issued=self._stats["certificates_issued"],
                bootstrap_certificates=self._stats["bootstrap_certificates"],
                enrollment_certificates=self._stats["enrollment_certificates"],
                total_requests=self._stats["total_requests"],
                bootstrap_requests=self._stats["bootstrap_requests"],
                enrollment_requests=self._stats["enrollment_requests"],
                failed_requests=self._stats["failed_requests"],
                recent_devices=recent_devices[-10:]  # Last 10 devices
            )

            return stats

    def get_device_by_ip(self, ip_address: str) -> List[DeviceInfo]:
        """Get all devices from a specific IP address."""
        return [
            device for device in self._devices.values()
            if device.ip_address == ip_address
        ]

    def delete_device(self, device_id: str) -> bool:
        """
        Delete a device from tracking.

        Args:
            device_id: Device identifier to delete

        Returns:
            True if device was deleted, False if not found
        """
        with self._lock:
            if device_id not in self._devices:
                logger.warning(f"Attempted to delete non-existent device: {device_id}")
                return False

            del self._devices[device_id]
            self._save_data()
            logger.info(f"Deleted device: {device_id}")
            return True

    def cleanup_old_devices(self, days: int = 30) -> int:
        """Remove device records older than specified days."""
        with self._lock:
            cutoff = datetime.utcnow() - timedelta(days=days)
            old_devices = [
                device_id for device_id, device in self._devices.items()
                if device.last_activity < cutoff
            ]

            for device_id in old_devices:
                del self._devices[device_id]

            if old_devices:
                self._save_data()
                logger.info(f"Cleaned up {len(old_devices)} old device records")

            return len(old_devices)

    def get_stats_summary(self) -> Dict:
        """Get a quick stats summary for logging."""
        return {
            "total_devices": len(self._devices),
            "enrolled_devices": len([d for d in self._devices.values() if d.status == "enrolled"]),
            "total_requests": self._stats["total_requests"],
            "certificates_issued": self._stats["certificates_issued"]
        }