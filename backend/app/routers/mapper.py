import os
import pathlib
import re
import subprocess
from typing import Optional
import secrets
import string
import hashlib
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import json

from ..dependencies import (
    AuthenticatedUser,
    require_auth,
    require_write_access,
    require_owner
)
from ..database import get_db
from ..models.network import Network


router = APIRouter()


class MapperResponse(BaseModel):
	content: str
	script_exit_code: int
	network_map_path: Optional[str] = None


def _project_root() -> pathlib.Path:
	# backend/app/routers -> repo root at ../../..
	return pathlib.Path(__file__).resolve().parents[3]


def _script_path() -> pathlib.Path:
	return _project_root() / "lan_mapper.sh"


def _network_map_candidates() -> list[pathlib.Path]:
	root = _project_root()
	return [
		root / "network_map.txt",
		root / "output" / "network_map.txt",
	]


@router.get("/config")
def get_config():
	# Frontend can use this to discover deployment base URL
	app_url = os.environ.get("APPLICATION_URL", "")
	return JSONResponse({"applicationUrl": app_url})


@router.post("/run-mapper", response_model=MapperResponse)
def run_mapper(user: AuthenticatedUser = Depends(require_write_access)) -> MapperResponse:
	"""Run the network mapper script. Requires write access."""
	script = _script_path()
	if not script.exists():
		raise HTTPException(status_code=404, detail=f"lan_mapper.sh not found at {script}")
	if not os.access(script, os.X_OK):
		# Try to run with /bin/bash even if not executable
		cmd = ["/bin/bash", str(script)]
	else:
		cmd = [str(script)]

	try:
		# Run from repo root to keep relative paths consistent
		proc = subprocess.run(
			cmd,
			cwd=str(_project_root()),
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE,
			text=True,
			timeout=300,
		)
	except subprocess.TimeoutExpired:
		raise HTTPException(status_code=504, detail="lan_mapper.sh timed out after 300s")
	except Exception as exc:  # pragma: no cover
		raise HTTPException(status_code=500, detail=f"Failed to run lan_mapper.sh: {exc}")

	# Prefer an actual file artifact if present
	content: Optional[str] = None
	map_path: Optional[str] = None
	for candidate in _network_map_candidates():
		if candidate.exists():
			try:
				content = candidate.read_text()
				map_path = str(candidate)
				break
			except Exception:
				pass

	# Fallback to stdout
	if content is None:
		content = proc.stdout.strip()

	if not content:
		# Provide stderr context for easier debugging
		raise HTTPException(
			status_code=500,
			detail=f"No network_map.txt content produced. stderr: {proc.stderr.strip()}",
		)

	return MapperResponse(
		content=content,
		script_exit_code=proc.returncode,
		network_map_path=map_path,
	)

def _sse_event(event: str, data: str) -> str:
	# Basic SSE formatting; split multi-line payloads
	lines = data.splitlines() or [""]
	chunks = [f"event: {event}"]
	for line in lines:
		chunks.append(f"data: {line}")
	chunks.append("")  # end of message
	return "\n".join(chunks) + "\n"


@router.get("/run-mapper/stream")
def run_mapper_stream(user: AuthenticatedUser = Depends(require_write_access)):
	"""Stream the mapper script output. Requires write access."""
	script = _script_path()
	if not script.exists():
		raise HTTPException(status_code=404, detail=f"lan_mapper.sh not found at {script}")

	def event_gen():
		# Try to execute with bash to avoid exec perm issues
		cmd = ["/bin/bash", str(script)] if not os.access(script, os.X_OK) else [str(script)]
		try:
			proc = subprocess.Popen(
				cmd,
				cwd=str(_project_root()),
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				text=True,
				bufsize=1,
				universal_newlines=True,
			)
		except Exception as exc:
			yield _sse_event("log", f"ERROR: failed to start lan_mapper.sh: {exc}")
			yield _sse_event("done", "exit=-1")
			return

		# Stream stdout
		if proc.stdout:
			for line in proc.stdout:
				yield _sse_event("log", line.rstrip("\n"))
		# Drain stderr afterwards (some scripts only write stderr)
		if proc.stderr:
			for line in proc.stderr:
				stripped = line.rstrip('\n')
				yield _sse_event("log", f"STDERR: {stripped}")

		exit_code = proc.wait()

		# Attempt to read produced file
		result_payload = {"content": "", "script_exit_code": exit_code, "network_map_path": None}
		for candidate in _network_map_candidates():
			if candidate.exists():
				try:
					result_payload["content"] = candidate.read_text()
					result_payload["network_map_path"] = str(candidate)
					break
				except Exception as exc:
					yield _sse_event("log", f"ERROR: could not read {candidate}: {exc}")

		# If no file, try to provide a minimal result from stdout (already streamed)
		if not result_payload["content"]:
			result_payload["content"] = ""

		yield _sse_event("result", json.dumps(result_payload))
		yield _sse_event("done", f"exit={exit_code}")

	return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.get("/download-map")
