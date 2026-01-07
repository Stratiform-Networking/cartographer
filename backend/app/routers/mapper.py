"""
Mapper router - Network mapping and embed management endpoints.
"""

import json

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..database import get_db
from ..dependencies import AuthenticatedUser, require_auth, require_owner, require_write_access
from ..models.network import Network
from ..services import embed_service, health_proxy_service, mapper_runner_service

settings = get_settings()

router = APIRouter()


class MapperResponse(BaseModel):
    """Response from running the mapper script."""

    content: str
    script_exit_code: int
    network_map_path: str | None = None


class EmbedHealthRegisterRequest(BaseModel):
    """Request body for registering embed devices for health monitoring."""

    device_ids: list[str] = []


# ==================== Config Endpoint ====================


@router.get("/config")
def get_config():
    """Frontend can use this to discover deployment base URL."""
    return JSONResponse({"applicationUrl": settings.application_url})


# ==================== Mapper Script Endpoints ====================


@router.post("/run-mapper", response_model=MapperResponse)
def run_mapper(user: AuthenticatedUser = Depends(require_write_access)) -> MapperResponse:
    """Run the network mapper script. Requires write access."""
    try:
        result = mapper_runner_service.run_mapper_sync()
        return MapperResponse(
            content=result.content,
            script_exit_code=result.exit_code,
            network_map_path=result.map_path,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/run-mapper/stream")
def run_mapper_stream(user: AuthenticatedUser = Depends(require_write_access)):
    """Stream the mapper script output. Requires write access."""
    script = mapper_runner_service.script_path()
    if not script.exists():
        raise HTTPException(status_code=404, detail=f"lan_mapper.sh not found at {script}")

    return StreamingResponse(
        mapper_runner_service.run_mapper_streaming(), media_type="text/event-stream"
    )


@router.get("/download-map")
def download_map(user: AuthenticatedUser = Depends(require_auth)):
    """Download the network map file. Requires authentication."""
    map_path = mapper_runner_service.find_network_map()
    if map_path is None:
        raise HTTPException(status_code=404, detail="network_map.txt not found")

    return FileResponse(
        path=str(map_path),
        filename=map_path.name,
        media_type="text/plain",
    )


# ==================== Layout Persistence Endpoints ====================


@router.post("/save-layout")
def save_layout(layout: dict, user: AuthenticatedUser = Depends(require_write_access)):
    """Save the network layout to the server. Requires write access."""
    try:
        path = mapper_runner_service.save_layout(layout)
        return JSONResponse({"success": True, "message": "Layout saved successfully", "path": path})
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/load-layout")
def load_layout(user: AuthenticatedUser = Depends(require_auth)):
    """Load the saved network layout from the server. Requires authentication."""
    try:
        layout = mapper_runner_service.load_layout()
        if layout is None:
            return JSONResponse({"exists": False, "layout": None})
        return JSONResponse({"exists": True, "layout": layout})
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Embed CRUD Endpoints ====================


@router.get("/embed-data/{embed_id}")
async def get_embed_data(embed_id: str, db: AsyncSession = Depends(get_db)):
    """Get the network map data for a specific embed (read-only, no auth required)."""
    embed_config = embed_service.get_embed(embed_id)

    if not embed_config:
        raise HTTPException(status_code=404, detail="Embed not found")

    network_id = embed_config.get("networkId")
    root = None

    # Load the network map - from database if networkId is set, otherwise from file
    if network_id:
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
        try:
            layout = mapper_runner_service.load_layout()
            if layout:
                root = layout.get("root")
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    if not root:
        return JSONResponse(
            {
                "exists": False,
                "root": None,
                "sensitiveMode": False,
                "showOwner": False,
                "ownerDisplayName": None,
            }
        )

    sensitive_mode = embed_config.get("sensitiveMode", False)

    # If sensitive mode is enabled, sanitize all IPs in the response
    if sensitive_mode:
        ip_mapping: dict[str, str] = {}
        root = embed_service.sanitize_node_ips(root, embed_id, ip_mapping)
        embed_service.set_ip_mapping(embed_id, ip_mapping)

    return JSONResponse(
        {
            "exists": True,
            "root": root,
            "sensitiveMode": sensitive_mode,
            "showOwner": embed_config.get("showOwner", False),
            "ownerDisplayName": (
                embed_config.get("ownerDisplayName") if embed_config.get("showOwner") else None
            ),
            "name": embed_config.get("name", "Unnamed Embed"),
        }
    )


@router.get("/embeds")
def list_embeds(
    user: AuthenticatedUser = Depends(require_auth),
    network_id: str | None = Query(None, description="Filter embeds by network ID (UUID)"),
):
    """List all embed configurations. Requires authentication."""
    embeds = embed_service.load_all_embeds()

    embed_list = []
    for eid, config in embeds.items():
        # Filter by network_id if provided
        if network_id is not None:
            embed_network_id = config.get("networkId")
            if embed_network_id != network_id:
                continue
        embed_list.append(
            {
                "id": eid,
                "name": config.get("name", "Unnamed Embed"),
                "sensitiveMode": config.get("sensitiveMode", False),
                "showOwner": config.get("showOwner", False),
                "ownerDisplayName": config.get("ownerDisplayName"),
                "networkId": config.get("networkId"),
                "createdAt": config.get("createdAt"),
                "updatedAt": config.get("updatedAt"),
            }
        )

    # Sort by creation date, newest first
    embed_list.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
    return JSONResponse({"embeds": embed_list})


@router.post("/embeds")
def create_embed(config: dict, user: AuthenticatedUser = Depends(require_write_access)):
    """Create a new embed configuration. Requires write access."""
    try:
        embed_id, embed_config = embed_service.create_embed(config)
        return JSONResponse({"success": True, "id": embed_id, "embed": embed_config})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create embed: {exc}")


@router.patch("/embeds/{embed_id}")
def update_embed(
    embed_id: str, config: dict, user: AuthenticatedUser = Depends(require_write_access)
):
    """Update an existing embed configuration. Requires write access."""
    try:
        embed_config = embed_service.update_embed(embed_id, config)
        if embed_config is None:
            raise HTTPException(status_code=404, detail="Embed not found")
        return JSONResponse({"success": True, "id": embed_id, "embed": embed_config})
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to update embed: {exc}")


@router.delete("/embeds/{embed_id}")
def delete_embed(embed_id: str, user: AuthenticatedUser = Depends(require_owner)):
    """Delete an embed configuration. Requires owner access."""
    try:
        deleted = embed_service.delete_embed(embed_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Embed not found")
        return JSONResponse({"success": True, "message": "Embed deleted"})
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to delete embed: {exc}")


# ==================== Embed Health Endpoints ====================


@router.post("/embed/{embed_id}/health/register")
async def register_embed_health_devices(embed_id: str, request: EmbedHealthRegisterRequest):
    """Register devices for health monitoring using anonymized IDs.

    The backend translates these to real IPs server-side.
    """
    embed_config = embed_service.get_embed(embed_id)
    if not embed_config:
        raise HTTPException(status_code=404, detail="Embed not found")

    # Get anonymized IDs from request and translate to real IPs
    anon_ids = request.device_ids
    real_ips = embed_service.translate_anon_ids_to_ips(embed_id, anon_ids)

    if not real_ips:
        return JSONResponse({"message": "No valid devices to register", "count": 0})

    # Get network_id from embed config for health service registration
    network_id = embed_config.get("networkId") or f"embed-{embed_id}"

    try:
        response = await health_proxy_service.register_devices(real_ips, network_id=network_id)
        response.raise_for_status()

        return JSONResponse(
            {
                "message": f"Registered {len(real_ips)} devices for monitoring",
                "count": len(real_ips),
            }
        )
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Health service unavailable")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to register devices: {exc}")


@router.post("/embed/{embed_id}/health/check-now")
async def trigger_embed_health_check(embed_id: str):
    """Trigger an immediate health check for embed devices."""
    embed_config = embed_service.get_embed(embed_id)
    if not embed_config:
        raise HTTPException(status_code=404, detail="Embed not found")

    try:
        response = await health_proxy_service.trigger_health_check()
        if response.status_code == 400:
            return JSONResponse({"message": "No devices registered"})
        response.raise_for_status()
        return JSONResponse({"message": "Check triggered"})
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Health service unavailable")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to trigger check: {exc}")


@router.get("/embed/{embed_id}/health/cached")
async def get_embed_cached_health(embed_id: str):
    """Get cached health metrics for an embed, using anonymized IDs.

    Real IPs are never exposed to the client.
    """
    embed_config = embed_service.get_embed(embed_id)
    if not embed_config:
        raise HTTPException(status_code=404, detail="Embed not found")

    sensitive_mode = embed_config.get("sensitiveMode", False)

    try:
        all_metrics = await health_proxy_service.get_cached_metrics()

        # Anonymize metrics if in sensitive mode
        result_metrics = embed_service.anonymize_health_metrics(
            embed_id, all_metrics, sensitive_mode
        )

        return JSONResponse(result_metrics)
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Health service unavailable")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to get cached health: {exc}")
