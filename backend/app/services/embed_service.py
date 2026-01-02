"""
Embed management service.

Handles:
- Embed configuration storage and retrieval
- IP anonymization for sensitive embeds
- Embed ID generation
"""

import hashlib
import json
import pathlib
import re
import secrets
import string
from datetime import datetime

from ..config import get_settings

settings = get_settings()

# In-memory cache for embed IP mappings (anonymized_id -> real_ip)
# This allows health checks to work without exposing IPs to the client
_embed_ip_mappings: dict[str, dict[str, str]] = {}


def _project_root() -> pathlib.Path:
    """Get the project root directory."""
    # services -> app -> backend -> repo root
    return pathlib.Path(__file__).resolve().parents[3]


def _embeds_config_path() -> pathlib.Path:
    """Path where all embed configurations are stored."""
    data_dir = pathlib.Path("/app/data")
    if data_dir.exists():
        return data_dir / "embeds.json"
    return _project_root() / "embeds.json"


def generate_embed_id() -> str:
    """Generate a cryptographically secure random embed ID.

    Returns:
        24-character alphanumeric string (~143 bits of entropy)
    """
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(24))


def generate_anonymized_id(ip: str, embed_id: str) -> str:
    """Generate a consistent anonymized ID for an IP within an embed context.

    Args:
        ip: Real IP address
        embed_id: Embed identifier for scoping

    Returns:
        Anonymized device ID (e.g., "device_abc123def456")
    """
    combined = f"{embed_id}:{ip}"
    hash_bytes = hashlib.sha256(combined.encode()).hexdigest()[:12]
    return f"device_{hash_bytes}"


def sanitize_node_ips(node: dict, embed_id: str, ip_mapping: dict[str, str]) -> dict:
    """Recursively sanitize a node tree, replacing real IPs with anonymized IDs.

    Args:
        node: Network node dictionary
        embed_id: Embed identifier for consistent ID generation
        ip_mapping: Dict to populate with reverse lookup (anonymized_id -> real_ip)

    Returns:
        Sanitized copy of the node with IPs replaced
    """
    sanitized = node.copy()

    # Replace IP if present
    if "ip" in sanitized and sanitized["ip"]:
        real_ip = sanitized["ip"]
        anon_id = generate_anonymized_id(real_ip, embed_id)
        ip_mapping[anon_id] = real_ip
        sanitized["ip"] = anon_id

    # Also sanitize the 'id' field if it looks like an IP
    if "id" in sanitized:
        id_val = str(sanitized["id"])
        if _is_ip_address(id_val):
            anon_id = generate_anonymized_id(id_val, embed_id)
            ip_mapping[anon_id] = id_val
            sanitized["id"] = anon_id

    # Sanitize parentId if it looks like an IP
    if "parentId" in sanitized and sanitized["parentId"]:
        parent_id = str(sanitized["parentId"])
        if _is_ip_address(parent_id):
            anon_id = generate_anonymized_id(parent_id, embed_id)
            if anon_id not in ip_mapping:
                ip_mapping[anon_id] = parent_id
            sanitized["parentId"] = anon_id

    # Remove/sanitize hostname if it contains IP-like patterns
    if "hostname" in sanitized and sanitized["hostname"]:
        hostname = sanitized["hostname"]
        if re.search(r"\d+\.\d+\.\d+\.\d+", hostname):
            sanitized["hostname"] = ""

    # Recursively sanitize children
    if "children" in sanitized and sanitized["children"]:
        sanitized["children"] = [
            sanitize_node_ips(child, embed_id, ip_mapping) for child in sanitized["children"]
        ]

    return sanitized


def _is_ip_address(value: str) -> bool:
    """Check if a string looks like an IP address."""
    if not value:
        return False
    parts = value.split(".")
    return len(parts) == 4 and all(part.isdigit() for part in parts if part)