def download_map(user: AuthenticatedUser = Depends(require_auth)):
	"""Download the network map file. Requires authentication."""
	# Serve the latest produced network_map.txt as a download
	for candidate in _network_map_candidates():
		if candidate.exists():
			filename = candidate.name
			return FileResponse(
				path=str(candidate),
				filename=filename,
				media_type="text/plain",
			)
	raise HTTPException(status_code=404, detail="network_map.txt not found")


def _saved_layout_path() -> pathlib.Path:
	"""Path where the saved network layout JSON is stored"""
	# Use /app/data for Docker volume persistence
	data_dir = pathlib.Path("/app/data")
	if data_dir.exists():
		return data_dir / "saved_network_layout.json"
	# Fallback to project root for local development
	return _project_root() / "saved_network_layout.json"


@router.post("/save-layout")
def save_layout(layout: dict, user: AuthenticatedUser = Depends(require_write_access)):
	"""Save the network layout to the server. Requires write access."""
	try:
		layout_path = _saved_layout_path()
		with open(layout_path, 'w') as f:
			json.dump(layout, f, indent=2)
		return JSONResponse({
			"success": True,
			"message": "Layout saved successfully",
			"path": str(layout_path)
		})
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"Failed to save layout: {exc}")


@router.get("/load-layout")
def load_layout(user: AuthenticatedUser = Depends(require_auth)):
	"""Load the saved network layout from the server. Requires authentication."""
	layout_path = _saved_layout_path()
	if not layout_path.exists():
		return JSONResponse({"exists": False, "layout": None})
	
	try:
		with open(layout_path, 'r') as f:
			layout = json.load(f)
		return JSONResponse({
			"exists": True,
			"layout": layout
		})
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"Failed to load layout: {exc}")


# In-memory cache for embed IP mappings (anonymized_id -> real_ip)
# This allows health checks to work without exposing IPs to the client
_embed_ip_mappings: dict[str, dict[str, str]] = {}


def _generate_anonymized_id(ip: str, embed_id: str) -> str:
	"""Generate a consistent anonymized ID for an IP within an embed context"""
	# Use a hash to create a consistent but non-reversible ID
	# Include embed_id to make IDs unique per embed
	combined = f"{embed_id}:{ip}"
	hash_bytes = hashlib.sha256(combined.encode()).hexdigest()[:12]
	return f"device_{hash_bytes}"


def _sanitize_node_ips(node: dict, embed_id: str, ip_mapping: dict[str, str]) -> dict:
	"""
	Recursively sanitize a node tree, replacing real IPs with anonymized IDs.
	Also populates ip_mapping with reverse lookup (anonymized_id -> real_ip).
	"""
	sanitized = node.copy()
	
	# Replace IP if present
	if "ip" in sanitized and sanitized["ip"]:
		real_ip = sanitized["ip"]
		anon_id = _generate_anonymized_id(real_ip, embed_id)
		ip_mapping[anon_id] = real_ip
		sanitized["ip"] = anon_id
	
	# Also sanitize the 'id' field if it looks like an IP
	if "id" in sanitized:
		id_val = str(sanitized["id"])
		# Check if id looks like an IP address
		if id_val and all(part.isdigit() for part in id_val.split(".") if part) and id_val.count(".") == 3:
			anon_id = _generate_anonymized_id(id_val, embed_id)
			ip_mapping[anon_id] = id_val
			sanitized["id"] = anon_id
	
	# Sanitize parentId if it looks like an IP
	if "parentId" in sanitized and sanitized["parentId"]:
		parent_id = str(sanitized["parentId"])
		if parent_id and all(part.isdigit() for part in parent_id.split(".") if part) and parent_id.count(".") == 3:
			anon_id = _generate_anonymized_id(parent_id, embed_id)
			# Don't overwrite if already mapped
			if anon_id not in ip_mapping:
				ip_mapping[anon_id] = parent_id
			sanitized["parentId"] = anon_id
	
	# Also remove/sanitize hostname if it contains IP-like patterns
	if "hostname" in sanitized and sanitized["hostname"]:
		hostname = sanitized["hostname"]
		# Check if hostname contains IP pattern
		if re.search(r'\d+\.\d+\.\d+\.\d+', hostname):
			sanitized["hostname"] = ""
	
	# Recursively sanitize children
	if "children" in sanitized and sanitized["children"]:
		sanitized["children"] = [
			_sanitize_node_ips(child, embed_id, ip_mapping)
			for child in sanitized["children"]
		]
	
	return sanitized


def _embeds_config_path() -> pathlib.Path:
	"""Path where all embed configurations are stored"""
	data_dir = pathlib.Path("/app/data")
	if data_dir.exists():
		return data_dir / "embeds.json"
	return _project_root() / "embeds.json"


def _generate_embed_id() -> str:
	"""Generate a cryptographically secure random embed ID"""
	# 24 characters from alphanumeric = ~143 bits of entropy
	alphabet = string.ascii_letters + string.digits
	return ''.join(secrets.choice(alphabet) for _ in range(24))


def _load_all_embeds() -> dict:
	"""Load all embed configurations"""
	embeds_path = _embeds_config_path()
	if not embeds_path.exists():
		return {}
	try:
		with open(embeds_path, 'r') as f:
			return json.load(f)
	except Exception:
		return {}


def _save_all_embeds(embeds: dict) -> None:
	"""Save all embed configurations"""
	embeds_path = _embeds_config_path()
	with open(embeds_path, 'w') as f:
		json.dump(embeds, f, indent=2)


@router.get("/embed-data/{embed_id}")
async def get_embed_data(embed_id: str, db: AsyncSession = Depends(get_db)):
	"""Get the network map data for a specific embed (read-only, no auth required)"""
	global _embed_ip_mappings
	
	# Load embed config
	embeds = _load_all_embeds()
	embed_config = embeds.get(embed_id)
	
	if not embed_config:
		raise HTTPException(status_code=404, detail="Embed not found")
	
	network_id = embed_config.get("networkId")
	root = None
	
	# Load the network map - from database if networkId is set, otherwise from file
	if network_id:
		# Load from database (multi-tenant mode)
		try:
			result = await db.execute(select(Network).where(Network.id == network_id))
			network = result.scalar_one_or_none()
			
			if network and network.layout_data:
				layout = network.layout_data
				if isinstance(layout, str):
					layout = json.loads(layout)
				root = layout.get("root")
		except Exception as exc:
			raise HTTPException(status_code=500, detail=f"Failed to load network data: {exc}")
	else:
		# Legacy: load from file
		layout_path = _saved_layout_path()
		if layout_path.exists():
			try:
				with open(layout_path, 'r') as f:
					layout = json.load(f)
				root = layout.get("root")
			except Exception as exc:
				raise HTTPException(status_code=500, detail=f"Failed to load embed data: {exc}")
	
	if not root:
		return JSONResponse({
			"exists": False,
			"root": None,
			"sensitiveMode": False,
			"showOwner": False,
			"ownerDisplayName": None
		})
	
	sensitive_mode = embed_config.get("sensitiveMode", False)
	
	# If sensitive mode is enabled, sanitize all IPs in the response
	if sensitive_mode:
		ip_mapping: dict[str, str] = {}
		root = _sanitize_node_ips(root, embed_id, ip_mapping)
		# Store the mapping for health checks
		_embed_ip_mappings[embed_id] = ip_mapping
	
	return JSONResponse({
		"exists": True,
		"root": root,
		"sensitiveMode": sensitive_mode,
		"showOwner": embed_config.get("showOwner", False),
		"ownerDisplayName": embed_config.get("ownerDisplayName") if embed_config.get("showOwner") else None,
		"name": embed_config.get("name", "Unnamed Embed")
	})