def load_all_embeds() -> dict:
    """Load all embed configurations from storage.

    Returns:
        Dict of embed_id -> embed_config
    """
    embeds_path = _embeds_config_path()
    if not embeds_path.exists():
        return {}
    try:
        with open(embeds_path, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_all_embeds(embeds: dict) -> None:
    """Save all embed configurations to storage.

    Args:
        embeds: Dict of embed_id -> embed_config
    """
    embeds_path = _embeds_config_path()
    with open(embeds_path, "w") as f:
        json.dump(embeds, f, indent=2)


def get_embed(embed_id: str) -> dict | None:
    """Get a single embed configuration.

    Args:
        embed_id: Embed identifier

    Returns:
        Embed config dict or None if not found
    """
    embeds = load_all_embeds()
    return embeds.get(embed_id)


def create_embed(config: dict) -> tuple[str, dict]:
    """Create a new embed configuration.

    Args:
        config: Embed configuration options

    Returns:
        Tuple of (embed_id, embed_config)
    """
    embeds = load_all_embeds()

    # Generate unique ID
    embed_id = generate_embed_id()
    while embed_id in embeds:
        embed_id = generate_embed_id()

    # Create embed config with timestamp
    now = datetime.utcnow().isoformat() + "Z"
    embed_config = {
        "name": config.get("name", "Unnamed Embed"),
        "sensitiveMode": config.get("sensitiveMode", False),
        "showOwner": config.get("showOwner", False),
        "ownerDisplayType": config.get("ownerDisplayType", "fullName"),
        "ownerDisplayName": config.get("ownerDisplayName"),
        "networkId": config.get("networkId"),
        "createdAt": now,
        "updatedAt": now,
    }

    embeds[embed_id] = embed_config
    save_all_embeds(embeds)

    return embed_id, embed_config


def update_embed(embed_id: str, config: dict) -> dict | None:
    """Update an existing embed configuration.

    Args:
        embed_id: Embed identifier
        config: Fields to update

    Returns:
        Updated embed config or None if not found
    """
    embeds = load_all_embeds()

    if embed_id not in embeds:
        return None

    embed_config = embeds[embed_id]

    # Update allowed fields
    for field in ["name", "sensitiveMode", "showOwner", "ownerDisplayType", "ownerDisplayName"]:
        if field in config:
            embed_config[field] = config[field]

    embed_config["updatedAt"] = datetime.utcnow().isoformat() + "Z"

    embeds[embed_id] = embed_config
    save_all_embeds(embeds)

    return embed_config


def delete_embed(embed_id: str) -> bool:
    """Delete an embed configuration.

    Args:
        embed_id: Embed identifier

    Returns:
        True if deleted, False if not found
    """
    global _embed_ip_mappings

    embeds = load_all_embeds()

    if embed_id not in embeds:
        return False

    del embeds[embed_id]
    save_all_embeds(embeds)

    # Clean up IP mapping if exists
    if embed_id in _embed_ip_mappings:
        del _embed_ip_mappings[embed_id]

    return True


def get_ip_mapping(embed_id: str) -> dict[str, str]:
    """Get the IP mapping for an embed.

    Args:
        embed_id: Embed identifier

    Returns:
        Dict of anonymized_id -> real_ip
    """
    return _embed_ip_mappings.get(embed_id, {})


def set_ip_mapping(embed_id: str, mapping: dict[str, str]) -> None:
    """Store the IP mapping for an embed.

    Args:
        embed_id: Embed identifier
        mapping: Dict of anonymized_id -> real_ip
    """
    global _embed_ip_mappings
    _embed_ip_mappings[embed_id] = mapping


def translate_anon_ids_to_ips(embed_id: str, anon_ids: list[str]) -> list[str]:
    """Translate anonymized IDs back to real IPs.

    Args:
        embed_id: Embed identifier
        anon_ids: List of anonymized device IDs

    Returns:
        List of real IP addresses (only those found in mapping)
    """
    ip_mapping = get_ip_mapping(embed_id)
    return [ip_mapping[anon_id] for anon_id in anon_ids if anon_id in ip_mapping]


def anonymize_health_metrics(
    embed_id: str, metrics: dict[str, dict], sensitive_mode: bool
) -> dict[str, dict]:
    """Anonymize health metrics for an embed.

    Args:
        embed_id: Embed identifier
        metrics: Dict of ip -> metrics
        sensitive_mode: Whether to anonymize IPs

    Returns:
        Metrics dict with IPs replaced by anonymized IDs if sensitive
    """
    if not sensitive_mode:
        return metrics

    ip_mapping = get_ip_mapping(embed_id)
    # Create reverse mapping: real_ip -> anon_id
    reverse_mapping = {v: k for k, v in ip_mapping.items()}

    anonymized_metrics = {}
    for ip, metric_data in metrics.items():
        anon_id = reverse_mapping.get(ip)
        if anon_id:
            safe_metrics = dict(metric_data)
            if "ip" in safe_metrics:
                safe_metrics["ip"] = anon_id
            anonymized_metrics[anon_id] = safe_metrics

    return anonymized_metrics