@router.get("/embeds")
def list_embeds(
	user: AuthenticatedUser = Depends(require_auth),
	network_id: Optional[str] = Query(None, description="Filter embeds by network ID (UUID)")
):
	"""List all embed configurations. Requires authentication."""
	embeds = _load_all_embeds()
	# Return list with IDs but without exposing full config details
	embed_list = []
	for embed_id, config in embeds.items():
		# Filter by network_id if provided
		if network_id is not None:
			embed_network_id = config.get("networkId")
			if embed_network_id != network_id:
				continue
		embed_list.append({
			"id": embed_id,
			"name": config.get("name", "Unnamed Embed"),
			"sensitiveMode": config.get("sensitiveMode", False),
			"showOwner": config.get("showOwner", False),
			"ownerDisplayName": config.get("ownerDisplayName"),
			"networkId": config.get("networkId"),
			"createdAt": config.get("createdAt"),
			"updatedAt": config.get("updatedAt")
		})
	# Sort by creation date, newest first
	embed_list.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
	return JSONResponse({"embeds": embed_list})


@router.post("/embeds")
def create_embed(config: dict, user: AuthenticatedUser = Depends(require_write_access)):
	"""Create a new embed configuration. Requires write access."""
	try:
		embeds = _load_all_embeds()
		
		# Generate unique ID
		embed_id = _generate_embed_id()
		while embed_id in embeds:  # Ensure uniqueness
			embed_id = _generate_embed_id()
		
		# Create embed config with timestamp
		now = datetime.utcnow().isoformat() + "Z"
		embed_config = {
			"name": config.get("name", "Unnamed Embed"),
			"sensitiveMode": config.get("sensitiveMode", False),
			"showOwner": config.get("showOwner", False),
			"ownerDisplayType": config.get("ownerDisplayType", "fullName"),
			"ownerDisplayName": config.get("ownerDisplayName"),
			"networkId": config.get("networkId"),  # Store network ID for multi-tenant mode
			"createdAt": now,
			"updatedAt": now
		}
		
		embeds[embed_id] = embed_config
		_save_all_embeds(embeds)
		
		return JSONResponse({
			"success": True,
			"id": embed_id,
			"embed": embed_config
		})
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"Failed to create embed: {exc}")


@router.patch("/embeds/{embed_id}")
def update_embed(embed_id: str, config: dict, user: AuthenticatedUser = Depends(require_write_access)):
	"""Update an existing embed configuration. Requires write access."""
	try:
		embeds = _load_all_embeds()
		
		if embed_id not in embeds:
			raise HTTPException(status_code=404, detail="Embed not found")
		
		# Update fields
		embed_config = embeds[embed_id]
		if "name" in config:
			embed_config["name"] = config["name"]
		if "sensitiveMode" in config:
			embed_config["sensitiveMode"] = config["sensitiveMode"]
		if "showOwner" in config:
			embed_config["showOwner"] = config["showOwner"]
		if "ownerDisplayType" in config:
			embed_config["ownerDisplayType"] = config["ownerDisplayType"]
		if "ownerDisplayName" in config:
			embed_config["ownerDisplayName"] = config["ownerDisplayName"]
		
		embed_config["updatedAt"] = datetime.utcnow().isoformat() + "Z"
		
		embeds[embed_id] = embed_config
		_save_all_embeds(embeds)
		
		return JSONResponse({
			"success": True,
			"id": embed_id,
			"embed": embed_config
		})
	except HTTPException:
		raise
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"Failed to update embed: {exc}")


@router.delete("/embeds/{embed_id}")
def delete_embed(embed_id: str, user: AuthenticatedUser = Depends(require_owner)):
	"""Delete an embed configuration. Requires owner access."""
	global _embed_ip_mappings
	
	try:
		embeds = _load_all_embeds()
		
		if embed_id not in embeds:
			raise HTTPException(status_code=404, detail="Embed not found")
		
		del embeds[embed_id]
		_save_all_embeds(embeds)
		
		# Clean up IP mapping if exists
		if embed_id in _embed_ip_mappings:
			del _embed_ip_mappings[embed_id]
		
		return JSONResponse({"success": True, "message": "Embed deleted"})
	except HTTPException:
		raise
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"Failed to delete embed: {exc}")


# ==================== Embed Health Endpoints ====================
# These endpoints allow embeds to use health monitoring without exposing real IPs

import httpx

# Health service URL - same as health_proxy.py
HEALTH_SERVICE_URL = os.environ.get("HEALTH_SERVICE_URL", "http://localhost:8001")


async def _health_service_request(method: str, path: str, json_body: dict = None, timeout: float = 30.0):
	"""Make a request to the health service"""
	url = f"{HEALTH_SERVICE_URL}/api/health{path}"
	
	async with httpx.AsyncClient(timeout=timeout) as client:
		if method == "GET":
			response = await client.get(url)
		elif method == "POST":
			response = await client.post(url, json=json_body)
		else:
			raise ValueError(f"Unsupported method: {method}")
		
		return response


@router.post("/embed/{embed_id}/health/register")
async def register_embed_health_devices(embed_id: str, request: dict):
	"""
	Register devices for health monitoring using anonymized IDs.
	The backend translates these to real IPs server-side.
	"""
	global _embed_ip_mappings
	
	# Verify embed exists
	embeds = _load_all_embeds()
	if embed_id not in embeds:
		raise HTTPException(status_code=404, detail="Embed not found")
	
	# Get the IP mapping for this embed
	ip_mapping = _embed_ip_mappings.get(embed_id, {})
	
	# Get anonymized IDs from request
	anon_ids = request.get("device_ids", [])
	
	# Translate to real IPs
	real_ips = []
	for anon_id in anon_ids:
		if anon_id in ip_mapping:
			real_ips.append(ip_mapping[anon_id])
	
	if not real_ips:
		return JSONResponse({"message": "No valid devices to register", "count": 0})
	
	# Register with health service
	try:
		response = await _health_service_request(
			"POST",
			"/monitoring/devices",
			json_body={"ips": real_ips},
			timeout=10.0
		)
		response.raise_for_status()
		
		return JSONResponse({
			"message": f"Registered {len(real_ips)} devices for monitoring",
			"count": len(real_ips)
		})
	except httpx.ConnectError:
		raise HTTPException(status_code=503, detail="Health service unavailable")
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"Failed to register devices: {exc}")


@router.post("/embed/{embed_id}/health/check-now")
async def trigger_embed_health_check(embed_id: str):
	"""Trigger an immediate health check for embed devices."""
	# Verify embed exists
	embeds = _load_all_embeds()
	if embed_id not in embeds:
		raise HTTPException(status_code=404, detail="Embed not found")
	
	try:
		response = await _health_service_request(
			"POST",
			"/monitoring/check-now",
			timeout=30.0
		)
		if response.status_code == 400:
			# No devices registered - that's ok
			return JSONResponse({"message": "No devices registered"})
		response.raise_for_status()
		
		return JSONResponse({"message": "Check triggered"})
	except httpx.ConnectError:
		raise HTTPException(status_code=503, detail="Health service unavailable")
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"Failed to trigger check: {exc}")


@router.get("/embed/{embed_id}/health/cached")
async def get_embed_cached_health(embed_id: str):
	"""
	Get cached health metrics for an embed, using anonymized IDs.
	Real IPs are never exposed to the client.
	"""
	global _embed_ip_mappings
	
	# Verify embed exists and check sensitive mode
	embeds = _load_all_embeds()
	embed_config = embeds.get(embed_id)
	if not embed_config:
		raise HTTPException(status_code=404, detail="Embed not found")
	
	sensitive_mode = embed_config.get("sensitiveMode", False)
	
	try:
		response = await _health_service_request(
			"GET",
			"/cached",
			timeout=10.0
		)
		response.raise_for_status()
		all_metrics = response.json()
		
		if not sensitive_mode:
			# Not in sensitive mode - return as-is
			return JSONResponse(all_metrics)
		
		# In sensitive mode - translate IPs to anonymized IDs
		ip_mapping = _embed_ip_mappings.get(embed_id, {})
		# Create reverse mapping: real_ip -> anon_id
		reverse_mapping = {v: k for k, v in ip_mapping.items()}
		
		anonymized_metrics = {}
		for ip, metrics in all_metrics.items():
			anon_id = reverse_mapping.get(ip)
			if anon_id:
				# Create a copy of metrics without the IP field
				safe_metrics = dict(metrics)
				if "ip" in safe_metrics:
					safe_metrics["ip"] = anon_id
				anonymized_metrics[anon_id] = safe_metrics
		
		return JSONResponse(anonymized_metrics)
	except httpx.ConnectError:
		raise HTTPException(status_code=503, detail="Health service unavailable")
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"Failed to get cached health: {exc}")


